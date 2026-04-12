"""
PROMEOS - Flex Score Routes
GET  /api/flex/score/sites/{site_id}           — score flexibilite par usage du site
GET  /api/flex/score/usages                    — referentiel 15 usages + scores
GET  /api/flex/score/prix-signal               — interprete un prix spot en signal NEBCO
GET  /api/flex/score/portfolios/{portfolio_id}  — score flex agrege portefeuille
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.flex.archetype_resolver import (
    resolve_archetype as _resolve_archetype,
    normalize_archetype as _normalize_archetype,
    batch_resolve_archetypes,
)
from services.power.power_profile_service import resolve_p_max_kw as _get_p_max_kw

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flex/score", tags=["Flex Score Engine"])


# --- Endpoints ---


@router.get("/sites/{site_id}")
def get_site_flex_score(
    site_id: int,
    db: Session = Depends(get_db),
):
    """Score de flexibilite du site par usage."""
    from models.site import Site
    from models.energy_models import Meter
    from services.flex.flexibility_scoring_engine import get_usages_par_archetype, score_site_flex

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} non trouve")

    meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).first()
    archetype = _resolve_archetype(db, site, meter)
    P_max_kw = _get_p_max_kw(db, meter, site)

    usages = get_usages_par_archetype(archetype)
    result = score_site_flex(usages, P_max_kw, archetype)

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "archetype_code": archetype,
        "P_max_kw": P_max_kw,
        **result,
    }


@router.get("/usages")
def get_all_usages_scores(
    P_max_kw: float = Query(0.0, description="Puissance max pour filtrage NEBCO"),
):
    """Referentiel des 15 usages avec scores."""
    from services.flex.flexibility_scoring_engine import USAGE_PROFILES, score_usage

    scores = []
    for code in USAGE_PROFILES:
        s = score_usage(code, P_max_kw)
        scores.append(
            {
                "code": code,
                "label": s.usage_label,
                "score_global": s.score_global,
                "pilotabilite": s.score_pilotabilite,
                "nebco_compat": s.nebco_compat,
                "nebco_score": s.score_nebco,
                "mecanismes": s.mecanismes,
                "modulations": s.modulations,
                "priorite": s.priorite,
                "nogo_nebco": s.nogo_nebco,
                "signal_prix_negatifs": s.signal_prix_negatifs,
                "heures_solaires": s.heures_solaires,
                "instrumentation": s.instrumentation_requise,
            }
        )

    scores.sort(key=lambda x: x["score_global"], reverse=True)
    return {
        "n_usages": len(scores),
        "usages": scores,
        "source": "flexibility_scoring_engine",
    }


@router.get("/prix-signal")
def get_prix_signal(
    prix_spot_eur_mwh: float = Query(..., description="Prix spot en EUR/MWh"),
):
    """
    Interprete un prix spot en signal NEBCO actionnable.

    Seuils (sources RTE/CRE 2025) :
    - <= -10 EUR/MWh -> signal ANTICIPATION (augmenter conso)
    - >= 100 EUR/MWh -> signal EFFACEMENT (baisser conso)
    """
    from services.flex.flexibility_scoring_engine import detect_prix_negatif_signal

    return detect_prix_negatif_signal(prix_spot_eur_mwh)


@router.get("/portfolios/{portfolio_id}")
def get_portfolio_flex_score(
    portfolio_id: int,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Score de flexibilite agrege pour un portefeuille (pondere par surface)."""
    from models.site import Site
    from models.energy_models import Meter, UsageProfile
    from models import Portefeuille
    from models.base import not_deleted
    from services.flex.flexibility_scoring_engine import get_usages_par_archetype, score_site_flex

    portfolio = db.query(Portefeuille).filter(Portefeuille.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"Portefeuille {portfolio_id} non trouve")

    sites = db.query(Site).filter(Site.portefeuille_id == portfolio_id, not_deleted(Site)).all()
    if not sites:
        return {
            "portfolio_id": portfolio_id,
            "portfolio_nom": portfolio.nom,
            "score_flex_global": 0.0,
            "n_sites": 0,
            "sites": [],
            "source": "flexibility_scoring_engine",
            "computed_at": datetime.now().isoformat(),
        }

    # Batch-load meters and usage profiles to avoid N+1
    site_ids = [s.id for s in sites]
    meters = db.query(Meter).filter(Meter.site_id.in_(site_ids), Meter.is_active == True).all()
    meter_by_site = {m.site_id: m for m in meters}

    meter_ids = [m.id for m in meters]
    profiles = db.query(UsageProfile).filter(UsageProfile.meter_id.in_(meter_ids)).all() if meter_ids else []
    profile_by_meter = {p.meter_id: p for p in profiles}

    archetypes_by_site = batch_resolve_archetypes(db, sites, meter_by_site, profile_by_meter)

    total_surface = sum(s.surface_m2 or 0 for s in sites)
    use_equal_weight = total_surface == 0
    score_pondere = 0.0
    sites_detail = []

    for site in sites:
        meter = meter_by_site.get(site.id)
        archetype = archetypes_by_site[site.id]
        P_max_kw = _get_p_max_kw(db, meter, site)

        usages = get_usages_par_archetype(archetype)
        result = score_site_flex(usages, P_max_kw, archetype)
        score_site = result["score_global_site"]

        if use_equal_weight:
            poids = 1.0 / len(sites)
        else:
            poids = (site.surface_m2 or 0) / total_surface
        score_pondere += score_site * poids

        sites_detail.append(
            {
                "site_id": site.id,
                "site_nom": site.nom,
                "archetype_code": archetype,
                "score_flex": score_site,
                "poids_surface": round(poids, 3),
                "nebco_eligible": result["nebco_eligible_direct"],
            }
        )

    sites_detail.sort(key=lambda x: x["score_flex"], reverse=True)

    return {
        "portfolio_id": portfolio_id,
        "portfolio_nom": portfolio.nom,
        "score_flex_global": round(score_pondere, 3),
        "n_sites": len(sites),
        "sites": sites_detail,
        "source": "flexibility_scoring_engine",
        "computed_at": datetime.now().isoformat(),
    }
