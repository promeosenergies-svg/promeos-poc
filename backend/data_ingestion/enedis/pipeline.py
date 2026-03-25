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
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from data_ingestion.enedis.decrypt import (
    SKIP_FLUX_TYPES,
    DecryptError,
    classify_flux,
    decrypt_file,
)
from data_ingestion.enedis.enums import FluxStatus, FluxType
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
)
from data_ingestion.enedis.parsers.r4 import R4xParseError, parse_r4x
from data_ingestion.enedis.parsers.r50 import R50ParseError, parse_r50
from data_ingestion.enedis.parsers.r151 import R151ParseError, parse_r151
from data_ingestion.enedis.parsers.r171 import R171ParseError, parse_r171

logger = logging.getLogger("promeos.enedis.pipeline")

_R4X_FLUX_TYPES = frozenset({FluxType.R4H, FluxType.R4M, FluxType.R4Q})

DEFAULT_CHUNK_SIZE = 1000


def ingest_file(
    file_path: Path,
    session: Session,
    keys: list[tuple[bytes, bytes]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    archive_dir: Path | None = None,
) -> FluxStatus:
    """Ingest one Enedis flux file: decrypt → parse → store in DB.

    Commits the session on success or on recorded error/skip.
    The caller should NOT commit separately.

    Args:
        file_path: Path to the encrypted .zip file.
        session: SQLAlchemy session.
        keys: Decryption key/IV pairs from load_keys_from_env().
        chunk_size: Number of mesure rows per batch insert.
        archive_dir: Optional directory to write decrypted XML for audit.

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

    # Compute hash once, used for all paths
    file_hash = _hash_file(file_path)

    # Idempotence check — applies to all flux types
    # pre_registered tracks a RECEIVED record to update in-place
    pre_registered: EnedisFluxFile | None = None

    existing = session.query(EnedisFluxFile).filter_by(file_hash=file_hash).first()
    if existing is not None:
        if existing.status in (FluxStatus.PARSED, FluxStatus.SKIPPED, FluxStatus.NEEDS_REVIEW):
            logger.info(
                "Already processed %s (hash=%s…, status=%s), skipping", filename, file_hash[:12], existing.status
            )
            return FluxStatus(existing.status)
        if existing.status == FluxStatus.ERROR:
            logger.info("Retrying previously failed %s (hash=%s…)", filename, file_hash[:12])
            session.delete(existing)
            session.flush()
        elif existing.status == FluxStatus.RECEIVED:
            logger.info("Processing pre-registered %s (hash=%s…)", filename, file_hash[:12])
            pre_registered = existing

    # Skip non-decryptable flux types
    if flux_type in SKIP_FLUX_TYPES:
        logger.info("Skipping %s (flux type %s)", filename, flux_type.value)
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.SKIPPED, existing=pre_registered)
        session.commit()
        return FluxStatus.SKIPPED

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
            session, filename, file_hash, flux_type.value, FluxStatus.ERROR, str(exc), existing=pre_registered,
        )
        session.commit()
        return FluxStatus.ERROR

    # Parse
    try:
        parsed = parser_fn(xml_bytes)
    except parse_error_cls as exc:
        logger.error("Parse failed for %s: %s", filename, exc)
        _record_file(
            session, filename, file_hash, flux_type.value, FluxStatus.ERROR, str(exc), existing=pre_registered,
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
            filename, file_hash, flux_type, file_status, file_version, supersedes_id, parsed,
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
            session.query(EnedisFluxFile).filter_by(file_hash=file_hash).first()
            if pre_registered is not None
            else None
        )
        _record_file(
            session, filename, file_hash, flux_type.value, FluxStatus.ERROR, str(exc),
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
) -> dict[str, int]:
    """Ingest all flux files in a directory: scan → register → process.

    Two-phase design for crash recovery:
      Phase 1: scan directory, register each new file as RECEIVED (single commit).
      Phase 2: process each RECEIVED file via ingest_file() → PARSED/ERROR/SKIPPED.
    Files left in RECEIVED after a crash are re-processed on the next run.

    Args:
        directory: Path to the directory containing encrypted .zip files.
        session: SQLAlchemy session.
        keys: Decryption key/IV pairs from load_keys_from_env().
        chunk_size: Number of mesure rows per batch insert.
        archive_dir: Optional directory to write decrypted XML for audit.
        recursive: If True, scan subdirectories recursively.
        pattern: Glob pattern for file matching (default ``*.zip``).

    Returns:
        Dict of counters: received, parsed, needs_review, skipped, error,
        already_processed.
        ``received == parsed + needs_review + skipped + error``.
    """
    counters: dict[str, int] = {
        "received": 0,
        "parsed": 0,
        "needs_review": 0,
        "skipped": 0,
        "error": 0,
        "already_processed": 0,
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
            else:
                # Already processed (PARSED/ERROR/SKIPPED/NEEDS_REVIEW)
                counters["already_processed"] += 1
            continue

        # New file — register as RECEIVED
        flux_file = EnedisFluxFile(
            filename=file_path.name,
            file_hash=file_hash,
            flux_type=classify_flux(file_path.name).value,
            status=FluxStatus.RECEIVED,
            measures_count=0,
        )
        session.add(flux_file)
        to_process.append((file_path, file_hash, flux_file))

    if to_process:
        session.commit()  # Single commit for all RECEIVED registrations
    counters["received"] = len(to_process)

    logger.info(
        "ingest_directory: %d files to process, %d already processed",
        len(to_process),
        counters["already_processed"],
    )

    # Phase 2 — Process each RECEIVED file
    for file_path, phase1_hash, flux_file in to_process:
        try:
            status = ingest_file(file_path, session, keys, chunk_size, archive_dir)
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

    return counters


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _hash_file(file_path: Path) -> str:
    """SHA256 hash of file contents (raw ciphertext)."""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


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

    If *existing* is provided (pre-registered RECEIVED record), updates it
    in-place instead of creating a new row.
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


def _store_r4x(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    """Store R4x CDC measures. Returns total rows inserted."""
    total_inserted = 0
    batch: list[EnedisFluxMesureR4x] = []
    for courbe in parsed.courbes:
        for point in courbe.points:
            batch.append(
                EnedisFluxMesureR4x(
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
            )
            if len(batch) >= chunk_size:
                session.bulk_save_objects(batch)
                total_inserted += len(batch)
                batch = []

    if batch:
        session.bulk_save_objects(batch)
        total_inserted += len(batch)
    return total_inserted


def _store_r171(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    """Store R171 index measures. Returns total rows inserted."""
    total_inserted = 0
    batch: list[EnedisFluxMesureR171] = []
    for serie in parsed.series:
        for mesure in serie.mesures:
            batch.append(
                EnedisFluxMesureR171(
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
            )
            if len(batch) >= chunk_size:
                session.bulk_save_objects(batch)
                total_inserted += len(batch)
                batch = []

    if batch:
        session.bulk_save_objects(batch)
        total_inserted += len(batch)
    return total_inserted


def _store_r50(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    """Store R50 CDC C5 measures. Returns total rows inserted."""
    total_inserted = 0
    batch: list[EnedisFluxMesureR50] = []
    for prm in parsed.prms:
        for releve in prm.releves:
            for point in releve.points:
                batch.append(
                    EnedisFluxMesureR50(
                        flux_file_id=flux_file.id,
                        flux_type=flux_file.flux_type,
                        point_id=prm.point_id,
                        date_releve=releve.date_releve,
                        id_affaire=releve.id_affaire,
                        horodatage=point.horodatage,
                        valeur=point.valeur,
                        indice_vraisemblance=point.indice_vraisemblance,
                    )
                )
                if len(batch) >= chunk_size:
                    session.bulk_save_objects(batch)
                    total_inserted += len(batch)
                    batch = []

    if batch:
        session.bulk_save_objects(batch)
        total_inserted += len(batch)
    return total_inserted


def _store_r151(parsed: Any, flux_file: EnedisFluxFile, session: Session, chunk_size: int) -> int:
    """Store R151 index + puissance max C5 measures. Returns total rows inserted."""
    total_inserted = 0
    batch: list[EnedisFluxMesureR151] = []
    for prm in parsed.prms:
        for releve in prm.releves:
            for donnee in releve.donnees:
                batch.append(
                    EnedisFluxMesureR151(
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
                )
                if len(batch) >= chunk_size:
                    session.bulk_save_objects(batch)
                    total_inserted += len(batch)
                    batch = []

    if batch:
        session.bulk_save_objects(batch)
        total_inserted += len(batch)
    return total_inserted


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
