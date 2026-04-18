"""
Scheduler Sol V1 — file d'attente d'exécution différée (grace period L2).

Réutilise le pattern JobOutbox existant (DÉCISION P1-2 : pas d'APScheduler).

Flux :
1. `schedule_pending_action(db, ctx, plan, confirmation_token)` :
   consomme token, crée SolPendingAction, insère JobOutbox, log SCHEDULED
   — TOUT EN UNE TRANSACTION (atomic).
2. Worker `jobs.worker.process_one` picks up le job — dispatcher Sol
   (worker modifié Phase 3.7) appelle `execute_due_sol_action`.
3. `execute_due_sol_action(db, correlation_id)` :
   lookup SolPendingAction, reconstruit ctx, appelle engine.execute,
   log EXECUTED puis commit une fois. Wrapping try/except pour marquer
   'failed' avec audit sur exception.
4. `cancel_pending_action(db, cancellation_token, user_id=None)` :
   marque status='cancelled' + log CANCELLED. Le worker skippe au
   moment de la dispatch s'il trouve status != 'waiting'.

Annulation one-click sans JWT : le cancellation_token URL-safe suffit
(lookup DB unique, pas d'HMAC — la sécurité vient du secret du token
envoyé par email au seul utilisateur concerné).

Audit Phase 3 (post-merge) : 3 corrections P0 appliquées :
- P0-2 : schedule_pending_action atomic (une seule tx)
- P0-3 : log_action utilise flush (pattern cx_logger), caller commit
- P0-4 : execute_due_sol_action log avant commit final, try/except ciblé
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import JobOutbox, JobStatus, JobType
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
# schedule_pending_action — atomic transaction (P0-2 fix)
# ─────────────────────────────────────────────────────────────────────────────


def schedule_pending_action(
    db: Session,
    ctx: SolContextData,
    plan: ActionPlan,
    confirmation_token: str,
) -> SolPendingAction:
    """
    Programme l'exécution d'un plan confirmé — atomique en une seule tx.

    Pré-conditions :
    - Plan déjà validé via `validate_plan_for_execution` (HMAC OK, plan non
      altéré, pas dry-run, confiance OK, dual validation OK).
    - SolConfirmationToken row exists (lookup par `confirmation_token`).

    Flow atomique (une seule db.commit() à la fin) :
    1. Consume token (consumed=True + consumed_at)
    2. Create SolPendingAction status='waiting'
    3. Insert JobOutbox (pas via enqueue_job qui commit seul — on veut
       atomicity, donc création manuelle inline)
    4. log_action(phase=SCHEDULED, commit=False) → flush
    5. db.commit() une fois

    Si n'importe quelle étape échoue, rollback automatique par SQLAlchemy
    → zéro état partiel (token non consommé, pending non créé, job non
    enfilé, audit log non écrit). C'est l'invariant critique L4 audit.
    """
    token_row = (
        db.query(SolConfirmationToken)
        .filter(SolConfirmationToken.token == confirmation_token)
        .one_or_none()
    )
    if token_row is None:
        raise PendingActionNotFound(f"Confirmation token not found: {confirmation_token[:16]}...")

    # 1. Consume token (in-session, pas encore commit)
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

    # 3. Create JobOutbox inline (pas via enqueue_job qui commit seul —
    #    on veut atomicity avec le reste de la transaction).
    job = JobOutbox(
        job_type=JobType.SOL_EXECUTE_PENDING_ACTION,
        payload_json=json.dumps(
            {
                "correlation_id": plan.correlation_id,
                "scheduled_for_iso": scheduled_for.isoformat(),
            }
        ),
        priority=3,
        status=JobStatus.PENDING,
        created_at=now_utc(),
    )
    db.add(job)

    # 4. Audit log (flush only)
    log_action(db, ctx, ActionPhase.SCHEDULED, plan_or_refusal=plan, commit=False)

    # 5. One commit for all
    db.commit()
    db.refresh(pending)

    # TODO Sprint 3+ : email notif avec cancellation_token + deadline
    return pending


# ─────────────────────────────────────────────────────────────────────────────
# cancel_pending_action — atomic, une tx
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

    Atomic : update status + audit log + commit en une tx.

    Le worker JobOutbox qui picke plus tard verra status='cancelled' et
    skippera l'exécution (execute_due_sol_action early-return None).
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

    # Log (flush only) puis commit atomique
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
        commit=False,
    )
    db.commit()
    return pending


# ─────────────────────────────────────────────────────────────────────────────
# execute_due_sol_action — appelé par worker.process_one
# ─────────────────────────────────────────────────────────────────────────────


def execute_due_sol_action(
    db: Session,
    correlation_id: str,
) -> ExecutionResult | None:
    """
    Exécute une action Sol schedulée dont le grace period est écoulé.

    Appelée par le worker (backend/jobs/worker.py) quand il picke un
    JobOutbox type=SOL_EXECUTE_PENDING_ACTION.

    Logique (P0-4 fix : log avant commit final) :
    1. Lookup SolPendingAction par correlation_id
    2. Si status != 'waiting' (cancelled, already executed) → None
    3. Si now < scheduled_for → None (worker peut re-queue)
    4. Marquer status='executing' + commit (observable par autres workers)
    5. Appel engine.execute(ctx, plan, ...) — peut lever
    6. Sur succès : log_action EXECUTED (flush) + mark status='executed'
       + executed_at + commit une fois
    7. Sur exception : catch + mark status='failed' + log EXECUTED avec
       outcome="execution_failed" + commit + reraise

    Returns:
        ExecutionResult si exécuté, None si skip (cancelled / pas encore due).

    Risque connu (documented P1-3 audit) : crash entre étape 4 et 5 →
    status='executing' zombie. Mitigation : Sprint 3+ reaper périodique
    qui rebascule 'executing' > N min vers 'failed'.
    """
    pending = (
        db.query(SolPendingAction)
        .filter(SolPendingAction.correlation_id == correlation_id)
        .one_or_none()
    )
    if pending is None:
        raise PendingActionNotFound(f"No pending action for correlation_id {correlation_id}")

    if pending.status != "waiting":
        return None  # cancelled / already executed

    scheduled_for = pending.scheduled_for
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
    if now_utc() < scheduled_for:
        return None  # pas encore due, worker peut re-queue

    # Mark executing (observable)
    pending.status = "executing"
    db.commit()

    intent = IntentKind(pending.intent_kind)
    engine = get_engine(intent)
    plan = ActionPlan(**pending.plan_json)
    ctx = SolContextData(
        org_id=pending.org_id,
        user_id=pending.user_id,
        correlation_id=pending.correlation_id,
        now=now_utc(),
    )

    try:
        result = engine.execute(ctx, plan, confirmation_token="consumed-by-scheduler")
    except Exception as e:  # noqa: BLE001
        # Mark failed + audit log "execution_failed" + commit + reraise
        pending.status = "failed"
        log_action(
            db,
            ctx,
            ActionPhase.EXECUTED,
            plan_or_refusal=plan,
            outcome={
                "outcome_code": "execution_failed",
                "outcome_message_fr": (
                    f"L'exécution a échoué. L'action n'est pas partie. "
                    f"Erreur technique : {type(e).__name__}"
                ),
            },
            commit=False,
        )
        db.commit()
        raise

    # Success path : log + mark executed atomic
    pending.status = "executed"
    pending.executed_at = now_utc()
    log_action(db, ctx, ActionPhase.EXECUTED, plan_or_refusal=plan, outcome=result, commit=False)
    db.commit()
    return result


__all__ = [
    "schedule_pending_action",
    "cancel_pending_action",
    "execute_due_sol_action",
    "PendingActionNotFound",
    "PendingActionNotCancellable",
]
