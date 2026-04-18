"""
PROMEOS — Sol V1 routes (Phase 4)

Endpoints principaux du cycle agentique :
- POST  /api/sol/propose     — Engine dry_run → ActionPlan | PlanRefused
- POST  /api/sol/preview     — retourne ActionPlan (avec token HMAC préview→confirm)
- POST  /api/sol/confirm     — validate + schedule en attente (grace period)
- POST  /api/sol/cancel      — annule via cancellation_token (one-click, pas de JWT)
- GET   /api/sol/pending     — liste pending actions pour org courante
- POST  /api/sol/ask         — Mode 2 conversation (stub 501, Sprint 7-8)
- POST  /api/sol/headline    — voice layer ambient (stub 501, Sprint 7-8)

Pattern PROMEOS (aligné actions.py, copilot.py) :
- `Depends(get_optional_auth)` pour AuthContext
- `resolve_org_id(request, auth, db)` appelé dans body (pas Depends — signature incompatible)
- Pydantic `response_model` obligatoire sur chaque route
- Gestion erreur standardisée HTTPException avec code/message_fr/correlation_id
- Logs structurés via `logging.getLogger("promeos.sol")`
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models.sol import SolConfirmationToken, SolPendingAction
from services.scope_utils import resolve_org_id
from sol.context import build_sol_context
from sol.planner import propose_plan
from sol.scheduler import (
    PendingActionNotCancellable,
    PendingActionNotFound,
    cancel_pending_action,
    schedule_pending_action,
)
from sol.schemas import ActionPlan, IntentKind, PlanRefused
from sol.utils import generate_confirmation_token, now_utc
from sol.validator import (
    ConfidenceTooLow,
    DryRunBlocked,
    DualValidationMissing,
    InvalidToken,
    PlanAltered,
    SolValidationError,
    _plan_hash,
    validate_plan_for_execution,
)

router = APIRouter(prefix="/api/sol", tags=["Sol V1 agentic"])
logger = logging.getLogger("promeos.sol")


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────────────────────


class ProposeRequest(BaseModel):
    """Body de POST /api/sol/propose."""

    intent: IntentKind
    params: dict[str, Any] = Field(default_factory=dict)
    scope_site_id: Optional[int] = None


class ProposeResponse(BaseModel):
    """Retour propose : ActionPlan ou PlanRefused (discriminant type)."""

    type: Literal["plan", "refused"]
    plan: Optional[ActionPlan] = None
    refused: Optional[PlanRefused] = None


class PreviewRequest(BaseModel):
    """Body de POST /api/sol/preview — re-émet plan + token HMAC."""

    correlation_id: str = Field(..., min_length=36, max_length=36)
    intent: IntentKind
    params: dict[str, Any] = Field(default_factory=dict)


class PreviewResponse(BaseModel):
    plan: ActionPlan
    confirmation_token: str
    expires_at: datetime


class ConfirmRequest(BaseModel):
    correlation_id: str = Field(..., min_length=36, max_length=36)
    confirmation_token: str = Field(..., min_length=16)
    intent: IntentKind
    params: dict[str, Any] = Field(default_factory=dict)
    second_validator_user_id: Optional[int] = None


class ConfirmResponse(BaseModel):
    pending_action_id: int
    correlation_id: str
    scheduled_for: datetime
    cancellation_token: str


class CancelRequest(BaseModel):
    cancellation_token: str = Field(..., min_length=16)


class CancelResponse(BaseModel):
    correlation_id: str
    cancelled_at: datetime


class PendingActionDTO(BaseModel):
    """DTO exposé pour GET /api/sol/pending (pas de plan_json full, trop lourd)."""

    id: int
    correlation_id: str
    intent_kind: str
    status: str
    scheduled_for: datetime
    created_at: datetime


class PendingListResponse(BaseModel):
    total: int
    items: list[PendingActionDTO]


# Stubs Sprint 7-8
class AskRequest(BaseModel):
    question_fr: str = Field(..., min_length=1, max_length=500)


class HeadlineRequest(BaseModel):
    template_key: str
    context: dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


_CONFIRMATION_TOKEN_TTL = timedelta(minutes=5)


def _log_route(event: str, **extra: Any) -> None:
    """Log structuré JSON cohérent avec le reste du repo."""
    logger.info(event, extra={"sol_event": event, **extra})


def _error_dict(code: str, message_fr: str, correlation_id: str | None, hint_fr: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message_fr": message_fr,
        "correlation_id": correlation_id,
        "hint_fr": hint_fr,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sol/propose
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/propose", response_model=ProposeResponse, status_code=201)
async def propose(
    body: ProposeRequest,
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
) -> ProposeResponse:
    """
    Dispatch intent → engine.dry_run (déterministe, 0 effet de bord).
    Retourne ActionPlan (succès) ou PlanRefused (L5 refus explicite).
    Log audit phase=proposed ou phase=refused.
    """
    # resolve_org_id lève HTTPException 401/403 si pas résoluble
    resolve_org_id(request, auth, db)  # validation scope
    ctx = build_sol_context(request, auth, db, scope_site_id=body.scope_site_id)

    result = propose_plan(db, ctx, body.intent, body.params)

    _log_route(
        "sol_propose",
        correlation_id=ctx.correlation_id,
        org_id=ctx.org_id,
        intent=body.intent.value,
        outcome="plan" if isinstance(result, ActionPlan) else "refused",
    )

    if isinstance(result, ActionPlan):
        return ProposeResponse(type="plan", plan=result)
    return ProposeResponse(type="refused", refused=result)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sol/preview
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/preview", response_model=PreviewResponse)
async def preview(
    body: PreviewRequest,
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
) -> PreviewResponse:
    """
    Re-dispatch l'engine pour reproduire le plan (idempotent si params
    identiques). Émet un SolConfirmationToken HMAC TTL 5 min.
    """
    resolve_org_id(request, auth, db)
    ctx = build_sol_context(request, auth, db, correlation_id=body.correlation_id)

    result = propose_plan(db, ctx, body.intent, body.params)
    if not isinstance(result, ActionPlan):
        raise HTTPException(
            status_code=409,
            detail=_error_dict(
                code=result.reason_code,
                message_fr=result.reason_fr,
                correlation_id=ctx.correlation_id,
                hint_fr=result.remediation_fr,
            ),
        )

    plan_hash = _plan_hash(result)
    token = generate_confirmation_token(result.correlation_id, plan_hash, ctx.user_id)
    expires_at = now_utc() + _CONFIRMATION_TOKEN_TTL

    db.add(
        SolConfirmationToken(
            token=token,
            correlation_id=result.correlation_id,
            plan_hash=plan_hash,
            user_id=ctx.user_id,
            org_id=ctx.org_id,
            expires_at=expires_at,
        )
    )
    db.commit()

    _log_route(
        "sol_preview",
        correlation_id=ctx.correlation_id,
        org_id=ctx.org_id,
        intent=body.intent.value,
    )

    return PreviewResponse(plan=result, confirmation_token=token, expires_at=expires_at)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sol/confirm
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/confirm", response_model=ConfirmResponse, status_code=202)
async def confirm(
    body: ConfirmRequest,
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
) -> ConfirmResponse:
    """
    Valide token HMAC + plan + confidence + dry-run + dual validation
    puis schedule l'action (grace period L2).
    """
    resolve_org_id(request, auth, db)
    ctx = build_sol_context(request, auth, db, correlation_id=body.correlation_id)

    # Re-compute plan deterministically pour validate_plan_for_execution
    result = propose_plan(db, ctx, body.intent, body.params)
    if not isinstance(result, ActionPlan):
        raise HTTPException(
            status_code=409,
            detail=_error_dict(
                code=result.reason_code,
                message_fr=result.reason_fr,
                correlation_id=ctx.correlation_id,
            ),
        )

    try:
        validate_plan_for_execution(
            db,
            ctx,
            result,
            body.confirmation_token,
            second_validator_user_id=body.second_validator_user_id,
        )
    except SolValidationError as exc:
        # Mapping exception → HTTP status : 401 token, 409 plan altéré / dry-run / confidence, 428 dual validation
        status_map: dict[type, int] = {
            InvalidToken: 401,
            PlanAltered: 409,
            ConfidenceTooLow: 409,
            DryRunBlocked: 409,
            DualValidationMissing: 428,
        }
        http_status = status_map.get(type(exc), 400)
        raise HTTPException(
            status_code=http_status,
            detail=_error_dict(
                code=exc.reason_code,
                message_fr=str(exc),
                correlation_id=ctx.correlation_id,
            ),
        ) from exc

    pending = schedule_pending_action(db, ctx, result, body.confirmation_token)

    _log_route(
        "sol_confirm",
        correlation_id=ctx.correlation_id,
        org_id=ctx.org_id,
        pending_action_id=pending.id,
    )

    return ConfirmResponse(
        pending_action_id=pending.id,
        correlation_id=pending.correlation_id,
        scheduled_for=pending.scheduled_for,
        cancellation_token=pending.cancellation_token,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sol/cancel  (sans JWT, auth par cancellation_token)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/cancel", response_model=CancelResponse)
async def cancel(
    body: CancelRequest,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
) -> CancelResponse:
    """
    Annule une action pending via cancellation_token URL-safe.

    Accepté SANS JWT (lien one-click depuis email). Si auth présent,
    on utilise user_id pour traçabilité — sinon cancelled_by=None.
    """
    user_id = getattr(auth, "user_id", None) if auth else None
    try:
        pending = cancel_pending_action(db, body.cancellation_token, user_id=user_id)
    except PendingActionNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=_error_dict(
                code="pending_not_found",
                message_fr="Cette action n'existe pas ou le lien d'annulation est invalide.",
                correlation_id=None,
            ),
        ) from exc
    except PendingActionNotCancellable as exc:
        raise HTTPException(
            status_code=409,
            detail=_error_dict(
                code="pending_not_cancellable",
                message_fr=(
                    "Cette action est déjà exécutée ou annulée — trop tard pour l'annuler."
                ),
                correlation_id=None,
            ),
        ) from exc

    _log_route(
        "sol_cancel",
        correlation_id=pending.correlation_id,
        org_id=pending.org_id,
    )

    return CancelResponse(
        correlation_id=pending.correlation_id,
        cancelled_at=pending.cancelled_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/sol/pending
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/pending", response_model=PendingListResponse)
async def list_pending(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
) -> PendingListResponse:
    """Liste des actions pending pour l'org courante, org-scoped strict."""
    org_id = resolve_org_id(request, auth, db)

    q = db.query(SolPendingAction).filter(SolPendingAction.org_id == org_id)
    if status:
        q = q.filter(SolPendingAction.status == status)
    rows = q.order_by(SolPendingAction.scheduled_for.asc()).all()

    items = [
        PendingActionDTO(
            id=r.id,
            correlation_id=r.correlation_id,
            intent_kind=r.intent_kind,
            status=r.status,
            scheduled_for=r.scheduled_for if r.scheduled_for.tzinfo else r.scheduled_for.replace(tzinfo=timezone.utc),
            created_at=r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc),
        )
        for r in rows
    ]
    return PendingListResponse(total=len(items), items=items)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sol/ask  (stub Sprint 7-8)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/ask", status_code=501)
async def ask_stub(
    body: AskRequest,  # noqa: ARG001
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Stub — Mode 2 conversation Sol. Implémenté Sprint 7-8 (LLM sandboxing)."""
    resolve_org_id(request, auth, db)  # valide scope même pour le stub
    raise HTTPException(
        status_code=501,
        detail=_error_dict(
            code="not_implemented_yet",
            message_fr="Le mode conversation Sol arrive prochainement.",
            correlation_id=None,
            hint_fr="Essayez /api/sol/propose avec un intent explicite.",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sol/headline  (stub Sprint 7-8)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/headline", status_code=501)
async def headline_stub(
    body: HeadlineRequest,  # noqa: ARG001
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Stub — voice layer ambient. Implémenté Sprint 7-8 (LLM EXPLAIN role)."""
    resolve_org_id(request, auth, db)
    raise HTTPException(
        status_code=501,
        detail=_error_dict(
            code="not_implemented_yet",
            message_fr="Le voice layer ambient arrive prochainement.",
            correlation_id=None,
        ),
    )
