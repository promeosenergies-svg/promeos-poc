"""
PROMEOS — Power Intelligence API.
Endpoints pour l'analyse de la courbe de charge (CDC) et l'optimisation puissance.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.energy_models import Meter
from models.site import Site
from schemas.power_schemas import (
    PowerProfileResponse,
    PowerContractResponse,
    PowerPeaksResponse,
    PowerFactorResponse,
    OptimizePsResponse,
    NebcoResponse,
    NebcoPortfolioResponse,
)

router = APIRouter(prefix="/api/power", tags=["Power Intelligence"])


def _get_primary_meter(db: Session, site_id: int) -> Meter | None:
    """Récupère le compteur principal d'un site."""
    return (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.parent_meter_id.is_(None),
        )
        .first()
    )


@router.get("/sites/{site_id}/profile", response_model=PowerProfileResponse)
def api_power_profile(
    site_id: int,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """
    KPIs puissance : P_max, P_mean, P_base (p5%), E_totale,
    taux utilisation PS, facteur de forme, tan φ, complétude.
    """
    from services.power.power_profile_service import get_power_profile

    if date_fin is None:
        date_fin = date.today()
    if date_debut is None:
        date_debut = date_fin - timedelta(days=30)

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, "Site non trouvé")

    meter = _get_primary_meter(db, site_id)
    if not meter:
        raise HTTPException(404, f"Aucun compteur pour le site {site_id}")

    result = get_power_profile(db, meter.id, date_debut, date_fin)
    result["site_id"] = site_id
    result["site_name"] = site.nom
    return result


@router.get("/sites/{site_id}/contract", response_model=PowerContractResponse)
def api_power_contract(
    site_id: int,
    db: Session = Depends(get_db),
):
    """Paramètres contractuels de puissance (PS par poste, FTA, type compteur)."""
    from models.power import PowerContract

    meter = _get_primary_meter(db, site_id)
    if not meter:
        raise HTTPException(404, f"Aucun compteur pour le site {site_id}")

    contract = (
        db.query(PowerContract)
        .filter(PowerContract.meter_id == meter.id, PowerContract.date_fin.is_(None))
        .order_by(PowerContract.date_debut.desc())
        .first()
    )

    if not contract:
        return {"site_id": site_id, "contract": None}

    return {
        "site_id": site_id,
        "contract": {
            "fta_code": contract.fta_code,
            "domaine_tension": contract.domaine_tension,
            "type_compteur": contract.type_compteur,
            "ps_par_poste_kva": contract.ps_par_poste_kva,
            "p_raccordement_kva": contract.p_raccordement_kva,
            "p_limite_soutirage_kva": contract.p_limite_soutirage_kva,
            "has_periode_mobile": contract.has_periode_mobile,
            "date_debut": contract.date_debut.isoformat(),
        },
    }


def _default_period(date_debut, date_fin, days=30):
    if date_fin is None:
        date_fin = date.today()
    if date_debut is None:
        date_debut = date_fin - timedelta(days=days)
    return date_debut, date_fin


@router.get("/sites/{site_id}/peaks", response_model=PowerPeaksResponse)
def api_power_peaks(
    site_id: int,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    seuil_pct: float = Query(85.0, ge=50, le=100),
    db: Session = Depends(get_db),
):
    """Détection des pics >= seuil_pct% de la PS par poste + CMDPS."""
    from services.power.peak_detection_engine import detect_peaks

    date_debut, date_fin = _default_period(date_debut, date_fin)
    meter = _get_primary_meter(db, site_id)
    if not meter:
        raise HTTPException(404, f"Aucun compteur pour le site {site_id}")

    result = detect_peaks(db, meter.id, date_debut, date_fin, seuil_pct)
    result["site_id"] = site_id
    return result


@router.get("/sites/{site_id}/factor", response_model=PowerFactorResponse)
def api_power_factor(
    site_id: int,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Analyse facteur de puissance (tan φ). Seuil TURPE 7 = 0.4."""
    from services.power.power_factor_analyzer import analyze_power_factor

    date_debut, date_fin = _default_period(date_debut, date_fin)
    meter = _get_primary_meter(db, site_id)
    if not meter:
        raise HTTPException(404, f"Aucun compteur pour le site {site_id}")

    result = analyze_power_factor(db, meter.id, date_debut, date_fin)
    result["site_id"] = site_id
    return result


@router.get("/sites/{site_id}/optimize-ps", response_model=OptimizePsResponse)
def api_optimize_ps(
    site_id: int,
    date_debut: Optional[date] = Query(None),
    date_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Optimisation PS par poste. EIR BT ≥ 36 kVA / HTA ≥ 100 kW."""
    from services.power.subscribed_power_optimizer import optimize_subscribed_power

    date_debut, date_fin = _default_period(date_debut, date_fin, days=180)
    meter = _get_primary_meter(db, site_id)
    if not meter:
        raise HTTPException(404, f"Aucun compteur pour le site {site_id}")

    result = optimize_subscribed_power(db, meter.id, date_debut, date_fin)
    result["site_id"] = site_id
    return result


@router.get("/sites/{site_id}/nebco", response_model=NebcoResponse)
def api_nebco(
    site_id: int,
    site_archetype: str = Query("DEFAULT", description="Archétype site (BUREAU_STANDARD, HOTEL_HEBERGEMENT, etc.)"),
    tarif_central: float = Query(140.0, ge=0, description="Revenu central €/kW/an"),
    tarif_min: float = Query(80.0, ge=0),
    tarif_max: float = Query(200.0, ge=0),
    db: Session = Depends(get_db),
):
    """Éligibilité NEBCO : P_max ≥ 100 kW, checklist 9 critères, tarif paramétrable."""
    from services.power.nebco_eligibility_engine import check_nebco_eligibility

    meter = _get_primary_meter(db, site_id)
    if not meter:
        raise HTTPException(404, f"Aucun compteur pour le site {site_id}")

    result = check_nebco_eligibility(
        db,
        meter.id,
        site_archetype=site_archetype,
        tarif_central=tarif_central,
        tarif_min=tarif_min,
        tarif_max=tarif_max,
    )
    result["site_id"] = site_id
    return result


@router.get("/portfolio/nebco-summary", response_model=NebcoPortfolioResponse)
def api_portfolio_nebco_summary(
    tarif_central: float = Query(140.0, ge=0, description="Revenu central €/kW/an"),
    tarif_min: float = Query(80.0, ge=0),
    tarif_max: float = Query(200.0, ge=0),
    db: Session = Depends(get_db),
):
    """Agrégation NEBCO sur tous les sites. Somme uniquement les éligibles techniques."""
    from services.power.nebco_eligibility_engine import check_nebco_eligibility

    sites = db.query(Site).filter(Site.actif.is_(True)).all()
    if not sites:
        raise HTTPException(404, "Aucun site actif")

    sites_detail = []
    total_p_eff = 0.0
    n_eligible = 0

    for site in sites:
        meter = _get_primary_meter(db, site.id)
        if not meter:
            continue
        result = check_nebco_eligibility(
            db,
            meter.id,
            tarif_central=tarif_central,
            tarif_min=tarif_min,
            tarif_max=tarif_max,
        )
        potentiel = result.get("potentiel")
        is_elig_tech = result.get("eligible_technique", False)

        p_eff = potentiel["P_effacable_total_kw"] if potentiel else 0
        rev_central = potentiel["revenu_central_eur_an"] if potentiel else 0

        sites_detail.append(
            {
                "site_id": site.id,
                "site_name": site.nom,
                "eligible_technique": is_elig_tech,
                "P_max_kw": result.get("P_max_kw"),
                "P_effacable_kw": p_eff,
                "revenu_central_eur_an": rev_central,
                "justification": result.get("justification", ""),
            }
        )

        if is_elig_tech and potentiel:
            total_p_eff += p_eff
            n_eligible += 1

    rev_total = round(total_p_eff * tarif_central)

    return {
        "n_sites_evalues": len(sites_detail),
        "n_sites_eligibles": n_eligible,
        "parametrage_tarif": {
            "tarif_central_eur_kw_an": tarif_central,
            "tarif_min_eur_kw_an": tarif_min,
            "tarif_max_eur_kw_an": tarif_max,
        },
        "agregation": {
            "P_effacable_totale_kw": round(total_p_eff, 1),
            "revenu_central_eur_an": rev_total,
            "revenu_min_eur_an": round(total_p_eff * tarif_min),
            "revenu_max_eur_an": round(total_p_eff * tarif_max),
            "formule": f"{round(total_p_eff, 1)} kW × {tarif_central} €/kW/an = {rev_total} €/an",
        },
        "sites": sites_detail,
        "source": "nebco_eligibility_engine (agrégation portefeuille)",
        "computed_at": datetime.now().isoformat(),
    }
