"""
PROMEOS - Demo Seed: Consumption Targets Generator (V87)
Creates ConsumptionTarget records per site (yearly + monthly, 2024-2026).
Aligned with Decret Tertiaire reduction trajectory.
"""
import random

from models.consumption_target import ConsumptionTarget

# Seasonal weight per month (Jan=high, Jul=low) — same pattern as gen_readings seasonal
_MONTHLY_WEIGHTS = [1.40, 1.30, 1.10, 0.90, 0.75, 0.65,
                    0.60, 0.65, 0.85, 1.00, 1.20, 1.40]
_WEIGHT_SUM = sum(_MONTHLY_WEIGHTS)

# Average FR electricity cost and CO2 intensity used for EUR and CO2e targets
_EUR_PER_KWH = 0.155
_CO2_G_PER_KWH = 52.0  # gCO2/kWh France (mix 2024)


def generate_targets(db, sites: list, rng: random.Random) -> dict:
    """
    Generate ConsumptionTarget (electricity) for 2024-2026, per site.
    Each year: 1 yearly target + 12 monthly targets (seasonal distribution).
    Trajectory: -1.5%/year vs 2024 baseline (modest Decret Tertiaire path).
    """
    count = 0

    for site in sites:
        baseline_kwh = site.annual_kwh_total or 500_000

        for year in [2024, 2025, 2026]:
            reduction = 1.0 - (year - 2024) * 0.015
            annual_target = baseline_kwh * reduction

            # Yearly target
            db.add(ConsumptionTarget(
                site_id=site.id,
                energy_type="electricity",
                period="yearly",
                year=year,
                month=None,
                target_kwh=round(annual_target),
                target_eur=round(annual_target * _EUR_PER_KWH),
                target_co2e_kg=round(annual_target * _CO2_G_PER_KWH / 1000.0),
                source="forecast",
                notes=f"Decret Tertiaire — base {baseline_kwh:.0f} kWh, reduction {(1 - reduction) * 100:.1f}%",
            ))
            count += 1

            # Monthly targets (seasonal distribution)
            for m, weight in enumerate(_MONTHLY_WEIGHTS, 1):
                monthly_kwh = annual_target * weight / _WEIGHT_SUM
                db.add(ConsumptionTarget(
                    site_id=site.id,
                    energy_type="electricity",
                    period="monthly",
                    year=year,
                    month=m,
                    target_kwh=round(monthly_kwh),
                    target_eur=round(monthly_kwh * _EUR_PER_KWH),
                    target_co2e_kg=round(monthly_kwh * _CO2_G_PER_KWH / 1000.0),
                    source="forecast",
                ))
                count += 1

    db.flush()
    return {"targets_count": count}
