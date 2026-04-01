"""
PROMEOS - Demo Seed: Consumption Targets Generator (V110)
Creates ConsumptionTarget records per site: ADEME benchmarks, seasonal profiles,
both electricity and gas, with realistic actuals for past months.
"""

import math
import random
from datetime import datetime, timezone

from models.consumption_target import ConsumptionTarget

# ── ADEME surface benchmarks (kWh/m2/year) ────────────────────────────────────

ADEME_BENCHMARKS = {
    "bureau": {"electricity": 170, "gas": 50},
    "entrepot": {"electricity": 120, "gas": 80},
    "hotel": {"electricity": 280, "gas": 100},
    "enseignement": {"electricity": 110, "gas": 60},
    "commerce": {"electricity": 200, "gas": 40},
    "sante": {"electricity": 250, "gas": 120},
}

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_GAZ_EUR_KWH

EUR_PER_KWH = {"electricity": DEFAULT_PRICE_ELEC_EUR_KWH, "gas": DEFAULT_PRICE_GAZ_EUR_KWH}
from config.emission_factors import get_emission_factor

CO2_KG_PER_KWH = {"electricity": get_emission_factor("ELEC"), "gas": get_emission_factor("GAZ")}

# ── Seasonal weight profiles (Jan-Dec, sum ~12.0) ─────────────────────────────

_SEASONAL_ELEC = {
    "bureau": [1.30, 1.25, 1.10, 0.95, 0.80, 0.70, 0.65, 0.70, 0.85, 1.00, 1.20, 1.30],
    "entrepot": [1.10, 1.08, 1.02, 0.98, 0.95, 0.92, 0.90, 0.92, 0.95, 1.00, 1.08, 1.10],
    "hotel": [0.75, 0.80, 0.88, 0.95, 1.10, 1.20, 1.30, 1.28, 1.10, 0.90, 0.80, 0.74],
    "enseignement": [1.30, 1.25, 1.15, 1.00, 0.90, 0.60, 0.20, 0.20, 0.90, 1.10, 1.20, 1.30],
}

_SEASONAL_GAS = {
    "bureau": [1.80, 1.65, 1.30, 0.80, 0.30, 0.10, 0.05, 0.05, 0.30, 0.85, 1.40, 1.80],
    "entrepot": [1.70, 1.55, 1.25, 0.80, 0.35, 0.15, 0.08, 0.08, 0.35, 0.85, 1.35, 1.70],
    "hotel": [1.50, 1.40, 1.15, 0.85, 0.50, 0.30, 0.20, 0.20, 0.50, 0.90, 1.30, 1.50],
    "enseignement": [1.70, 1.55, 1.25, 0.80, 0.35, 0.10, 0.05, 0.05, 0.35, 0.85, 1.40, 1.70],
}


def site_has_gas(db, site) -> bool:
    """Check if site has a gas meter (shared by gen_targets + gen_dt_baseline)."""
    try:
        from models import Meter
        from models.energy_models import EnergyVector

        return (
            db.query(Meter).filter(Meter.site_id == site.id, Meter.energy_vector == EnergyVector.GAS).first()
            is not None
        )
    except Exception:
        return False


def _get_weights(type_site: str, energy_type: str) -> list:
    """Return normalized 12-month weight list (sum=12.0)."""
    if energy_type == "gas":
        raw = _SEASONAL_GAS.get(type_site, _SEASONAL_GAS["bureau"])
    else:
        raw = _SEASONAL_ELEC.get(type_site, _SEASONAL_ELEC["bureau"])
    s = sum(raw)
    return [w * 12.0 / s for w in raw] if s > 0 else [1.0] * 12


def generate_targets(db, sites: list, rng: random.Random, site_meta: dict = None) -> dict:
    """
    Generate ConsumptionTarget for 2024-2026 per site.
    Each year: 1 yearly + 12 monthly targets with seasonal distribution.
    Past months include realistic actual values.
    Trajectory: -1.5%/year vs 2024 baseline (Decret Tertiaire).
    """
    now = datetime.now(timezone.utc)
    current_year = now.year
    current_month = now.month
    current_day = now.day
    count = 0

    for site in sites:
        meta = (site_meta or {}).get(site.id, {})
        type_site = meta.get("type_site", "bureau")
        surface_m2 = meta.get("surface_m2", 0) or getattr(site, "surface_m2", 0) or 0

        # Determine energy types for this site
        has_gas = getattr(site, "_has_gas", False) or site_has_gas(db, site)

        energy_types = ["electricity"]
        if has_gas:
            energy_types.append("gas")

        for energy_type in energy_types:
            benchmarks = ADEME_BENCHMARKS.get(type_site, ADEME_BENCHMARKS["bureau"])
            bench_kwh_m2 = benchmarks.get(energy_type, benchmarks.get("electricity", 170))

            # Compute annual baseline from surface
            if surface_m2 > 0:
                baseline_kwh = bench_kwh_m2 * surface_m2
            else:
                baseline_kwh = site.annual_kwh_total or 500_000

            eur_rate = EUR_PER_KWH.get(energy_type, DEFAULT_PRICE_ELEC_EUR_KWH)
            co2_rate = CO2_KG_PER_KWH.get(energy_type, get_emission_factor("ELEC"))
            weights = _get_weights(type_site, energy_type)

            for year in [2024, 2025, 2026]:
                # Decret Tertiaire trajectory: -1.5%/year from 2024
                reduction = 1.0 - (year - 2024) * 0.015
                annual_target = baseline_kwh * reduction

                # Yearly target
                yearly_actual = _compute_yearly_actual(
                    annual_target, year, current_year, current_month, current_day, weights, rng, eur_rate, co2_rate
                )
                db.add(
                    ConsumptionTarget(
                        site_id=site.id,
                        energy_type=energy_type,
                        period="yearly",
                        year=year,
                        month=None,
                        target_kwh=round(annual_target),
                        target_eur=round(annual_target * eur_rate),
                        target_co2e_kg=round(annual_target * co2_rate),
                        actual_kwh=yearly_actual["kwh"],
                        actual_eur=yearly_actual["eur"],
                        actual_co2e_kg=yearly_actual["co2"],
                        source="forecast",
                        notes=f"ADEME {type_site} {bench_kwh_m2} kWh/m2, surface {surface_m2} m2",
                    )
                )
                count += 1

                # Monthly targets
                for m in range(1, 13):
                    monthly_target = annual_target * weights[m - 1] / 12.0
                    actual = _compute_monthly_actual(
                        monthly_target, year, m, current_year, current_month, current_day, rng, eur_rate, co2_rate
                    )
                    db.add(
                        ConsumptionTarget(
                            site_id=site.id,
                            energy_type=energy_type,
                            period="monthly",
                            year=year,
                            month=m,
                            target_kwh=round(monthly_target),
                            target_eur=round(monthly_target * eur_rate),
                            target_co2e_kg=round(monthly_target * co2_rate),
                            actual_kwh=actual["kwh"],
                            actual_eur=actual["eur"],
                            actual_co2e_kg=actual["co2"],
                            source="forecast",
                        )
                    )
                    count += 1

    db.flush()
    return {"targets_count": count}


def _compute_monthly_actual(target_kwh, year, month, cur_year, cur_month, cur_day, rng, eur_rate, co2_rate) -> dict:
    """Compute actual values for a given month. None if future."""
    # Future month
    if year > cur_year or (year == cur_year and month > cur_month):
        return {"kwh": None, "eur": None, "co2": None}

    # Current month: partial actual (prorated)
    if year == cur_year and month == cur_month:
        days_in_month = 31  # approximate
        fraction = cur_day / days_in_month
        variance = rng.uniform(-0.05, 0.08)
        actual_kwh = round(target_kwh * fraction * (1.0 + variance))
        return {
            "kwh": actual_kwh,
            "eur": round(actual_kwh * eur_rate),
            "co2": round(actual_kwh * co2_rate),
        }

    # Past month: full actual with realistic variance
    # 2024: mostly on-track (-5% to +5%)
    # 2025: slight upward drift (+2% to +10%) — degradation triggering alerts
    # 2026 past months: +3% to +12% — continuing drift
    if year == 2024:
        variance = rng.uniform(-0.05, 0.05)
    elif year == 2025:
        variance = rng.uniform(0.02, 0.10)
    else:
        variance = rng.uniform(0.03, 0.12)

    # Occasional over-budget spike (~15% of months)
    if rng.random() < 0.15:
        variance += rng.uniform(0.05, 0.10)

    actual_kwh = round(target_kwh * (1.0 + variance))
    return {
        "kwh": actual_kwh,
        "eur": round(actual_kwh * eur_rate),
        "co2": round(actual_kwh * co2_rate),
    }


def _compute_yearly_actual(annual_target, year, cur_year, cur_month, cur_day, weights, rng, eur_rate, co2_rate) -> dict:
    """Compute yearly actual as sum of monthly actuals for completed months."""
    if year > cur_year:
        return {"kwh": None, "eur": None, "co2": None}

    total_kwh = 0
    months_done = 12 if year < cur_year else cur_month - 1
    # For past years, sum all 12 months; for current year, sum completed months
    for m in range(1, months_done + 1):
        monthly_target = annual_target * weights[m - 1] / 12.0
        actual = _compute_monthly_actual(monthly_target, year, m, cur_year, cur_month, cur_day, rng, eur_rate, co2_rate)
        if actual["kwh"] is not None:
            total_kwh += actual["kwh"]

    # Add current month partial for current year
    if year == cur_year and cur_month <= 12:
        monthly_target = annual_target * weights[cur_month - 1] / 12.0
        partial = _compute_monthly_actual(
            monthly_target, year, cur_month, cur_year, cur_month, cur_day, rng, eur_rate, co2_rate
        )
        if partial["kwh"] is not None:
            total_kwh += partial["kwh"]

    if total_kwh == 0 and year > cur_year:
        return {"kwh": None, "eur": None, "co2": None}

    return {
        "kwh": round(total_kwh),
        "eur": round(total_kwh * eur_rate),
        "co2": round(total_kwh * co2_rate),
    }
