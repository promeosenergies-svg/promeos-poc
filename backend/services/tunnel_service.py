"""
PROMEOS - Tunnel Service (Consumption Envelope)
Computes quantile-based envelopes (P10-P25-P50-P75-P90) per time slot
and calculates the percentage of readings "outside" the normal band.
"""
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session

from models import Meter, MeterReading, Site
from models.energy_models import FrequencyType


def _percentile(data: List[float], pct: float) -> float:
    """Compute percentile without numpy."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * pct / 100.0
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[-1]
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return round(d0 + d1, 4)


def _classify_day_type(ts: datetime) -> str:
    """Classify timestamp into day type: weekday or weekend."""
    return "weekend" if ts.weekday() >= 5 else "weekday"


def compute_tunnel(
    db: Session,
    site_id: int,
    days: int = 90,
    interval_minutes: int = 60,
    energy_type: str = "electricity",
) -> Dict[str, Any]:
    """
    Compute consumption tunnel (envelope) for a site.

    Groups readings by (day_type, hour) and computes quantiles P10/P25/P50/P75/P90.
    Then counts how many recent readings fall outside the P10-P90 band.

    Returns:
        {
            "site_id": int,
            "energy_type": str,
            "days": int,
            "readings_count": int,
            "envelope": {
                "weekday": [{"hour": 0, "p10": ..., "p25": ..., "p50": ..., "p75": ..., "p90": ...}, ...],
                "weekend": [...]
            },
            "outside_pct": float,      # % readings outside P10-P90
            "outside_count": int,
            "total_evaluated": int,
            "confidence": str,         # "high", "medium", "low"
            "confidence_score": float,  # 0-100
        }
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Find meters for this site and energy type
    meters = db.query(Meter).filter(
        Meter.site_id == site_id,
        Meter.is_active == True,
    ).all()

    if energy_type == "electricity":
        from models.energy_models import EnergyVector
        meters = [m for m in meters if m.energy_vector == EnergyVector.ELECTRICITY]
    elif energy_type == "gas":
        from models.energy_models import EnergyVector
        meters = [m for m in meters if m.energy_vector == EnergyVector.GAS]

    if not meters:
        return _empty_tunnel(site_id, energy_type, days)

    meter_ids = [m.id for m in meters]

    # Fetch readings
    readings = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_date,
            MeterReading.timestamp <= end_date,
        )
        .order_by(MeterReading.timestamp)
        .all()
    )

    if len(readings) < 48:
        return _empty_tunnel(site_id, energy_type, days, readings_count=len(readings))

    # Group by (day_type, hour) → list of kWh values
    hours_per_interval = interval_minutes / 60.0
    buckets: Dict[str, Dict[int, List[float]]] = {
        "weekday": defaultdict(list),
        "weekend": defaultdict(list),
    }

    for r in readings:
        day_type = _classify_day_type(r.timestamp)
        hour = r.timestamp.hour
        power_kw = r.value_kwh / hours_per_interval if hours_per_interval > 0 else r.value_kwh
        buckets[day_type][hour].append(power_kw)

    # Compute envelope per (day_type, hour)
    envelope = {}
    for day_type in ("weekday", "weekend"):
        slots = []
        for h in range(24):
            vals = buckets[day_type].get(h, [])
            if vals:
                slots.append({
                    "hour": h,
                    "p10": round(_percentile(vals, 10), 2),
                    "p25": round(_percentile(vals, 25), 2),
                    "p50": round(_percentile(vals, 50), 2),
                    "p75": round(_percentile(vals, 75), 2),
                    "p90": round(_percentile(vals, 90), 2),
                    "count": len(vals),
                })
            else:
                slots.append({"hour": h, "p10": 0, "p25": 0, "p50": 0, "p75": 0, "p90": 0, "count": 0})
        envelope[day_type] = slots

    # Count outside readings (last 7 days)
    recent_start = end_date - timedelta(days=7)
    outside_count = 0
    total_evaluated = 0

    for r in readings:
        if r.timestamp < recent_start:
            continue
        day_type = _classify_day_type(r.timestamp)
        hour = r.timestamp.hour
        power_kw = r.value_kwh / hours_per_interval if hours_per_interval > 0 else r.value_kwh

        slot = envelope[day_type][hour]
        if slot["count"] > 0:
            total_evaluated += 1
            if power_kw < slot["p10"] or power_kw > slot["p90"]:
                outside_count += 1

    outside_pct = round(outside_count / max(total_evaluated, 1) * 100, 1)

    # Confidence scoring
    confidence_score, confidence = _compute_confidence(len(readings), days)

    return {
        "site_id": site_id,
        "energy_type": energy_type,
        "days": days,
        "readings_count": len(readings),
        "envelope": envelope,
        "outside_pct": outside_pct,
        "outside_count": outside_count,
        "total_evaluated": total_evaluated,
        "confidence": confidence,
        "confidence_score": confidence_score,
    }


def _compute_confidence(readings_count: int, days: int) -> Tuple[float, str]:
    """Compute confidence level based on data density."""
    expected = days * 24  # hourly readings
    ratio = readings_count / max(expected, 1)

    if ratio >= 0.8 and readings_count >= 500:
        return min(100.0, round(ratio * 100, 1)), "high"
    elif ratio >= 0.5 and readings_count >= 200:
        return round(ratio * 80, 1), "medium"
    else:
        return round(ratio * 50, 1), "low"


def _empty_tunnel(site_id: int, energy_type: str, days: int, readings_count: int = 0) -> Dict:
    return {
        "site_id": site_id,
        "energy_type": energy_type,
        "days": days,
        "readings_count": readings_count,
        "envelope": {
            "weekday": [{"hour": h, "p10": 0, "p25": 0, "p50": 0, "p75": 0, "p90": 0, "count": 0} for h in range(24)],
            "weekend": [{"hour": h, "p10": 0, "p25": 0, "p50": 0, "p75": 0, "p90": 0, "count": 0} for h in range(24)],
        },
        "outside_pct": 0,
        "outside_count": 0,
        "total_evaluated": 0,
        "confidence": "low",
        "confidence_score": 0,
    }
