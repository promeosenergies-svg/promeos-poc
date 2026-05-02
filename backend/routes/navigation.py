"""PROMEOS — Navigation badges endpoint.

GET /api/v1/navigation/badges → NavBadgesResponse (8 compteurs + metadata).

Phase 2.A — P1.2 (audit navigation_audit_20260501.md §3.3 + §5).
Source de vérité unique pour le rail/panel FE — remplace 3 fetches
dispersés (Sidebar.jsx getNotificationsSummary + getMonitoringAlerts +
AppShell.jsx getActionCenter*Summary). Consommation FE = P1.2.bis.

Auth/org : passe par scope_utils.resolve_org_id (SoT canonique CLAUDE.md
règle 2) — gère DEMO_MODE, fallback DemoState, et lève 401 quand
DEMO_MODE=false sans auth.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from schemas.navigation import NavBadgesResponse
from services.navigation_badges_service import compute_navigation_badges
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/v1/navigation", tags=["navigation"])


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
    org_id = resolve_org_id(request, auth, db)
    return compute_navigation_badges(db, org_id)
