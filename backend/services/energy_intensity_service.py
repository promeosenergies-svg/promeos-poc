"""
PROMEOS — Energy Intensity Service (kWh/m²/an)
Calcul d'intensité énergétique finale et primaire par site et portefeuille.

Intensité finale  = kWh_final / surface_m2
Intensité primaire = kWh_final × coeff_EP / surface_m2

Coefficients EP (énergie primaire) depuis janvier 2026 — RE2020 :
  - Électricité : 1.9 (anciennement 2.3)
  - Gaz : 1.0
  - Chaleur réseau : 1.0 (valeur par défaut — dépend du mix local)
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import Site, Portefeuille
from models.energy_models import EnergyVector
from services.consumption_unified_service import get_consumption_summary

logger = logging.getLogger("promeos.energy_intensity")

# ── EP coefficients (énergie primaire) ──────────────────────────────
# Source: RE2020 — applicable depuis le 1er janvier 2026
EP_COEFFICIENTS = {
    EnergyVector.ELECTRICITY: 1.9,
    EnergyVector.GAS: 1.0,
    EnergyVector.HEAT: 1.0,
    EnergyVector.WATER: 0.0,  # pas de conversion EP pour l'eau
    EnergyVector.OTHER: 1.0,
}


def get_site_intensity(
    db: Session,
    site_id: int,
    year: Optional[int] = None,
) -> dict:
    """
    Intensité énergétique d'un site (finale + primaire).

    Returns:
        {
            site_id, site_nom, surface_m2, year,
            kWh_final, kWh_m2_final, kWh_m2_primary,
            ep_detail: { electricity: {kwh, coeff_ep, kwh_ep}, gas: {...}, ... },
            data_source, confidence,
            warnings: [str]
        }
    """
    site = db.query(Site).filter(Site.id == site_id, Site.actif == True).first()
    if not site:
        return {"error": "site_not_found", "site_id": site_id}

    warnings = []
    surface = site.surface_m2

    # Surface validation
    if not surface or surface <= 0:
        warnings.append("surface_m2 absente ou nulle — intensité non calculable")
        return {
            "site_id": site_id,
            "site_nom": site.nom,
            "surface_m2": None,
            "year": year or date.today().year,
            "kWh_final": None,
            "kWh_m2_final": None,
            "kWh_m2_primary": None,
            "ep_detail": {},
            "data_source": None,
            "confidence": "none",
            "warnings": warnings,
        }

    # Period
    if year is None:
        year = date.today().year
    period_start = date(year - 1, 1, 1)
    period_end = date(year - 1, 12, 31)

    # Consumption per energy vector
    ep_detail = {}
    total_kwh_final = 0.0
    total_kwh_ep = 0.0
    best_source = "none"
    best_confidence = "none"
    confidence_order = {"high": 3, "medium": 2, "low": 1, "none": 0}

    for vector in [EnergyVector.ELECTRICITY, EnergyVector.GAS, EnergyVector.HEAT]:
        summary = get_consumption_summary(
            db, site_id, period_start, period_end, energy_vector=vector
        )
        kwh = summary.get("value_kwh", 0) or 0
        if kwh <= 0:
            continue
        # Skip estimated fallback — it uses total site kWh, not per-vector
        if summary.get("source_used") == "estimated":
            continue

        coeff = EP_COEFFICIENTS.get(vector, 1.0)
        kwh_ep = kwh * coeff

        ep_detail[vector.value] = {
            "kwh": round(kwh, 2),
            "coeff_ep": coeff,
            "kwh_ep": round(kwh_ep, 2),
        }
        total_kwh_final += kwh
        total_kwh_ep += kwh_ep

        # Track best confidence across vectors
        src = summary.get("source_used", "none")
        conf = summary.get("confidence", "none")
        if confidence_order.get(conf, 0) > confidence_order.get(best_confidence, 0):
            best_confidence = conf
            best_source = src

    # If no per-vector data, fallback to unified (all vectors combined)
    if total_kwh_final == 0:
        summary = get_consumption_summary(db, site_id, period_start, period_end)
        kwh = summary.get("value_kwh", 0) or 0
        if kwh > 0:
            # Assume electricity if vector breakdown unavailable
            coeff = EP_COEFFICIENTS[EnergyVector.ELECTRICITY]
            ep_detail["electricity"] = {
                "kwh": round(kwh, 2),
                "coeff_ep": coeff,
                "kwh_ep": round(kwh * coeff, 2),
            }
            total_kwh_final = kwh
            total_kwh_ep = kwh * coeff
            best_source = summary.get("source_used", "estimated")
            best_confidence = summary.get("confidence", "low")
            warnings.append(
                "ventilation par vecteur indisponible — "
                "coefficient EP électricité appliqué par défaut"
            )

    # Compute intensities
    kwh_m2_final = round(total_kwh_final / surface, 2) if total_kwh_final > 0 else 0.0
    kwh_m2_primary = round(total_kwh_ep / surface, 2) if total_kwh_ep > 0 else 0.0

    if total_kwh_final == 0:
        warnings.append("aucune donnée de consommation pour la période")
        best_confidence = "none"

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "surface_m2": surface,
        "year": year,
        "kWh_final": round(total_kwh_final, 2),
        "kWh_m2_final": kwh_m2_final,
        "kWh_m2_primary": kwh_m2_primary,
        "ep_detail": ep_detail,
        "data_source": best_source,
        "confidence": best_confidence,
        "warnings": warnings,
    }


def get_portfolio_intensity(
    db: Session,
    portfolio_id: int,
    year: Optional[int] = None,
) -> dict:
    """
    Intensité énergétique agrégée d'un portefeuille.

    Moyenne pondérée par surface : Σ(kWh_sites) / Σ(surface_sites)
    pour les sites ayant une surface renseignée.

    Returns:
        {
            portfolio_id, portfolio_nom, year,
            kWh_m2_final, kWh_m2_primary,
            total_kwh_final, total_kwh_primary, total_surface_m2,
            coverage: { sites_total, sites_with_surface, sites_with_data, ratio },
            sites: [ site_intensity_result, ... ],
            warnings: [str]
        }
    """
    portfolio = db.query(Portefeuille).filter(Portefeuille.id == portfolio_id).first()
    if not portfolio:
        return {"error": "portfolio_not_found", "portfolio_id": portfolio_id}

    sites = (
        db.query(Site)
        .filter(Site.portefeuille_id == portfolio_id, Site.actif == True)
        .all()
    )

    if not sites:
        return {
            "portfolio_id": portfolio_id,
            "portfolio_nom": portfolio.nom,
            "year": year or date.today().year,
            "kWh_m2_final": None,
            "kWh_m2_primary": None,
            "total_kwh_final": 0,
            "total_kwh_primary": 0,
            "total_surface_m2": 0,
            "coverage": {"sites_total": 0, "sites_with_surface": 0, "sites_with_data": 0, "ratio": 0},
            "sites": [],
            "warnings": ["aucun site actif dans ce portefeuille"],
        }

    warnings = []
    site_results = []
    total_kwh_final = 0.0
    total_kwh_primary = 0.0
    total_surface = 0.0
    sites_with_surface = 0
    sites_with_data = 0

    for site in sites:
        result = get_site_intensity(db, site.id, year)
        site_results.append(result)

        surface = result.get("surface_m2")
        kwh_final = result.get("kWh_final")

        if surface and surface > 0:
            sites_with_surface += 1
            total_surface += surface

            if kwh_final and kwh_final > 0:
                sites_with_data += 1
                total_kwh_final += kwh_final
                # Sum EP kWh from ep_detail
                for vec_data in result.get("ep_detail", {}).values():
                    total_kwh_primary += vec_data.get("kwh_ep", 0)

    # Weighted average intensity
    if total_surface > 0 and total_kwh_final > 0:
        kwh_m2_final = round(total_kwh_final / total_surface, 2)
        kwh_m2_primary = round(total_kwh_primary / total_surface, 2)
    else:
        kwh_m2_final = None
        kwh_m2_primary = None

    sites_total = len(sites)
    coverage_ratio = round(sites_with_surface / sites_total, 2) if sites_total > 0 else 0

    if sites_with_surface < sites_total:
        n_missing = sites_total - sites_with_surface
        warnings.append(
            f"{n_missing} site(s) exclu(s) du calcul — surface manquante"
        )

    return {
        "portfolio_id": portfolio_id,
        "portfolio_nom": portfolio.nom,
        "year": year or date.today().year,
        "kWh_m2_final": kwh_m2_final,
        "kWh_m2_primary": kwh_m2_primary,
        "total_kwh_final": round(total_kwh_final, 2),
        "total_kwh_primary": round(total_kwh_primary, 2),
        "total_surface_m2": round(total_surface, 2),
        "coverage": {
            "sites_total": sites_total,
            "sites_with_surface": sites_with_surface,
            "sites_with_data": sites_with_data,
            "ratio": coverage_ratio,
        },
        "sites": site_results,
        "warnings": warnings,
    }
