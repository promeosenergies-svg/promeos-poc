"""
PROMEOS — Staging Bridge: flux Enedis staging → MeterReading

Convertit les données brutes des tables staging (EnedisFluxMesureR4x, R50, R151, R171)
en MeterReading normalisées pour le modèle energy_models.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import insert
from sqlalchemy.orm import Session

from models.energy_models import Meter, MeterReading, FrequencyType

logger = logging.getLogger("promeos.services.staging_bridge")


@dataclass
class BridgeResult:
    """Résultat d'une opération de bridge."""

    prm: str
    meter_id: int | None = None
    rows_inserted: int = 0
    rows_skipped: int = 0
    rows_errored: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.rows_errored == 0 and self.meter_id is not None


@dataclass
class GapInfo:
    """Information sur un trou dans les données."""

    start: datetime
    end: datetime
    expected_readings: int
    actual_readings: int

    @property
    def missing_readings(self) -> int:
        return self.expected_readings - self.actual_readings


def resolve_meter_for_prm(prm: str, db: Session) -> Optional[Meter]:
    """Trouve le Meter correspondant à un PRM.

    Cherche d'abord par meter_id exact, puis via DeliveryPoint.code.
    """
    # 1. Recherche directe par meter_id
    meter = db.query(Meter).filter(Meter.meter_id == prm, Meter.is_active == True).first()
    if meter:
        return meter

    # 2. Recherche via DeliveryPoint
    from models.patrimoine import DeliveryPoint

    dp = db.query(DeliveryPoint).filter(DeliveryPoint.code == prm).first()
    if dp:
        meter = db.query(Meter).filter(Meter.delivery_point_id == dp.id, Meter.is_active == True).first()
        if meter:
            return meter

    return None


def _parse_iso_datetime(iso_str: str) -> Optional[datetime]:
    """Parse une chaîne ISO8601 brute Enedis en datetime UTC."""
    if not iso_str:
        return None
    try:
        # Formats Enedis: "2024-01-15T00:00:00+01:00", "2024-01-15"
        iso_str = iso_str.strip()
        if "T" in iso_str:
            # Avec timezone offset
            if "+" in iso_str[10:] or iso_str.endswith("Z"):
                dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
        else:
            dt = datetime.strptime(iso_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)  # Stocker naïf UTC
    except (ValueError, TypeError) as e:
        logger.debug("Parse ISO datetime failed: %s (%s)", iso_str, e)
        return None


def _resolve_meter_or_fail(prm: str, db: Session) -> tuple[Meter | None, BridgeResult]:
    """Résout le Meter pour un PRM, retourne (meter, result) pré-rempli."""
    result = BridgeResult(prm=prm)
    meter = resolve_meter_for_prm(prm, db)
    if not meter:
        result.errors.append(f"Aucun Meter trouvé pour PRM {prm}")
    else:
        result.meter_id = meter.id
    return meter, result


def _bridge_mesures(
    prm: str,
    db: Session,
    mesures: list,
    flux_label: str,
    extract_fn,
    import_job_id: int | None = None,
) -> BridgeResult:
    """Logique commune de bridge staging → MeterReading.

    extract_fn(mesure) → (value_kwh, frequency, is_estimated, quality_score) ou None pour skip.
    """
    meter, result = _resolve_meter_or_fail(prm, db)
    if not meter:
        return result

    if not mesures:
        return result

    seen_timestamps = set()
    for m in mesures:
        ts = _parse_iso_datetime(m.horodatage)
        if not ts or ts in seen_timestamps:
            result.rows_skipped += 1
            continue
        seen_timestamps.add(ts)

        try:
            extracted = extract_fn(m)
            if extracted is None:
                result.rows_skipped += 1
                continue

            value_kwh, freq, is_estimated, quality_score = extracted

            stmt = (
                insert(MeterReading)
                .prefix_with("OR IGNORE")
                .values(
                    meter_id=meter.id,
                    timestamp=ts,
                    frequency=freq,
                    value_kwh=round(value_kwh, 3),
                    is_estimated=is_estimated,
                    quality_score=quality_score,
                    import_job_id=import_job_id,
                    created_at=datetime.utcnow(),
                )
            )
            db.execute(stmt)
            result.rows_inserted += 1

        except (ValueError, TypeError) as e:
            result.rows_errored += 1
            result.errors.append(f"Mesure {flux_label} id={m.id}: {e}")

    db.flush()
    logger.info(
        "Bridge %s PRM=%s: %d inserted, %d skipped, %d errors",
        flux_label,
        prm,
        result.rows_inserted,
        result.rows_skipped,
        result.rows_errored,
    )
    return result


def _extract_r4x(m):
    """Extrait les données d'une mesure R4x (kW → kWh)."""
    if not m.valeur_point:
        return None
    value_kw = float(m.valeur_point)
    pas_minutes = 30
    if m.granularite:
        try:
            pas_minutes = int(m.granularite)
        except ValueError:
            pass
    value_kwh = value_kw * (pas_minutes / 60.0)

    if pas_minutes <= 15:
        freq = FrequencyType.MIN_15
    elif pas_minutes <= 30:
        freq = FrequencyType.MIN_30
    else:
        freq = FrequencyType.HOURLY

    is_estimated = (m.statut_point or "R") not in ("R", "C")
    quality_score = 1.0 if m.statut_point == "R" else 0.8
    return value_kwh, freq, is_estimated, quality_score


def _extract_r50(m):
    """Extrait les données d'une mesure R50 (Wh → kWh)."""
    if not m.valeur:
        return None
    value_kwh = float(m.valeur) / 1000.0
    is_estimated = (m.indice_vraisemblance or "1") != "1"
    quality_score = 1.0 if m.indice_vraisemblance == "1" else 0.7
    return value_kwh, FrequencyType.MIN_30, is_estimated, quality_score


def bridge_r4x_to_meter(prm: str, db: Session, import_job_id: int | None = None) -> BridgeResult:
    """Bridge les mesures R4x (CDC C2-C4) vers MeterReading.

    - Granularité: 10min/30min/60min selon le flux
    - Valeurs en kW → conversion en kWh selon le pas
    - INSERT OR IGNORE pour idempotence
    """
    from data_ingestion.enedis.models import EnedisFluxMesureR4x

    mesures = (
        db.query(EnedisFluxMesureR4x)
        .filter(EnedisFluxMesureR4x.point_id == prm)
        .order_by(EnedisFluxMesureR4x.horodatage, EnedisFluxMesureR4x.id.desc())
        .all()
    )
    return _bridge_mesures(prm, db, mesures, "R4x", _extract_r4x, import_job_id)


def bridge_r50_to_meter(prm: str, db: Session, import_job_id: int | None = None) -> BridgeResult:
    """Bridge les mesures R50 (CDC C5 30min) vers MeterReading.

    - Pas fixe 30 min
    - Valeurs directement en Wh → conversion en kWh
    - INSERT OR IGNORE pour idempotence
    """
    from data_ingestion.enedis.models import EnedisFluxMesureR50

    mesures = (
        db.query(EnedisFluxMesureR50)
        .filter(EnedisFluxMesureR50.point_id == prm)
        .order_by(EnedisFluxMesureR50.horodatage, EnedisFluxMesureR50.id.desc())
        .all()
    )
    return _bridge_mesures(prm, db, mesures, "R50", _extract_r50, import_job_id)


def bridge_all_prms(db: Session, prms: List[str] | None = None, import_job_id: int | None = None) -> List[BridgeResult]:
    """Bridge toutes les mesures staging vers MeterReading pour une liste de PRMs.

    Si prms est None, détecte tous les PRMs connus dans les tables staging.
    """
    from data_ingestion.enedis.models import EnedisFluxMesureR4x, EnedisFluxMesureR50

    if prms is None:
        # Découvrir tous les PRMs dans le staging
        r4x_prms = {row[0] for row in db.query(EnedisFluxMesureR4x.point_id).distinct().all()}
        r50_prms = {row[0] for row in db.query(EnedisFluxMesureR50.point_id).distinct().all()}
        prms = sorted(r4x_prms | r50_prms)

    results = []
    try:
        for prm in prms:
            # Bridge R4x
            r4x_result = bridge_r4x_to_meter(prm, db, import_job_id)
            # Bridge R50
            r50_result = bridge_r50_to_meter(prm, db, import_job_id)

            # Fusionner les résultats
            combined = BridgeResult(
                prm=prm,
                meter_id=r4x_result.meter_id or r50_result.meter_id,
                rows_inserted=r4x_result.rows_inserted + r50_result.rows_inserted,
                rows_skipped=r4x_result.rows_skipped + r50_result.rows_skipped,
                rows_errored=r4x_result.rows_errored + r50_result.rows_errored,
                errors=r4x_result.errors + r50_result.errors,
            )
            results.append(combined)

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Bridge all PRMs failed, rolled back")
        raise

    logger.info("Bridge all PRMs: %d PRMs traités", len(results))
    return results


def detect_gaps(
    meter_id: int,
    start: datetime,
    end: datetime,
    expected_freq_minutes: int,
    db: Session,
) -> List[GapInfo]:
    """Détecte les trous dans les MeterReading pour un compteur.

    Compare le nombre de lectures attendues vs réelles par jour.
    """
    gaps = []
    expected_per_day = (24 * 60) // expected_freq_minutes

    current = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while current < end:
        day_end = current + timedelta(days=1)

        actual_count = (
            db.query(MeterReading)
            .filter(
                MeterReading.meter_id == meter_id,
                MeterReading.timestamp >= current,
                MeterReading.timestamp < day_end,
            )
            .count()
        )

        if actual_count < expected_per_day * 0.9:  # Tolérance 10%
            gaps.append(
                GapInfo(
                    start=current,
                    end=day_end,
                    expected_readings=expected_per_day,
                    actual_readings=actual_count,
                )
            )

        current = day_end

    return gaps
