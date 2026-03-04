"""
PROMEOS - Emissions Service (Sprint V9 Decarbonation)
Computes CO2e emissions summary from KPIs + emission factors.

Usage:
    summary = compute_emissions_summary(db, site_id, kpis)
    # Returns: { total_co2e_kg, off_hours_co2e_kg, factor_used, ... }
"""

from typing import Dict, Any, Optional
from datetime import date

from sqlalchemy.orm import Session


# Default fallback factor: France electricity mix (ADEME 2024 approx)
DEFAULT_FACTOR_KGCO2E = 0.052


def get_emission_factor(
    db: Session,
    energy_type: str = "electricity",
    region: str = "FR",
    ref_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Retrieve the best-matching emission factor from DB.
    Falls back to DEFAULT_FACTOR_KGCO2E if none found.

    Returns:
        { kgco2e_per_kwh, source_label, quality, id }
    """
    from models import EmissionFactor

    query = db.query(EmissionFactor).filter(
        EmissionFactor.energy_type == energy_type,
        EmissionFactor.region == region,
    )

    if ref_date:
        query = query.filter(
            (EmissionFactor.valid_from.is_(None)) | (EmissionFactor.valid_from <= ref_date),
            (EmissionFactor.valid_to.is_(None)) | (EmissionFactor.valid_to >= ref_date),
        )

    factor = query.order_by(EmissionFactor.created_at.desc()).first()

    if factor:
        return {
            "id": factor.id,
            "kgco2e_per_kwh": factor.kgco2e_per_kwh,
            "source_label": factor.source_label,
            "quality": factor.quality,
            "energy_type": factor.energy_type,
            "region": factor.region,
        }

    return {
        "id": None,
        "kgco2e_per_kwh": DEFAULT_FACTOR_KGCO2E,
        "source_label": "Facteur par defaut (France mix elec)",
        "quality": "fallback",
        "energy_type": energy_type,
        "region": region,
    }


def compute_emissions_summary(
    db: Session,
    site_id: int,
    kpis: Dict[str, Any],
    energy_type: str = "electricity",
    region: str = "FR",
) -> Dict[str, Any]:
    """
    Compute CO2e emissions summary from monitoring KPIs.

    Uses total_kwh and off_hours_kwh from the KPIs dict.

    Returns:
        {
            total_kwh, total_co2e_kg,
            off_hours_kwh, off_hours_co2e_kg,
            factor: { kgco2e_per_kwh, source_label, quality },
            annualized_co2e_kg, annualized_co2e_tonnes,
        }
    """
    factor_info = get_emission_factor(db, energy_type, region)
    factor = factor_info["kgco2e_per_kwh"]

    total_kwh = kpis.get("total_kwh", 0) or 0
    off_hours_kwh = kpis.get("off_hours_kwh", 0) or 0

    total_co2e_kg = round(total_kwh * factor, 2)
    off_hours_co2e_kg = round(off_hours_kwh * factor, 2)

    # Annualize from 90-day period
    readings_count = kpis.get("readings_count", 0) or 0
    interval_minutes = kpis.get("interval_minutes", 60) or 60
    hours_covered = readings_count * (interval_minutes / 60.0)
    days_covered = hours_covered / 24.0 if hours_covered > 0 else 90

    if days_covered > 0:
        annualized_co2e_kg = round(total_co2e_kg * (365.0 / days_covered), 1)
    else:
        annualized_co2e_kg = 0

    annualized_co2e_tonnes = round(annualized_co2e_kg / 1000.0, 2)

    return {
        "total_kwh": total_kwh,
        "total_co2e_kg": total_co2e_kg,
        "off_hours_kwh": off_hours_kwh,
        "off_hours_co2e_kg": off_hours_co2e_kg,
        "factor": {
            "kgco2e_per_kwh": factor,
            "source_label": factor_info["source_label"],
            "quality": factor_info["quality"],
            "factor_id": factor_info["id"],
        },
        "annualized_co2e_kg": annualized_co2e_kg,
        "annualized_co2e_tonnes": annualized_co2e_tonnes,
        "days_covered": round(days_covered, 1),
    }
