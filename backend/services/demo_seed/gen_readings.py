"""
PROMEOS - Demo Seed: Meter Readings Generator
V107 — World-class realism:
  - Surface-normalized consumption (kWh/m²/an ADEME benchmarks)
  - Per-city hotel occupancy (seasonal, weekday/weekend)
  - French school vacation calendar (Zone B/C)
  - Temperature-correlated gas DJU readings
  - 365-day 15-min with CVC cycling patterns
  - Diverse anomalies per site (not same days for all)
"""

import math
import random
from datetime import datetime, timedelta, timezone

from models import MeterReading, FrequencyType
from models.energy_models import EnergyVector


# ── Surface benchmarks ADEME (kWh/m²/an) ────────────────────────────────────
SURFACE_BENCHMARKS = {
    "bureau": {"elec_kwh_m2": 170, "gas_kwh_m2": 50},
    "entrepot": {"elec_kwh_m2": 120, "gas_kwh_m2": 80},
    "hotel": {"elec_kwh_m2": 280, "gas_kwh_m2": 100},
    "enseignement": {"elec_kwh_m2": 110, "gas_kwh_m2": 60},
    "commerce": {"elec_kwh_m2": 200, "gas_kwh_m2": 40},
    "sante": {"elec_kwh_m2": 250, "gas_kwh_m2": 120},
}

# Profile → type_site mapping for benchmark lookup
_PROFILE_TO_TYPE = {
    "office": "bureau",
    "hotel": "hotel",
    "warehouse": "entrepot",
    "school": "enseignement",
    "hospital": "sante",
    "retail": "commerce",
}

# ── Legacy profile dict (kept for vacation_weeks + backward compat) ──────────
_PROFILES = {
    "office": {"heat": 1.5, "cool": 0.8, "peak_h": (8, 18)},
    "hotel": {"heat": 2.0, "cool": 1.2, "peak_h": (7, 22)},
    "retail": {"heat": 1.0, "cool": 1.5, "peak_h": (9, 20)},
    "warehouse": {"heat": 0.5, "cool": 0.3, "peak_h": (6, 20)},
    "school": {
        "heat": 2.5,
        "cool": 0.3,
        "peak_h": (8, 17),
        "vacation_weeks": [1, 2, 7, 8, 16, 17, 27, 28, 29, 30, 31, 32, 33, 34],
    },
    "hospital": {"heat": 2.0, "cool": 1.8, "peak_h": (7, 21)},
}

# ── Per-hour normalized patterns (index 0 = 00:00 … 23 = 23:00) ─────────────
_HOURLY_PATTERN = {
    "office": [
        0.12,
        0.10,
        0.10,
        0.10,
        0.11,
        0.14,
        0.22,
        0.48,
        0.74,
        0.92,
        1.00,
        0.96,
        0.76,
        0.79,
        1.00,
        0.97,
        0.92,
        0.74,
        0.50,
        0.30,
        0.22,
        0.17,
        0.14,
        0.12,
    ],
    "hotel": [
        0.52,
        0.48,
        0.44,
        0.42,
        0.44,
        0.55,
        0.68,
        0.88,
        0.96,
        0.90,
        0.82,
        0.88,
        0.90,
        0.84,
        0.78,
        0.80,
        0.85,
        0.92,
        1.00,
        1.00,
        0.96,
        0.88,
        0.74,
        0.62,
    ],
    "warehouse": [
        0.28,
        0.25,
        0.22,
        0.22,
        0.26,
        0.42,
        0.65,
        0.85,
        1.00,
        1.00,
        0.97,
        0.82,
        0.58,
        0.80,
        0.98,
        1.00,
        0.95,
        0.80,
        0.55,
        0.40,
        0.33,
        0.30,
        0.28,
        0.28,
    ],
    "school": [
        0.10,
        0.08,
        0.08,
        0.08,
        0.09,
        0.14,
        0.25,
        0.52,
        0.82,
        0.94,
        1.00,
        0.96,
        0.62,
        0.52,
        0.88,
        0.94,
        0.75,
        0.50,
        0.26,
        0.18,
        0.14,
        0.12,
        0.10,
        0.10,
    ],
    "hospital": [
        0.65,
        0.60,
        0.56,
        0.55,
        0.58,
        0.65,
        0.75,
        0.86,
        0.94,
        0.99,
        1.00,
        0.99,
        0.94,
        0.92,
        0.98,
        1.00,
        0.99,
        0.95,
        0.90,
        0.85,
        0.82,
        0.78,
        0.74,
        0.68,
    ],
    "retail": [
        0.12,
        0.10,
        0.08,
        0.08,
        0.10,
        0.16,
        0.22,
        0.40,
        0.65,
        0.84,
        0.95,
        1.00,
        1.00,
        0.98,
        0.96,
        0.99,
        1.00,
        0.95,
        0.85,
        0.72,
        0.52,
        0.30,
        0.18,
        0.13,
    ],
}

# ── Day-of-week multipliers (Mon=0 … Sun=6) ──────────────────────────────────
_DOW_MULT = {
    "office": [1.00, 0.98, 0.97, 0.97, 0.94, 0.38, 0.25],
    "hotel": [0.88, 0.86, 0.88, 0.92, 0.95, 1.00, 1.00],
    "warehouse": [1.00, 1.00, 0.98, 0.98, 0.95, 0.65, 0.40],
    "school": [1.00, 0.99, 0.98, 0.98, 0.95, 0.15, 0.12],
    "hospital": [1.00, 1.00, 1.00, 1.00, 1.00, 0.95, 0.90],
    "retail": [0.85, 0.88, 0.90, 0.92, 0.98, 1.00, 0.95],
}

# ── Temperature sensitivity (multiplicative, per °C outside comfort zone) ────
_TEMP_SENS = {
    "office": (0.035, 0.015),
    "hotel": (0.030, 0.025),
    "warehouse": (0.015, 0.008),
    "school": (0.040, 0.010),
    "hospital": (0.025, 0.020),
    "retail": (0.020, 0.018),
}

# ── Seasonal multiplier by month ─────────────────────────────────────────────
_SEASONAL_MULT = {
    1: 1.25,
    2: 1.20,
    3: 1.10,
    4: 0.95,
    5: 0.85,
    6: 0.80,
    7: 0.75,
    8: 0.75,
    9: 0.85,
    10: 0.95,
    11: 1.10,
    12: 1.25,
}

# School vacation months for monthly readings
_SCHOOL_VACATION_MONTHS = {7, 8}

# ── Hotel occupancy by season & city (V107) ──────────────────────────────────
# Returns multiplicateur 0.0-1.0 for hotel consumption
_HOTEL_OCCUPANCY = {
    # city: {month: occupancy_rate}  — based on French tourism patterns
    "Nice": {
        1: 0.45,
        2: 0.50,
        3: 0.55,
        4: 0.65,
        5: 0.75,
        6: 0.90,
        7: 0.95,
        8: 0.95,
        9: 0.85,
        10: 0.65,
        11: 0.50,
        12: 0.45,
    },
    "Paris": {
        1: 0.65,
        2: 0.68,
        3: 0.75,
        4: 0.82,
        5: 0.85,
        6: 0.80,
        7: 0.75,
        8: 0.70,
        9: 0.82,
        10: 0.80,
        11: 0.72,
        12: 0.68,
    },
    "Marseille": {
        1: 0.40,
        2: 0.45,
        3: 0.55,
        4: 0.65,
        5: 0.75,
        6: 0.88,
        7: 0.92,
        8: 0.92,
        9: 0.80,
        10: 0.60,
        11: 0.45,
        12: 0.42,
    },
    "Lyon": {
        1: 0.55,
        2: 0.58,
        3: 0.65,
        4: 0.70,
        5: 0.72,
        6: 0.75,
        7: 0.68,
        8: 0.62,
        9: 0.72,
        10: 0.70,
        11: 0.60,
        12: 0.55,
    },
    "Toulouse": {
        1: 0.50,
        2: 0.55,
        3: 0.60,
        4: 0.65,
        5: 0.70,
        6: 0.75,
        7: 0.72,
        8: 0.68,
        9: 0.70,
        10: 0.65,
        11: 0.55,
        12: 0.52,
    },
}
_DEFAULT_OCCUPANCY = {m: 0.65 for m in range(1, 13)}

# ── French school vacation weeks (2025-2026 approx, Zone B + Zone C) ─────────
# Zone B: Lyon, Toulouse, Marseille  |  Zone C: Paris, Nice
_VACATION_WEEKS_ZONE_B = [
    # Toussaint, Noel, Hiver, Printemps, Ete
    *range(44, 45),  # Toussaint: W44
    *range(52, 53),
    1,  # Noel: W52-W1
    *range(8, 10),  # Hiver: W8-W9
    *range(16, 18),  # Printemps: W16-W17
    *range(27, 36),  # Ete: W27-W35
]
_VACATION_WEEKS_ZONE_C = [
    *range(44, 45),
    *range(52, 53),
    1,
    *range(7, 9),  # Hiver: W7-W8
    *range(15, 17),  # Printemps: W15-W16
    *range(27, 36),  # Ete
]

# City → vacation zone
_CITY_VACATION_ZONE = {
    "Paris": _VACATION_WEEKS_ZONE_C,
    "Nice": _VACATION_WEEKS_ZONE_C,
    "Lyon": _VACATION_WEEKS_ZONE_B,
    "Toulouse": _VACATION_WEEKS_ZONE_B,
    "Marseille": _VACATION_WEEKS_ZONE_B,
}


def _compute_calibration_factors():
    """Precompute correction factors so annual consumption matches ADEME benchmarks.
    The patterns and DOW multipliers reduce average utilization well below 1.0,
    so we need to scale base_kw up to compensate."""
    factors = {}
    for profile_name in _HOURLY_PATTERN:
        pattern = _HOURLY_PATTERN[profile_name]
        dow = _DOW_MULT.get(profile_name, _DOW_MULT["office"])
        seasonal_vals = list(_SEASONAL_MULT.values())
        avg_pattern = sum(pattern) / len(pattern)
        avg_dow = sum(dow) / len(dow)
        avg_seasonal = sum(seasonal_vals) / len(seasonal_vals)
        avg_utilization = avg_pattern * avg_dow * avg_seasonal
        factors[profile_name] = 1.0 / avg_utilization if avg_utilization > 0 else 1.0
    return factors


_CALIBRATION = _compute_calibration_factors()


def _get_base_kw(meter, site_profiles: dict, site_meta: dict) -> float:
    """Compute surface-normalized base_kw for a meter (V107).
    Includes calibration factor to match ADEME benchmarks after
    pattern/DOW/seasonal averaging."""
    profile_name = site_profiles.get(meter.site_id, "office")
    type_site = _PROFILE_TO_TYPE.get(profile_name, "bureau")

    # Try surface from site metadata
    surface_m2 = site_meta.get(meter.site_id, {}).get("surface_m2", 0)
    benchmark = SURFACE_BENCHMARKS.get(type_site, SURFACE_BENCHMARKS["bureau"])

    if surface_m2 and surface_m2 > 0:
        # Surface-normalized: annual_kwh / 8760 hours × calibration
        annual_kwh = benchmark["elec_kwh_m2"] * surface_m2
        calib = _CALIBRATION.get(profile_name, 2.0)
        return annual_kwh / 8760.0 * calib
    else:
        # Fallback: use legacy _BASE_KW scaled by psub
        return _LEGACY_BASE_KW.get(profile_name, 80) * (meter.subscribed_power_kva or 80) / 100.0


# Legacy base_kw (fallback for sites without surface data)
_LEGACY_BASE_KW = {
    "office": 80,
    "hotel": 65,
    "warehouse": 110,
    "school": 70,
    "hospital": 85,
    "retail": 75,
}


def _get_vacation_weeks(profile_name: str, city: str) -> list:
    """Get vacation weeks for school profiles based on city zone."""
    if profile_name != "school":
        return []
    return _CITY_VACATION_ZONE.get(city, _VACATION_WEEKS_ZONE_B)


def _get_hotel_occupancy(city: str, month: int) -> float:
    """Get hotel occupancy rate for a city and month."""
    city_occ = _HOTEL_OCCUPANCY.get(city, _DEFAULT_OCCUPANCY)
    return city_occ.get(month, 0.65)


# ── Anomaly definitions per site (V107: diverse, not same days) ──────────────


def _build_anomaly_schedule(site_idx: int, profile_name: str, days: int, rng: random.Random) -> list:
    """
    Build a list of anomaly descriptors for a specific site.
    Each anomaly: {"day_start", "day_end", "hours", "type", "multiplier", "quality"}
    """
    anomalies = []

    if profile_name == "office" and site_idx == 0:
        # CVC drift: Bureau Paris, Jan-Feb (days ~300-315 in 730-day window)
        drift_start = max(0, days - 60) + rng.randint(0, 15)
        for d in range(drift_start, min(drift_start + 15, days)):
            progress = (d - drift_start) / 15.0
            mult = 1.0 + 0.15 * math.sin(math.pi * progress)  # rise and fall
            anomalies.append(
                {
                    "day": d,
                    "hours": list(range(0, 6)),
                    "type": "cvc_drift",
                    "multiplier": mult,
                    "quality": 0.75,
                }
            )

    elif profile_name == "warehouse" and site_idx == 2:
        # Eclairage oublie: Entrepot Toulouse, 5 random weekends
        # Multiplier 2.0 = eclairage entrepot reste allume (realiste, ~2x le talon nuit)
        weekend_days = [
            d
            for d in range(max(0, days - 365), days)
            if (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days - d)).weekday() >= 5
        ]
        chosen = rng.sample(weekend_days, min(5, len(weekend_days)))
        for d in chosen:
            anomalies.append(
                {
                    "day": d,
                    "hours": list(range(20, 24)) + list(range(0, 6)),
                    "type": "forgotten_lights",
                    "multiplier": 2.0,
                    "quality": 0.75,
                }
            )

    elif profile_name == "hotel" and site_idx == 3:
        # Pic puissance: Hotel Nice, 3 jours canicule ete
        summer_start = max(0, days - 180)
        heat_days = rng.sample(range(summer_start, summer_start + 60), min(3, 60))
        for d in heat_days:
            anomalies.append(
                {
                    "day": d,
                    "hours": list(range(12, 20)),
                    "type": "heatwave_spike",
                    "multiplier": 1.40,
                    "quality": 0.65,
                }
            )

    elif profile_name == "school" and site_idx == 4:
        # Panne partielle: Enseignement Marseille, 1 semaine en Mars
        outage_start = max(0, days - 30) + rng.randint(0, 7)
        for d in range(outage_start, min(outage_start + 7, days)):
            anomalies.append(
                {
                    "day": d,
                    "hours": list(range(24)),
                    "type": "partial_outage",
                    "multiplier": 0.50,
                    "quality": 0.60,
                }
            )

    # Transition saisonniere: tous les sites, Oct + Avril (3 jours overlap chaud+clim)
    for target_month in [4, 10]:
        # Find days in this month within the window
        for d in range(days):
            dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days - d)
            if dt.month == target_month and 10 <= dt.day <= 12:
                anomalies.append(
                    {
                        "day": d,
                        "hours": list(range(8, 18)),
                        "type": "season_transition",
                        "multiplier": 1.10,
                        "quality": 0.85,
                    }
                )

    return anomalies


def generate_readings(
    db, meters: list, site_profiles: dict, temp_lookup: dict, days: int, rng: random.Random, site_meta: dict = None
) -> int:
    """Generate hourly electricity readings for each meter."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(days=days)
    total = 0
    site_meta = site_meta or {}

    for meter_idx, meter in enumerate(meters):
        # Skip gas meters — handled separately
        ev = getattr(meter, "energy_vector", None)
        if ev and (ev == EnergyVector.GAS or str(ev).lower() == "gas"):
            continue

        profile_name = site_profiles.get(meter.site_id, "office")
        profile = _PROFILES.get(profile_name, _PROFILES["office"])
        site_temps = temp_lookup.get(meter.site_id, {})
        city = site_meta.get(meter.site_id, {}).get("city", "")
        base_kw = _get_base_kw(meter, site_profiles, site_meta)
        psub = meter.subscribed_power_kva or 80
        vacation_weeks = _get_vacation_weeks(profile_name, city)

        # Build anomaly schedule for this site
        anomalies = _build_anomaly_schedule(meter_idx, profile_name, days, rng)
        anomaly_lookup = {}
        for a in anomalies:
            anomaly_lookup.setdefault(a["day"], []).append(a)

        readings = _gen_meter_readings(
            meter.id,
            profile_name,
            profile,
            site_temps,
            start,
            days,
            base_kw,
            psub,
            rng,
            vacation_weeks,
            city,
            anomaly_lookup,
        )
        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


def _gen_meter_readings(
    meter_id: int,
    profile_name: str,
    profile: dict,
    temps: dict,
    start: datetime,
    days: int,
    base_kw: float,
    psub: float,
    rng: random.Random,
    vacation_weeks: list,
    city: str,
    anomaly_lookup: dict,
) -> list:
    """Generate hourly readings for a single electricity meter."""
    readings = []
    pattern = _HOURLY_PATTERN.get(profile_name, _HOURLY_PATTERN["office"])
    dow_mult = _DOW_MULT.get(profile_name, _DOW_MULT["office"])
    heat_pct, cool_pct = _TEMP_SENS.get(profile_name, (0.030, 0.015))
    max_kw = psub * 1.2 if psub > 0 else base_kw * 3.0

    for day_offset in range(days):
        dt = start + timedelta(days=day_offset)
        dow = dt.weekday()
        day_key = dt.date().isoformat()
        temp = temps.get(day_key, 12.0)
        is_vacation = dt.isocalendar()[1] in vacation_weeks if vacation_weeks else False

        # Day-level multipliers
        day_dow = dow_mult[dow]
        if is_vacation:
            day_dow *= 0.15

        # Hotel occupancy adjustment (V107)
        if profile_name == "hotel":
            occ = _get_hotel_occupancy(city, dt.month)
            # Weekend boost for hotels
            if dow >= 5:
                occ = min(1.0, occ * 1.15)
            day_dow *= occ

        seasonal = _SEASONAL_MULT.get(dt.month, 1.0)
        temp_adj = 1.0 + heat_pct * max(0.0, 15.0 - temp) + cool_pct * max(0.0, temp - 25.0)

        # Get anomalies for this day
        day_anomalies = anomaly_lookup.get(day_offset, [])

        for hour in range(24):
            ts = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
            value = base_kw * pattern[hour] * day_dow * seasonal * temp_adj

            # Apply anomalies
            quality = 1.0
            for anom in day_anomalies:
                if hour in anom["hours"]:
                    value *= anom["multiplier"]
                    quality = min(quality, anom["quality"])

            # Noise ±7% + guardrail
            value *= rng.uniform(0.93, 1.07)
            value = max(0.1, min(round(value, 2), max_kw))

            readings.append(
                MeterReading(
                    meter_id=meter_id,
                    timestamp=ts,
                    frequency=FrequencyType.HOURLY,
                    value_kwh=value,
                    is_estimated=False,
                    quality_score=quality,
                )
            )

    return readings


# ── Gas readings (V107) ──────────────────────────────────────────────────────


def generate_gas_readings(
    db, meters: list, site_profiles: dict, temp_lookup: dict, days: int, rng: random.Random, site_meta: dict = None
) -> int:
    """Generate daily gas readings correlated to DJU (degree-day units)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(days=days)
    total = 0
    site_meta = site_meta or {}

    for meter in meters:
        ev = getattr(meter, "energy_vector", None)
        if not ev or not (ev == EnergyVector.GAS or str(ev).lower() == "gas"):
            continue

        profile_name = site_profiles.get(meter.site_id, "office")
        type_site = _PROFILE_TO_TYPE.get(profile_name, "bureau")
        surface_m2 = site_meta.get(meter.site_id, {}).get("surface_m2", 2000)
        benchmark = SURFACE_BENCHMARKS.get(type_site, SURFACE_BENCHMARKS["bureau"])
        annual_gas_kwh = benchmark["gas_kwh_m2"] * surface_m2
        site_temps = temp_lookup.get(meter.site_id, {})

        # Compute average DJU for normalization
        # DJU = max(0, 18 - temp_avg) summed over heating days
        dju_total = sum(max(0, 18.0 - t) for t in site_temps.values()) if site_temps else 2500.0
        if dju_total < 100:
            dju_total = 100  # safety floor

        readings = []
        for day_offset in range(days):
            dt = start + timedelta(days=day_offset)
            day_key = dt.date().isoformat()
            temp = site_temps.get(day_key, 12.0)

            # DJU-based: consumption proportional to heating need
            dju_day = max(0, 18.0 - temp)
            gas_kwh = annual_gas_kwh * (dju_day / dju_total)

            # Hotel: minimum hot water even in summer
            if profile_name == "hotel":
                city = site_meta.get(meter.site_id, {}).get("city", "")
                occ = _get_hotel_occupancy(city, dt.month)
                min_hot_water = annual_gas_kwh * 0.0005 * occ  # ~0.05% of annual per day
                gas_kwh = max(gas_kwh, min_hot_water)

            # Noise ±8%
            gas_kwh *= rng.uniform(0.92, 1.08)
            gas_kwh = max(0.0, round(gas_kwh, 2))

            readings.append(
                MeterReading(
                    meter_id=meter.id,
                    timestamp=dt.replace(hour=0, minute=0, second=0, microsecond=0),
                    frequency=FrequencyType.DAILY,
                    value_kwh=gas_kwh,
                    is_estimated=False,
                    quality_score=1.0,
                )
            )

        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


# ── Monthly readings (helios billing history) ────────────────────────────────

_MONTHLY_BASE = {
    "office": 25000,
    "hotel": 80000,
    "retail": 35000,
    "warehouse": 50000,
    "school": 18000,
    "hospital": 120000,
}


def generate_monthly_readings(
    db, meters: list, site_profiles: dict, months: int, rng: random.Random, site_meta: dict = None
) -> int:
    """Generate monthly aggregated readings."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    total = 0
    site_meta = site_meta or {}

    for meter in meters:
        # Skip gas meters for monthly (gas has its own daily generator)
        ev = getattr(meter, "energy_vector", None)
        if ev and (ev == EnergyVector.GAS or str(ev).lower() == "gas"):
            continue

        profile_name = site_profiles.get(meter.site_id, "office")
        is_school = profile_name == "school"

        # V107: surface-normalized monthly base
        type_site = _PROFILE_TO_TYPE.get(profile_name, "bureau")
        surface_m2 = site_meta.get(meter.site_id, {}).get("surface_m2", 0)
        if surface_m2 > 0:
            benchmark = SURFACE_BENCHMARKS.get(type_site, SURFACE_BENCHMARKS["bureau"])
            base_kwh = benchmark["elec_kwh_m2"] * surface_m2 / 12.0  # monthly
        else:
            base_kwh = _MONTHLY_BASE.get(profile_name, _MONTHLY_BASE["office"])
            psub = meter.subscribed_power_kva or 80
            base_kwh *= psub / 100.0

        anomaly_months = set(rng.sample(range(months), min(2, months)))

        readings = []
        seen_months = set()
        for m_offset in range(months):
            target_month = now.month - (months - m_offset)
            target_year = now.year + (target_month - 1) // 12
            target_month = ((target_month - 1) % 12) + 1
            dt = datetime(target_year, target_month, 1)
            key = (meter.id, dt)
            if key in seen_months:
                continue
            seen_months.add(key)
            month_num = dt.month

            seasonal = _SEASONAL_MULT.get(month_num, 1.0)
            value = base_kwh * seasonal

            if is_school and month_num in _SCHOOL_VACATION_MONTHS:
                value *= 0.20

            if m_offset in anomaly_months:
                value *= 1.80

            value *= rng.uniform(0.92, 1.08)
            value = max(100, round(value, 0))

            readings.append(
                MeterReading(
                    meter_id=meter.id,
                    timestamp=dt,
                    frequency=FrequencyType.MONTHLY,
                    value_kwh=value,
                    is_estimated=False,
                )
            )

        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


# ── 15-minute readings (V107: 365 days, CVC cycling) ────────────────────────


def generate_15min_readings(
    db, meters: list, site_profiles: dict, temp_lookup: dict, days: int, rng: random.Random, site_meta: dict = None
) -> int:
    """Generate 15-minute interval readings with CVC cycling patterns."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(days=days)
    total = 0
    site_meta = site_meta or {}

    for meter_idx, meter in enumerate(meters):
        # Skip gas meters
        ev = getattr(meter, "energy_vector", None)
        if ev and (ev == EnergyVector.GAS or str(ev).lower() == "gas"):
            continue

        profile_name = site_profiles.get(meter.site_id, "office")
        profile = _PROFILES.get(profile_name, _PROFILES["office"])
        site_temps = temp_lookup.get(meter.site_id, {})
        city = site_meta.get(meter.site_id, {}).get("city", "")
        base_kw = _get_base_kw(meter, site_profiles, site_meta)
        psub = meter.subscribed_power_kva or 80
        max_kw = psub * 1.2 if psub > 0 else base_kw * 3.0
        vacation_weeks = _get_vacation_weeks(profile_name, city)

        anomalies = _build_anomaly_schedule(meter_idx, profile_name, days, rng)
        anomaly_lookup = {}
        for a in anomalies:
            anomaly_lookup.setdefault(a["day"], []).append(a)

        readings = _gen_15min_meter_readings(
            meter.id,
            profile_name,
            profile,
            site_temps,
            start,
            days,
            base_kw,
            psub,
            max_kw,
            rng,
            vacation_weeks,
            city,
            anomaly_lookup,
        )
        _bulk_insert_ignore(db, readings)
        total += len(readings)

    db.flush()
    return total


def _gen_15min_meter_readings(
    meter_id: int,
    profile_name: str,
    profile: dict,
    temps: dict,
    start: datetime,
    days: int,
    base_kw: float,
    psub: float,
    max_kw: float,
    rng: random.Random,
    vacation_weeks: list,
    city: str,
    anomaly_lookup: dict,
) -> list:
    """Generate 15-min readings with CVC cycling patterns."""
    readings = []
    pattern = _HOURLY_PATTERN.get(profile_name, _HOURLY_PATTERN["office"])
    dow_mult = _DOW_MULT.get(profile_name, _DOW_MULT["office"])
    heat_pct, cool_pct = _TEMP_SENS.get(profile_name, (0.030, 0.015))

    for day_offset in range(days):
        dt = start + timedelta(days=day_offset)
        dow = dt.weekday()
        day_key = dt.date().isoformat()
        temp = temps.get(day_key, 12.0)
        is_vacation = dt.isocalendar()[1] in vacation_weeks if vacation_weeks else False

        day_dow = dow_mult[dow]
        if is_vacation:
            day_dow *= 0.15

        if profile_name == "hotel":
            occ = _get_hotel_occupancy(city, dt.month)
            if dow >= 5:
                occ = min(1.0, occ * 1.15)
            day_dow *= occ

        seasonal = _SEASONAL_MULT.get(dt.month, 1.0)
        temp_adj = 1.0 + heat_pct * max(0.0, 15.0 - temp) + cool_pct * max(0.0, temp - 25.0)

        day_anomalies = anomaly_lookup.get(day_offset, [])

        # Is CVC active? (business hours and not vacation)
        is_business_period = not is_vacation and dow < 5

        for hour in range(24):
            hourly_value = base_kw * pattern[hour] * day_dow * seasonal * temp_adj

            # Apply anomalies
            quality = 1.0
            for anom in day_anomalies:
                if hour in anom["hours"]:
                    hourly_value *= anom["multiplier"]
                    quality = min(quality, anom["quality"])

            hourly_value *= rng.uniform(0.93, 1.07)
            hourly_value = max(0.1, min(hourly_value, max_kw))

            # Split into 4 × 15-min with CVC cycling (V107)
            slot_base = hourly_value / 4.0
            # CVC cycling amplitude: higher during business hours
            if is_business_period and 7 <= hour <= 19:
                cycling_amp = 0.08  # ±8% CVC compressor on/off
            else:
                cycling_amp = 0.03  # ±3% overnight minimal cycling

            for quarter in range(4):
                ts = dt.replace(hour=hour, minute=quarter * 15, second=0, microsecond=0)
                # CVC cycling: alternate high/low with randomness
                cycle_phase = rng.uniform(-cycling_amp, cycling_amp)
                slot_val = slot_base * (1.0 + cycle_phase)
                slot_val = max(0.01, round(slot_val, 3))

                readings.append(
                    MeterReading(
                        meter_id=meter_id,
                        timestamp=ts,
                        frequency=FrequencyType.MIN_15,
                        value_kwh=slot_val,
                        is_estimated=False,
                        quality_score=quality,
                    )
                )

    return readings


# ── Bulk insert helper ───────────────────────────────────────────────────────


def _bulk_insert_ignore(db, readings: list):
    """INSERT OR IGNORE — safety net against duplicate (meter_id, timestamp)."""
    if not readings:
        return
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect == "sqlite":
        from sqlalchemy import text

        stmt = text(
            "INSERT OR IGNORE INTO meter_reading "
            "(meter_id, timestamp, frequency, value_kwh, is_estimated, quality_score, created_at) "
            "VALUES (:meter_id, :ts, :freq, :kwh, :est, :qs, :cat)"
        )
        params = [
            {
                "meter_id": r.meter_id,
                "ts": r.timestamp.isoformat() if r.timestamp else None,
                "freq": r.frequency.name if hasattr(r.frequency, "name") else str(r.frequency),
                "kwh": r.value_kwh,
                "est": 1 if r.is_estimated else 0,
                "qs": getattr(r, "quality_score", None) or 1.0,
                "cat": r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat(),
            }
            for r in readings
        ]
        # Batch in chunks of 500 for memory efficiency
        chunk_size = 500
        for i in range(0, len(params), chunk_size):
            db.execute(stmt, params[i : i + chunk_size])
    elif dialect == "postgresql":
        from sqlalchemy import text

        stmt = text(
            "INSERT INTO meter_reading "
            "(meter_id, timestamp, frequency, value_kwh, is_estimated, quality_score, created_at) "
            "VALUES (:meter_id, :ts, :freq, :kwh, :est, :qs, :cat) "
            "ON CONFLICT (meter_id, timestamp) DO NOTHING"
        )
        params = [
            {
                "meter_id": r.meter_id,
                "ts": r.timestamp.isoformat() if r.timestamp else None,
                "freq": r.frequency.name if hasattr(r.frequency, "name") else str(r.frequency),
                "kwh": r.value_kwh,
                "est": r.is_estimated,
                "qs": getattr(r, "quality_score", None) or 1.0,
                "cat": r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat(),
            }
            for r in readings
        ]
        chunk_size = 500
        for i in range(0, len(params), chunk_size):
            db.execute(stmt, params[i : i + chunk_size])
    else:
        db.bulk_save_objects(readings)
