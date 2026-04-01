"""
PROMEOS — Routes API Usage V1.2
Endpoints pour la brique Usages Energetiques.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.usage_service import (
    compute_usage_readiness,
    get_metering_plan,
    get_top_ues,
    get_usage_cost_breakdown,
    get_usages_dashboard,
    compute_baselines,
    get_usage_compliance,
    get_usage_billing_links,
    get_usage_timeline,
    get_portfolio_usage_comparison,
    get_meter_readings_preview,
    get_scoped_usages_dashboard,
    get_scoped_usage_timeline,
)
from models import Usage, UsageBaseline, USAGE_LABELS_FR, USAGE_FAMILY_MAP, TypeUsage, UsageFamily, DataSourceType

router = APIRouter(prefix="/api/usages", tags=["usages"])


# ── Dashboard scoped (multi-niveaux) ─────────────────────────────────────


@router.get("/scoped-dashboard")
def api_scoped_usages_dashboard(
    request: Request,
    entity_id: Optional[int] = Query(None),
    portefeuille_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    archetype_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Dashboard usages adaptatif : org → entité → portefeuille → site, filtrable par archétype."""
    org_id = resolve_org_id(request, auth, db)
    return get_scoped_usages_dashboard(
        db,
        org_id,
        entity_id=entity_id,
        portefeuille_id=portefeuille_id,
        site_id=site_id,
        archetype_code=archetype_code,
    )


@router.get("/scoped-timeline")
def api_scoped_usage_timeline(
    request: Request,
    entity_id: Optional[int] = Query(None),
    portefeuille_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    archetype_code: Optional[str] = Query(None),
    months: int = Query(12, ge=3, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Timeline usages agrégée par scope, filtrable par archétype."""
    org_id = resolve_org_id(request, auth, db)
    return get_scoped_usage_timeline(
        db,
        org_id,
        entity_id=entity_id,
        portefeuille_id=portefeuille_id,
        site_id=site_id,
        archetype_code=archetype_code,
        months=months,
    )


@router.get("/archetypes-in-scope")
def api_archetypes_in_scope(
    request: Request,
    entity_id: Optional[int] = Query(None),
    portefeuille_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Distribution des archétypes (TypeSite) dans le scope courant, pour les chips filtre."""
    from models.site import Site as SiteModel
    from services.scope_utils import resolve_site_ids as _resolve

    org_id = resolve_org_id(request, auth, db)
    site_ids = _resolve(db, org_id, entity_id=entity_id, portefeuille_id=portefeuille_id, site_id=site_id)
    if not site_ids:
        return {"archetypes": []}

    sites = db.query(SiteModel.type).filter(SiteModel.id.in_(site_ids)).all()
    counts = {}
    for (t,) in sites:
        label = t.value if hasattr(t, "value") else str(t)
        counts[label] = counts.get(label, 0) + 1

    archetypes = sorted(
        [{"code": k, "label": k.replace("_", " ").title(), "count": v} for k, v in counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )
    return {"archetypes": archetypes}


# ── Coût par période tarifaire × usage ───────────────────────────────────


@router.get("/cost-by-period/{site_id}")
def api_cost_by_period(
    site_id: int,
    months: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Ventilation du coût par usage × période tarifaire TURPE 7 (HPH/HCH/HPB/HCB)."""
    from services.cost_by_period_service import get_cost_by_period

    return get_cost_by_period(db, site_id, months)


# ── Dashboard agrege (legacy mono-site) ──────────────────────────────────


@router.get("/dashboard/{site_id}")
def api_usages_dashboard(site_id: int, db: Session = Depends(get_db)):
    """Endpoint principal de la page /usages : readiness + plan + UES + derives + cout."""
    return get_usages_dashboard(db, site_id)


# ── Readiness Score ───────────────────────────────────────────────────────


@router.get("/readiness/{site_id}")
def api_usage_readiness(site_id: int, db: Session = Depends(get_db)):
    """Score de readiness usage d'un site (/100)."""
    return compute_usage_readiness(db, site_id)


# ── Metering Plan ─────────────────────────────────────────────────────────


@router.get("/metering-plan/{site_id}")
def api_metering_plan(site_id: int, db: Session = Depends(get_db)):
    """Plan de comptage dynamique d'un site."""
    return get_metering_plan(db, site_id)


# ── Top UES ───────────────────────────────────────────────────────────────


@router.get("/top-ues/{site_id}")
def api_top_ues(
    site_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Top usages energetiques significatifs, tries par kWh."""
    return get_top_ues(db, site_id, limit=limit)


# ── Cost Breakdown ────────────────────────────────────────────────────────


@router.get("/cost-breakdown/{site_id}")
def api_usage_cost_breakdown(
    site_id: int,
    days: int = Query(365, ge=30, le=1095),
    db: Session = Depends(get_db),
):
    """Ventilation du cout energetique par usage."""
    return get_usage_cost_breakdown(db, site_id, days=days)


# ── Taxonomie ─────────────────────────────────────────────────────────────


@router.get("/taxonomy")
def api_usage_taxonomy():
    """Retourne la taxonomie des usages energetiques (familles + types + labels FR)."""
    families = {}
    for usage_type in TypeUsage:
        family = USAGE_FAMILY_MAP.get(usage_type, UsageFamily.AUXILIAIRES)
        if family.value not in families:
            families[family.value] = {"family": family.value, "usages": []}
        families[family.value]["usages"].append(
            {
                "type": usage_type.value,
                "label": USAGE_LABELS_FR.get(usage_type, usage_type.value),
                "is_legacy": usage_type in (TypeUsage.BUREAUX, TypeUsage.CVC, TypeUsage.FROID),
            }
        )
    return {
        "families": list(families.values()),
        "data_sources": [{"value": ds.value, "label": ds.value.replace("_", " ").title()} for ds in DataSourceType],
    }


# ── V1.2 — Baselines ─────────────────────────────────────────────────────


@router.get("/baselines/{site_id}")
def api_usage_baselines(site_id: int, db: Session = Depends(get_db)):
    """Baselines auto-calculees avec comparaison avant/apres."""
    return compute_baselines(db, site_id)


# ── V1.2 — Compliance par usage ──────────────────────────────────────────


@router.get("/compliance/{site_id}")
def api_usage_compliance(site_id: int, db: Session = Depends(get_db)):
    """Widget conformite par usage (BACS, DT, ISO 50001)."""
    return get_usage_compliance(db, site_id)


# ── V1.2 — Billing links ────────────────────────────────────────────────


@router.get("/billing-links/{site_id}")
def api_usage_billing_links(site_id: int, db: Session = Depends(get_db)):
    """Liens usage → facture → contrat → achat."""
    return get_usage_billing_links(db, site_id)


# ── CRUD Usages (liste, create) ──────────────────────────────────────────


@router.get("/site/{site_id}")
def api_list_usages(site_id: int, db: Session = Depends(get_db)):
    """Liste les usages declares pour un site."""
    usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=site_id)).all()

    return [
        {
            "id": u.id,
            "batiment_id": u.batiment_id,
            "type": u.type.value,
            "label": u.label or USAGE_LABELS_FR.get(u.type, u.type.value),
            "family": USAGE_FAMILY_MAP.get(u.type, UsageFamily.AUXILIAIRES).value,
            "description": u.description,
            "surface_m2": u.surface_m2,
            "data_source": u.data_source.value if u.data_source else None,
            "is_significant": u.is_significant,
            "pct_of_total": u.pct_of_total,
        }
        for u in usages
    ]


# ── V2 — Timeline mensuelle ─────────────────────────────────────────────


@router.get("/timeline/{site_id}")
def api_usage_timeline(
    site_id: int,
    months: int = Query(12, ge=3, le=36),
    db: Session = Depends(get_db),
):
    """Consommation mensuelle par usage pour AreaChart empile."""
    return get_usage_timeline(db, site_id, months=months)


# ── V2 — Comparaison inter-sites ────────────────────────────────────────


@router.get("/portfolio-compare")
def api_portfolio_usage_comparison(
    org_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Compare les IPE par usage pour tous les sites d'une organisation."""
    return get_portfolio_usage_comparison(db, org_id)


# ── V2 — Meter readings preview ─────────────────────────────────────────


@router.get("/meter-readings/{meter_id}")
def api_meter_readings_preview(
    meter_id: int,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Releves recents d'un compteur pour mini-graphe inline."""
    return get_meter_readings_preview(db, meter_id, days=days)
