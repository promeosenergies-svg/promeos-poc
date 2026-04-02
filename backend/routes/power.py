"""
PROMEOS — Power Intelligence API.
Endpoints pour l'analyse de la courbe de charge (CDC) et l'optimisation puissance.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.energy_models import Meter
from models.site import Site

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


@router.get("/sites/{site_id}/profile")
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


@router.get("/sites/{site_id}/contract")
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


@router.get("/sites/{site_id}/peaks")
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


@router.get("/sites/{site_id}/factor")
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


@router.get("/sites/{site_id}/optimize-ps")
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


@router.get("/sites/{site_id}/nebef")
def api_nebef(
    site_id: int,
    db: Session = Depends(get_db),
):
    """Éligibilité NEBEF : P_max ≥ 100 kW, checklist 9 critères."""
    from services.power.nebef_eligibility_engine import check_nebef_eligibility

    meter = _get_primary_meter(db, site_id)
    if not meter:
        raise HTTPException(404, f"Aucun compteur pour le site {site_id}")

    result = check_nebef_eligibility(db, meter.id)
    result["site_id"] = site_id
    return result
