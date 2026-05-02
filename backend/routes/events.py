"""Route REST /api/v1/events/* — Phase 1.A Sprint α-fin.

Expose `compute_events` (event_bus) à des consommateurs Tier3 (mobile,
email digest, intégrations 3rd party) via une couche query d'adaptation
(`services/events_query_service.py`).

Le handler est strictement délégateur — aucune logique métier inline,
toute la transformation est dans la couche query.

Réf : docs/adr/ADR-002-chantier-alpha-moteur-evenements.md (§endpoint),
docs/audits/sprint_alpha_phase0_audit_20260502.md (Voie C arbitrée).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from schemas.events import EventCardSchema, EventUpcomingResponse
from services.events_query_service import (
    DEFAULT_HORIZON_DAYS,
    DEFAULT_LIMIT,
    get_upcoming_events,
)
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/upcoming", response_model=EventUpcomingResponse)
def get_upcoming_events_endpoint(
    request: Request,
    persona: Optional[str] = None,
    page_key: Optional[str] = None,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    cursor: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
) -> EventUpcomingResponse:
    """Retourne la page courante des événements en attente, scope org.

    Délégation pure à `events_query_service.get_upcoming_events` —
    aucune logique métier dans ce handler.
    """
    org_id = resolve_org_id(request, auth, db)
    result = get_upcoming_events(
        db=db,
        org_id=org_id,
        persona=persona,
        page_key=page_key,
        horizon_days=horizon_days,
        cursor=cursor,
        limit=limit,
    )
    return EventUpcomingResponse(
        events=[EventCardSchema.from_sol_event_card(e) for e in result["events"]],
        next_cursor=result["next_cursor"],
        total=result["total"],
        computed_at=datetime.now(timezone.utc),
    )
