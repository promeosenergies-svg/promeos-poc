"""
Signature énergétique : décomposition E = a × DJU + b.

- b = baseload (kWh/jour) — ce qui tourne même quand T = 18°C
- a = thermosensibilité (kWh/DJU) — énergie par degré d'écart
- R² = qualité du modèle (> 0.7 = bon, > 0.85 = excellent)

Comparaison au benchmark archétype pour détecter :
- Baseload excessif → serveurs, éclairage nuit, veille
- Thermosensibilité élevée → isolation déficiente, GTB mal réglée
"""

import logging
import random
import time
from datetime import date, timedelta, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH
from models.site import Site
from models.energy_models import Meter, MeterReading
from services.weather_dju_service import get_site_coordinates, get_daily_temperatures, compute_dju

logger = logging.getLogger(__name__)

# Cache TTL en secondes (la signature ne change pas en temps réel)
_SIG_CACHE: dict[tuple, tuple] = {}
_SIG_CACHE_TTL = 1800  # 30 min

# Benchmarks baseload et thermosensibilité par archétype.
# Valeurs pour 1000 m² — sources : ADEME, CSTB, retours terrain.
_SIGNATURE_BENCHMARKS = {
    "bureau": {"baseload_per_1000m2": 200, "thermo_per_1000m2": 15},
    "hotel": {"baseload_per_1000m2": 400, "thermo_per_1000m2": 20},
    "enseignement": {"baseload_per_1000m2": 100, "thermo_per_1000m2": 18},
    "entrepot": {"baseload_per_1000m2": 50, "thermo_per_1000m2": 8},
    "usine": {"baseload_per_1000m2": 150, "thermo_per_1000m2": 10},
    "magasin": {"baseload_per_1000m2": 250, "thermo_per_1000m2": 12},
    "commerce": {"baseload_per_1000m2": 250, "thermo_per_1000m2": 12},
    "sante": {"baseload_per_1000m2": 350, "thermo_per_1000m2": 22},
    "collectivite": {"baseload_per_1000m2": 120, "thermo_per_1000m2": 16},
    "copropriete": {"baseload_per_1000m2": 80, "thermo_per_1000m2": 20},
    "logement_social": {"baseload_per_1000m2": 70, "thermo_per_1000m2": 22},
}


def compute_energy_signature(db: Session, site_id: int, months: int = 12) -> dict | None:
    """
    Décompose la consommation d'un site en baseload + thermosensibilité.
    Agréger kWh/jour, récupérer DJU, régression linéaire, benchmark archétype.
    """
    key = (site_id, months)
    cached = _SIG_CACHE.get(key)
    if cached and time.monotonic() < cached[1]:
        return cached[0]

    result = _compute_energy_signature(db, site_id, months)
    if result and "error" not in result:
        _SIG_CACHE[key] = (result, time.monotonic() + _SIG_CACHE_TTL)
    return result


def _compute_energy_signature(db: Session, site_id: int, months: int) -> dict | None:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return None

    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    meters = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.parent_meter_id.is_(None),
        )
        .all()
    )

    if not meters:
        return {"error": "Aucun compteur principal", "site_id": site_id}

    meter_ids = [m.id for m in meters]

    # func.date compatible SQLite + PostgreSQL
    day_expr = func.date(MeterReading.timestamp)
    rows = (
        db.query(
            day_expr.label("day"),
            func.sum(MeterReading.value_kwh).label("kwh"),
        )
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= datetime(start_date.year, start_date.month, start_date.day),
        )
        .group_by(day_expr)
        .all()
    )

    daily_kwh = {str(row.day): float(row.kwh or 0) for row in rows}

    if len(daily_kwh) < 60:
        return {"error": "Données insuffisantes", "days": len(daily_kwh), "min_required": 60}

    coords = get_site_coordinates(site)
    if not coords:
        return {"error": "Coordonnées GPS non disponibles"}

    temperatures = get_daily_temperatures(coords[0], coords[1], start_date, end_date)
    if len(temperatures) < 60:
        return {"error": "Données météo insuffisantes", "meteo_days": len(temperatures)}

    dju_data = compute_dju(temperatures)

    dju_by_date = {d["date"]: d for d in dju_data}
    aligned = []
    for day_str, kwh in daily_kwh.items():
        if day_str in dju_by_date:
            aligned.append(
                {
                    "date": day_str,
                    "kwh": kwh,
                    "dju_chauf": dju_by_date[day_str]["dju_chauf"],
                    "dju_clim": dju_by_date[day_str]["dju_clim"],
                    "temp_mean": dju_by_date[day_str]["temp_mean"],
                }
            )

    if len(aligned) < 60:
        return {"error": "Données alignées insuffisantes", "aligned_days": len(aligned)}

    x_vals = [d["dju_chauf"] for d in aligned]
    y_vals = [d["kwh"] for d in aligned]

    a, b, r_squared = _linear_regression(x_vals, y_vals)

    surface = site.surface_m2 or getattr(site, "tertiaire_area_m2", None) or 1000
    arch_code = site.type.value if site.type else "bureau"

    benchmark = _get_signature_benchmark(arch_code, surface)

    baseload_excess = max(0, b - benchmark["baseload_expected"])
    thermo_excess = max(0, a - benchmark["thermo_expected"])

    dju_annual_chauf = sum(d["dju_chauf"] for d in dju_data)
    dju_annual_clim = sum(d["dju_clim"] for d in dju_data)

    savings_baseload = baseload_excess * 365
    savings_thermo = thermo_excess * dju_annual_chauf

    # Échantillon aléatoire pour le scatter (max 120 points)
    scatter_sample = random.sample(aligned, min(120, len(aligned)))

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "period_days": len(aligned),
        "signature": {
            "baseload_kwh_day": round(b, 1),
            "thermosensitivity_kwh_dju": round(a, 2),
            "r_squared": round(r_squared, 3),
            "model_quality": ("excellent" if r_squared > 0.85 else "bon" if r_squared > 0.70 else "faible"),
        },
        "benchmark": {
            "archetype": arch_code,
            "surface_m2": round(surface),
            "baseload_expected": benchmark["baseload_expected"],
            "thermo_expected": benchmark["thermo_expected"],
            "baseload_verdict": ("elevated" if baseload_excess > benchmark["baseload_expected"] * 0.15 else "normal"),
            "thermo_verdict": ("elevated" if thermo_excess > benchmark["thermo_expected"] * 0.15 else "normal"),
        },
        "savings_potential": {
            "baseload_excess_kwh_year": round(savings_baseload),
            "baseload_excess_eur_year": round(savings_baseload * DEFAULT_PRICE_ELEC_EUR_KWH),
            "thermo_excess_kwh_year": round(savings_thermo),
            "thermo_excess_eur_year": round(savings_thermo * DEFAULT_PRICE_ELEC_EUR_KWH),
            "total_savings_kwh": round(savings_baseload + savings_thermo),
            "total_savings_eur": round((savings_baseload + savings_thermo) * DEFAULT_PRICE_ELEC_EUR_KWH),
        },
        "dju_summary": {
            "annual_dju_chauf": round(dju_annual_chauf),
            "annual_dju_clim": round(dju_annual_clim),
            "source": "Open-Meteo / COSTIC 18°C",
        },
        "scatter_data": [
            {"dju": round(d["dju_chauf"], 1), "kwh": round(d["kwh"], 1), "date": d["date"]} for d in scatter_sample
        ],
        "regression_line": {
            "x_min": 0,
            "x_max": round(max(x_vals), 1) if x_vals else 20,
            "y_at_x_min": round(b, 1),
            "y_at_x_max": round(a * max(x_vals) + b, 1) if x_vals else round(b, 1),
        },
    }


# ── Régression linéaire ────────────────────────────────────────────────────


def _linear_regression(x_vals: list[float], y_vals: list[float]) -> tuple[float, float, float]:
    """
    Régression linéaire y = a*x + b.
    Retourne (a, b, r_squared).
    Utilise numpy si disponible, sinon moindres carrés manuels.
    """
    try:
        import numpy as np

        coeffs = np.polyfit(x_vals, y_vals, 1)
        a = float(coeffs[0])
        b = float(coeffs[1])
    except ImportError:
        a, b = _manual_least_squares(x_vals, y_vals)
    except Exception:
        logger.warning("numpy.polyfit failed, falling back to manual OLS")
        a, b = _manual_least_squares(x_vals, y_vals)

    y_mean = sum(y_vals) / len(y_vals)
    ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
    ss_res = sum((y - (a * x + b)) ** 2 for x, y in zip(x_vals, y_vals))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return (a, b, max(0, r_squared))


def _manual_least_squares(x_vals: list[float], y_vals: list[float]) -> tuple[float, float]:
    """Moindres carrés manuels sans numpy."""
    n = len(x_vals)
    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
    sum_x2 = sum(x**2 for x in x_vals)
    denom = n * sum_x2 - sum_x**2
    if denom == 0:
        return (0, sum_y / n if n else 0)
    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n
    return (a, b)


# ── Benchmarks par archétype ───────────────────────────────────────────────


def _get_signature_benchmark(archetype: str, surface_m2: float) -> dict:
    """Benchmark baseload et thermosensibilité, proportionnel à la surface."""
    fallback = {"baseload_per_1000m2": 200, "thermo_per_1000m2": 15}
    bench = _SIGNATURE_BENCHMARKS.get(str(archetype).lower(), fallback)

    factor = surface_m2 / 1000
    return {
        "baseload_expected": round(bench["baseload_per_1000m2"] * factor, 1),
        "thermo_expected": round(bench["thermo_per_1000m2"] * factor, 2),
    }
