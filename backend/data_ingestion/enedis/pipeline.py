"""PROMEOS — Enedis R4x CDC ingestion pipeline.

Orchestrates: classify → hash check → decrypt → parse → store.

Idempotence:
  - File-level only: SHA256 of the raw ciphertext. Same .zip = skip.
  - No measure-level deduplication: corrections/republications by Enedis
    are archived alongside originals. Deduplication is deferred to a
    future staging/normalization layer.

Usage:
    from data_ingestion.enedis.pipeline import ingest_file
    from data_ingestion.enedis.decrypt import load_keys_from_env

    keys = load_keys_from_env()
    session = SessionLocal()
    status = ingest_file(Path("flux.zip"), session, keys)
    # ingest_file commits on success, rolls back on unhandled error
"""

import hashlib
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from data_ingestion.enedis.decrypt import (
    SKIP_FLUX_TYPES,
    DecryptError,
    classify_flux,
    decrypt_file,
)
from data_ingestion.enedis.enums import FluxStatus, FluxType
from data_ingestion.enedis.models import EnedisFluxFile, EnedisFluxMesure
from data_ingestion.enedis.parsers.r4 import R4xParseError, parse_r4x

logger = logging.getLogger("promeos.enedis.pipeline")

R4X_FLUX_TYPES = frozenset({FluxType.R4H, FluxType.R4M, FluxType.R4Q})

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
    filename = file_path.name
    flux_type = classify_flux(filename)

    # Compute hash once, used for all paths
    file_hash = _hash_file(file_path)

    # Idempotence check — applies to all flux types
    existing = session.query(EnedisFluxFile).filter_by(file_hash=file_hash).first()
    if existing is not None:
        if existing.status in (FluxStatus.PARSED, FluxStatus.SKIPPED):
            logger.info(
                "Already processed %s (hash=%s…, status=%s), skipping", filename, file_hash[:12], existing.status
            )
            return FluxStatus(existing.status)
        if existing.status == FluxStatus.ERROR:
            logger.info("Retrying previously failed %s (hash=%s…)", filename, file_hash[:12])
            session.delete(existing)
            session.flush()

    # Skip non-decryptable flux types
    if flux_type in SKIP_FLUX_TYPES:
        logger.info("Skipping %s (flux type %s)", filename, flux_type.value)
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.SKIPPED)
        session.commit()
        return FluxStatus.SKIPPED

    # Only R4x is supported in SF2
    if flux_type not in R4X_FLUX_TYPES:
        logger.info("Skipping %s (flux type %s not in R4x scope)", filename, flux_type.value)
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.SKIPPED)
        session.commit()
        return FluxStatus.SKIPPED

    # Decrypt
    try:
        xml_bytes = decrypt_file(file_path, keys, archive_dir)
    except DecryptError as exc:
        logger.error("Decrypt failed for %s: %s", filename, exc)
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.ERROR, str(exc))
        session.commit()
        return FluxStatus.ERROR

    # Parse
    try:
        parsed = parse_r4x(xml_bytes)
    except R4xParseError as exc:
        logger.error("Parse failed for %s: %s", filename, exc)
        _record_file(session, filename, file_hash, flux_type.value, FluxStatus.ERROR, str(exc))
        session.commit()
        return FluxStatus.ERROR

    # Store file record
    flux_file = EnedisFluxFile(
        filename=filename,
        file_hash=file_hash,
        flux_type=flux_type.value,
        status=FluxStatus.PARSED,
        frequence_publication=parsed.header.frequence_publication,
        nature_courbe_demandee=parsed.header.nature_courbe_demandee,
        identifiant_destinataire=parsed.header.identifiant_destinataire,
    )
    flux_file.set_header_raw(parsed.header.raw)
    session.add(flux_file)
    session.flush()  # Get flux_file.id

    # Store mesures in batches
    total_inserted = 0
    batch = []
    for courbe in parsed.courbes:
        for point in courbe.points:
            batch.append(
                EnedisFluxMesure(
                    flux_file_id=flux_file.id,
                    flux_type=flux_type.value,
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

    flux_file.measures_count = total_inserted
    session.commit()

    logger.info(
        "Ingested %s: %d mesures from PRM %s [%s]",
        filename,
        total_inserted,
        parsed.point_id,
        flux_type.value,
    )
    return FluxStatus.PARSED


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
) -> EnedisFluxFile:
    """Create a minimal EnedisFluxFile record for skipped/error files."""
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
