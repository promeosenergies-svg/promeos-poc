"""Route REST /api/v1/digest/dispatch — Phase 2.D Sprint α-push.

Endpoint admin déclenché par GitHub Actions cron (job `dispatch-digest`
dépendant de `refresh-events`). Auth strict `require_platform_admin`
(cohérent Phase 2.A — pas de bypass DEMO_MODE).

Délégation pure à `digest_service.dispatch_daily_digest`.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import require_platform_admin
from schemas.digest import DigestRunSummary, DispatchRequest
from services.digest_service import dispatch_daily_digest

router = APIRouter(prefix="/api/v1/digest", tags=["digest"])


@router.post("/dispatch", response_model=DigestRunSummary, status_code=200)
def dispatch_digest_endpoint(
    body: DispatchRequest = Body(default=DispatchRequest()),
    _admin: dict = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> DigestRunSummary:
    """Déclenche le dispatch digest matinal.

    Auth strict via `require_platform_admin` (cohérent /events/refresh
    Phase 2.A). Délégation pure à `digest_service.dispatch_daily_digest`
    — aucune logique métier dans ce handler.
    """
    summary = dispatch_daily_digest(
        db,
        dry_run=body.dry_run,
        user_filter=body.user_filter,
    )
    return DigestRunSummary(
        sent=summary.sent,
        skipped_no_opt_in=summary.skipped_no_opt_in,
        skipped_no_events=summary.skipped_no_events,
        failed=summary.failed,
        dry_run=summary.dry_run,
        correlation_id=summary.correlation_id,
    )
