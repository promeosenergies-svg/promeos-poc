"""
PROMEOS — Data Quality routes (Chantier 1)
GET /api/data-quality/completeness — org-level data quality overview
GET /api/data-quality/completeness/{site_id} — single site detail
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from fastapi import HTTPException, Request
from typing import Optional
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.data_quality_service import (
    compute_org_completeness,
    compute_site_completeness,
    compute_site_data_quality,
    compute_portfolio_data_quality,
    compute_site_freshness,
)
from services.error_catalog import business_error

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])


@router.get("/completeness")
def get_org_completeness(
    org_id: int = Query(..., description="Organisation ID"),
    db: Session = Depends(get_db),
):
    """Data quality completeness for all sites in an organisation."""
    return compute_org_completeness(db, org_id)


@router.get("/completeness/{site_id}")
def get_site_completeness(
    site_id: int,
    db: Session = Depends(get_db),
):
    """Data quality completeness detail for a single site."""
    rows = compute_site_completeness(db, site_id)
    return {"site_id": site_id, "rows": rows}


# ── D.1: Score qualité données 4 dimensions ──


@router.get("/site/{site_id}")
def get_site_data_quality(
    site_id: int,
    db: Session = Depends(get_db),
):
    """Score qualité données 0-100 pour un site (4 dimensions pondérées)."""
    from models import Site

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(**business_error("SITE_NOT_FOUND", site_id=site_id))
    return compute_site_data_quality(db, site_id)


@router.get("/freshness/{site_id}")
def get_site_freshness(
    site_id: int,
    db: Session = Depends(get_db),
):
    """D.2 — Fraîcheur des données pour un site."""
    from models import Site

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(**business_error("SITE_NOT_FOUND", site_id=site_id))
    return compute_site_freshness(db, site_id)


@router.get("/portfolio")
def get_portfolio_data_quality(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Score qualité données agrégé pour tous les sites de l'organisation."""
    org_id = resolve_org_id(request, auth, db)
    return compute_portfolio_data_quality(db, org_id)
