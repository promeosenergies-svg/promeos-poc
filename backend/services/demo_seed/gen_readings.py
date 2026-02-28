"""
PROMEOS - Demo Seed: Meter Readings Generator
Generates hourly and 15-min readings per meter with realistic building profiles.

V86 — rich intraday patterns:
  - Per-hour normalized pattern (24 values, 0.0–1.0) per building type
  - Peak consumption scaled by subscribed power (psub / 100 kVA)
  - Day-of-week variation (weekday vs weekend)
  - Temperature sensitivity (heating < 15 °C, cooling > 22 °C)
  - Seasonal multiplier from _SEASONAL_MULT (shared with monthly generator)
"""
import math
import random
from datetime import datetime, timedelta

from models import MeterReading, FrequencyType


# ── Legacy profile dict (kept for vacation_weeks + backward compat) ──────────
_PROFILES = {
    "office":    {"heat": 1.5, "cool": 0.8, "peak_h": (8, 18)},
    "hotel":     {"heat": 2.0, "cool": 1.2, "peak_h": (7, 22)},
    "retail":    {"heat": 1.0, "cool": 1.5, "peak_h": (9, 20)},
    "warehouse": {"heat": 0.5, "cool": 0.3, "peak_h": (6, 20)},
    "school":    {"heat": 2.5, "cool": 0.3, "peak_h": (8, 17),
                  "vacation_weeks": [1, 2, 7, 8, 16, 17, 27, 28, 29, 30, 31, 32, 33, 34]},
    "hospital":  {"heat": 2.0, "cool": 1.8, "peak_h": (7, 21)},
}

# ── Per-hour normalized patterns (index 0 = 00:00 … 23 = 23:00) ─────────────
# Values 0.0–1.0: fraction of peak kW consumed at that hour on a typical weekday.
_HOURLY_PATTERN = {
    # Office: clear 8h–18h activity, morning ramp, lunch dip at 12h, low nights
    "office": [
        0.12, 0.10, 0.10, 0.10, 0.11, 0.14,  # 00–05 night standby
        0.22, 0.48, 0.74, 0.92, 1.00, 0.96,  # 06–11 morning ramp → peak
        0.76, 0.79, 1.00, 0.97, 0.92, 0.74,  # 12–17 lunch dip, afternoon plateau
        0.50, 0.30, 0.22, 0.17, 0.14, 0.12,  # 18–23 wind-down
    ],
    # Hotel: high baseload 24/7, breakfast spike, dinner peak
    "hotel": [
        0.52, 0.48, 0.44, 0.42, 0.44, 0.55,  # 00–05 night ops
        0.68, 0.88, 0.96, 0.90, 0.82, 0.88,  # 06–11 breakfast peak
        0.90, 0.84, 0.78, 0.80, 0.85, 0.92,  # 12–17 lunch + afternoon
        1.00, 1.00, 0.96, 0.88, 0.74, 0.62,  # 18–23 dinner peak
    ],
    # Warehouse / industrial: two shifts, lunch break, minimal nights
    "warehouse": [
        0.28, 0.25, 0.22, 0.22, 0.26, 0.42,  # 00–05 security + standby
        0.65, 0.85, 1.00, 1.00, 0.97, 0.82,  # 06–11 morning shift
        0.58, 0.80, 0.98, 1.00, 0.95, 0.80,  # 12–17 lunch break → afternoon
        0.55, 0.40, 0.33, 0.30, 0.28, 0.28,  # 18–23 evening
    ],
    # School: strong 8h–17h, lunch dip, very low evenings/weekends
    "school": [
        0.10, 0.08, 0.08, 0.08, 0.09, 0.14,  # 00–05 standby
        0.25, 0.52, 0.82, 0.94, 1.00, 0.96,  # 06–11 morning ramp
        0.62, 0.52, 0.88, 0.94, 0.75, 0.50,  # 12–17 lunch break, afternoon
        0.26, 0.18, 0.14, 0.12, 0.10, 0.10,  # 18–23 minimal
    ],
    # Hospital: 24/7, slight overnight dip, afternoon peak
    "hospital": [
        0.65, 0.60, 0.56, 0.55, 0.58, 0.65,  # 00–05 overnight
        0.75, 0.86, 0.94, 0.99, 1.00, 0.99,  # 06–11 morning
        0.94, 0.92, 0.98, 1.00, 0.99, 0.95,  # 12–17 afternoon peak
        0.90, 0.85, 0.82, 0.78, 0.74, 0.68,  # 18–23 evening
    ],
    # Retail: closed nights, ramp at opening, peak midday + late afternoon
    "retail": [
        0.12, 0.10, 0.08, 0.08, 0.10, 0.16,  # 00–05 overnight
        0.22, 0.40, 0.65, 0.84, 0.95, 1.00,  # 06–11 opening ramp
        1.00, 0.98, 0.96, 0.99, 1.00, 0.95,  # 12–17 peak shopping
        0.85, 0.72, 0.52, 0.30, 0.18, 0.13,  # 18–23 closing
    ],
}

# ── Peak consumption at 100 kVA subscribed power baseline (kWh/h ≡ kW) ──────
# Scaled at runtime by (psub / 100), so a 200 kVA office gets 2× these values.
# Calibrated so annual consumption roughly matches packs.py annual_kwh targets.
_BASE_KW = {
    "office":    80,   # ×2.0 (200 kVA) → ~160 kW peak, ~700k kWh/yr
    "hotel":     65,   # ×2.5 (250 kVA) → ~162 kW peak, ~1.0 M kWh/yr
    "warehouse": 110,  # ×4.0 (400 kVA) → ~440 kW peak, ~2.3 M kWh/yr
    "school":    70,   # ×1.5 (150 kVA) → ~105 kW peak, ~420k kWh/yr
    "hospital":  85,   # → varies
    "retail":    75,
}

# ── Day-of-week multipliers (Mon=0 … Sun=6) ──────────────────────────────────
_DOW_MULT = {
    "office":    [1.00, 0.98, 0.97, 0.97, 0.94, 0.38, 0.25],
    "hotel":     [0.88, 0.86, 0.88, 0.92, 0.95, 1.00, 1.00],
    "warehouse": [1.00, 1.00, 0.98, 0.98, 0.95, 0.65, 0.40],
    "school":    [1.00, 0.99, 0.98, 0.98, 0.95, 0.15, 0.12],
    "hospital":  [1.00, 1.00, 1.00, 1.00, 1.00, 0.95, 0.90],
    "retail":    [0.85, 0.88, 0.90, 0.92, 0.98, 1.00, 0.95],
}

# ── Temperature sensitivity (multiplicative, per °C outside comfort zone) ────
# heat_pct: % increase per °C below 15 °C
# cool_pct: % increase per °C above 22 °C
_TEMP_SENS = {
    "office":    (0.035, 0.015),
    "hotel":     (0.030, 0.025),
    "warehouse": (0.015, 0.008),
    "school":    (0.040, 0.010),
    "hospital":  (0.025, 0.020),
    "retail":    (0.020, 0.018),
}


def generate_readings(db, meters: list, site_profiles: dict,
                      temp_lookup: dict, days: int, rng: random.Random) -> int:
    """
    Generate hourly readings for each meter.

    Args:
        meters: list of Meter ORM objects
        site_profiles: {site_id: profile_name}
        temp_lookup: {site_id: {"YYYY-MM-DD": temp_avg_c}}
        days: lookback days
        rng: seeded Random instance

    Returns:
        total number of readings created
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    total = 0

    for meter in meters:
        profile_name = site_profiles.get(meter.site_id, "office")
        profile = _PROFILES.get(profile_name, _PROFILES["office"])
        site_temps = temp_lookup.get(meter.site_id, {})
        psub = meter.subscribed_power_kva or 80

        readings = _gen_meter_readings(
            meter.id, profile_name, profile, site_temps, start, days, psub, rng
        )
        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


def _gen_meter_readings(meter_id: int, profile_name: str, profile: dict,
                        temps: dict, start: datetime, days: int, psub: float,
                        rng: random.Random) -> list:
    """
    Generate hourly readings for a single meter.

    Uses per-hour normalized patterns (_HOURLY_PATTERN) scaled by psub,
    day-of-week variation (_DOW_MULT), temperature sensitivity (_TEMP_SENS),
    and seasonal multiplier (_SEASONAL_MULT) for realistic building load curves.
    """
    readings = []
    pattern   = _HOURLY_PATTERN.get(profile_name, _HOURLY_PATTERN["office"])
    base_kw   = _BASE_KW.get(profile_name, _BASE_KW["office"])
    dow_mult  = _DOW_MULT.get(profile_name, _DOW_MULT["office"])
    heat_pct, cool_pct = _TEMP_SENS.get(profile_name, (0.030, 0.015))
    scale     = psub / 100.0          # calibrate to site subscribed power
    max_kw    = psub * 1.2            # realistic guardrail (120% of psub)
    vacation_weeks = profile.get("vacation_weeks", [])

    for day_offset in range(days):
        dt      = start + timedelta(days=day_offset)
        dow     = dt.weekday()        # 0=Mon … 6=Sun
        day_key = dt.date().isoformat()
        temp    = temps.get(day_key, 12.0)
        is_vacation = dt.isocalendar()[1] in vacation_weeks if vacation_weeks else False

        # Day-level multipliers
        day_dow = dow_mult[dow]
        if is_vacation:
            day_dow *= 0.15           # school/office during holiday = near-zero

        # Seasonal (matches monthly generator: peak winter, low summer)
        seasonal = _SEASONAL_MULT.get(dt.month, 1.0)

        # Temperature adjustment (multiplicative: +% per °C outside comfort band)
        temp_adj = 1.0 + heat_pct * max(0.0, 15.0 - temp) \
                       + cool_pct * max(0.0, temp - 22.0)

        for hour in range(24):
            ts = dt.replace(hour=hour, minute=0, second=0, microsecond=0)

            # Core value: pattern × psub calibration × time factors
            value = base_kw * scale * pattern[hour] * day_dow * seasonal * temp_adj

            # ── Anomalies (same temporal windows as V1, rescaled) ───────────
            # Anomaly 1: elevated night baseload (days 30–44, weeknights only)
            if 30 <= day_offset <= 44 and pattern[hour] < 0.25 and dow < 5:
                value *= 2.5

            # Anomaly 2: unexpected weekend spike (days 35–36)
            if day_offset in [35, 36] and dow >= 5:
                value = base_kw * scale * 1.3

            # Anomaly 3: sudden demand spike (day 55, 14:00)
            if day_offset == 55 and hour == 14:
                value = base_kw * scale * 2.8

            # Anomaly 4: flat curve / equipment malfunction (days 70–73)
            if 70 <= day_offset <= 73:
                value = base_kw * scale * 0.15

            # Noise ±7% + guardrail
            value *= rng.uniform(0.93, 1.07)
            value = max(0.1, min(round(value, 2), max_kw))

            readings.append(MeterReading(
                meter_id=meter_id, timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=value, is_estimated=False,
            ))

    return readings


# ── Monthly readings (V52 — helios) ─────────────────────────────────────────

# Monthly base kWh per profile (average month)
_MONTHLY_BASE = {
    "office":    25000,
    "hotel":     80000,
    "retail":    35000,
    "warehouse": 50000,
    "school":    18000,
    "hospital":  120000,
}

# Seasonal multiplier by month (1=Jan..12=Dec), cosine-based: peak winter, low summer
_SEASONAL_MULT = {
    1: 1.25, 2: 1.20, 3: 1.10, 4: 0.95, 5: 0.85, 6: 0.80,
    7: 0.75, 8: 0.75, 9: 0.85, 10: 0.95, 11: 1.10, 12: 1.25,
}

# School vacation months — consumption drops to 20%
_SCHOOL_VACATION_MONTHS = {7, 8}


def generate_monthly_readings(db, meters: list, site_profiles: dict,
                              months: int, rng: random.Random) -> int:
    """
    Generate monthly aggregated readings (V52 helios).

    Args:
        meters: list of Meter ORM objects
        site_profiles: {site_id: profile_name}
        months: number of months of history
        rng: seeded Random instance

    Returns:
        total number of readings created
    """
    now = datetime.utcnow()
    total = 0

    for meter in meters:
        profile_name = site_profiles.get(meter.site_id, "office")
        base_kwh = _MONTHLY_BASE.get(profile_name, _MONTHLY_BASE["office"])
        psub = meter.subscribed_power_kva or 80
        # Scale base by subscribed power (bigger site → more consumption)
        scale = psub / 100.0
        is_school = profile_name == "school"

        # Pick 1-2 anomaly months (spike to 180%)
        anomaly_months = set(rng.sample(range(months), min(2, months)))

        readings = []
        seen_months = set()
        for m_offset in range(months):
            # Compute exact month by subtracting m_offset months from current month
            target_month = now.month - (months - m_offset)
            target_year = now.year + (target_month - 1) // 12
            target_month = ((target_month - 1) % 12) + 1
            dt = datetime(target_year, target_month, 1)
            # Skip duplicates (safety)
            key = (meter.id, dt)
            if key in seen_months:
                continue
            seen_months.add(key)
            month_num = dt.month

            # Seasonal variation
            seasonal = _SEASONAL_MULT.get(month_num, 1.0)
            value = base_kwh * scale * seasonal

            # School vacation
            if is_school and month_num in _SCHOOL_VACATION_MONTHS:
                value *= 0.20

            # Anomaly spike
            if m_offset in anomaly_months:
                value *= 1.80

            # Noise
            value *= rng.uniform(0.92, 1.08)
            value = max(100, round(value, 0))

            readings.append(MeterReading(
                meter_id=meter.id, timestamp=dt,
                frequency=FrequencyType.MONTHLY,
                value_kwh=value, is_estimated=False,
            ))

        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


# ── 15-minute readings (V85 — helios rich data) ─────────────────────────────

def generate_15min_readings(db, meters: list, site_profiles: dict,
                            temp_lookup: dict, days: int,
                            rng: random.Random) -> int:
    """
    Generate 15-minute interval readings for the last `days` days.

    Each 15-min slot = hourly_value / 4 + intra-hour noise (±5%).
    Uses same rich patterns as generate_readings().
    Idempotent via INSERT OR IGNORE.

    Returns:
        total number of readings created
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    total = 0

    for meter in meters:
        profile_name = site_profiles.get(meter.site_id, "office")
        profile = _PROFILES.get(profile_name, _PROFILES["office"])
        site_temps = temp_lookup.get(meter.site_id, {})
        psub = meter.subscribed_power_kva or 80

        readings = _gen_15min_meter_readings(
            meter.id, profile_name, profile, site_temps, start, days, psub, rng
        )
        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


def _gen_15min_meter_readings(meter_id: int, profile_name: str, profile: dict,
                               temps: dict, start: datetime, days: int,
                               psub: float, rng: random.Random) -> list:
    """Generate 15-min readings for a single meter (4 slots per hour)."""
    readings = []
    pattern   = _HOURLY_PATTERN.get(profile_name, _HOURLY_PATTERN["office"])
    base_kw   = _BASE_KW.get(profile_name, _BASE_KW["office"])
    dow_mult  = _DOW_MULT.get(profile_name, _DOW_MULT["office"])
    heat_pct, cool_pct = _TEMP_SENS.get(profile_name, (0.030, 0.015))
    scale     = psub / 100.0
    max_kw    = psub * 1.2
    vacation_weeks = profile.get("vacation_weeks", [])

    for day_offset in range(days):
        dt      = start + timedelta(days=day_offset)
        dow     = dt.weekday()
        day_key = dt.date().isoformat()
        temp    = temps.get(day_key, 12.0)
        is_vacation = dt.isocalendar()[1] in vacation_weeks if vacation_weeks else False

        day_dow  = dow_mult[dow]
        if is_vacation:
            day_dow *= 0.15
        seasonal = _SEASONAL_MULT.get(dt.month, 1.0)
        temp_adj = 1.0 + heat_pct * max(0.0, 15.0 - temp) \
                       + cool_pct * max(0.0, temp - 22.0)

        for hour in range(24):
            # Compute hourly base (same logic as _gen_meter_readings)
            hourly_value = base_kw * scale * pattern[hour] * day_dow * seasonal * temp_adj

            # Anomaly injection (same windows)
            if 30 <= day_offset <= 44 and pattern[hour] < 0.25 and dow < 5:
                hourly_value *= 2.5
            if day_offset in [35, 36] and dow >= 5:
                hourly_value = base_kw * scale * 1.3
            if day_offset == 55 and hour == 14:
                hourly_value = base_kw * scale * 2.8
            if 70 <= day_offset <= 73:
                hourly_value = base_kw * scale * 0.15

            hourly_value *= rng.uniform(0.93, 1.07)
            hourly_value = max(0.1, min(hourly_value, max_kw))

            # Split into 4 × 15-min slots with intra-hour noise
            slot_base = hourly_value / 4.0
            for quarter in range(4):
                ts = dt.replace(hour=hour, minute=quarter * 15,
                                second=0, microsecond=0)
                slot_val = slot_base * rng.uniform(0.95, 1.05)
                slot_val = max(0.01, round(slot_val, 3))

                readings.append(MeterReading(
                    meter_id=meter_id, timestamp=ts,
                    frequency=FrequencyType.MIN_15,
                    value_kwh=slot_val, is_estimated=False,
                ))

    return readings


def _bulk_insert_ignore(db, readings: list):
    """
    Insert readings with ON CONFLICT IGNORE — safety net against duplicate
    (meter_id, timestamp) pairs that would crash bulk_save_objects.
    Falls back to bulk_save_objects for non-SQLite engines.
    """
    if not readings:
        return
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect == "sqlite":
        from sqlalchemy import text
        stmt = text(
            "INSERT OR IGNORE INTO meter_reading "
            "(meter_id, timestamp, frequency, value_kwh, is_estimated, created_at) "
            "VALUES (:meter_id, :ts, :freq, :kwh, :est, :cat)"
        )
        params = [
            {
                "meter_id": r.meter_id,
                "ts": r.timestamp.isoformat() if r.timestamp else None,
                "freq": r.frequency.name if hasattr(r.frequency, "name") else str(r.frequency),
                "kwh": r.value_kwh,
                "est": 1 if r.is_estimated else 0,
                "cat": r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat(),
            }
            for r in readings
        ]
        db.execute(stmt, params)
    else:
        db.bulk_save_objects(readings)
