"""
PROMEOS — Schedule Detection Service V0
Auto-detect operating schedule from load curve (multi-interval per day).

Algorithm:
  A) Per-day baseload subtraction (Q10)
  B) Median activity profile per day-of-week
  C) Threshold + interval extraction (multi-plage)
  D) Post-processing: gap fill <=30min, drop <30min, no midnight cross
  E) Confidence: coverage × stability × separation

Inputs: MeterReading (15min / 30min / hourly)
Output: { detected_schedule, confidence, evidence }
"""
import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Site, Meter, MeterReading
from models.energy_models import FrequencyType, EnergyVector
from models.site_operating_schedule import SiteOperatingSchedule

logger = logging.getLogger(__name__)

# Day keys matching frontend/backend convention: 0=Mon, 6=Sun
DOW_KEYS = ["0", "1", "2", "3", "4", "5", "6"]

# Algo params
MIN_DAYS = 10
DEFAULT_WINDOW_DAYS = 56  # 8 weeks
FALLBACK_WINDOW_DAYS = 28  # 4 weeks
GAP_FILL_MINUTES = 30
MIN_INTERVAL_MINUTES = 30
EPSILON_ABS = 0.1  # kWh minimum threshold for activity
ACTIVITY_QUANTILE = 0.70  # q70 for threshold


def _quantile(values: list, q: float) -> float:
    """Simple quantile (no numpy dependency)."""
    if not values:
        return 0.0
    s = sorted(values)
    idx = q * (len(s) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _median(values: list) -> float:
    return _quantile(values, 0.5)


def _freq_minutes(freq: FrequencyType) -> int:
    """Convert frequency to minutes."""
    return {
        FrequencyType.MIN_15: 15,
        FrequencyType.MIN_30: 30,
        FrequencyType.HOURLY: 60,
    }.get(freq, 60)


def _minutes_to_hhmm(m: int) -> str:
    """Convert total minutes to HH:MM string."""
    h = min(23, m // 60)
    mm = m % 60
    return f"{h:02d}:{mm:02d}"


def _fetch_readings(db: Session, site_id: int, days: int):
    """Fetch sub-daily readings for a site."""
    meters = db.query(Meter).filter(
        Meter.site_id == site_id,
        Meter.is_active == True,
        Meter.energy_vector == EnergyVector.ELECTRICITY,
    ).all()
    if not meters:
        return [], 60  # no meters

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    meter_ids = [m.id for m in meters]
    readings = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= cutoff,
            MeterReading.frequency.in_([
                FrequencyType.MIN_15,
                FrequencyType.MIN_30,
                FrequencyType.HOURLY,
            ]),
        )
        .order_by(MeterReading.timestamp)
        .all()
    )

    # Determine dominant frequency
    freq_counts = defaultdict(int)
    for r in readings:
        freq_counts[r.frequency] += 1
    dominant = max(freq_counts, key=freq_counts.get) if freq_counts else FrequencyType.HOURLY
    step_min = _freq_minutes(dominant)

    return readings, step_min


def detect_schedule(db: Session, site_id: int, window_days: int = DEFAULT_WINDOW_DAYS) -> dict:
    """Detect operating schedule from load curve.

    Returns dict with detected_schedule, confidence, evidence.
    Raises ValueError if insufficient data.
    """
    readings, step_min = _fetch_readings(db, site_id, window_days)

    # Fallback to shorter window
    if len(readings) < MIN_DAYS * (24 * 60 // step_min):
        if window_days > FALLBACK_WINDOW_DAYS:
            readings, step_min = _fetch_readings(db, site_id, FALLBACK_WINDOW_DAYS)
            window_days = FALLBACK_WINDOW_DAYS

    slots_per_day = 24 * 60 // step_min

    # ── A) Group by date, compute per-day baseload, extract activity ──
    by_date = defaultdict(list)
    for r in readings:
        d = r.timestamp.date()
        minute_of_day = r.timestamp.hour * 60 + r.timestamp.minute
        by_date[d].append((minute_of_day, r.value_kwh))

    if len(by_date) < MIN_DAYS:
        raise ValueError(
            f"Donnees insuffisantes: {len(by_date)} jours (minimum {MIN_DAYS})"
        )

    # Per-day baseload + activity series
    # Keyed by (dow, minute_of_day) → list of activity values
    dow_activity = defaultdict(lambda: defaultdict(list))
    day_counts = defaultdict(int)

    for d, points in by_date.items():
        dow = d.weekday()  # 0=Mon, 6=Sun
        day_counts[dow] += 1
        values = [v for _, v in points]
        baseload = _quantile(values, 0.10) if len(values) >= 3 else min(values)

        for minute, kwh in points:
            # Snap to step grid
            slot = (minute // step_min) * step_min
            activity = max(0.0, kwh - baseload)
            dow_activity[dow][slot].append(activity)

    # ── B) Median activity profile per DOW ──
    dow_profiles = {}  # dow → [(slot_minute, median_activity), ...]
    for dow in range(7):
        slots = dow_activity[dow]
        profile = []
        for slot in range(0, 24 * 60, step_min):
            vals = slots.get(slot, [])
            med = _median(vals) if vals else 0.0
            profile.append((slot, med))
        dow_profiles[dow] = profile

    # ── C) Threshold + intervals per DOW ──
    detected = {}
    all_active_activities = []
    all_inactive_activities = []

    for dow in range(7):
        profile = dow_profiles[dow]
        activities = [a for _, a in profile if a > 0]

        # Threshold = max(epsilon, q70)
        threshold = max(EPSILON_ABS, _quantile(activities, ACTIVITY_QUANTILE)) if activities else EPSILON_ABS

        # Mark active slots
        active_slots = []
        for slot, act in profile:
            is_active = act >= threshold
            active_slots.append((slot, is_active, act))
            if is_active:
                all_active_activities.append(act)
            else:
                all_inactive_activities.append(act)

        # Convert to intervals
        intervals = _slots_to_intervals(active_slots, step_min)
        detected[str(dow)] = intervals

    # ── D) Confidence ──
    evidence = _compute_confidence(
        by_date, day_counts, dow_profiles, window_days, step_min,
        all_active_activities, all_inactive_activities,
    )

    return {
        "site_id": site_id,
        "window_days": window_days,
        "detected_schedule": detected,
        "confidence": evidence["confidence"],
        "confidence_label": evidence["confidence_label"],
        "evidence": evidence,
    }


def _slots_to_intervals(active_slots: list, step_min: int) -> list:
    """Convert list of (slot_minute, is_active, activity) to intervals with post-processing."""
    if not active_slots:
        return []

    # Extract raw intervals
    raw_intervals = []
    current_start = None
    for slot, is_active, _ in active_slots:
        if is_active and current_start is None:
            current_start = slot
        elif not is_active and current_start is not None:
            raw_intervals.append({"start": current_start, "end": slot})
            current_start = None
    if current_start is not None:
        # Close at end of day
        last_slot = active_slots[-1][0]
        raw_intervals.append({"start": current_start, "end": min(last_slot + step_min, 24 * 60 - 1)})

    if not raw_intervals:
        return []

    # Post-process: fill gaps <= 30 min
    merged = [raw_intervals[0].copy()]
    for iv in raw_intervals[1:]:
        gap = iv["start"] - merged[-1]["end"]
        if gap <= GAP_FILL_MINUTES:
            merged[-1]["end"] = iv["end"]
        else:
            merged.append(iv.copy())

    # Post-process: drop intervals < 30 min
    merged = [iv for iv in merged if (iv["end"] - iv["start"]) >= MIN_INTERVAL_MINUTES]

    # Cap at 23:59, no midnight crossing (already guaranteed by construction)
    result = []
    for iv in merged:
        start_m = max(0, iv["start"])
        end_m = min(24 * 60 - 1, iv["end"])
        if start_m < end_m:
            result.append({
                "start": _minutes_to_hhmm(start_m),
                "end": _minutes_to_hhmm(end_m),
            })

    return result


def _compute_confidence(
    by_date: dict, day_counts: dict, dow_profiles: dict,
    window_days: int, step_min: int,
    active_acts: list, inactive_acts: list,
) -> dict:
    """Compute confidence score and breakdown."""
    # Coverage: actual days / expected days
    expected_days = window_days
    actual_days = len(by_date)
    coverage = min(1.0, actual_days / max(1, expected_days))

    # Stability: std of first start per week (lower = better)
    # Approximate: std of start times across days for each dow
    start_times_by_dow = defaultdict(list)
    for d, points in by_date.items():
        dow = d.weekday()
        profile = dow_profiles.get(dow, [])
        threshold_acts = [a for _, a in profile if a > 0]
        threshold = max(EPSILON_ABS, _quantile(threshold_acts, ACTIVITY_QUANTILE)) if threshold_acts else EPSILON_ABS
        # Find first active slot for this specific day
        day_values = {(m // step_min) * step_min: v for m, v in points}
        baseload = _quantile(list(day_values.values()), 0.10) if day_values else 0
        for slot in range(0, 24 * 60, step_min):
            val = day_values.get(slot, 0)
            if max(0, val - baseload) >= threshold:
                start_times_by_dow[dow].append(slot)
                break

    if start_times_by_dow:
        stds = []
        for dow, starts in start_times_by_dow.items():
            if len(starts) >= 2:
                mean = sum(starts) / len(starts)
                variance = sum((s - mean) ** 2 for s in starts) / len(starts)
                stds.append(math.sqrt(variance))
        avg_std = sum(stds) / len(stds) if stds else 120
        # Score: 0 std = 1.0, 120min std = 0.0
        stability_score = max(0.0, 1.0 - avg_std / 120.0)
    else:
        stability_score = 0.0

    # Separation: median(active) / (median(inactive) + eps)
    med_active = _median(active_acts) if active_acts else 0
    med_inactive = _median(inactive_acts) if inactive_acts else 0
    separation = med_active / (med_inactive + 0.01)
    separation_score = min(1.0, separation / 5.0)  # ratio 5 = perfect

    # Final confidence
    confidence = max(0.0, min(1.0,
        0.4 * coverage + 0.3 * stability_score + 0.3 * separation_score
    ))
    confidence = round(confidence, 2)

    if confidence >= 0.7:
        label = "ELEVEE"
    elif confidence >= 0.4:
        label = "MOYEN"
    else:
        label = "FAIBLE"

    return {
        "confidence": confidence,
        "confidence_label": label,
        "coverage": round(coverage, 3),
        "coverage_days": actual_days,
        "expected_days": expected_days,
        "stability_score": round(stability_score, 3),
        "stability_avg_std_min": round(avg_std if start_times_by_dow else 0, 1),
        "separation_score": round(separation_score, 3),
        "separation_ratio": round(separation, 2),
        "baseload_stats": {
            "median_active_kwh": round(med_active, 3),
            "median_inactive_kwh": round(med_inactive, 3),
        },
    }


def compare_schedules(declared: dict, detected: dict) -> dict:
    """Compare declared vs detected schedule, per-day delta.

    Both inputs: {"0": [{"start":"08:00","end":"19:00"},...], ...}
    Returns per-day diff with delta_minutes and status.
    """
    diff = {}
    any_mismatch = False

    for dow_key in DOW_KEYS:
        dec_slots = declared.get(dow_key, [])
        det_slots = detected.get(dow_key, [])

        # Total active minutes
        dec_min = sum(_hhmm_to_min(s["end"]) - _hhmm_to_min(s["start"]) for s in dec_slots)
        det_min = sum(_hhmm_to_min(s["end"]) - _hhmm_to_min(s["start"]) for s in det_slots)

        delta = abs(dec_min - det_min)
        # Mismatch if delta > 60 min or different number of intervals
        is_mismatch = delta > 60 or len(dec_slots) != len(det_slots)

        if is_mismatch:
            any_mismatch = True

        diff[dow_key] = {
            "declared_intervals": len(dec_slots),
            "detected_intervals": len(det_slots),
            "declared_minutes": dec_min,
            "detected_minutes": det_min,
            "delta_minutes": delta,
            "status": "MISMATCH" if is_mismatch else "OK",
        }

    return {
        "diff": diff,
        "global_status": "MISMATCH" if any_mismatch else "OK",
    }


def _hhmm_to_min(t: str) -> int:
    """Parse HH:MM to minutes."""
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def get_declared_intervals(db: Session, site_id: int) -> dict:
    """Get declared schedule as intervals dict. Legacy fallback if no intervals_json."""
    sched = db.query(SiteOperatingSchedule).filter(
        SiteOperatingSchedule.site_id == site_id
    ).first()

    if sched and sched.intervals_json:
        try:
            return json.loads(sched.intervals_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Legacy fallback
    if sched:
        open_days = set(int(d) for d in sched.open_days.split(",") if d.strip())
        result = {}
        for k in DOW_KEYS:
            if int(k) in open_days:
                result[k] = [{"start": sched.open_time, "end": sched.close_time}]
            else:
                result[k] = []
        return result

    # Default: Mon-Fri 08:00-19:00
    default = {}
    for k in DOW_KEYS:
        default[k] = [{"start": "08:00", "end": "19:00"}] if int(k) < 5 else []
    return default
