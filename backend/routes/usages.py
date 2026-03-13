"""
PROMEOS — Routes API Usage V1.1
Endpoints pour la brique Usages Energetiques.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.usage_service import (
    compute_usage_readiness,
    get_metering_plan,
    get_top_ues,
    get_usage_cost_breakdown,
    get_usages_dashboard,
)
from models import Usage, UsageBaseline, USAGE_LABELS_FR, USAGE_FAMILY_MAP, TypeUsage, UsageFamily, DataSourceType

router = APIRouter(prefix="/api/usages", tags=["usages"])


# ── Dashboard agrege ──────────────────────────────────────────────────────


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
