"""
Profil de charge : baseload, facteur de charge, ratios temporels, score qualite.

Indicateurs issus de la doctrine CDC Enedis PROMEOS :
- Baseload P5 : percentile 5 des puissances nuit/WE (talon de consommation)
- Load factor : P_moy / P_max (0-1)
- Ratio nuit/jour : E_22h-6h / E_6h-22h
- Ratio semaine/WE : (E_WE/2) / (E_sem/5)
- Score qualite : 1 - (trous + aberrants + incoherents) / total_pas
"""

import logging
import math
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from models.site import Site

logger = logging.getLogger(__name__)

_LP_CACHE: dict[tuple, tuple] = {}
_LP_CACHE_TTL = 900  # 15 min


def compute_load_profile(db: Session, site_id: int, months: int = 12) -> dict | None:
    """Calcule le profil de charge complet d'un site."""
    key = (site_id, months)
    cached = _LP_CACHE.get(key)
    if cached and time.monotonic() < cached[1]:
        return cached[0]

    result = _compute_load_profile(db, site_id, months)
    if result and "error" not in result:
        _LP_CACHE[key] = (result, time.monotonic() + _LP_CACHE_TTL)
    return result


def _compute_load_profile(db: Session, site_id: int, months: int) -> dict | None:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return None

    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)
    start_dt = datetime(start_date.year, start_date.month, start_date.day)

    from data_staging.bridge import get_site_meter_ids, get_readings

    meter_ids = get_site_meter_ids(db, site_id)
    if not meter_ids:
        return {"error": "Aucun compteur principal", "site_id": site_id}

    raw_readings, data_source = get_readings(db, meter_ids, start_dt)
    # Convertir en tuples compatibles
    readings = [(r.timestamp, r.value_kwh, r.quality_score) for r in raw_readings]

    if len(readings) < 30:
        return {"error": "Donnees insuffisantes", "readings": len(readings), "min_required": 30}

    # Agreger par jour et par heure
    daily_kwh: dict[str, float] = defaultdict(float)
    hourly_powers: list[dict] = []

    for ts, kwh, qscore in readings:
        day_str = ts.strftime("%Y-%m-%d")
        daily_kwh[day_str] += kwh or 0
        hourly_powers.append(
            {
                "ts": ts,
                "kwh": kwh or 0,
                "hour": ts.hour,
                "weekday": ts.weekday(),  # 0=lundi, 6=dimanche
                "quality": qscore,
            }
        )

    if not hourly_powers:
        return {"error": "Aucune donnee exploitable"}

    # ── Single-pass accumulation ──────────────────────────────────────
    all_kwh_values = []
    night_weekend_powers = []
    e_night = 0.0
    e_day = 0.0
    e_weekday = 0.0
    e_weekend = 0.0
    weekday_dates: set[str] = set()
    weekend_dates: set[str] = set()
    hourly_by_hour: dict[int, list[float]] = defaultdict(list)

    for r in hourly_powers:
        kwh = r["kwh"]
        hour = r["hour"]
        wd = r["weekday"]
        day_str = r["ts"].strftime("%Y-%m-%d")

        all_kwh_values.append(kwh)
        hourly_by_hour[hour].append(kwh)

        is_night = hour >= 22 or hour < 6
        is_weekend = wd >= 5

        if is_night or is_weekend:
            night_weekend_powers.append(kwh)
        if is_night:
            e_night += kwh
        else:
            e_day += kwh
        if is_weekend:
            e_weekend += kwh
            weekend_dates.add(day_str)
        else:
            e_weekday += kwh
            weekday_dates.add(day_str)

    # ── Baseload P5 ──────────────────────────────────────────────────
    if len(night_weekend_powers) >= 10:
        night_weekend_powers.sort()
        baseload_kwh = night_weekend_powers[max(0, int(len(night_weekend_powers) * 0.05))]
    else:
        all_sorted = sorted(all_kwh_values)
        baseload_kwh = all_sorted[max(0, int(len(all_sorted) * 0.05))]

    # ── Puissances globales ───────────────────────────────────────────
    p_moy = sum(all_kwh_values) / len(all_kwh_values) if all_kwh_values else 0
    p_max = max(all_kwh_values) if all_kwh_values else 0
    p_min = min(all_kwh_values) if all_kwh_values else 0

    all_kwh_sorted = sorted(all_kwh_values)
    n = len(all_kwh_sorted)
    p95 = all_kwh_sorted[min(int(n * 0.95), n - 1)] if n else 0
    p5 = all_kwh_sorted[min(int(n * 0.05), n - 1)] if n else 0

    load_factor = p_moy / p_max if p_max > 0 else 0
    night_day_ratio = e_night / e_day if e_day > 0 else 0

    # ── Ratio semaine/week-end ────────────────────────────────────────
    n_weekday_days = len(weekday_dates)
    n_weekend_days = len(weekend_dates)

    if n_weekday_days > 0 and n_weekend_days > 0:
        e_weekday_per_day = e_weekday / n_weekday_days
        e_weekend_per_day = e_weekend / n_weekend_days
        weekend_weekday_ratio = e_weekend_per_day / e_weekday_per_day if e_weekday_per_day > 0 else 0
    else:
        e_weekday_per_day = 0
        e_weekend_per_day = 0
        weekend_weekday_ratio = 0

    base_peak_ratio = p5 / p95 if p95 > 0 else 0

    # ── Variabilite intra-journaliere ─────────────────────────────────
    hourly_means = [sum(v) / len(v) for v in hourly_by_hour.values() if v]
    if len(hourly_means) > 1 and sum(hourly_means) > 0:
        mu = sum(hourly_means) / len(hourly_means)
        sigma = math.sqrt(sum((x - mu) ** 2 for x in hourly_means) / len(hourly_means))
        variability_intraday = sigma / mu if mu > 0 else 0
    else:
        variability_intraday = 0

    # ── Variabilite inter-journaliere ─────────────────────────────────
    daily_vals = list(daily_kwh.values())
    if len(daily_vals) > 1:
        mu_d = sum(daily_vals) / len(daily_vals)
        sigma_d = math.sqrt(sum((x - mu_d) ** 2 for x in daily_vals) / len(daily_vals))
        variability_interday = sigma_d / mu_d if mu_d > 0 else 0
    else:
        variability_interday = 0

    # ── Intensite des pics ────────────────────────────────────────────
    peak_intensity = (p_max - p_moy) / p_moy if p_moy > 0 else 0

    # ── Score qualite donnees ─────────────────────────────────────────
    quality = _compute_quality_score(hourly_powers, start_date, end_date)

    # ── Profil horaire type (24 valeurs) ──────────────────────────────
    hourly_profile = []
    for h in range(24):
        vals = hourly_by_hour.get(h, [])
        hourly_profile.append(round(sum(vals) / len(vals), 2) if vals else 0)

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "period_days": len(daily_kwh),
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "data_source": data_source,
        "baseload": {
            "p5_kwh": round(baseload_kwh, 2),
            "baseload_pct_of_mean": round(baseload_kwh / p_moy * 100, 1) if p_moy > 0 else 0,
            "verdict": (
                "eleve"
                if p_moy > 0 and baseload_kwh / p_moy > 0.6
                else "modere"
                if p_moy > 0 and baseload_kwh / p_moy > 0.35
                else "normal"
            ),
        },
        "load_factor": round(load_factor, 3),
        "ratios": {
            "night_day": round(night_day_ratio, 3),
            "weekend_weekday": round(weekend_weekday_ratio, 3),
            "base_peak": round(base_peak_ratio, 3),
        },
        "power_stats": {
            "p_mean_kwh": round(p_moy, 2),
            "p_max_kwh": round(p_max, 2),
            "p_min_kwh": round(p_min, 2),
            "p95_kwh": round(p95, 2),
            "p5_kwh": round(p5, 2),
        },
        "variability": {
            "intraday_cv": round(variability_intraday, 3),
            "interday_cv": round(variability_interday, 3),
            "peak_intensity": round(peak_intensity, 2),
        },
        "data_quality": quality,
        "hourly_profile": hourly_profile,
        "daily_consumption": {
            "weekday_kwh_day": round(e_weekday_per_day, 1),
            "weekend_kwh_day": round(e_weekend_per_day, 1),
            "total_kwh": round(sum(daily_vals), 0),
        },
    }


def _compute_quality_score(readings: list[dict], start_date: date, end_date: date) -> dict:
    """Score qualite Q = 1 - (trous + aberrants + incoherents) / total.

    Seuils doctrine CDC :
    - >0.95 = Excellent
    - 0.90-0.95 = Bon
    - 0.80-0.90 = Acceptable
    - <0.80 = Insuffisant
    """
    total_days = (end_date - start_date).days
    if total_days <= 0:
        return {"score": 0, "label": "insuffisant", "details": {}}

    # Jours avec donnees
    days_with_data = len({r["ts"].strftime("%Y-%m-%d") for r in readings})
    gaps = max(0, total_days - days_with_data)

    # Valeurs aberrantes (negatif ou > 10x la mediane)
    all_kwh = sorted(r["kwh"] for r in readings)
    if all_kwh:
        median_kwh = all_kwh[len(all_kwh) // 2]
        threshold = max(median_kwh * 10, 1)
        outliers = sum(1 for r in readings if r["kwh"] < 0 or r["kwh"] > threshold)
    else:
        outliers = 0

    # Incoherences : sauts brusques > 5 sigma
    inconsistencies = 0
    if len(readings) > 10:
        diffs = [abs(readings[i]["kwh"] - readings[i - 1]["kwh"]) for i in range(1, len(readings))]
        if diffs:
            mu_diff = sum(diffs) / len(diffs)
            sigma_diff = math.sqrt(sum((d - mu_diff) ** 2 for d in diffs) / len(diffs)) if len(diffs) > 1 else 1
            threshold_diff = mu_diff + 5 * sigma_diff if sigma_diff > 0 else mu_diff * 10
            inconsistencies = sum(1 for d in diffs if d > threshold_diff)

    total_issues = gaps + outliers + inconsistencies
    total_points = max(total_days, len(readings))
    score = max(0, 1 - total_issues / total_points) if total_points > 0 else 0

    if score > 0.95:
        label = "excellent"
    elif score > 0.90:
        label = "bon"
    elif score > 0.80:
        label = "acceptable"
    else:
        label = "insuffisant"

    return {
        "score": round(score, 3),
        "label": label,
        "details": {
            "total_days": total_days,
            "days_with_data": days_with_data,
            "gaps": gaps,
            "outliers": outliers,
            "inconsistencies": inconsistencies,
            "completeness_pct": round(days_with_data / total_days * 100, 1) if total_days > 0 else 0,
        },
    }
