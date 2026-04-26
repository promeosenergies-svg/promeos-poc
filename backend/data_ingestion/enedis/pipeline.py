"""PROMEOS — Enedis multi-flux ingestion pipeline.

Orchestrates: classify → hash check → decrypt → parse → store.
Supports R4x (CDC C1-C4), R171 (index C2-C4), R50 (CDC C5), R151 (index C5).

Idempotence:
  - File-level: SHA256 of the raw ciphertext. Same .zip = skip.
  - Republication detection: same filename + different hash = versioned
    republication (status needs_review, version 2+, supersedes_file_id chain).
    Both original and republication data are preserved.
  - No measure-level deduplication: deferred to a future staging layer.

Usage:
    from data_ingestion.enedis.pipeline import ingest_file, ingest_directory
    from data_ingestion.enedis.decrypt import load_keys_from_env

    keys = load_keys_from_env()
    session = SessionLocal()

    # Single file
    status = ingest_file(Path("flux.zip"), session, keys)

    # Whole directory (scan → register RECEIVED → process)
    counters = ingest_directory(Path("flux_enedis/C1-C4"), session, keys)
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import func, insert
from sqlalchemy.orm import Session

from data_ingestion.enedis.decrypt import (
    SKIP_FLUX_TYPES,
    DecryptError,
    classify_flux,
    decrypt_file,
)
from data_ingestion.enedis.containers import ContainerError, extract_c68_payloads, extract_r6x_payload
from data_ingestion.enedis.config import MAX_RETRIES
from data_ingestion.enedis.enums import FluxStatus, FluxType, IngestionRunStatus
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxFileError,
    EnedisFluxIndexR64,
    EnedisFluxItcC68,
    EnedisFluxMesureR63,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
    IngestionRun,
)
from data_ingestion.enedis.parsers.c68 import C68ParseError, parse_c68_payload
from data_ingestion.enedis.parsers.r63 import R63ParseError, parse_r63_payload
from data_ingestion.enedis.parsers.r4 import R4xParseError, parse_r4x
from data_ingestion.enedis.parsers.r50 import R50ParseError, parse_r50
from data_ingestion.enedis.parsers.r151 import R151ParseError, parse_r151
from data_ingestion.enedis.parsers.r171 import R171ParseError, parse_r171
from data_ingestion.enedis.parsers.r64 import R64ParseError, parse_r64_payload
from data_ingestion.enedis.transport import TransportError, resolve_payload

logger = logging.getLogger("promeos.enedis.pipeline")

_R4X_FLUX_TYPES = frozenset({FluxType.R4H, FluxType.R4M, FluxType.R4Q})

DEFAULT_CHUNK_SIZE = 1000


def ingest_file(
    file_path: Path,
    session: Session,
    keys: list[tuple[bytes, bytes]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    archive_dir: Path | None = None,
    file_hash: str | None = None,
) -> FluxStatus:
    """Ingest one Enedis flux file: decrypt → parse → store in DB.

    Commits the session on success, on recorded error/skip, and when
    archiving error history before a retry or PERMANENTLY_FAILED transition.
    The caller should NOT commit separately.

    Args:
        file_path: Path to the encrypted .zip file.
        session: SQLAlchemy session.
        keys: Decryption key/IV pairs from load_keys_from_env().
        chunk_size: Number of mesure rows per batch insert.
        archive_dir: Optional directory to write decrypted XML for audit.
        file_hash: Pre-computed SHA256 hash (avoids re-reading the file).

    Returns:
        FluxStatus indicating the outcome.

    Raises:
        FileNotFoundError: file_path does not exist.
        MissingKeyError: no decryption keys available (from decrypt module).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Flux file not found: {file_path}")

    filename = file_path.name
    flux_type = classify_flux(filename)

    # Use pre-computed hash if available, otherwise compute
    if file_hash is None:
        file_hash = _hash_file(file_path)

    # Idempotence check — applies to all flux types
    # pre_registered tracks a RECEIVED record to update in-place
    pre_registered: EnedisFluxFile | None = None

    existing = session.query(EnedisFluxFile).filter_by(file_hash=file_hash).first()
    if existing is not None:
        if existing.status in (
            FluxStatus.PARSED,
            FluxStatus.SKIPPED,
            FluxStatus.NEEDS_REVIEW,
            FluxStatus.PERMANENTLY_FAILED,
        ):
            logger.info(
                "Already processed %s (hash=%s…, status=%s), skipping", filename, file_hash[:12], existing.status
            )
            return FluxStatus(existing.status)
        if existing.status == FluxStatus.ERROR:
            error_count = session.query(func.count(EnedisFluxFileError.id)).filter_by(flux_file_id=existing.id).scalar()
            if error_count >= MAX_RETRIES:
                _archive_error(session, existing)
                existing.status = FluxStatus.PERMANENTLY_FAILED
                existing.error_message = None
                session.commit()
                logger.info("File %s reached MAX_RETRIES — marked PERMANENTLY_FAILED", filename)
                return FluxStatus.PERMANENTLY_FAILED
            logger.info("Retrying previously failed %s (hash=%s…)", filename, file_hash[:12])
            _archive_error(session, existing)
            existing.error_message = None
            session.commit()  # persist error history before retry attempt
            pre_registered = existing  # reuse same record in-place
        elif existing.status == FluxStatus.RECEIVED:
            logger.info("Processing pre-registered %s (hash=%s…)", filename, file_hash[:12])
            pre_registered = existing

    # Skip non-decryptable flux types
    if flux_type in SKIP_FLUX_TYPES:
        logger.info("Skipping %s (flux type %s)", filename, flux_type.value)
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.SKIPPED, existing=pre_registered)
        session.commit()
        return FluxStatus.SKIPPED

    # SF5 direct/encrypted ZIP flows use transport + container handlers, not
    # the legacy decrypt-to-XML dispatch table.
    if flux_type in {FluxType.R63, FluxType.R64}:
        previous_file = (
            session.query(EnedisFluxFile)
            .filter(
                EnedisFluxFile.filename == filename,
                EnedisFluxFile.status.in_([FluxStatus.PARSED, FluxStatus.NEEDS_REVIEW]),
            )
            .order_by(EnedisFluxFile.version.desc())
            .first()
        )
        return _ingest_r6x_file(
            file_path,
            session,
            keys,
            chunk_size,
            file_hash,
            flux_type,
            pre_registered,
            previous_file,
        )

    if flux_type == FluxType.C68:
        previous_file = (
            session.query(EnedisFluxFile)
            .filter(
                EnedisFluxFile.filename == filename,
                EnedisFluxFile.status.in_([FluxStatus.PARSED, FluxStatus.NEEDS_REVIEW]),
            )
            .order_by(EnedisFluxFile.version.desc())
            .first()
        )
        return _ingest_c68_file(
            file_path,
            session,
            keys,
            chunk_size,
            file_hash,
            pre_registered,
            previous_file,
        )

    # Dispatch lookup — skip flux types without a handler
    handler = _DISPATCH.get(flux_type)
    if handler is None:
        logger.info("Skipping %s (flux type %s not yet supported)", filename, flux_type.value)
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.SKIPPED, existing=pre_registered)
        session.commit()
        return FluxStatus.SKIPPED

    parser_fn, parse_error_cls, store_fn = handler

    # Republication detection — same filename, different hash, already ingested
    previous_file = (
        session.query(EnedisFluxFile)
        .filter(
            EnedisFluxFile.filename == filename,
            EnedisFluxFile.status.in_([FluxStatus.PARSED, FluxStatus.NEEDS_REVIEW]),
        )
        .order_by(EnedisFluxFile.version.desc())
        .first()
    )
    is_republication = previous_file is not None

    # Decrypt
    try:
        xml_bytes = decrypt_file(file_path, keys, archive_dir)
    except DecryptError as exc:
        logger.error("Decrypt failed for %s: %s", filename, exc)
        _record_file(
            session,
            filename,
            file_hash,
            flux_type.value,
            FluxStatus.ERROR,
            str(exc),
            existing=pre_registered,
        )
        session.commit()
        return FluxStatus.ERROR

    # Parse
    try:
        parsed = parser_fn(xml_bytes)
    except parse_error_cls as exc:
        logger.error("Parse failed for %s: %s", filename, exc)
        _record_file(
            session,
            filename,
            file_hash,
            flux_type.value,
            FluxStatus.ERROR,
            str(exc),
            existing=pre_registered,
        )
        session.commit()
        return FluxStatus.ERROR

    # Store file record + mesures
    try:
        if is_republication:
            file_status = FluxStatus.NEEDS_REVIEW
            file_version = previous_file.version + 1
            supersedes_id = previous_file.id
            logger.warning(
                "Republication detected for %s: v%d supersedes file id=%d (v%d). Status set to needs_review.",
                filename,
                file_version,
                previous_file.id,
                previous_file.version,
            )
        else:
            file_status = FluxStatus.PARSED
            file_version = 1
            supersedes_id = None

        flux_file = _create_flux_file(
            filename,
            file_hash,
            flux_type,
            file_status,
            file_version,
            supersedes_id,
            parsed,
            existing=pre_registered,
        )
        if pre_registered is None:
            session.add(flux_file)
        session.flush()  # Get flux_file.id

        total_inserted = store_fn(parsed, flux_file, session, chunk_size)
        flux_file.measures_count = total_inserted
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("DB storage failed for %s: %s", filename, exc)
        # After rollback, objects are detached — re-fetch the pre-registered
        # record if it exists so the update actually persists.
        refetched = (
            session.query(EnedisFluxFile).filter_by(file_hash=file_hash).first() if pre_registered is not None else None
        )
        _record_file(
            session,
            filename,
            file_hash,
            flux_type.value,
            FluxStatus.ERROR,
            str(exc),
            existing=refetched,
        )
        session.commit()
        return FluxStatus.ERROR

    logger.info(
        "Ingested %s: %d mesures from %s [%s] (v%d%s)",
        filename,
        total_inserted,
        _prm_summary(parsed),
        flux_type.value,
        file_version,
        ", needs_review" if is_republication else "",
    )
    return file_status


def ingest_directory(
    directory: Path,
    session: Session,
    keys: list[tuple[bytes, bytes]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    archive_dir: Path | None = None,
    recursive: bool = False,
    pattern: str = "*.zip",
    *,
    dry_run: bool = False,
    run: IngestionRun | None = None,
) -> dict[str, int]:
    """Ingest all flux files in a directory: scan → register → process.

    Two-phase design for crash recovery:
      Phase 1: scan directory, register new files as RECEIVED, queue ERROR
        files for retry, transition max-retried files to PERMANENTLY_FAILED.
      Phase 2: process each RECEIVED/ERROR file via ingest_file().
    Files left in RECEIVED after a crash are re-processed on the next run.

    Args:
        directory: Path to the directory containing encrypted .zip files.
        session: SQLAlchemy session.
        keys: Decryption key/IV pairs from load_keys_from_env().
        chunk_size: Number of mesure rows per batch insert.
        archive_dir: Optional directory to write decrypted XML for audit.
        recursive: If True, scan subdirectories recursively.
        pattern: Glob pattern for file matching (default ``*.zip``).
        dry_run: If True, scan and classify without ingesting (no DB mutations).
        run: Optional IngestionRun for incremental counter updates.

    Returns:
        Dict of counters: received (new + stale RECEIVED files), parsed, needs_review,
        skipped, error, permanently_failed, already_processed, retried,
        max_retries_reached.
        ``received + retried == parsed + needs_review + skipped + error``
        (in non-dry-run mode).  ``permanently_failed`` counts files
        transitioned to PERMANENTLY_FAILED during this run (Phase 1).
    """
    counters: dict[str, int] = {
        "received": 0,
        "parsed": 0,
        "needs_review": 0,
        "skipped": 0,
        "error": 0,
        "permanently_failed": 0,
        "already_processed": 0,
        "retried": 0,
        "max_retries_reached": 0,
    }

    if not directory.is_dir():
        logger.warning("ingest_directory: %s is not a directory", directory)
        return counters

    # Phase 1 — Scan & register as RECEIVED
    glob_fn = directory.rglob if recursive else directory.glob
    zip_files = sorted(p for p in glob_fn(pattern) if p.is_file())

    # (file_path, file_hash, flux_file) — hash is kept to avoid re-reading
    # the file in the Phase 2 exception handler.
    to_process: list[tuple[Path, str, EnedisFluxFile]] = []

    for file_path in zip_files:
        file_hash = _hash_file(file_path)
        existing = session.query(EnedisFluxFile).filter_by(file_hash=file_hash).first()

        if existing is not None:
            if existing.status == FluxStatus.RECEIVED:
                # Stale from a previous interrupted run — re-process
                logger.info("Found stale RECEIVED %s, will re-process", file_path.name)
                to_process.append((file_path, file_hash, existing))
                counters["received"] += 1
            elif existing.status == FluxStatus.NEEDS_REVIEW:
                # Data loaded, awaiting human review (republication) — no retry
                counters["already_processed"] += 1
            elif existing.status == FluxStatus.PERMANENTLY_FAILED:
                # Max retries reached — skip, needs manual intervention
                counters["max_retries_reached"] += 1
            elif existing.status == FluxStatus.ERROR:
                error_count = (
                    session.query(func.count(EnedisFluxFileError.id)).filter_by(flux_file_id=existing.id).scalar()
                )
                if error_count < MAX_RETRIES:
                    logger.info("Retrying ERROR file %s (attempt %d/%d)", file_path.name, error_count + 1, MAX_RETRIES)
                    to_process.append((file_path, file_hash, existing))
                    counters["retried"] += 1
                else:
                    # Transition to PERMANENTLY_FAILED (skip in dry-run)
                    if not dry_run:
                        _archive_error(session, existing)
                        existing.status = FluxStatus.PERMANENTLY_FAILED
                        existing.error_message = None
                        session.commit()
                    logger.info(
                        "File %s reached MAX_RETRIES (%d) — %s",
                        file_path.name,
                        MAX_RETRIES,
                        "marked PERMANENTLY_FAILED" if not dry_run else "would mark PERMANENTLY_FAILED (dry-run)",
                    )
                    counters["max_retries_reached"] += 1
                    counters["permanently_failed"] += 1
            else:
                # PARSED, SKIPPED
                counters["already_processed"] += 1
            continue

        # New file — register as RECEIVED
        if not dry_run:
            flux_file = EnedisFluxFile(
                filename=file_path.name,
                file_hash=file_hash,
                flux_type=classify_flux(file_path.name).value,
                status=FluxStatus.RECEIVED,
                measures_count=0,
            )
            session.add(flux_file)
            to_process.append((file_path, file_hash, flux_file))
        else:
            to_process.append((file_path, file_hash, None))
        counters["received"] += 1

    if to_process and not dry_run:
        session.commit()  # Single commit for all RECEIVED registrations

    # Update run scan counters after Phase 1
    if run:
        run.files_received = counters["received"]
        run.files_already_processed = counters["already_processed"]
        run.files_retried = counters["retried"]
        run.files_max_retries = counters["max_retries_reached"]
        session.commit()

    logger.info(
        "ingest_directory: %d files to process, %d already processed",
        len(to_process),
        counters["already_processed"],
    )

    # Phase 2 — Process each RECEIVED file (skipped entirely in dry-run)
    if not dry_run:
        for file_path, phase1_hash, flux_file in to_process:
            try:
                status = ingest_file(file_path, session, keys, chunk_size, archive_dir, file_hash=phase1_hash)
            except Exception as exc:
                # ingest_file raises FileNotFoundError/MissingKeyError without recording;
                # update the RECEIVED record to ERROR so it doesn't stay stale.
                logger.error("Unhandled error processing %s: %s", file_path.name, exc)
                # Use Phase 1 hash — the file may no longer exist on disk.
                record = session.query(EnedisFluxFile).filter_by(file_hash=phase1_hash).first()
                if record is not None and record.status == FluxStatus.RECEIVED:
                    record.status = FluxStatus.ERROR
                    record.error_message = str(exc)
                    session.commit()
                status = FluxStatus.ERROR

            counters[status.value] += 1

            # Incremental run counter update after each file
            if run:
                if status == FluxStatus.PARSED:
                    run.files_parsed += 1
                elif status == FluxStatus.ERROR:
                    run.files_error += 1
                elif status == FluxStatus.SKIPPED:
                    run.files_skipped += 1
                elif status == FluxStatus.NEEDS_REVIEW:
                    run.files_needs_review += 1
                elif status == FluxStatus.PERMANENTLY_FAILED:
                    run.files_max_retries += 1
                session.commit()

    if run:
        run.status = IngestionRunStatus.COMPLETED
        run.finished_at = datetime.now(timezone.utc)
        session.commit()

    return counters


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _hash_file(file_path: Path) -> str:
    """SHA256 hash of file contents (raw ciphertext)."""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def _archive_error(session: Session, flux_file: EnedisFluxFile) -> None:
    """Archive the current error_message into EnedisFluxFileError before retry.

    No-op if error_message is empty or None.
    """
    if flux_file.error_message:
        session.add(
            EnedisFluxFileError(
                flux_file_id=flux_file.id,
                error_message=flux_file.error_message,
            )
        )
        session.flush()


def _record_file(
    session: Session,
    filename: str,
    file_hash: str,
    flux_type: str,
    status: FluxStatus,
    error_message: str | None = None,
    existing: EnedisFluxFile | None = None,
) -> EnedisFluxFile:
    """Create or update a minimal EnedisFluxFile record for skipped/error files.

    If *existing* is provided (pre-registered RECEIVED or ERROR record being
    retried), updates it in-place instead of creating a new row.
    """
    if existing is not None:
        existing.status = status
        existing.error_message = error_message
        existing.measures_count = 0
        return existing
    flux_file = EnedisFluxFile(
        filename=filename,
        file_hash=file_hash,
        flux_type=flux_type,
        status=status,
        error_message=error_message,
        measures_count=0,
    )
    session.add(flux_file)
    return flux_file


def _create_flux_file(
    filename: str,
    file_hash: str,
    flux_type: FluxType,
    status: FluxStatus,
    version: int,
    supersedes_id: int | None,
    parsed: Any,
    existing: EnedisFluxFile | None = None,
) -> EnedisFluxFile:
    """Create or update an EnedisFluxFile ORM object with header fields.

    If *existing* is provided (pre-registered RECEIVED record), updates it
    in-place instead of creating a new row — preserving id and created_at.

    R4x-specific columns (frequence_publication, nature_courbe_demandee,
    identifiant_destinataire) are populated only for R4x flux types.
    header_raw is always set from parsed.header.raw.
    """
    # R4x headers expose promoted queryable fields; others do not
    if flux_type in _R4X_FLUX_TYPES:
        freq = parsed.header.frequence_publication
        nature = parsed.header.nature_courbe_demandee
        dest = parsed.header.identifiant_destinataire
    else:
        freq = None
        nature = None
        dest = None

    if existing is not None:
        existing.status = status
        existing.version = version
        existing.supersedes_file_id = supersedes_id
        existing.frequence_publication = freq
        existing.nature_courbe_demandee = nature
        existing.identifiant_destinataire = dest
        existing.set_header_raw(parsed.header.raw)
        return existing

    flux_file = EnedisFluxFile(
        filename=filename,
        file_hash=file_hash,
        flux_type=flux_type.value,
        status=status,
        version=version,
        supersedes_file_id=supersedes_id,
        frequence_publication=freq,
        nature_courbe_demandee=nature,
        identifiant_destinataire=dest,
    )
    flux_file.set_header_raw(parsed.header.raw)
    return flux_file


def _create_sf5_flux_file(
    filename: str,
    file_hash: str,
    flux_type: FluxType,
    status: FluxStatus,
    version: int,
    supersedes_id: int | None,
    container_payload: Any,
    parsed: Any,
    existing: EnedisFluxFile | None = None,
) -> EnedisFluxFile:
    outer_meta = container_payload.outer_metadata
    header_raw = {
        "source": "filename+archive",
        "filename_metadata": {
            "code_flux": outer_meta.code_flux,
            "mode_publication": outer_meta.mode_publication,
            "type_donnee": outer_meta.type_donnee,
            "id_demande": outer_meta.id_demande,
            "num_sequence": outer_meta.num_sequence,
            "publication_horodatage": outer_meta.publication_horodatage,
            "siren_publication": outer_meta.siren_publication,
            "code_contrat_publication": outer_meta.code_contrat_publication,
            "extension": outer_meta.extension,
        },
        "archive_manifest": {
            "outer_member_count": container_payload.archive_members_count,
            "payload_member_name": container_payload.member_name,
            "payload_format": container_payload.payload_format,
        },
        "payload_header": parsed.header.raw,
        "warnings": parsed.header.raw.get("warnings", []),
    }

    target = existing or EnedisFluxFile(filename=filename, file_hash=file_hash, flux_type=flux_type.value)
    target.status = status
    target.version = version
    target.supersedes_file_id = supersedes_id
    target.code_flux = outer_meta.code_flux
    target.mode_publication = outer_meta.mode_publication
    target.type_donnee = outer_meta.type_donnee
    target.id_demande = outer_meta.id_demande
    target.payload_format = container_payload.payload_format
    target.num_sequence = outer_meta.num_sequence
    target.siren_publication = outer_meta.siren_publication
    target.code_contrat_publication = outer_meta.code_contrat_publication
    target.publication_horodatage = outer_meta.publication_horodatage
    target.archive_members_count = container_payload.archive_members_count
    target.frequence_publication = None
    target.nature_courbe_demandee = None
    target.identifiant_destinataire = None
    target.set_header_raw(header_raw)
    return target


def _create_c68_flux_file(
    filename: str,
    file_hash: str,
    status: FluxStatus,
    version: int,
    supersedes_id: int | None,
    archive_payload: Any,
    parsed_payloads: list[Any],
    existing: EnedisFluxFile | None = None,
) -> EnedisFluxFile:
    primary_meta = archive_payload.primary_metadata
    secondary_archives = []
    warnings = []
    for payload, parsed in zip(archive_payload.payloads, parsed_payloads):
        row_warnings = list(parsed.warnings)
        warnings.extend(row_warnings)
        secondary_archives.append(
            {
                "name": payload.secondary_archive_name,
                "payload_member_name": payload.payload_member_name,
                "payload_format": payload.payload_format,
                "row_count": parsed.total_prms,
                "warnings": row_warnings,
            }
        )

    header_raw = {
        "source": "filename+archive",
        "filename_metadata": {
            "code_flux": primary_meta.code_flux,
            "mode_publication": primary_meta.mode_publication,
            "type_donnee": primary_meta.type_donnee,
            "id_demande": primary_meta.id_demande,
            "num_sequence": primary_meta.num_sequence,
            "publication_horodatage": primary_meta.publication_horodatage,
            "extension": primary_meta.extension,
        },
        "archive_manifest": {
            "primary_archive_name": filename,
            "outer_member_count": archive_payload.archive_members_count,
            "secondary_archives": secondary_archives,
        },
        "payload_header": None,
        "warnings": warnings,
    }

    target = existing or EnedisFluxFile(filename=filename, file_hash=file_hash, flux_type=FluxType.C68.value)
    target.status = status
    target.version = version
    target.supersedes_file_id = supersedes_id
    target.code_flux = primary_meta.code_flux
    target.mode_publication = primary_meta.mode_publication
    target.type_donnee = primary_meta.type_donnee
    target.id_demande = primary_meta.id_demande
    target.payload_format = archive_payload.payloads[0].payload_format if archive_payload.payloads else None
    target.num_sequence = primary_meta.num_sequence
    target.siren_publication = primary_meta.siren_publication
    target.code_contrat_publication = primary_meta.code_contrat_publication
    target.publication_horodatage = primary_meta.publication_horodatage
    target.archive_members_count = archive_payload.archive_members_count
    target.frequence_publication = None
    target.nature_courbe_demandee = None
    target.identifiant_destinataire = None
    target.set_header_raw(header_raw)
    return target


def _ingest_c68_file(
    file_path: Path,
    session: Session,
    keys: list[tuple[bytes, bytes]],
    chunk_size: int,
    file_hash: str,
    pre_registered: EnedisFluxFile | None,
    previous_file: EnedisFluxFile | None,
) -> FluxStatus:
    filename = file_path.name
    try:
        resolved = resolve_payload(file_path, "zip", keys=keys or None)
        archive_payload = extract_c68_payloads(filename, resolved.payload_bytes)
        parsed_payloads = [
            parse_c68_payload(payload.payload_bytes, payload.payload_format, payload.payload_member_name)
            for payload in archive_payload.payloads
        ]
    except (TransportError, ContainerError, C68ParseError) as exc:
        logger.error("SF5 C68 ingest failed for %s: %s", filename, exc)
        _record_file(
            session, filename, file_hash, FluxType.C68.value, FluxStatus.ERROR, str(exc), existing=pre_registered
        )
        session.commit()
        return FluxStatus.ERROR

    try:
        if previous_file is not None:
            file_status = FluxStatus.NEEDS_REVIEW
            file_version = previous_file.version + 1
            supersedes_id = previous_file.id
        else:
            file_status = FluxStatus.PARSED
            file_version = 1
            supersedes_id = None

        flux_file = _create_c68_flux_file(
            filename,
            file_hash,
            file_status,
            file_version,
            supersedes_id,
            archive_payload,
            parsed_payloads,
            existing=pre_registered,
        )
        if pre_registered is None:
            session.add(flux_file)
        session.flush()
        total_inserted = _store_c68(archive_payload, parsed_payloads, flux_file, session, chunk_size)
        flux_file.measures_count = total_inserted
        session.commit()
        return file_status
    except Exception as exc:
        session.rollback()
        logger.error("SF5 C68 storage failed for %s: %s", filename, exc)
        refetched = (
            session.query(EnedisFluxFile).filter_by(file_hash=file_hash).first() if pre_registered is not None else None
        )
        _record_file(session, filename, file_hash, FluxType.C68.value, FluxStatus.ERROR, str(exc), existing=refetched)
        session.commit()
        return FluxStatus.ERROR


def _ingest_r6x_file(
    file_path: Path,
    session: Session,
    keys: list[tuple[bytes, bytes]],
    chunk_size: int,
    file_hash: str,
    flux_type: FluxType,
    pre_registered: EnedisFluxFile | None,
    previous_file: EnedisFluxFile | None,
) -> FluxStatus:
    filename = file_path.name
    parser_fn = parse_r63_payload if flux_type == FluxType.R63 else parse_r64_payload
    parse_error_cls = R63ParseError if flux_type == FluxType.R63 else R64ParseError
    store_fn = _store_r63 if flux_type == FluxType.R63 else _store_r64
    try:
        resolved = resolve_payload(file_path, "zip", keys=keys or None)
        container_payload = extract_r6x_payload(filename, resolved.payload_bytes)
        parsed = parser_fn(
            container_payload.payload_bytes,
            container_payload.payload_format,
            container_payload.member_name,
        )
    except (TransportError, ContainerError, parse_error_cls) as exc:
        logger.error("SF5 %s ingest failed for %s: %s", flux_type.value, filename, exc)
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.ERROR, str(exc), existing=pre_registered)
        session.commit()
        return FluxStatus.ERROR

    try:
        if previous_file is not None:
            file_status = FluxStatus.NEEDS_REVIEW
            file_version = previous_file.version + 1
            supersedes_id = previous_file.id
        else:
            file_status = FluxStatus.PARSED
            file_version = 1
            supersedes_id = None

        flux_file = _create_sf5_flux_file(
            filename,
            file_hash,
            flux_type,
            file_status,
            file_version,
            supersedes_id,
            container_payload,
            parsed,
            existing=pre_registered,
        )
        if pre_registered is None:
            session.add(flux_file)
        session.flush()
        total_inserted = store_fn(parsed, flux_file, session, chunk_size)
        flux_file.measures_count = total_inserted
        session.commit()
        return file_status
    except Exception as exc:
        session.rollback()
        logger.error("SF5 %s storage failed for %s: %s", flux_type.value, filename, exc)
        refetched = (
            session.query(EnedisFluxFile).filter_by(file_hash=file_hash).first() if pre_registered is not None else None
        )
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.ERROR, str(exc), existing=refetched)
        session.commit()
        return FluxStatus.ERROR


def _prm_summary(parsed: Any) -> str:
    """Return a concise PRM summary for log output.

    R4x (single PRM): "PRM 30000210411333"
    Multi-PRM (R171/R50/R151): "2 PRMs" or single PRM if only one.
    """
    if hasattr(parsed, "point_id"):
        # R4x — single PRM at file level
        return f"PRM {parsed.point_id}"

    if hasattr(parsed, "series"):
        # R171 — PRM per serie
        prm_ids = {s.point_id for s in parsed.series}
    elif hasattr(parsed, "prms"):
        # R50 / R151 — PRM per prm block
        prm_ids = {p.point_id for p in parsed.prms}
    else:
        return "unknown PRMs"

    count = len(prm_ids)
    if count == 1:
        return f"PRM {next(iter(prm_ids))}"
    return f"{count} PRMs"


# ---------------------------------------------------------------------------
# Store functions — one per flux family
# ---------------------------------------------------------------------------


def _batch_insert(session: Session, model_cls, rows, chunk_size: int) -> int:
    """Flush *rows* (iterable of dicts) into *model_cls* in chunks. Returns total inserted."""
    total = 0
    batch: list[dict] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= chunk_size:
            session.execute(insert(model_cls), batch)
            total += len(batch)
            batch = []
    if batch:
        session.execute(insert(model_cls), batch)
        total += len(batch)
    return total


def _iter_r4x(parsed: Any, flux_file: EnedisFluxFile):
    for courbe in parsed.courbes:
        for point in courbe.points:
            yield dict(
                flux_file_id=flux_file.id,
                flux_type=flux_file.flux_type,
                point_id=parsed.point_id,
                grandeur_physique=courbe.grandeur_physique,
                grandeur_metier=courbe.grandeur_metier,
                unite_mesure=courbe.unite_mesure,
                granularite=courbe.granularite,
                horodatage_debut=courbe.horodatage_debut,
                horodatage_fin=courbe.horodatage_fin,
                horodatage=point.horodatage,
                valeur_point=point.valeur_point,
                statut_point=point.statut_point,
            )


def _store_r4x(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    return _batch_insert(session, EnedisFluxMesureR4x, _iter_r4x(parsed, flux_file), chunk_size)


def _iter_r171(parsed: Any, flux_file: EnedisFluxFile):
    for serie in parsed.series:
        for mesure in serie.mesures:
            yield dict(
                flux_file_id=flux_file.id,
                flux_type=flux_file.flux_type,
                point_id=serie.point_id,
                type_mesure=serie.type_mesure,
                grandeur_metier=serie.grandeur_metier,
                grandeur_physique=serie.grandeur_physique,
                type_calendrier=serie.type_calendrier,
                code_classe_temporelle=serie.code_classe_temporelle,
                libelle_classe_temporelle=serie.libelle_classe_temporelle,
                unite=serie.unite,
                date_fin=mesure.date_fin,
                valeur=mesure.valeur,
            )


def _store_r171(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    return _batch_insert(session, EnedisFluxMesureR171, _iter_r171(parsed, flux_file), chunk_size)


def _iter_r50(parsed: Any, flux_file: EnedisFluxFile):
    for prm in parsed.prms:
        for releve in prm.releves:
            for point in releve.points:
                yield dict(
                    flux_file_id=flux_file.id,
                    flux_type=flux_file.flux_type,
                    point_id=prm.point_id,
                    date_releve=releve.date_releve,
                    id_affaire=releve.id_affaire,
                    horodatage=point.horodatage,
                    valeur=point.valeur,
                    indice_vraisemblance=point.indice_vraisemblance,
                )


def _store_r50(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    return _batch_insert(session, EnedisFluxMesureR50, _iter_r50(parsed, flux_file), chunk_size)


def _iter_r151(parsed: Any, flux_file: EnedisFluxFile):
    for prm in parsed.prms:
        for releve in prm.releves:
            for donnee in releve.donnees:
                yield dict(
                    flux_file_id=flux_file.id,
                    flux_type=flux_file.flux_type,
                    point_id=prm.point_id,
                    date_releve=releve.date_releve,
                    id_calendrier_fournisseur=releve.id_calendrier_fournisseur,
                    libelle_calendrier_fournisseur=releve.libelle_calendrier_fournisseur,
                    id_calendrier_distributeur=releve.id_calendrier_distributeur,
                    libelle_calendrier_distributeur=releve.libelle_calendrier_distributeur,
                    id_affaire=releve.id_affaire,
                    type_donnee=donnee.type_donnee,
                    id_classe_temporelle=donnee.id_classe_temporelle,
                    libelle_classe_temporelle=donnee.libelle_classe_temporelle,
                    rang_cadran=donnee.rang_cadran,
                    valeur=donnee.valeur,
                    indice_vraisemblance=donnee.indice_vraisemblance,
                )


def _store_r151(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    return _batch_insert(session, EnedisFluxMesureR151, _iter_r151(parsed, flux_file), chunk_size)


def _iter_r63(parsed: Any, flux_file: EnedisFluxFile):
    for row in parsed.rows:
        yield dict(
            flux_file_id=flux_file.id,
            flux_type=flux_file.flux_type,
            source_format=parsed.source_format,
            archive_member_name=parsed.member_name,
            point_id=row.point_id,
            periode_date_debut=row.periode_date_debut,
            periode_date_fin=row.periode_date_fin,
            etape_metier=row.etape_metier,
            mode_calcul=row.mode_calcul,
            grandeur_metier=row.grandeur_metier,
            grandeur_physique=row.grandeur_physique,
            unite=row.unite,
            horodatage=row.horodatage,
            pas=row.pas,
            nature_point=row.nature_point,
            type_correction=row.type_correction,
            valeur=row.valeur,
            indice_vraisemblance=row.indice_vraisemblance,
            etat_complementaire=row.etat_complementaire,
        )


def _store_r63(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    return _batch_insert(session, EnedisFluxMesureR63, _iter_r63(parsed, flux_file), chunk_size)


def _iter_r64(parsed: Any, flux_file: EnedisFluxFile):
    for row in parsed.rows:
        yield dict(
            flux_file_id=flux_file.id,
            flux_type=flux_file.flux_type,
            source_format=parsed.source_format,
            archive_member_name=parsed.member_name,
            point_id=row.point_id,
            periode_date_debut=row.periode_date_debut,
            periode_date_fin=row.periode_date_fin,
            etape_metier=row.etape_metier,
            contexte_releve=row.contexte_releve,
            type_releve=row.type_releve,
            motif_releve=row.motif_releve,
            grandeur_metier=row.grandeur_metier,
            grandeur_physique=row.grandeur_physique,
            unite=row.unite,
            horodatage=row.horodatage,
            valeur=row.valeur,
            indice_vraisemblance=row.indice_vraisemblance,
            code_grille=row.code_grille,
            id_calendrier=row.id_calendrier,
            libelle_calendrier=row.libelle_calendrier,
            libelle_grille=row.libelle_grille,
            id_classe_temporelle=row.id_classe_temporelle,
            libelle_classe_temporelle=row.libelle_classe_temporelle,
            code_cadran=row.code_cadran,
        )


def _store_r64(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    return _batch_insert(session, EnedisFluxIndexR64, _iter_r64(parsed, flux_file), chunk_size)


def _iter_c68(archive_payload: Any, parsed_payloads: list[Any], flux_file: EnedisFluxFile):
    for payload, parsed in zip(archive_payload.payloads, parsed_payloads):
        for row in parsed.rows:
            yield dict(
                flux_file_id=flux_file.id,
                source_format=parsed.source_format,
                secondary_archive_name=payload.secondary_archive_name,
                payload_member_name=payload.payload_member_name,
                point_id=row.point_id,
                payload_raw=row.payload_raw,
                contractual_situation_count=row.contractual_situation_count,
                date_debut_situation_contractuelle=row.date_debut_situation_contractuelle,
                segment=row.segment,
                etat_contractuel=row.etat_contractuel,
                formule_tarifaire_acheminement=row.formule_tarifaire_acheminement,
                code_tarif_acheminement=row.code_tarif_acheminement,
                siret=row.siret,
                siren=row.siren,
                domaine_tension=row.domaine_tension,
                tension_livraison=row.tension_livraison,
                type_comptage=row.type_comptage,
                mode_releve=row.mode_releve,
                media_comptage=row.media_comptage,
                periodicite_releve=row.periodicite_releve,
                puissance_souscrite_valeur=row.puissance_souscrite_valeur,
                puissance_souscrite_unite=row.puissance_souscrite_unite,
                puissance_limite_soutirage_valeur=row.puissance_limite_soutirage_valeur,
                puissance_limite_soutirage_unite=row.puissance_limite_soutirage_unite,
                puissance_raccordement_soutirage_valeur=row.puissance_raccordement_soutirage_valeur,
                puissance_raccordement_soutirage_unite=row.puissance_raccordement_soutirage_unite,
                puissance_raccordement_injection_valeur=row.puissance_raccordement_injection_valeur,
                puissance_raccordement_injection_unite=row.puissance_raccordement_injection_unite,
                type_injection=row.type_injection,
                borne_fixe=row.borne_fixe,
                refus_pose_linky=row.refus_pose_linky,
                date_refus_pose_linky=row.date_refus_pose_linky,
            )


def _store_c68(
    archive_payload: Any,
    parsed_payloads: list[Any],
    flux_file: EnedisFluxFile,
    session: Session,
    chunk_size: int,
) -> int:
    return _batch_insert(session, EnedisFluxItcC68, _iter_c68(archive_payload, parsed_payloads, flux_file), chunk_size)


# ---------------------------------------------------------------------------
# Dispatch table — FluxType → (parser_fn, parse_error_cls, store_fn)
# ---------------------------------------------------------------------------

_StoreFn = Callable[[Any, EnedisFluxFile, Session, int], int]
_DispatchEntry = tuple[Callable[[bytes], Any], type[Exception], _StoreFn]

_DISPATCH: dict[FluxType, _DispatchEntry] = {
    FluxType.R4H: (parse_r4x, R4xParseError, _store_r4x),
    FluxType.R4M: (parse_r4x, R4xParseError, _store_r4x),
    FluxType.R4Q: (parse_r4x, R4xParseError, _store_r4x),
    FluxType.R171: (parse_r171, R171ParseError, _store_r171),
    FluxType.R50: (parse_r50, R50ParseError, _store_r50),
    FluxType.R151: (parse_r151, R151ParseError, _store_r151),
}
