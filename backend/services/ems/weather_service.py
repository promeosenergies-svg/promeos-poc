"""
PROMEOS - EMS Weather Service
Demo weather provider with deterministic generation + DB cache.
"""
import math
import random
from datetime import datetime, timedelta, date as date_type
from typing import List, Dict

from sqlalchemy.orm import Session
from models import Site
from models.ems_models import EmsWeatherCache


def get_weather(
    db: Session,
    site_id: int,
    date_from: date_type,
    date_to: date_type,
) -> List[Dict]:
    """Get daily weather data for a site. Check cache first, generate demo if missing."""
    dt_from = datetime.combine(date_from, datetime.min.time())
    dt_to = datetime.combine(date_to, datetime.min.time())

    cached = (
        db.query(EmsWeatherCache)
        .filter(
            EmsWeatherCache.site_id == site_id,
            EmsWeatherCache.date >= dt_from,
            EmsWeatherCache.date <= dt_to,
        )
        .order_by(EmsWeatherCache.date)
        .all()
    )
    cached_dates = {c.date.date() for c in cached}

    # Get site latitude for seasonal model
    site = db.query(Site).filter(Site.id == site_id).first()
    latitude = site.latitude if site and site.latitude else 48.86  # Paris default

    # Generate missing dates
    new_entries = []
    d = date_from
    while d <= date_to:
        if d not in cached_dates:
            entry = _generate_demo_weather(site_id, d, latitude)
            new_entries.append(entry)
        d += timedelta(days=1)

    if new_entries:
        db.bulk_save_objects(new_entries)
        db.flush()
        # Re-query for consistency
        cached = (
            db.query(EmsWeatherCache)
            .filter(
                EmsWeatherCache.site_id == site_id,
                EmsWeatherCache.date >= dt_from,
                EmsWeatherCache.date <= dt_to,
            )
            .order_by(EmsWeatherCache.date)
            .all()
        )

    return [
        {
            "date": c.date.date().isoformat(),
            "temp_avg_c": c.temp_avg_c,
            "temp_min_c": c.temp_min_c,
            "temp_max_c": c.temp_max_c,
            "source": c.source,
        }
        for c in cached
    ]


def ensure_weather(
    db: Session,
    site_ids: List[int],
    date_from: date_type,
    date_to: date_type,
) -> Dict:
    """Ensure weather data exists for all given sites in the date range.
    Returns summary: {sites_ok, sites_total, days_generated}.
    """
    days_generated = 0
    for sid in site_ids:
        weather = get_weather(db, sid, date_from, date_to)
        days_generated += len(weather)
    db.commit()
    return {
        "sites_ok": len(site_ids),
        "sites_total": len(site_ids),
        "days_generated": days_generated,
    }


def get_weather_multi(
    db: Session,
    site_ids: List[int],
    date_from: date_type,
    date_to: date_type,
) -> Dict:
    """Get daily weather across multiple sites with envelope (avg/min/max across sites).

    Returns::

        {
          "days": [{date, temp_avg_c, temp_min_c, temp_max_c,
                    envelope_min_c, envelope_max_c, source}],
          "meta": {n_sites, multi_city_risk}
        }
    """
    if not site_ids:
        return {"days": [], "meta": {"n_sites": 0, "multi_city_risk": False}}

    all_data = {}
    site_latitudes = []
    for sid in site_ids:
        weather = get_weather(db, sid, date_from, date_to)
        site = db.query(Site).filter(Site.id == sid).first()
        if site and site.latitude:
            site_latitudes.append(site.latitude)
        for w in weather:
            d = w["date"]
            if d not in all_data:
                all_data[d] = {"avgs": [], "mins": [], "maxs": []}
            all_data[d]["avgs"].append(w["temp_avg_c"])
            all_data[d]["mins"].append(w["temp_min_c"])
            all_data[d]["maxs"].append(w["temp_max_c"])

    # Detect multi-city risk: latitude spread > 2 degrees (~220 km)
    multi_city_risk = False
    if len(site_latitudes) >= 2:
        lat_spread = max(site_latitudes) - min(site_latitudes)
        multi_city_risk = lat_spread > 2.0

    days = []
    for d in sorted(all_data.keys()):
        entry = all_data[d]
        avgs = entry["avgs"]
        days.append({
            "date": d,
            "temp_avg_c": round(sum(avgs) / len(avgs), 1),
            "temp_min_c": round(sum(entry["mins"]) / len(entry["mins"]), 1),
            "temp_max_c": round(sum(entry["maxs"]) / len(entry["maxs"]), 1),
            "envelope_min_c": round(min(avgs), 1),
            "envelope_max_c": round(max(avgs), 1),
            "source": "demo_avg" if len(site_ids) > 1 else "demo",
        })

    return {
        "days": days,
        "meta": {"n_sites": len(site_ids), "multi_city_risk": multi_city_risk},
    }


def _generate_demo_weather(site_id: int, d: date_type, latitude: float) -> EmsWeatherCache:
    """Generate realistic demo weather using sinusoidal model.
    Deterministic: same (site_id, date) always produces the same result.
    """
    random.seed(site_id * 10000 + d.toordinal())

    day_of_year = d.timetuple().tm_yday
    # Sinusoidal annual pattern: coldest mid-January, warmest mid-July
    base_temp = 12.0
    amplitude = 10.0
    phase = 2 * math.pi * (day_of_year - 15) / 365
    seasonal = base_temp - amplitude * math.cos(phase)

    noise = random.gauss(0, 2.5)
    temp_avg = round(seasonal + noise, 1)
    temp_min = round(temp_avg - random.uniform(3, 7), 1)
    temp_max = round(temp_avg + random.uniform(3, 7), 1)

    return EmsWeatherCache(
        site_id=site_id,
        date=datetime.combine(d, datetime.min.time()),
        temp_avg_c=temp_avg,
        temp_min_c=temp_min,
        temp_max_c=temp_max,
        source="demo",
    )
