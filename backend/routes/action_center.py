"""Action Center — aggregated actionable issues across PROMEOS domains."""

from fastapi import APIRouter, Depends, Query, Request
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import get_optional_auth, AuthContext

router = APIRouter(prefix="/api/action-center", tags=["action-center"])


def _get_org_id(request: Request, auth: Optional[AuthContext]) -> int:
    org_header = request.headers.get("X-Org-Id")
    if org_header:
        return int(org_header)
    if auth and auth.org_id:
        return auth.org_id
    return 1


@router.get("/issues")
def list_issues(
    request: Request,
    domain: Optional[str] = Query(None, description="Filter by domain: compliance, billing, purchase, patrimoine"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low, info"),
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    status: Optional[str] = Query(None, description="Filter by status: open, acknowledged, resolved, dismissed"),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Get all actionable issues across compliance, billing, purchase, patrimoine."""
    org_id = _get_org_id(request, auth)
    from services.action_center_service import get_action_center_issues

    return get_action_center_issues(db, org_id, domain, severity, site_id, status)


@router.get("/summary")
def action_center_summary(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Quick summary: count of issues by domain and severity."""
    org_id = _get_org_id(request, auth)
    from services.action_center_service import get_action_center_issues

    result = get_action_center_issues(db, org_id)
    return {
        "total": result["total"],
        "domains": result["domains"],
        "severities": result["severities"],
        "critical_count": result["severities"].get("critical", 0),
        "high_count": result["severities"].get("high", 0),
    }
