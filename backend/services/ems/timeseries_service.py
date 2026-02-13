"""
PROMEOS - EMS Timeseries Service
SQL-level bucket aggregation for consumption timeseries.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, literal_column, Integer as SAInteger, cast

from models import Meter, MeterReading
from models.energy_models import EnergyVector

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------
GRANULARITY_MAX_POINTS = 5000  # Per series — non-negotiable

VALID_GRANULARITIES = ("15min", "30min", "hourly", "daily", "monthly")

# Bucket hours for kW conversion
BUCKET_HOURS = {
    "15min": 0.25,
    "30min": 0.5,
    "hourly": 1.0,
    "daily": 24.0,
    "monthly": 730.0,
}

# SQLite strftime patterns for bucket keys
_STRFTIME_FORMATS = {
    "hourly": "%Y-%m-%d %H:00:00",
    "daily": "%Y-%m-%d",
    "monthly": "%Y-%m",
}


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------
def suggest_granularity(date_from: datetime, date_to: datetime) -> str:
    """Auto-suggest granularity based on date range span."""
    span_days = (date_to - date_from).days
    if span_days <= 3:
        return "15min"
    elif span_days <= 14:
        return "hourly"
    elif span_days <= 120:
        return "daily"
    else:
        return "monthly"


def estimate_points(date_from: datetime, date_to: datetime, granularity: str) -> int:
    """Estimate number of points per series for a given range + granularity."""
    span_hours = max((date_to - date_from).total_seconds() / 3600, 0)
    multiplier = {
        "15min": 4,
        "30min": 2,
        "hourly": 1,
        "daily": 1.0 / 24,
        "monthly": 1.0 / (24 * 30),
    }
    return max(1, int(span_hours * multiplier.get(granularity, 1)))


def validate_cap_points(
    date_from: datetime,
    date_to: datetime,
    granularity: str,
) -> Tuple[bool, Optional[str], int]:
    """Check if estimated points exceed cap.

    Returns (ok, suggested_granularity_if_not_ok, estimated_points).
    """
    estimated = estimate_points(date_from, date_to, granularity)
    if estimated <= GRANULARITY_MAX_POINTS:
        return True, None, estimated
    suggested = suggest_granularity(date_from, date_to)
    return False, suggested, estimated


def query_timeseries(
    db: Session,
    site_ids: List[int],
    meter_ids: Optional[List[int]],
    date_from: datetime,
    date_to: datetime,
    granularity: str,
    mode: str = "aggregate",
    metric: str = "kwh",
    energy_vector: Optional[str] = None,
) -> Dict[str, Any]:
    """SQL-level bucketed timeseries query.

    Returns::

        {
          "series": [{key, label, data: [{t, v, quality, estimated_pct}]}],
          "meta": {granularity, n_points, n_meters, date_from, date_to, metric}
        }
    """
    # 1. Resolve meters
    meter_q = db.query(Meter).filter(
        Meter.site_id.in_(site_ids),
        Meter.is_active == True,
    )
    if energy_vector:
        try:
            ev = EnergyVector(energy_vector)
            meter_q = meter_q.filter(Meter.energy_vector == ev)
        except ValueError:
            pass
    if meter_ids:
        meter_q = meter_q.filter(Meter.id.in_(meter_ids))

    meters = meter_q.all()
    if not meters:
        return {
            "series": [],
            "meta": _meta(granularity, 0, 0, date_from, date_to, metric),
        }

    meter_id_list = [m.id for m in meters]

    # 2. Build bucket expression
    bucket_expr = _bucket_key_expr(granularity)

    # 3. Query per mode
    if mode == "aggregate":
        series = [_query_aggregate(db, meter_id_list, bucket_expr, date_from, date_to, granularity, metric)]
    elif mode == "stack":
        series = [
            _query_single(db, m, bucket_expr, date_from, date_to, granularity, metric)
            for m in meters
        ]
    else:  # split
        MAX_SPLIT = 8
        sorted_meters = sorted(meters, key=lambda m: m.id)
        main_meters = sorted_meters[:MAX_SPLIT]
        other_meters = sorted_meters[MAX_SPLIT:]

        series = [
            _query_single(db, m, bucket_expr, date_from, date_to, granularity, metric)
            for m in main_meters
        ]
        if other_meters:
            other_ids = [m.id for m in other_meters]
            series.append(_query_aggregate(
                db, other_ids, bucket_expr, date_from, date_to, granularity, metric,
                key="others", label="Autres",
            ))

    n_points = max((len(s["data"]) for s in series), default=0)
    return {
        "series": series,
        "meta": _meta(granularity, n_points, len(meters), date_from, date_to, metric),
    }


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------
def _meta(granularity, n_points, n_meters, date_from, date_to, metric):
    return {
        "granularity": granularity,
        "metric": metric,
        "n_points": n_points,
        "n_meters": n_meters,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
    }


def _bucket_key_expr(granularity: str):
    """Build SQLite strftime expression for bucket grouping."""
    if granularity == "15min":
        return (
            func.strftime("%Y-%m-%d %H:", MeterReading.timestamp)
            + func.printf(
                "%02d",
                (cast(func.strftime("%M", MeterReading.timestamp), SAInteger) / 15) * 15,
            )
            + literal_column("':00'")
        )
    elif granularity == "30min":
        return (
            func.strftime("%Y-%m-%d %H:", MeterReading.timestamp)
            + func.printf(
                "%02d",
                (cast(func.strftime("%M", MeterReading.timestamp), SAInteger) / 30) * 30,
            )
            + literal_column("':00'")
        )
    else:
        fmt = _STRFTIME_FORMATS.get(granularity, "%Y-%m-%d")
        return func.strftime(fmt, MeterReading.timestamp)


def _base_query(db, meter_ids, bucket_expr, date_from, date_to):
    """Shared bucket query base."""
    return (
        db.query(
            bucket_expr.label("bucket"),
            func.sum(MeterReading.value_kwh).label("total_kwh"),
            func.avg(MeterReading.quality_score).label("avg_quality"),
            func.avg(cast(MeterReading.is_estimated, SAInteger)).label("est_pct"),
        )
        .filter(
            MeterReading.meter_id.in_(meter_ids) if isinstance(meter_ids, list) else MeterReading.meter_id == meter_ids,
            MeterReading.timestamp >= date_from,
            MeterReading.timestamp < date_to,
        )
        .group_by(literal_column("bucket"))
        .order_by(literal_column("bucket"))
    )


def _rows_to_series(key: str, label: str, rows, granularity: str, metric: str) -> Dict:
    hours = BUCKET_HOURS.get(granularity, 1.0)
    data = []
    for row in rows:
        value = row.total_kwh or 0.0
        if metric == "kw":
            value = value / hours if hours > 0 else 0.0
        data.append({
            "t": row.bucket,
            "v": round(value, 2),
            "quality": round(row.avg_quality, 2) if row.avg_quality is not None else None,
            "estimated_pct": round(row.est_pct, 2) if row.est_pct is not None else 0.0,
        })
    return {"key": key, "label": label, "data": data}


def _query_aggregate(db, meter_ids, bucket_expr, date_from, date_to, granularity, metric,
                     key="total", label="Total"):
    rows = _base_query(db, meter_ids, bucket_expr, date_from, date_to).all()
    return _rows_to_series(key, label, rows, granularity, metric)


def _query_single(db, meter, bucket_expr, date_from, date_to, granularity, metric):
    rows = _base_query(db, meter.id, bucket_expr, date_from, date_to).all()
    label = meter.name or meter.meter_id or f"Meter {meter.id}"
    return _rows_to_series(f"meter_{meter.id}", label, rows, granularity, metric)
