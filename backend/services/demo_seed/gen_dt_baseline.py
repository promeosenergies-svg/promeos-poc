"""
PROMEOS - Demo Seed: DT Baseline 2020-2023 Generator
Extends HELIOS consumption targets to include the Decret Tertiaire
reference year (2020) and intermediate years (2021-2023).

Calibration: ADEME benchmarks x surface_m2 (same as gen_targets.py).
Drift: -1.5%/year with +/-3% climate noise.
DT targets: interpolated from milestones (-40% 2030, -50% 2040, -60% 2050).
Deterministic: uses provided RNG for reproducibility.
Idempotent: skips existing (site_id, energy_type, period, year) records.
"""

import random

from models.consumption_target import ConsumptionTarget
from .gen_targets import ADEME_BENCHMARKS, EUR_PER_KWH, CO2_KG_PER_KWH, _get_weights, site_has_gas

# Decret Tertiaire milestones (Decret n°2019-771)
_DT_MILESTONES = {2030: -0.40, 2040: -0.50, 2050: -0.60}
_BASELINE_YEARS = [2020, 2021, 2022, 2023]
_REF_YEAR = 2020
_ANNUAL_DRIFT = -0.015
_CLIMATE_NOISE = 0.03


def _interpolate_dt_reduction(year: int, ref_year: int = _REF_YEAR) -> float:
    """Return reduction ratio for a given year (e.g., -0.20 means 20% below baseline)."""
    if year <= ref_year:
        return 0.0
    milestones = sorted(_DT_MILESTONES.items())
    for i, (my, mr) in enumerate(milestones):
        if year <= my:
            prev_y = ref_year if i == 0 else milestones[i - 1][0]
            prev_r = 0.0 if i == 0 else milestones[i - 1][1]
            if my == prev_y:
                return mr
            return prev_r + (mr - prev_r) * (year - prev_y) / (my - prev_y)
    return milestones[-1][1]


def generate_dt_baseline(
    db,
    sites: list,
    rng: random.Random,
    site_meta: dict = None,
) -> dict:
    """
    Seed ConsumptionTarget records for 2020-2023 (DT reference period).

    For each site and energy_type:
      - 2020 baseline = ADEME benchmark * surface_m2
      - 2021-2023 actual = baseline * drift * (1 + climate_noise)
      - target_kwh = baseline * (1 + DT_reduction_interpolated)

    Idempotent: skips records where (site_id, energy_type, period, year) already exists.

    Returns: {"dt_baseline_count": int}
    """
    count = 0

    # Batch idempotency check: fetch all existing (site_id, energy_type, year) in one query
    site_ids = [s.id for s in sites]
    existing_keys = set()
    if site_ids:
        rows = (
            db.query(
                ConsumptionTarget.site_id,
                ConsumptionTarget.energy_type,
                ConsumptionTarget.year,
            )
            .filter(
                ConsumptionTarget.site_id.in_(site_ids),
                ConsumptionTarget.period == "yearly",
                ConsumptionTarget.year.in_(_BASELINE_YEARS),
            )
            .all()
        )
        existing_keys = {(r[0], r[1], r[2]) for r in rows}

    for site in sites:
        meta = (site_meta or {}).get(site.id, {})
        type_site = meta.get("type_site", "bureau")
        surface_m2 = meta.get("surface_m2", 0) or getattr(site, "surface_m2", 0) or 0
        if surface_m2 <= 0:
            continue

        has_gas = site_has_gas(db, site)
        energy_types = ["electricity"]
        if has_gas:
            energy_types.append("gas")

        for energy_type in energy_types:
            benchmarks = ADEME_BENCHMARKS.get(type_site, ADEME_BENCHMARKS["bureau"])
            bench_kwh_m2 = benchmarks.get(energy_type, benchmarks.get("electricity", 170))
            baseline_kwh = bench_kwh_m2 * surface_m2

            eur_rate = EUR_PER_KWH.get(energy_type, EUR_PER_KWH["electricity"])
            co2_rate = CO2_KG_PER_KWH.get(energy_type, CO2_KG_PER_KWH["electricity"])
            weights = _get_weights(type_site, energy_type)

            for year in _BASELINE_YEARS:
                if (site.id, energy_type, year) in existing_keys:
                    continue

                # Compute actual with drift + climate noise
                drift_factor = 1.0 + _ANNUAL_DRIFT * (year - _REF_YEAR)
                noise = rng.uniform(-_CLIMATE_NOISE, _CLIMATE_NOISE) if year > _REF_YEAR else 0.0
                actual_kwh = round(baseline_kwh * drift_factor * (1.0 + noise))

                # DT target: interpolated from milestones
                dt_reduction = _interpolate_dt_reduction(year)
                target_kwh = round(baseline_kwh * (1.0 + dt_reduction))

                # Yearly record
                db.add(
                    ConsumptionTarget(
                        site_id=site.id,
                        energy_type=energy_type,
                        period="yearly",
                        year=year,
                        month=None,
                        target_kwh=target_kwh,
                        actual_kwh=actual_kwh,
                        target_eur=round(target_kwh * eur_rate),
                        actual_eur=round(actual_kwh * eur_rate),
                        target_co2e_kg=round(target_kwh * co2_rate),
                        actual_co2e_kg=round(actual_kwh * co2_rate),
                        source="historical",
                        notes=f"DT baseline {type_site} {bench_kwh_m2} kWh/m2, surface {surface_m2} m2",
                    )
                )
                count += 1

                # 12 monthly records
                for m in range(1, 13):
                    monthly_target = target_kwh * weights[m - 1] / 12.0
                    monthly_noise = rng.uniform(-0.03, 0.03)
                    monthly_actual = round(actual_kwh * weights[m - 1] / 12.0 * (1.0 + monthly_noise))
                    db.add(
                        ConsumptionTarget(
                            site_id=site.id,
                            energy_type=energy_type,
                            period="monthly",
                            year=year,
                            month=m,
                            target_kwh=round(monthly_target),
                            actual_kwh=monthly_actual,
                            target_eur=round(monthly_target * eur_rate),
                            actual_eur=round(monthly_actual * eur_rate),
                            target_co2e_kg=round(monthly_target * co2_rate),
                            actual_co2e_kg=round(monthly_actual * co2_rate),
                            source="historical",
                        )
                    )
                    count += 1

    db.flush()
    return {"dt_baseline_count": count}
