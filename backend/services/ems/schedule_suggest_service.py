"""
PROMEOS -- Schedule Suggestion Service (Sprint V4.9)
Suggests operating schedule from actual consumption data (MeterReading).
Algorithm: build 7x24 avg power matrix, detect active hours from talon.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Meter, MeterReading, FrequencyType


def suggest_schedule_from_consumption(
    db: Session,
    site_id: int,
    days: int = 90,
) -> dict:
    """
    Analyze hourly consumption data to suggest operating schedule.

    Returns:
        {
            "schedule_suggested": {"open_days", "open_time", "close_time", "is_24_7"},
            "confidence": "high"|"medium"|"low",
            "talon_kw", "threshold_kw",
            "profiles": {0: [24 vals], ..., 6: [24 vals]},
            "n_readings", "active_days", "reasons": [str]
        }
    """
    # Find active meters for this site
    meter = (
        db.query(Meter)
        .filter_by(site_id=site_id, is_active=True)
        .first()
    )
    if not meter:
        return {
            "error": "no_meter",
            "reasons": ["Aucun compteur actif trouve pour ce site"],
            "schedule_suggested": None,
        }

    # Fetch hourly readings
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    readings = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id == meter.id,
            MeterReading.timestamp >= cutoff,
        )
        .order_by(MeterReading.timestamp)
        .all()
    )

    if len(readings) < 168:  # Less than 1 week of hourly data
        return {
            "error": "insufficient_data",
            "reasons": [f"Seulement {len(readings)} releves (minimum 168 requis)"],
            "n_readings": len(readings),
            "schedule_suggested": None,
        }

    # Build 7x24 matrix: day_of_week -> hour -> [values]
    matrix = defaultdict(lambda: defaultdict(list))  # dow -> hour -> [kw]
    for r in readings:
        dow = r.timestamp.weekday()  # 0=Monday
        hour = r.timestamp.hour
        matrix[dow][hour].append(r.value_kwh or 0)

    # Compute average power per slot
    profiles = {}
    all_values = []
    for dow in range(7):
        profile = []
        for h in range(24):
            vals = matrix[dow][h]
            avg = sum(vals) / len(vals) if vals else 0
            profile.append(round(avg, 2))
            all_values.extend(vals)
        profiles[dow] = profile

    if not all_values:
        return {
            "error": "no_data",
            "reasons": ["Aucune donnee de consommation exploitable"],
            "n_readings": len(readings),
            "schedule_suggested": None,
        }

    # Compute talon (P10 = 10th percentile)
    sorted_vals = sorted(all_values)
    p10_idx = max(0, int(len(sorted_vals) * 0.10) - 1)
    talon_kw = sorted_vals[p10_idx]
    threshold_kw = talon_kw * 1.5

    # Detect flat curve: if max/min ratio < 1.3 -> likely 24/7
    max_val = max(all_values) if all_values else 0
    min_val = min(all_values) if all_values else 0
    is_flat = (max_val <= 0) or (min_val > 0 and max_val / min_val < 1.3)

    if is_flat:
        return {
            "schedule_suggested": {
                "open_days": "0,1,2,3,4,5,6",
                "open_time": "00:00",
                "close_time": "23:59",
                "is_24_7": True,
            },
            "confidence": "medium",
            "talon_kw": round(talon_kw, 2),
            "threshold_kw": round(threshold_kw, 2),
            "profiles": profiles,
            "n_readings": len(readings),
            "active_days": 7,
            "reasons": ["Courbe plate detectee — site probablement 24/7"],
        }

    # Detect active hours per day
    active_days = []
    day_boundaries = {}  # dow -> (open_hour, close_hour)

    for dow in range(7):
        active_hours = [h for h in range(24) if profiles[dow][h] > threshold_kw]
        if len(active_hours) >= 4:
            active_days.append(dow)
            day_boundaries[dow] = (min(active_hours), max(active_hours))

    if not active_days:
        return {
            "schedule_suggested": {
                "open_days": "0,1,2,3,4",
                "open_time": "08:00",
                "close_time": "19:00",
                "is_24_7": False,
            },
            "confidence": "low",
            "talon_kw": round(talon_kw, 2),
            "threshold_kw": round(threshold_kw, 2),
            "profiles": profiles,
            "n_readings": len(readings),
            "active_days": 0,
            "reasons": ["Aucun jour avec activite significative detecte — horaires par defaut"],
        }

    # Compute median open/close across active days
    open_hours = [day_boundaries[d][0] for d in active_days]
    close_hours = [day_boundaries[d][1] for d in active_days]
    median_open = sorted(open_hours)[len(open_hours) // 2]
    median_close = sorted(close_hours)[len(close_hours) // 2]

    # Confidence based on reading count
    if len(readings) >= 2000:
        confidence = "high"
    elif len(readings) >= 500:
        confidence = "medium"
    else:
        confidence = "low"

    open_days_str = ",".join(str(d) for d in sorted(active_days))

    return {
        "schedule_suggested": {
            "open_days": open_days_str,
            "open_time": f"{median_open:02d}:00",
            "close_time": f"{median_close + 1:02d}:00",
            "is_24_7": False,
        },
        "confidence": confidence,
        "talon_kw": round(talon_kw, 2),
        "threshold_kw": round(threshold_kw, 2),
        "profiles": profiles,
        "n_readings": len(readings),
        "active_days": len(active_days),
        "reasons": [
            f"{len(active_days)} jours actifs detectes",
            f"Ouverture mediane: {median_open:02d}h - {median_close + 1:02d}h",
            f"Talon: {talon_kw:.1f} kW, seuil: {threshold_kw:.1f} kW",
        ],
    }
