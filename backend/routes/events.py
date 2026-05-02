"""Route REST /api/v1/events/* — Phase 1.A + 2.A Sprint α.

Phase 1.A (Sprint α-fin) — `GET /api/v1/events/upcoming` : expose
`compute_events` (event_bus) à des consommateurs Tier3 (mobile, email
digest, intégrations 3rd party) via la couche query d'adaptation
(`services/events_query_service.py`).

Phase 2.A (Sprint α-push) — `POST /api/v1/events/refresh` : endpoint
admin déclenché par cron GitHub Actions à 7h45 Paris pour rafraîchir
les events de toutes les orgs actives. Auth strict
(`require_platform_admin`, pas de bypass DEMO_MODE).

Les handlers sont strictement délégateurs — aucune logique métier
inline, toute la transformation est dans la couche query.

Réf : docs/adr/ADR-002-chantier-alpha-moteur-evenements.md (§endpoint),
docs/audits/sprint_alpha_phase0_audit_20260502.md (Voie C arbitrée),
docs/audits/sprint_alpha_push_phase0_audit_20260502.md (Q3+Q4 arbitrées).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth, require_platform_admin
from schemas.events import EventCardSchema, EventUpcomingResponse
from services.events_query_service import (
    DEFAULT_HORIZON_DAYS,
    DEFAULT_LIMIT,
    get_upcoming_events,
    refresh_all_active_orgs,
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


@router.post("/refresh", status_code=200)
def refresh_events_endpoint(
    request: Request,
    _admin: dict = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Recalcule les events pour toutes les orgs actives.

    Endpoint admin appelé par cron GitHub Actions à 7h45 Paris
    (`.github/workflows/digest-daily.yml`). Auth strict via
    `require_platform_admin` — pas de bypass DEMO_MODE (Q4 audit
    Phase 0.bis arbitrée).

    Délégation pure à `events_query_service.refresh_all_active_orgs` —
    aucune logique métier dans ce handler.

    Idempotent : `compute_events` est stateless. Appels répétés sans
    effet de bord cumulatif. Erreurs par org sont capturées (continue
    sur les suivantes) et retournées dans `errors`.

    Returns
    -------
    dict
        Voir `events_query_service.refresh_all_active_orgs` —
        `{refreshed_orgs, total_events, errors, computed_at}`.
    """
    return refresh_all_active_orgs(db)
