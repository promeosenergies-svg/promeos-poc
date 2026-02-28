"""
PROMEOS - Demo Seed: Weather Data Generator
Generates daily weather per site (sinusoidal + noise).
Supports arbitrary lookback period (default 90 days, helios 730 days).
"""
import math
import random
from datetime import datetime, timedelta

from models import EmsWeatherCache


def _insert_weather_ignore(db, records: list):
    """INSERT OR IGNORE into ems_weather_cache — idempotent re-seed safety."""
    if not records:
        return
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect == "sqlite":
        from sqlalchemy import text
        now_iso = datetime.utcnow().isoformat()
        stmt = text(
            "INSERT OR IGNORE INTO ems_weather_cache "
            "(site_id, date, temp_avg_c, temp_min_c, temp_max_c, source, created_at, updated_at) "
            "VALUES (:sid, :dt, :avg, :mn, :mx, :src, :cat, :uat)"
        )
        db.execute(stmt, [
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
        ])
    else:
        db.bulk_save_objects(records)


def generate_weather(db, sites: list, days: int, rng: random.Random) -> dict:
    """
    Generate daily weather for each site.

    Returns:
        temp_lookup: {site_id: {"YYYY-MM-DD": temp_avg_c}}
    """
    now = datetime.utcnow()
    start = now - timedelta(days=days)
    temp_lookup = {}

    for site in sites:
        lat = site.latitude or 46.0
        site_temps = {}
        records = []

        for d in range(days):
            dt = start + timedelta(days=d)
            day_of_year = dt.timetuple().tm_yday

            # Base: sinusoidal seasonal (cold winter, warm summer)
            # Adjusted by latitude (southern France warmer)
            lat_offset = (46.0 - lat) * 0.3  # ~+1C per degree south
            base = 12.0 + lat_offset - 10.0 * math.cos(2 * math.pi * (day_of_year - 15) / 365)
            noise = rng.uniform(-2.0, 2.0)
            temp = round(base + noise, 1)

            day_key = dt.date().isoformat()
            site_temps[day_key] = temp

            records.append(EmsWeatherCache(
                site_id=site.id,
                date=dt.replace(hour=0, minute=0, second=0, microsecond=0),
                temp_avg_c=temp,
                temp_min_c=round(temp - rng.uniform(3, 6), 1),
                temp_max_c=round(temp + rng.uniform(3, 6), 1),
                source="demo_seed",
            ))

        _insert_weather_ignore(db, records)
        temp_lookup[site.id] = site_temps

    db.flush()
    return temp_lookup
