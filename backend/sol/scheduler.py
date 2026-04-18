"""
Scheduler Sol V1 — file d'attente d'exécution différée (grace period L2).

Réutilise le pattern JobOutbox existant (DÉCISION P1-2 : pas d'APScheduler).

Flux :
1. `schedule_pending_action(db, ctx, plan, confirmation_token)` :
   consomme token, crée SolPendingAction, enqueue JobOutbox,
   log phase=SCHEDULED.
2. Worker `jobs.worker.process_one` picks up le job — dispatcher Sol
   (worker modifié Phase 3.7) appelle `execute_due_sol_action`.
3. `execute_due_sol_action(db, correlation_id)` :
   lookup SolPendingAction, reconstruit ctx, appelle engine.execute,
   log phase=EXECUTED, met status=executed.
4. `cancel_pending_action(db, cancellation_token, user_id=None)` :
   marque status=cancelled. Le worker skip au moment de la dispatch
   s'il trouve status != 'waiting'.

Annulation one-click sans JWT : le cancellation_token URL-safe suffit
(lookup DB unique, pas d'HMAC — la sécurité vient du secret du token
envoyé par email au seul utilisateur concerné).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import JobType
from models.sol import SolConfirmationToken, SolPendingAction

from .audit import log_action
from .engines.base import get_engine
from .schemas import ActionPhase, ActionPlan, ExecutionResult, IntentKind, SolContextData
from .utils import generate_cancellation_token, now_utc


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions métier
# ─────────────────────────────────────────────────────────────────────────────


class PendingActionNotFound(Exception):
    """cancellation_token ou correlation_id introuvable."""


class PendingActionNotCancellable(Exception):
    """Pending action n'est plus au statut waiting (déjà exécuté ou annulé)."""


# ─────────────────────────────────────────────────────────────────────────────
# schedule_pending_action — orchestration après /confirm
# ─────────────────────────────────────────────────────────────────────────────


def schedule_pending_action(
    db: Session,
    ctx: SolContextData,
    plan: ActionPlan,
    confirmation_token: str,
) -> SolPendingAction:
    """
    Programme l'exécution d'un plan confirmé (grace period L2).

    Pré-conditions :
    - Le plan a déjà été validé via `validate_plan_for_execution` (token
      HMAC OK, plan non altéré, pas dry-run, confiance OK, dual validation OK)
    - SolConfirmationToken row exists (lookup par `confirmation_token`)

    Flux :
    1. Marque SolConfirmationToken.consumed=True + consumed_at=now
    2. Crée SolPendingAction status='waiting', scheduled_for=now+grace
    3. Enqueue JobOutbox type SOL_EXECUTE_PENDING_ACTION avec payload
       {correlation_id, scheduled_for_iso}
    4. Log append-only phase=SCHEDULED (via audit)

    Retourne la SolPendingAction créée.
    """
    # 1. Consume token
    token_row = (
        db.query(SolConfirmationToken)
        .filter(SolConfirmationToken.token == confirmation_token)
        .one_or_none()
    )
    if token_row is None:
        raise PendingActionNotFound(f"Confirmation token not found: {confirmation_token[:16]}...")

    token_row.consumed = True
    token_row.consumed_at = now_utc()

    # 2. Create SolPendingAction
    scheduled_for = now_utc() + timedelta(seconds=plan.grace_period_seconds)
    cancellation_token = generate_cancellation_token()
    pending = SolPendingAction(
        correlation_id=plan.correlation_id,
        org_id=ctx.org_id,
        user_id=ctx.user_id,
        intent_kind=plan.intent.value,
        plan_json=plan.model_dump(mode="json"),
        scheduled_for=scheduled_for,
        cancellation_token=cancellation_token,
        status="waiting",
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)

    # 3. Enqueue JobOutbox
    from jobs.worker import enqueue_job
    enqueue_job(
        db,
        JobType.SOL_EXECUTE_PENDING_ACTION,
        {
            "correlation_id": plan.correlation_id,
            "scheduled_for_iso": scheduled_for.isoformat(),
        },
        priority=3,
    )

    # 4. Audit log
    log_action(db, ctx, ActionPhase.SCHEDULED, plan_or_refusal=plan)

    # TODO Sprint 3+: envoyer email notif avec cancellation_token + deadline

    return pending


# ─────────────────────────────────────────────────────────────────────────────
# cancel_pending_action — one-click email, pas d'auth
# ─────────────────────────────────────────────────────────────────────────────


def cancel_pending_action(
    db: Session,
    cancellation_token: str,
    user_id: int | None = None,
) -> SolPendingAction:
    """
    Annule une pending action avant exécution.

    Accepté SANS JWT — le cancellation_token URL-safe est secret par
    construction (envoyé par email au seul utilisateur concerné).

    Le worker JobOutbox qui picke plus tard verra status='cancelled' et
    skippera l'exécution (execute_due_sol_action early-return).

    Args:
        cancellation_token: URL-safe token reçu par email.
        user_id: optionnel, user qui a cliqué (pour audit trail).

    Raises:
        PendingActionNotFound si token inconnu.
        PendingActionNotCancellable si status != 'waiting'.
    """
    pending = (
        db.query(SolPendingAction)
        .filter(SolPendingAction.cancellation_token == cancellation_token)
        .one_or_none()
    )
    if pending is None:
        raise PendingActionNotFound(f"Cancellation token not found: {cancellation_token[:16]}...")
    if pending.status != "waiting":
        raise PendingActionNotCancellable(
            f"SolPendingAction status='{pending.status}' — cannot cancel."
        )

    pending.status = "cancelled"
    pending.cancelled_at = now_utc()
    pending.cancelled_by = user_id
    db.commit()

    # Log cancel — on reconstruit un ctx minimal depuis pending
    minimal_ctx = SolContextData(
        org_id=pending.org_id,
        user_id=user_id or pending.user_id,
        correlation_id=pending.correlation_id,
        now=now_utc(),
    )
    log_action(
        db,
        minimal_ctx,
        ActionPhase.CANCELLED,
        outcome={
            "outcome_code": "cancelled_by_user",
            "outcome_message_fr": (
                "Annulation enregistrée. Rien n'a été envoyé. "
                "Vous pouvez reprendre plus tard."
            ),
        },
    )
    return pending


# ─────────────────────────────────────────────────────────────────────────────
# execute_due_sol_action — appelé par worker.process_one Phase 3.7
# ─────────────────────────────────────────────────────────────────────────────


def execute_due_sol_action(
    db: Session,
    correlation_id: str,
) -> ExecutionResult | None:
    """
    Exécute une action Sol schedulée dont le grace period est écoulé.

    Appelée par le worker (backend/jobs/worker.py) quand il picke un
    JobOutbox type=SOL_EXECUTE_PENDING_ACTION.

    Logique :
    1. Lookup SolPendingAction par correlation_id
    2. Si status != 'waiting' (cancelled, already executed) → None, skip
    3. Si now < scheduled_for → None, le worker doit re-queue
    4. Marquer status='executing'
    5. Reconstruire ctx minimal + plan depuis pending.plan_json
    6. Dispatcher vers engine.execute(ctx, plan, ...)
    7. Marquer status='executed' + executed_at
    8. Log phase=EXECUTED via audit

    Returns:
        ExecutionResult si exécuté, None si skip (cancelled / pas encore due).
    """
    pending = (
        db.query(SolPendingAction)
        .filter(SolPendingAction.correlation_id == correlation_id)
        .one_or_none()
    )
    if pending is None:
        raise PendingActionNotFound(f"No pending action for correlation_id {correlation_id}")

    if pending.status != "waiting":
        return None  # cancelled / already executed → worker marks DONE

    scheduled_for = pending.scheduled_for
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
    if now_utc() < scheduled_for:
        return None  # pas encore due, worker doit re-queue

    # Mark executing
    pending.status = "executing"
    db.commit()

    try:
        intent = IntentKind(pending.intent_kind)
        engine = get_engine(intent)

        # Reconstruct plan from stored plan_json
        plan = ActionPlan(**pending.plan_json)

        # Reconstruct minimal ctx for engine execution
        ctx = SolContextData(
            org_id=pending.org_id,
            user_id=pending.user_id,
            correlation_id=pending.correlation_id,
            now=now_utc(),
        )

        # Engine execute — peut lever, on catche pour status=failed
        result = engine.execute(ctx, plan, confirmation_token="consumed-by-scheduler")

        # Mark executed + log audit
        pending.status = "executed"
        pending.executed_at = now_utc()
        db.commit()

        log_action(db, ctx, ActionPhase.EXECUTED, plan_or_refusal=plan, outcome=result)
        return result

    except Exception as e:  # noqa: BLE001
        # Rollback status → waiting (worker réessaiera) OU marquer failed définitif ?
        # Pour Phase 3 : on marque failed, worker marque DONE (pas de retry auto)
        pending.status = "failed"
        db.commit()
        # Log d'audit "failed" même si exception
        ctx = SolContextData(
            org_id=pending.org_id,
            user_id=pending.user_id,
            correlation_id=pending.correlation_id,
            now=now_utc(),
        )
        log_action(
            db,
            ctx,
            ActionPhase.EXECUTED,
            plan_or_refusal=None,
            outcome={
                "outcome_code": "execution_failed",
                "outcome_message_fr": (
                    f"L'exécution a échoué. L'action n'est pas partie. "
                    f"Erreur technique : {type(e).__name__}"
                ),
            },
        )
        raise


__all__ = [
    "schedule_pending_action",
    "cancel_pending_action",
    "execute_due_sol_action",
    "PendingActionNotFound",
    "PendingActionNotCancellable",
]
