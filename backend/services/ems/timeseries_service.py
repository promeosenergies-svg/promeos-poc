"""
PROMEOS - EMS Timeseries Service
SQL-level bucket aggregation for consumption timeseries.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, literal_column, Integer as SAInteger, cast

from models import Meter, MeterReading, Site
from models.energy_models import EnergyVector, FrequencyType

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

# When aggregating at granularity G, only include readings whose frequency is
# G or finer — prevents monthly aggregate values from polluting daily/hourly charts.
_COMPATIBLE_FREQS = {
    "15min": [FrequencyType.MIN_15],
    "30min": [FrequencyType.MIN_15, FrequencyType.MIN_30],
    "hourly": [FrequencyType.MIN_15, FrequencyType.MIN_30, FrequencyType.HOURLY],
    "daily": [FrequencyType.MIN_15, FrequencyType.MIN_30, FrequencyType.HOURLY, FrequencyType.DAILY],
    "monthly": [
        FrequencyType.MIN_15,
        FrequencyType.MIN_30,
        FrequencyType.HOURLY,
        FrequencyType.DAILY,
        FrequencyType.MONTHLY,
    ],
}


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------
def suggest_granularity(date_from: datetime, date_to: datetime) -> str:
    """Auto-suggest granularity based on date range span.

    Thresholds chosen so estimated points stay under GRANULARITY_MAX_POINTS:
      15min  → ≤3 days    (3×96   = 288 pts)
      hourly → ≤90 days   (90×24  = 2160 pts)
      daily  → ≤4000 days (4000 pts < 5000 cap)
      monthly→ >4000 days
    """
    span_days = (date_to - date_from).days
    if span_days <= 3:
        return "15min"
    elif span_days <= 90:
        return "hourly"
    elif span_days <= 4000:
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
    compare: Optional[str] = None,
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
            "meta": _meta(granularity, 0, 0, date_from, date_to, metric, series=[]),
        }

    meter_id_list = [m.id for m in meters]

    # 2. Build bucket expression
    bucket_expr = _bucket_key_expr(granularity)

    # 3. Query per mode
    if mode == "aggregate":
        series = [_query_aggregate(db, meter_id_list, bucket_expr, date_from, date_to, granularity, metric)]
    elif mode == "overlay":
        # One series per site (aggregate meters within each site)
        MAX_OVERLAY = 8
        site_meter_map = {}
        for m in meters:
            site_meter_map.setdefault(m.site_id, []).append(m)
        site_names = {s.id: s.nom for s in db.query(Site).filter(Site.id.in_(list(site_meter_map.keys()))).all()}
        sorted_site_ids = sorted(site_meter_map.keys())
        main_sites = sorted_site_ids[:MAX_OVERLAY]
        other_sites = sorted_site_ids[MAX_OVERLAY:]
        series = []
        for sid in main_sites:
            m_ids = [m.id for m in site_meter_map[sid]]
            label = site_names.get(sid, f"Site {sid}")
            series.append(
                _query_aggregate(
                    db, m_ids, bucket_expr, date_from, date_to, granularity, metric, key=f"site_{sid}", label=label
                )
            )
        if other_sites:
            other_ids = []
            for sid in other_sites:
                other_ids.extend([m.id for m in site_meter_map[sid]])
            series.append(
                _query_aggregate(
                    db,
                    other_ids,
                    bucket_expr,
                    date_from,
                    date_to,
                    granularity,
                    metric,
                    key="others",
                    label=f"Autres ({len(other_sites)} sites)",
                )
            )
    elif mode == "stack":
        site_meter_map = {}
        for m in meters:
            site_meter_map.setdefault(m.site_id, []).append(m)
        site_names = {s.id: s.nom for s in db.query(Site).filter(Site.id.in_(list(site_meter_map.keys()))).all()}
        series = []
        for sid, ms in sorted(site_meter_map.items()):
            m_ids = [m.id for m in ms]
            label = site_names.get(sid, f"Site {sid}")
            series.append(
                _query_aggregate(
                    db, m_ids, bucket_expr, date_from, date_to, granularity, metric, key=f"site_{sid}", label=label
                )
            )
    else:  # split
        MAX_SPLIT = 8
        sorted_meters = sorted(meters, key=lambda m: m.id)
        main_meters = sorted_meters[:MAX_SPLIT]
        other_meters = sorted_meters[MAX_SPLIT:]

        series = [_query_single(db, m, bucket_expr, date_from, date_to, granularity, metric) for m in main_meters]
        if other_meters:
            other_ids = [m.id for m in other_meters]
            series.append(
                _query_aggregate(
                    db,
                    other_ids,
                    bucket_expr,
                    date_from,
                    date_to,
                    granularity,
                    metric,
                    key="others",
                    label="Autres",
                )
            )

    n_points = max((len(s["data"]) for s in series), default=0)
    expected = estimate_points(date_from, date_to, granularity)
    availability = _compute_availability(series, expected, granularity)

    # YoY comparison: query N-1 period and append _prev series
    if compare == "yoy":
        prev_series = _query_yoy_prev(
            db,
            meter_ids=meter_id_list,
            meters=meters,
            bucket_expr=bucket_expr,
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
            mode=mode,
            metric=metric,
            energy_vector=energy_vector,
        )
        series.extend(prev_series)

    return {
        "series": series,
        "meta": _meta(granularity, n_points, len(meters), date_from, date_to, metric, series=series),
        "availability": availability,
    }


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------

# Sampling interval in minutes for each granularity key
_SAMPLING_MINUTES = {
    "15min": 15,
    "30min": 30,
    "hourly": 60,
    "daily": 1440,
    "monthly": 43200,
}

# Granularities ordered from finest to coarsest
_GRANULARITY_ORDER = ["15min", "30min", "hourly", "daily", "monthly"]


def _available_granularities(sampling_minutes: int, span_days: int) -> List[str]:
    """Return granularities that are (a) >= data frequency and (b) stay under GRANULARITY_MAX_POINTS."""
    result = []
    for g in _GRANULARITY_ORDER:
        g_minutes = _SAMPLING_MINUTES[g]
        # Must not be finer than the actual data resolution
        if g_minutes < sampling_minutes:
            continue
        # Coarse guard: monthly needs at least 30 days
        if g == "monthly" and span_days < 30:
            continue
        # Fine guard: sub-hourly requires at most 14 days to stay under cap
        if g in ("15min", "30min") and span_days > 14:
            continue
        # Fine guard: hourly capped at 200 days (200×24 = 4800 < 5000)
        if g == "hourly" and span_days > 200:
            continue
        result.append(g)
    return result


def _meta(granularity, n_points, n_meters, date_from, date_to, metric, series=None):
    sampling_minutes = _SAMPLING_MINUTES.get(granularity, 60)
    span_days = max((date_to - date_from).days, 1)
    available = _available_granularities(sampling_minutes, span_days)
    # valid_count: points with non-null value in the aggregate series
    valid_count = 0
    if series:
        for s in series:
            valid_count = max(valid_count, sum(1 for p in s.get("data", []) if p.get("v") is not None))
    return {
        "granularity": granularity,
        "metric": metric,
        "n_points": n_points,
        "n_meters": n_meters,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "sampling_minutes": sampling_minutes,
        "available_granularities": available,
        "valid_count": valid_count,
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


def _resolve_best_freq(db, meter_ids, date_from, date_to, granularity: str):
    """Pick a single frequency to avoid double-counting overlapping readings.

    When a meter has both 15min and hourly data for the same period, summing
    both would inflate values ~2×.  We select the finest frequency that has
    ≥ 48 readings for the window.  Falls back to full compatible list only
    when no single frequency meets the threshold.
    """
    compatible = _COMPATIBLE_FREQS.get(granularity, list(FrequencyType))
    if len(compatible) <= 1:
        return compatible

    meter_filter = (
        MeterReading.meter_id.in_(meter_ids) if isinstance(meter_ids, list) else MeterReading.meter_id == meter_ids
    )
    for freq in compatible:  # ordered finest → coarsest
        cnt = (
            db.query(func.count(MeterReading.id))
            .filter(
                meter_filter,
                MeterReading.frequency == freq,
                MeterReading.timestamp >= date_from,
                MeterReading.timestamp < date_to,
            )
            .scalar()
            or 0
        )
        if cnt >= 48:
            return [freq]
    return compatible  # fallback: no single freq has enough data


def _base_query(db, meter_ids, bucket_expr, date_from, date_to, granularity: str = "daily"):
    """Shared bucket query base.

    Filters readings to a single best frequency to prevent double-counting
    when multiple overlapping frequencies exist (e.g. 15min + hourly).
    Monthly aggregate values are never included for daily or hourly charts.
    """
    best = _resolve_best_freq(db, meter_ids, date_from, date_to, granularity)
    meter_filter = (
        MeterReading.meter_id.in_(meter_ids) if isinstance(meter_ids, list) else MeterReading.meter_id == meter_ids
    )
    return (
        db.query(
            bucket_expr.label("bucket"),
            func.sum(MeterReading.value_kwh).label("total_kwh"),
            func.avg(MeterReading.quality_score).label("avg_quality"),
            func.avg(cast(MeterReading.is_estimated, SAInteger)).label("est_pct"),
        )
        .filter(
            meter_filter,
            MeterReading.timestamp >= date_from,
            MeterReading.timestamp < date_to,
            MeterReading.frequency.in_(best),
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
        data.append(
            {
                "t": row.bucket,
                "v": round(value, 2),
                "quality": round(row.avg_quality, 2) if row.avg_quality is not None else None,
                "estimated_pct": round(row.est_pct, 2) if row.est_pct is not None else 0.0,
            }
        )
    return {"key": key, "label": label, "data": data}


def _query_aggregate(db, meter_ids, bucket_expr, date_from, date_to, granularity, metric, key="total", label="Total"):
    rows = _base_query(db, meter_ids, bucket_expr, date_from, date_to, granularity).all()
    return _rows_to_series(key, label, rows, granularity, metric)


def _query_single(db, meter, bucket_expr, date_from, date_to, granularity, metric):
    rows = _base_query(db, meter.id, bucket_expr, date_from, date_to, granularity).all()
    label = meter.name or meter.meter_id or f"Meter {meter.id}"
    return _rows_to_series(f"meter_{meter.id}", label, rows, granularity, metric)


def _compute_availability(series: list, expected_points: int, granularity: str) -> list:
    """Compute availability stats per series: coverage, gaps."""
    bucket_delta = {
        "15min": timedelta(minutes=15),
        "30min": timedelta(minutes=30),
        "hourly": timedelta(hours=1),
        "daily": timedelta(days=1),
        "monthly": timedelta(days=30),
    }
    delta = bucket_delta.get(granularity, timedelta(days=1))
    result = []
    for s in series:
        actual = len(s["data"])
        coverage = round(actual / expected_points, 4) if expected_points > 0 else 0.0
        # Detect gaps (consecutive missing buckets)
        gaps = []
        timestamps = [pt["t"] for pt in s["data"]]
        for i in range(1, len(timestamps)):
            try:
                t_prev = datetime.fromisoformat(timestamps[i - 1])
                t_curr = datetime.fromisoformat(timestamps[i])
                gap_size = (t_curr - t_prev) / delta if delta.total_seconds() > 0 else 0
                if gap_size > 1.5:  # More than 1.5x expected interval = gap
                    gaps.append(
                        {
                            "from": timestamps[i - 1],
                            "to": timestamps[i],
                            "missing_buckets": int(gap_size) - 1,
                        }
                    )
            except (ValueError, TypeError):
                pass
        result.append(
            {
                "key": s["key"],
                "expected_points": expected_points,
                "actual_points": actual,
                "coverage_pct": round(coverage * 100, 1),
                "gaps": gaps[:20],  # Cap at 20 gaps to avoid huge payloads
            }
        )
    return result


# -------------------------------------------------------------------
# YoY comparison helpers (Step 10 — F1)
# -------------------------------------------------------------------


def _shift_timestamp_forward_1y(ts_str: str) -> str:
    """Shift a timestamp string forward by 1 year for YoY overlay alignment.

    Handles monthly ('YYYY-MM'), daily ('YYYY-MM-DD'), and datetime formats.
    """
    if len(ts_str) == 7:  # 'YYYY-MM'
        parts = ts_str.split("-")
        return f"{int(parts[0]) + 1}-{parts[1]}"
    try:
        dt = datetime.fromisoformat(ts_str)
        try:
            shifted = dt.replace(year=dt.year + 1)
        except ValueError:
            # Feb 29 → Feb 28
            shifted = dt.replace(year=dt.year + 1, day=28)
        if " " in ts_str:
            return shifted.isoformat(sep=" ")
        if len(ts_str) == 10:
            return shifted.strftime("%Y-%m-%d")
        return shifted.isoformat(sep=" ")
    except (ValueError, TypeError):
        return ts_str


def _query_yoy_prev(
    db,
    meter_ids,
    meters,
    bucket_expr,
    date_from,
    date_to,
    granularity,
    mode,
    metric,
    energy_vector,
):
    """Query the N-1 period and return _prev series with timestamps shifted +1 year."""
    try:
        prev_from = date_from.replace(year=date_from.year - 1)
        prev_to = date_to.replace(year=date_to.year - 1)
    except ValueError:
        prev_from = date_from.replace(year=date_from.year - 1, day=28)
        prev_to = date_to.replace(year=date_to.year - 1, day=28)

    if mode == "aggregate":
        raw = [
            _query_aggregate(
                db, meter_ids, bucket_expr, prev_from, prev_to, granularity, metric, key="total_prev", label="N-1"
            )
        ]
    elif mode in ("overlay", "stack"):
        site_meter_map = {}
        for m in meters:
            site_meter_map.setdefault(m.site_id, []).append(m)
        raw = []
        for sid in sorted(site_meter_map.keys())[:8]:
            m_ids = [m.id for m in site_meter_map[sid]]
            raw.append(
                _query_aggregate(
                    db,
                    m_ids,
                    bucket_expr,
                    prev_from,
                    prev_to,
                    granularity,
                    metric,
                    key=f"site_{sid}_prev",
                    label=f"Site {sid} (N-1)",
                )
            )
    else:
        raw = [
            _query_aggregate(
                db, meter_ids, bucket_expr, prev_from, prev_to, granularity, metric, key="total_prev", label="N-1"
            )
        ]

    # Shift timestamps +1 year to align with current period
    for s in raw:
        for pt in s["data"]:
            pt["t"] = _shift_timestamp_forward_1y(pt["t"])

    return raw


def compare_summary(
    db: Session,
    site_ids: List[int],
    date_from: datetime,
    date_to: datetime,
    energy_vector: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute N vs N-1 summary totals for KPI delta display."""
    from sqlalchemy import func as sqla_func

    meter_q = db.query(Meter).filter(Meter.site_id.in_(site_ids), Meter.is_active == True)
    if energy_vector:
        try:
            ev = EnergyVector(energy_vector)
            meter_q = meter_q.filter(Meter.energy_vector == ev)
        except ValueError:
            pass
    meters = meter_q.all()
    if not meters:
        return {"current_kwh": None, "previous_kwh": None, "delta_pct": None}

    meter_ids = [m.id for m in meters]

    def _sum_kwh(mids, dt_from, dt_to):
        best = _resolve_best_freq(db, mids, dt_from, dt_to, "daily")
        val = (
            db.query(sqla_func.sum(MeterReading.value_kwh))
            .filter(
                MeterReading.meter_id.in_(mids),
                MeterReading.timestamp >= dt_from,
                MeterReading.timestamp < dt_to,
                MeterReading.frequency.in_(best),
            )
            .scalar()
        )
        return round(val, 2) if val else None

    current_kwh = _sum_kwh(meter_ids, date_from, date_to)

    try:
        prev_from = date_from.replace(year=date_from.year - 1)
        prev_to = date_to.replace(year=date_to.year - 1)
    except ValueError:
        prev_from = date_from.replace(year=date_from.year - 1, day=28)
        prev_to = date_to.replace(year=date_to.year - 1, day=28)

    previous_kwh = _sum_kwh(meter_ids, prev_from, prev_to)

    delta_pct = None
    if current_kwh is not None and previous_kwh and previous_kwh > 0:
        delta_pct = round((current_kwh - previous_kwh) / previous_kwh * 100, 1)

    return {
        "current_kwh": current_kwh,
        "previous_kwh": previous_kwh,
        "delta_pct": delta_pct,
        "period_current": f"{date_from.date().isoformat()} / {date_to.date().isoformat()}",
        "period_previous": f"{prev_from.date().isoformat()} / {prev_to.date().isoformat()}",
    }
