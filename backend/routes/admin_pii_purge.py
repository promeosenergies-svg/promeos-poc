"""M2-6.A.2 — Endpoint admin purge PII RGPD article 17.

POST /api/admin/users/{user_id}/purge

Sensible : opération irréversible (cascade delete + hard-clear PII). Réservée
aux platform admins (DG_OWNER / DSI_ADMIN) via `require_platform_admin` STRICT
qui ne bypass PAS en DEMO_MODE (contrairement à `require_permission("admin")`
classique). C'est volontaire : une démo ne doit JAMAIS pouvoir effacer du PII.

Body :
  - `reason` (str, min_length=10, max_length=500) — justification métier
  - `dry_run` (bool, default False) — si True, simule sans modifier la DB

Codes d'erreur :
  - 401 token manquant (require_platform_admin)
  - 403 rôle insuffisant (require_platform_admin)
  - 404 USER_NOT_FOUND user inexistant
  - 409 USER_ALREADY_PURGED idempotency
  - 422 PROTECTED_DEMO_USER email .demo whitelisté (Q5=B)
  - 422 reason length validation (Pydantic)
  - 500 PURGE_INTERNAL_ERROR cascade error (rollback effectué)
"""

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import require_platform_admin
from services.v4.pii_purge import PIIPurgeError, purge_user

router = APIRouter(prefix="/api/admin", tags=["Admin PII Purge"])


class PurgeRequest(BaseModel):
    """Body POST /api/admin/users/{user_id}/purge."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Justification métier (demande RGPD art. 17, audit, etc.)",
    )
    dry_run: bool = Field(
        default=False,
        description="Si True, simule la purge sans modifier la DB (preview report)",
    )


class PurgeResponse(BaseModel):
    """Réponse 200 — PurgeReport sérialisé."""

    user_pii_cleared: bool
    user_org_roles_deleted: int
    event_logs_anonymized: int
    action_items_owner_anonymized: int
    purge_log_id: int | None
    dry_run: bool


@router.post(
    "/users/{user_id}/purge",
    response_model=PurgeResponse,
    summary="Purge PII RGPD article 17",
    status_code=200,
)
def purge_user_endpoint(
    user_id: int,
    payload: PurgeRequest = Body(...),
    db: Session = Depends(get_db),
    admin_payload=Depends(require_platform_admin),
):
    """Purge PII du `user_id`. Réservé platform admins (DG_OWNER / DSI_ADMIN).

    L'admin auteur est extrait du JWT (`sub`). CNIL article 30 traceability
    via `purge_log` (hash SHA256, jamais user_id en clair).
    """
    # `admin_payload["sub"]` est l'id INT legacy du JWT (cf. middleware.auth).
    admin_id_raw = (admin_payload or {}).get("sub")
    try:
        admin_id = int(admin_id_raw) if admin_id_raw is not None else 0
    except (TypeError, ValueError):
        # JWT mal formé — sécurité défensive (require_platform_admin a déjà
        # validé le token, on ne devrait pas arriver ici en pratique).
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_ADMIN_SUB", "message": "JWT sub invalide."},
        )

    try:
        report = purge_user(
            db=db,
            user_id=user_id,
            purged_by_admin_id=admin_id,
            reason=payload.reason,
            dry_run=payload.dry_run,
        )
        return PurgeResponse(
            user_pii_cleared=report.user_pii_cleared,
            user_org_roles_deleted=report.user_org_roles_deleted,
            event_logs_anonymized=report.event_logs_anonymized,
            action_items_owner_anonymized=report.action_items_owner_anonymized,
            purge_log_id=report.purge_log_id,
            dry_run=report.dry_run,
        )
    except PIIPurgeError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"code": e.code, "message": e.message},
        )
