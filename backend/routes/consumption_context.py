"""
PROMEOS — Routes Consumption Context V0
GET /api/consumption-context/portfolio/summary         — sites ranked by behavior_score
GET /api/consumption-context/site/{site_id}           — contexte complet
GET /api/consumption-context/site/{site_id}/profile    — heatmap + daily profile + baseload
GET /api/consumption-context/site/{site_id}/activity   — schedule + archetype + TOU
GET /api/consumption-context/site/{site_id}/anomalies  — score + KPIs + insights
POST /api/consumption-context/site/{site_id}/diagnose  — refresh diagnostic
GET /api/consumption-context/site/{site_id}/suggest-schedule — auto-suggestion NAF
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access
from models import Site
from services.consumption_context_service import (
    get_full_context,
    get_consumption_profile,
    get_activity_context,
    get_anomalies_and_score,
    suggest_schedule_from_naf,
    get_portfolio_behavior_summary,
)
from services.consumption_diagnostic import run_diagnostic
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/consumption-context", tags=["Consumption Context"])


@router.get("/portfolio/summary")
def portfolio_behavior_summary(
    request: Request,
    days: int = Query(30, ge=7, le=365),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Rank all org sites by behavior_score (worst first)."""
    resolved_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    return get_portfolio_behavior_summary(db, resolved_org_id, days)


def _get_site_or_404(db: Session, site_id: int) -> Site:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")
    return site


@router.get("/site/{site_id}")
def full_context(
    site_id: int,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Full consumption context: profile + activity + anomalies."""
    check_site_access(auth, site_id)
    _get_site_or_404(db, site_id)
    return get_full_context(db, site_id, days)


@router.get("/site/{site_id}/profile")
def site_profile(
    site_id: int,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Consumption profile: heatmap 7x24, daily profile 24pts, baseload, peak."""
    check_site_access(auth, site_id)
    _get_site_or_404(db, site_id)
    return get_consumption_profile(db, site_id, days)


@router.get("/site/{site_id}/activity")
def site_activity(
    site_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Activity context: operating schedule, archetype from NAF, active TOU."""
    check_site_access(auth, site_id)
    _get_site_or_404(db, site_id)
    return get_activity_context(db, site_id)


@router.get("/site/{site_id}/anomalies")
def site_anomalies(
    site_id: int,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Anomalies + KPIs + behavior_score."""
    check_site_access(auth, site_id)
    _get_site_or_404(db, site_id)
    return get_anomalies_and_score(db, site_id, days)


@router.post("/site/{site_id}/diagnose")
def diagnose_refresh(
    site_id: int,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Refresh consumption diagnostics and return updated score."""
    check_site_access(auth, site_id)
    _get_site_or_404(db, site_id)
    run_diagnostic(db, site_id, days=days)
    db.commit()
    return get_anomalies_and_score(db, site_id, days)


@router.get("/site/{site_id}/suggest-schedule")
def suggest_schedule(
    site_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Auto-suggest operating schedule based on site NAF code."""
    check_site_access(auth, site_id)
    _get_site_or_404(db, site_id)
    suggestion = suggest_schedule_from_naf(db, site_id)
    if not suggestion:
        return {"suggestion": None, "message": "Aucun code NAF ou archetype trouve pour ce site"}
    return suggestion
