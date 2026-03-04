"""
PROMEOS - Demo Seed: Weather Data Generator
V107 — Realistic per-city French climate profiles (Meteo-France normals)
with AR(1) day-to-day autocorrelation.
Fallback to sinusoidal for unknown cities.
"""

import math
import random
from datetime import datetime, timedelta, timezone

from models import EmsWeatherCache


# ── Normales mensuelles Meteo-France (temp moyenne °C, Jan→Dec) ─────────────
# amplitude = diurne typique (max-min) / 2
CITY_CLIMATE = {
    "Paris": {"monthly_avg": [3.5, 4.5, 8.0, 11.0, 15.0, 18.5, 20.5, 20.0, 16.5, 12.0, 7.0, 4.0], "amplitude": 4.0},
    "Lyon": {"monthly_avg": [2.5, 4.0, 8.5, 11.5, 16.0, 20.0, 22.5, 22.0, 17.5, 12.5, 7.0, 3.5], "amplitude": 5.0},
    "Toulouse": {"monthly_avg": [5.5, 6.5, 9.5, 12.0, 16.0, 20.0, 22.5, 22.5, 19.0, 14.5, 9.0, 6.0], "amplitude": 4.5},
    "Nice": {"monthly_avg": [8.0, 8.5, 11.0, 13.5, 17.5, 21.5, 24.5, 24.5, 21.0, 16.5, 12.0, 9.0], "amplitude": 3.5},
    "Marseille": {
        "monthly_avg": [6.5, 7.5, 10.5, 13.5, 17.5, 22.0, 25.0, 24.5, 20.5, 16.0, 10.5, 7.5],
        "amplitude": 4.0,
    },
    "Bordeaux": {"monthly_avg": [6.0, 7.0, 10.0, 12.5, 16.0, 19.5, 21.5, 21.5, 18.5, 14.5, 9.5, 6.5], "amplitude": 4.0},
    "Nantes": {"monthly_avg": [5.5, 6.0, 8.5, 10.5, 14.0, 17.5, 19.5, 19.5, 16.5, 12.5, 8.5, 6.0], "amplitude": 3.5},
    "Lille": {"monthly_avg": [2.5, 3.0, 6.0, 8.5, 12.5, 15.5, 17.5, 17.5, 14.5, 10.5, 6.0, 3.5], "amplitude": 3.5},
    "Strasbourg": {
        "monthly_avg": [1.5, 2.5, 6.5, 10.0, 14.5, 18.0, 20.0, 19.5, 15.5, 10.5, 5.5, 2.5],
        "amplitude": 5.0,
    },
    "Montpellier": {
        "monthly_avg": [7.0, 7.5, 10.5, 13.0, 17.0, 21.5, 24.5, 24.0, 20.5, 16.0, 11.0, 7.5],
        "amplitude": 4.0,
    },
    "Grenoble": {"monthly_avg": [1.5, 3.0, 7.5, 10.5, 15.0, 19.0, 21.5, 21.0, 16.5, 11.5, 6.0, 2.5], "amplitude": 5.5},
    "Rennes": {"monthly_avg": [5.0, 5.5, 7.5, 9.5, 13.0, 16.0, 18.0, 18.0, 15.5, 12.0, 8.0, 5.5], "amplitude": 3.5},
}

# AR(1) persistence coefficient (0.0 = no memory, 1.0 = full persistence)
_AR1_PHI = 0.7
_RESIDUAL_SIGMA = 1.5  # °C day-to-day noise


def _interpolate_daily_avg(monthly_avg: list[float], day_of_year: int) -> float:
    """
    Interpolate smooth daily temperature from 12 monthly normals.
    Uses cosine interpolation between mid-month anchor points.
    """
    # Mid-month day-of-year for each month (15th)
    mid_days = [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]

    # Find bracketing months
    for i in range(12):
        next_i = (i + 1) % 12
        d0 = mid_days[i]
        d1 = mid_days[next_i]
        if d1 < d0:  # wrap Dec→Jan
            d1 += 365

        doy = day_of_year
        if doy < d0 and i == 11:
            doy += 365

        if d0 <= doy <= d1:
            # Cosine interpolation for smooth transition
            t = (doy - d0) / (d1 - d0)
            smooth = 0.5 * (1 - math.cos(math.pi * t))
            return monthly_avg[i] + smooth * (monthly_avg[next_i] - monthly_avg[i])

    # Fallback (shouldn't happen)
    month_idx = min(11, max(0, (day_of_year - 1) * 12 // 365))
    return monthly_avg[month_idx]


def _insert_weather_ignore(db, records: list):
    """INSERT OR IGNORE into ems_weather_cache — idempotent re-seed safety."""
    if not records:
        return
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect == "sqlite":
        from sqlalchemy import text

        now_iso = datetime.now(timezone.utc).isoformat()
        stmt = text(
            "INSERT OR IGNORE INTO ems_weather_cache "
            "(site_id, date, temp_avg_c, temp_min_c, temp_max_c, source, created_at, updated_at) "
            "VALUES (:sid, :dt, :avg, :mn, :mx, :src, :cat, :uat)"
        )
        db.execute(
            stmt,
            [
                {
                    "sid": r.site_id,
                    "dt": r.date.strftime("%Y-%m-%d %H:%M:%S") if r.date else None,
                    "avg": r.temp_avg_c,
                    "mn": r.temp_min_c,
                    "mx": r.temp_max_c,
                    "src": r.source,
                    "cat": now_iso,
                    "uat": now_iso,
                }
                for r in records
            ],
        )
    else:
        db.bulk_save_objects(records)


def generate_weather(db, sites: list, days: int, rng: random.Random) -> dict:
    """
    Generate daily weather for each site.
    Uses per-city Meteo-France normals + AR(1) autocorrelation.

    Returns:
        temp_lookup: {site_id: {"YYYY-MM-DD": temp_avg_c}}
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(days=days)
    temp_lookup = {}

    for site in sites:
        # Resolve city name from site metadata
        city = getattr(site, "_city", None) or site.ville or ""
        # Try exact match then prefix match
        climate = CITY_CLIMATE.get(city)
        if not climate:
            for key in CITY_CLIMATE:
                if key.lower() in city.lower() or city.lower() in key.lower():
                    climate = CITY_CLIMATE[key]
                    break

        if climate:
            site_temps, records = _generate_realistic(site.id, climate, start, days, rng)
        else:
            # Fallback: sinusoidal (legacy behavior)
            site_temps, records = _generate_sinusoidal(site.id, site.latitude or 46.0, start, days, rng)

        _insert_weather_ignore(db, records)
        temp_lookup[site.id] = site_temps

    db.flush()
    return temp_lookup


def _generate_realistic(
    site_id: int, climate: dict, start: datetime, days: int, rng: random.Random
) -> tuple[dict, list]:
    """Generate weather using Meteo-France normals + AR(1) autocorrelation."""
    monthly_avg = climate["monthly_avg"]
    amplitude = climate["amplitude"]
    records = []
    site_temps = {}
    ar_residual = 0.0  # AR(1) state

    for d in range(days):
        dt = start + timedelta(days=d)
        doy = dt.timetuple().tm_yday

        # Smooth daily normal from monthly data
        daily_normal = _interpolate_daily_avg(monthly_avg, doy)

        # AR(1) autocorrelation: today's residual depends on yesterday's
        innovation = rng.gauss(0, _RESIDUAL_SIGMA)
        ar_residual = _AR1_PHI * ar_residual + math.sqrt(1 - _AR1_PHI**2) * innovation

        temp_avg = round(daily_normal + ar_residual, 1)
        # Diurnal range with slight randomness
        amp_noise = rng.uniform(0.8, 1.2)
        temp_min = round(temp_avg - amplitude * amp_noise, 1)
        temp_max = round(temp_avg + amplitude * amp_noise, 1)

        day_key = dt.date().isoformat()
        site_temps[day_key] = temp_avg

        records.append(
            EmsWeatherCache(
                site_id=site_id,
                date=dt.replace(hour=0, minute=0, second=0, microsecond=0),
                temp_avg_c=temp_avg,
                temp_min_c=temp_min,
                temp_max_c=temp_max,
                source="demo_seed_v107",
            )
        )

    return site_temps, records


def _generate_sinusoidal(site_id: int, lat: float, start: datetime, days: int, rng: random.Random) -> tuple[dict, list]:
    """Fallback: legacy sinusoidal weather generation."""
    records = []
    site_temps = {}

    for d in range(days):
        dt = start + timedelta(days=d)
        day_of_year = dt.timetuple().tm_yday

        lat_offset = (46.0 - lat) * 0.3
        base = 12.0 + lat_offset - 10.0 * math.cos(2 * math.pi * (day_of_year - 15) / 365)
        noise = rng.uniform(-2.0, 2.0)
        temp = round(base + noise, 1)

        day_key = dt.date().isoformat()
        site_temps[day_key] = temp

        records.append(
            EmsWeatherCache(
                site_id=site_id,
                date=dt.replace(hour=0, minute=0, second=0, microsecond=0),
                temp_avg_c=temp,
                temp_min_c=round(temp - rng.uniform(3, 6), 1),
                temp_max_c=round(temp + rng.uniform(3, 6), 1),
                source="demo_seed",
            )
        )

    return site_temps, records
