"""
SF5 Bridge — Dual-source data access (promoted first, demo fallback).

Pattern : chaque service qui consomme des données CDC/index utilise ce module
pour interroger d'abord les tables promues (meter_load_curve), puis fallback
vers MeterReading (données démo/seed) si la couverture est insuffisante.
"""

import logging
import time
from datetime import datetime, timezone
from typing import NamedTuple

from sqlalchemy.orm import Session

from models.energy_models import Meter, MeterReading

logger = logging.getLogger(__name__)

# Flag module-level : évite de queryer meter_load_curve si table vide/inexistante.
# None = pas encore vérifié, True = données promues disponibles, False = skip.
_promoted_available: bool | None = None
_promoted_checked_at: float = 0.0
_PROMOTED_CHECK_TTL = 300  # Re-vérifier toutes les 5 min

# Seuil de couverture : si les données promues couvrent >= 50% de la période,
# on les utilise comme source principale.
PROMOTED_COVERAGE_THRESHOLD = 0.50


class ReadingRow(NamedTuple):
    """Ligne de lecture normalisée (compatible promoted et legacy)."""

    timestamp: datetime
    value_kwh: float
    quality_score: float | None


class DailyRow(NamedTuple):
    """Agrégation journalière."""

    day: str
    kwh: float


def get_site_meter_ids(db: Session, site_id: int) -> list[int]:
    """Retourne les IDs des compteurs principaux du site."""
    meters = db.query(Meter.id).filter(Meter.site_id == site_id, Meter.parent_meter_id.is_(None)).all()
    return [m.id for m in meters]


def get_readings(
    db: Session, meter_ids: list[int], start_dt: datetime, end_dt: datetime | None = None
) -> tuple[list[ReadingRow], str]:
    """Retourne les lectures (timestamp, kwh, quality) + source utilisée.

    Essaie d'abord meter_load_curve (promoted), puis fallback MeterReading.
    Retourne (readings, source) où source = "promoted" | "legacy".
    """
    if not meter_ids:
        return [], "none"

    # Hot-path skip : si on sait que meter_load_curve est vide, on saute
    if _is_promoted_available(db):
        promoted = _query_promoted(db, meter_ids, start_dt, end_dt)
        if promoted:
            period_days = max(1, ((end_dt or datetime.now(timezone.utc).replace(tzinfo=None)) - start_dt).days)
            days_covered = len({r.timestamp.date() for r in promoted})
            coverage = days_covered / period_days

            if coverage >= PROMOTED_COVERAGE_THRESHOLD:
                logger.debug("Bridge: promoted data (%d readings, %.0f%% coverage)", len(promoted), coverage * 100)
                return promoted, "promoted"

    legacy = _query_legacy(db, meter_ids, start_dt, end_dt)
    source = "legacy" if legacy else "none"
    logger.debug("Bridge: %s data (%d readings)", source, len(legacy))
    return legacy, source


def get_daily_kwh(
    db: Session, meter_ids: list[int], start_dt: datetime, end_dt: datetime | None = None
) -> tuple[dict[str, float], str]:
    """Retourne {date_str: kwh_total} par jour + source utilisée.

    Agrège automatiquement les lectures infra-journalières.
    """
    readings, source = get_readings(db, meter_ids, start_dt, end_dt)

    daily: dict[str, float] = {}
    for r in readings:
        day = r.timestamp.strftime("%Y-%m-%d")
        daily[day] = daily.get(day, 0) + r.value_kwh

    return daily, source


def _query_promoted(db: Session, meter_ids: list[int], start_dt: datetime, end_dt: datetime | None) -> list[ReadingRow]:
    """Query meter_load_curve (tables promues SF5).

    IMPORTANT : MeterLoadCurve stocke de la puissance (kW).
    Conversion en énergie : E(kWh) = P(kW) × pas_minutes / 60.
    """
    try:
        from data_staging.models import MeterLoadCurve
        from sqlalchemy.exc import OperationalError, ProgrammingError

        q = db.query(
            MeterLoadCurve.timestamp,
            MeterLoadCurve.active_power_kw,
            MeterLoadCurve.quality_score,
            MeterLoadCurve.pas_minutes,
        ).filter(
            MeterLoadCurve.meter_id.in_(meter_ids),
            MeterLoadCurve.timestamp >= start_dt,
        )
        if end_dt:
            q = q.filter(MeterLoadCurve.timestamp <= end_dt)

        rows = q.order_by(MeterLoadCurve.timestamp).all()

        return [
            ReadingRow(
                timestamp=r[0],
                value_kwh=(r[1] or 0) * ((r[3] or 30) / 60.0),  # kW × (pas/60) → kWh
                quality_score=r[2],
            )
            for r in rows
        ]
    except (OperationalError, ProgrammingError) as e:
        # Table n'existe pas encore (DB fresh sans migration)
        try:
            db.rollback()
        except Exception:
            pass
        logger.debug("Promoted query failed (table may not exist): %s", e)
        return []
    except Exception as e:
        logger.warning("Promoted query unexpected error: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return []


def _query_legacy(db: Session, meter_ids: list[int], start_dt: datetime, end_dt: datetime | None) -> list[ReadingRow]:
    """Query MeterReading (données démo/import CSV)."""
    q = db.query(
        MeterReading.timestamp,
        MeterReading.value_kwh,
        MeterReading.quality_score,
    ).filter(
        MeterReading.meter_id.in_(meter_ids),
        MeterReading.timestamp >= start_dt,
    )
    if end_dt:
        q = q.filter(MeterReading.timestamp <= end_dt)

    rows = q.order_by(MeterReading.timestamp).all()
    return [ReadingRow(timestamp=r[0], value_kwh=r[1] or 0, quality_score=r[2]) for r in rows]


def _is_promoted_available(db: Session) -> bool:
    """Vérifie (avec cache TTL) si meter_load_curve contient des données."""
    global _promoted_available, _promoted_checked_at

    now = time.monotonic()
    if _promoted_available is not None and (now - _promoted_checked_at) < _PROMOTED_CHECK_TTL:
        return _promoted_available

    try:
        from sqlalchemy import text

        result = db.execute(text("SELECT 1 FROM meter_load_curve LIMIT 1")).fetchone()
        _promoted_available = result is not None
    except Exception:
        _promoted_available = False
    _promoted_checked_at = now
    return _promoted_available


def invalidate_promoted_cache():
    """Force re-check au prochain appel (appelé après un run de promotion)."""
    global _promoted_available, _promoted_checked_at
    _promoted_available = None
    _promoted_checked_at = 0.0
