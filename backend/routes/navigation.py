"""PROMEOS — Navigation badges endpoint.

GET /api/v1/navigation/badges → NavBadgesResponse (8 compteurs + metadata).

Phase 2.A — P1.2 (audit navigation_audit_20260501.md §3.3 + §5).
Source de vérité unique pour le rail/panel FE — remplace 3 fetches
dispersés (Sidebar.jsx getNotificationsSummary + getMonitoringAlerts +
AppShell.jsx getActionCenter*Summary). Consommation FE = P1.2.bis.

Convention auth/org alignée sur backend/routes/action_center.py:21
(get_optional_auth + helper local _get_org_id, fallback X-Org-Id header
puis 1 pour DEMO_MODE).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from schemas.navigation import NavBadgesResponse
from services.navigation_badges_service import compute_navigation_badges

router = APIRouter(prefix="/api/v1/navigation", tags=["navigation"])


def _get_org_id(request: Request, auth: Optional[AuthContext]) -> int:
    """Resolve org_id — convention partagée avec action_center.py:21.

    Priorité : header X-Org-Id (intégrations / tests) > AuthContext.org_id
    (auth réelle) > fallback 1 (DEMO_MODE sans auth).
    """
    org_header = request.headers.get("X-Org-Id")
    if org_header:
        try:
            return int(org_header)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Org-Id header (must be an integer)",
            )
    if auth and auth.org_id:
        return auth.org_id
    return 1


@router.get("/badges", response_model=NavBadgesResponse)
def get_navigation_badges(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
) -> NavBadgesResponse:
    """Compteurs agrégés navigation rail/panel pour l'org courante.

    Returns NavBadgesResponse — 5 counters (int) + 3 progress (float
    0-100) + 2 metadata (computed_at, cache_ttl_seconds).
    """
    org_id = _get_org_id(request, auth)
    return compute_navigation_badges(db, org_id)
