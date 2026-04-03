"""
PROMEOS - Flex Score Routes
GET  /api/flex/score/sites/{site_id}           — score flexibilite par usage du site
GET  /api/flex/score/usages                    — referentiel 15 usages + scores
GET  /api/flex/score/prix-signal               — interprete un prix spot en signal NEBCO
GET  /api/flex/score/portfolios/{portfolio_id}  — score flex agrege portefeuille
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext

router = APIRouter(prefix="/api/flex/score", tags=["Flex Score Engine"])


# --- Helpers ---

COS_PHI_TERTIAIRE = 0.8  # kVA -> kW, facteur de puissance typique tertiaire
TAUX_UTILISATION_HEURISTIQUE = 0.25  # pour estimation P_max depuis conso annuelle


def _get_p_max_kw(db: Session, meter, site=None) -> float:
    """
    P_max du site. Ordre de priorite :
    1. PowerProfile CDC reelle (P_max_kw sur 365j)
    2. PowerContract PS par poste (somme kVA x 0.8)
    3. Estimation depuis conso annuelle (heuristique)
    4. 0.0 (fail-safe)
    """
    # 1. PowerProfile (donnees CDC reelles)
    if meter:
        try:
            from services.power.power_profile_service import get_power_profile

            today = date.today()
            profile = get_power_profile(db, meter.id, today - timedelta(days=365), today)
            p_max = profile.get("kpis", {}).get("P_max_kw", 0.0) or 0.0
            if p_max > 0:
                return float(p_max)
        except Exception:
            pass

    # 2. PowerContract (PS souscrite x cos phi)
    if meter:
        try:
            from services.power.power_profile_service import get_active_contract

            contract = get_active_contract(db, meter.id, date.today())
            if contract and contract.ps_par_poste_kva:
                total_kva = sum(v for v in contract.ps_par_poste_kva.values() if isinstance(v, (int, float)))
                if total_kva > 0:
                    return round(total_kva * COS_PHI_TERTIAIRE, 1)
        except Exception:
            pass

    # 3. Estimation depuis conso annuelle
    if site:
        conso = getattr(site, "annual_kwh_total", None) or 0
        if conso > 0:
            return round(conso / (8760 * TAUX_UTILISATION_HEURISTIQUE), 1)

    return 0.0


def _resolve_archetype(db, site, meter=None) -> str:
    """Resolve archetype from UsageProfile or NAF code."""
    try:
        from models.energy_models import Meter, UsageProfile

        if meter is None:
            meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.is_active == True).first()
        if meter:
            profile = db.query(UsageProfile).filter(UsageProfile.meter_id == meter.id).first()
            if profile and profile.archetype_code:
                return profile.archetype_code
    except Exception:
        pass

    NAF_TO_ARCHETYPE = {
        "6820": "BUREAU_STANDARD",
        "5510": "HOTEL_HEBERGEMENT",
        "8520": "ENSEIGNEMENT",
        "5210": "LOGISTIQUE_SEC",
        "4711": "COMMERCE_ALIMENTAIRE",
    }
    if site.naf_code and site.naf_code in NAF_TO_ARCHETYPE:
        return NAF_TO_ARCHETYPE[site.naf_code]

    return "DEFAULT"


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

    total_surface = sum(s.surface_m2 or 0 for s in sites)
    use_equal_weight = total_surface == 0
    score_pondere = 0.0
    sites_detail = []

    for site in sites:
        meter = meter_by_site.get(site.id)

        # Archetype from pre-loaded data
        archetype = "DEFAULT"
        if meter:
            up = profile_by_meter.get(meter.id)
            if up and up.archetype_code:
                archetype = up.archetype_code
        if archetype == "DEFAULT" and site.naf_code:
            archetype = _resolve_archetype(db, site, meter)

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
