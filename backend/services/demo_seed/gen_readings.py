"""
PROMEOS - Demo Seed: Meter Readings Generator
Generates 90 days of hourly readings per meter with profile-aware patterns.
"""
import math
import random
from datetime import datetime, timedelta

from models import MeterReading, FrequencyType


# Usage profiles — consumption patterns per hour
_PROFILES = {
    "office":    {"peak": 35, "shoulder": 18, "night": 6, "weekend": 5,
                  "peak_h": (8, 18), "heat": 1.5, "cool": 0.8},
    "hotel":     {"peak": 25, "shoulder": 20, "night": 15, "weekend": 22,
                  "peak_h": (7, 22), "heat": 2.0, "cool": 1.2},
    "retail":    {"peak": 40, "shoulder": 15, "night": 4, "weekend": 38,
                  "peak_h": (9, 20), "heat": 1.0, "cool": 1.5},
    "warehouse": {"peak": 20, "shoulder": 15, "night": 12, "weekend": 10,
                  "peak_h": (6, 20), "heat": 0.5, "cool": 0.3},
    "school":    {"peak": 28, "shoulder": 12, "night": 3, "weekend": 3,
                  "peak_h": (8, 17), "heat": 2.5, "cool": 0.3,
                  "vacation_weeks": [1, 2, 7, 8, 16, 17, 27, 28, 29, 30, 31, 32, 33, 34]},
    "hospital":  {"peak": 45, "shoulder": 35, "night": 28, "weekend": 30,
                  "peak_h": (7, 21), "heat": 2.0, "cool": 1.8},
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
            meter.id, profile, site_temps, start, days, psub, rng
        )
        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


def _gen_meter_readings(meter_id: int, profile: dict, temps: dict,
                        start: datetime, days: int, psub: float,
                        rng: random.Random) -> list:
    """Generate readings for a single meter."""
    readings = []
    peak_start, peak_end = profile["peak_h"]
    vacation_weeks = profile.get("vacation_weeks", [])
    max_kw = psub * 3  # guardrail

    for day_offset in range(days):
        dt = start + timedelta(days=day_offset)
        is_weekend = dt.weekday() >= 5
        day_key = dt.date().isoformat()
        temp = temps.get(day_key, 12.0)
        is_vacation = dt.isocalendar()[1] in vacation_weeks if vacation_weeks else False

        for hour in range(24):
            ts = dt.replace(hour=hour, minute=0, second=0, microsecond=0)

            # Base from profile
            if is_weekend or is_vacation:
                base = profile["weekend"]
            elif peak_start <= hour <= peak_end:
                base = profile["peak"]
            elif hour == peak_start - 1 or peak_end < hour <= peak_end + 2:
                base = profile["shoulder"]
            else:
                base = profile["night"]

            # Temperature sensitivity
            base += profile["heat"] * max(0, 15 - temp)
            base += profile["cool"] * max(0, temp - 22)

            # Seasonal variation
            seasonal = 1.0 + 0.15 * math.cos(2 * math.pi * (dt.month - 1) / 12.0)
            value = base * seasonal

            # Anomaly 1: high night base (days 30-44)
            if 30 <= day_offset <= 44 and (hour < peak_start or hour > peak_end) and not is_weekend:
                value *= 2.5

            # Anomaly 2: weekend spike (days 35-36)
            if day_offset in [35, 36] and is_weekend:
                value = 40.0

            # Anomaly 3: sudden ramp (day 55 14:00)
            if day_offset == 55 and hour == 14:
                value = profile["peak"] * 3.0

            # Anomaly 4: flat curve (days 70-73)
            if 70 <= day_offset <= 73:
                value = 15.0

            # Noise + guardrail
            value *= rng.uniform(0.90, 1.10)
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
    Shares the same profile patterns and anomaly injection as generate_readings().
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
            meter.id, profile, site_temps, start, days, psub, rng
        )
        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


def _gen_15min_meter_readings(meter_id: int, profile: dict, temps: dict,
                               start: datetime, days: int, psub: float,
                               rng: random.Random) -> list:
    """Generate 15-min readings for a single meter (4 slots per hour)."""
    readings = []
    peak_start, peak_end = profile["peak_h"]
    vacation_weeks = profile.get("vacation_weeks", [])
    max_kw = psub * 3

    for day_offset in range(days):
        dt = start + timedelta(days=day_offset)
        is_weekend = dt.weekday() >= 5
        day_key = dt.date().isoformat()
        temp = temps.get(day_key, 12.0)
        is_vacation = dt.isocalendar()[1] in vacation_weeks if vacation_weeks else False

        for hour in range(24):
            # Compute hourly base (same logic as _gen_meter_readings)
            if is_weekend or is_vacation:
                base = profile["weekend"]
            elif peak_start <= hour <= peak_end:
                base = profile["peak"]
            elif hour == peak_start - 1 or peak_end < hour <= peak_end + 2:
                base = profile["shoulder"]
            else:
                base = profile["night"]

            base += profile["heat"] * max(0, 15 - temp)
            base += profile["cool"] * max(0, temp - 22)
            seasonal = 1.0 + 0.15 * math.cos(2 * math.pi * (dt.month - 1) / 12.0)
            hourly_value = base * seasonal

            # Anomaly injection (same windows as hourly generator)
            if 30 <= day_offset <= 44 and (hour < peak_start or hour > peak_end) and not is_weekend:
                hourly_value *= 2.5
            if day_offset in [35, 36] and is_weekend:
                hourly_value = 40.0
            if day_offset == 55 and hour == 14:
                hourly_value = profile["peak"] * 3.0
            if 70 <= day_offset <= 73:
                hourly_value = 15.0

            hourly_value *= rng.uniform(0.90, 1.10)
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
