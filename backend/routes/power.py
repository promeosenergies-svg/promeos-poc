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
