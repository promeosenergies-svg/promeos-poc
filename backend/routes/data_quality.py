"""
PROMEOS — Data Quality routes (Chantier 1)
GET /api/data-quality/completeness — org-level data quality overview
GET /api/data-quality/completeness/{site_id} — single site detail
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.data_quality_service import compute_org_completeness, compute_site_completeness

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
