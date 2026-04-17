"""
PROMEOS - Purchase Strategy Routes
GET /api/purchase/strategy/sites/{site_id}
    — recommandation strategie d'achat via archetype flex canonique + profil CDC
"""

import logging
from dataclasses import asdict
from datetime import date, timedelta

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access
from services.flex.archetype_resolver import resolve_archetype
from services.power.power_profile_service import resolve_p_max_kw
from services.purchase.strategy_recommender import recommend_purchase_strategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/purchase/strategy", tags=["Purchase Strategy"])


@router.get("/sites/{site_id}")
def get_site_purchase_strategy(
    site_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    check_site_access(auth, site_id)
    """
    Recommande une strategie d'achat pour le site.

    Pipeline :
    1. Resolution archetype canonique (UsageProfile -> KB -> NAF -> DEFAULT)
    2. Extraction profil CDC (P_max_kw, facteur_forme) via PowerProfile
    3. Matching profil -> strategie + ajustements (P_max, FF, eligibilite PPA)

    Returns:
        {
            "site_id": ..., "site_nom": ..., "archetype_code": "BUREAU_STANDARD",
            "strategy": "fixe", "rationale": "...",
            "composition": {"fixe": 70, "indexe": 20, "spot": 10, "ppa": 0},
            "green_recommended": true, "ppa_eligible": false,
            "hp_pct": 70, "hc_pct": 30,
            "cdc_profile_snapshot": {"P_max_kw": 185.0, "facteur_forme": 0.42, ...},
            "adjustments": ["..."]
        }
    """
    from models.site import Site
    from models.energy_models import Meter

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} non trouve")

    meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).first()
    archetype = resolve_archetype(db, site, meter)

    P_max_kw = resolve_p_max_kw(db, meter, site)
    facteur_forme = _fetch_facteur_forme(db, meter)
    annual_kwh = getattr(site, "annual_kwh_total", None)

    reco = recommend_purchase_strategy(
        archetype_code=archetype,
        P_max_kw=P_max_kw,
        facteur_forme=facteur_forme,
        annual_kwh=annual_kwh,
    )

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        **asdict(reco),
    }


def _fetch_facteur_forme(db: Session, meter) -> float | None:
    """Facteur de forme sur 365j depuis PowerProfile, fail-safe -> None."""
    if not meter:
        return None
    try:
        from services.power.power_profile_service import get_power_profile

        today = date.today()
        profile = get_power_profile(db, meter.id, today - timedelta(days=365), today)
        return (profile.get("kpis") or {}).get("facteur_forme")
    except Exception as exc:
        logger.debug("facteur forme lookup failed: %s", exc)
        return None
