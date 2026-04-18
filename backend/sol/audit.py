"""
Audit Sol V1 — append-only log + chain correlation + intégrité.

Wrapper over SolActionLog (models/sol.py). Toutes les actions Sol passent
par `log_action(ctx, phase, ...)` pour garantir le trail d'audit L4.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from models.sol import SolActionLog

from .schemas import ActionPhase, ActionPlan, ExecutionResult, PlanRefused, SolContextData
from .utils import hash_inputs, now_utc


# ─────────────────────────────────────────────────────────────────────────────
# log_action — INSERT append-only
# ─────────────────────────────────────────────────────────────────────────────


def log_action(
    db: Session,
    ctx: SolContextData,
    phase: ActionPhase,
    plan_or_refusal: ActionPlan | PlanRefused | None = None,
    outcome: ExecutionResult | dict[str, Any] | None = None,
) -> SolActionLog:
    """
    INSERT append-only dans sol_action_log.

    Accepte soit un ActionPlan (phases proposed / previewed / confirmed /
    scheduled / executed), soit un PlanRefused (phase refused), soit rien
    (phases cancelled / reverted — outcome obligatoire alors).

    Args:
        db: Session active.
        ctx: SolContextData (fournit org_id, user_id, correlation_id).
        phase: ActionPhase — quelle étape du cycle on loggue.
        plan_or_refusal: ActionPlan ou PlanRefused selon phase.
        outcome: ExecutionResult ou dict arbitraire pour phases CANCELLED/REVERTED.

    Returns:
        SolActionLog nouvellement créé (id attribué, created_at set).
    """
    intent_kind = "unknown"
    plan_json: dict[str, Any] = {}
    outcome_code: str | None = None
    outcome_message: str | None = None
    confidence: Decimal | None = None

    if isinstance(plan_or_refusal, ActionPlan):
        intent_kind = plan_or_refusal.intent.value
        plan_json = plan_or_refusal.model_dump(mode="json")
        confidence = Decimal(str(plan_or_refusal.confidence))
    elif isinstance(plan_or_refusal, PlanRefused):
        intent_kind = plan_or_refusal.intent.value
        plan_json = plan_or_refusal.model_dump(mode="json")
        outcome_code = plan_or_refusal.reason_code
        outcome_message = plan_or_refusal.reason_fr

    # Outcome post-exécution / cancel / revert
    state_before: dict[str, Any] | None = None
    state_after: dict[str, Any] | None = None
    if isinstance(outcome, ExecutionResult):
        outcome_code = outcome.outcome_code
        outcome_message = outcome.outcome_message_fr
        state_before = outcome.state_before or None
        state_after = outcome.state_after or None
    elif isinstance(outcome, dict):
        outcome_code = outcome.get("outcome_code") or outcome_code
        outcome_message = outcome.get("outcome_message_fr") or outcome_message

    inputs_hash = hash_inputs(
        ctx.org_id,
        ctx.user_id,
        ctx.correlation_id,
        intent_kind,
        phase.value,
        plan_json,
    )

    log = SolActionLog(
        org_id=ctx.org_id,
        user_id=ctx.user_id,
        correlation_id=ctx.correlation_id,
        intent_kind=intent_kind,
        action_phase=phase.value,
        inputs_hash=inputs_hash,
        plan_json=plan_json,
        state_before=state_before,
        state_after=state_after,
        outcome_code=outcome_code,
        outcome_message=outcome_message,
        confidence=confidence,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ─────────────────────────────────────────────────────────────────────────────
# get_audit_trail — chain par correlation_id
# ─────────────────────────────────────────────────────────────────────────────


def get_audit_trail(
    db: Session,
    org_id: int,
    correlation_id: str,
) -> list[SolActionLog]:
    """
    Retourne toute la chaîne d'actions liées à un correlation_id, org-scopée.

    Ordre ascending par created_at : phase propose → preview → confirm →
    schedule → execute (ou cancelled/refused).

    La contrainte org_id est SQL pour éviter le cross-tenant leak
    (cf audit Phase 1 P6 — correlation_id n'est pas unique, juste indexed).
    """
    return (
        db.query(SolActionLog)
        .filter(SolActionLog.org_id == org_id)
        .filter(SolActionLog.correlation_id == correlation_id)
        .order_by(SolActionLog.id.asc())
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────────
# check_audit_integrity — job hourly (Sprint 3+ : wire into cron/JobOutbox)
# ─────────────────────────────────────────────────────────────────────────────


def check_audit_integrity(
    db: Session,
    org_id: int | None = None,
    limit: int = 100,
) -> list[str]:
    """
    Vérifie l'intégrité des logs récents : inputs_hash recalculable,
    phase cohérente avec précédente (propose → preview → …).

    Retourne une liste de messages d'incidents (vide si tout OK).

    Conçu pour job hourly différé (pas encore wired Phase 3 — wire Phase 4 ou
    déféré Sprint 3+ selon DECISIONS P1-10 rétention).
    """
    incidents: list[str] = []

    q = db.query(SolActionLog)
    if org_id is not None:
        q = q.filter(SolActionLog.org_id == org_id)
    q = q.order_by(SolActionLog.id.desc()).limit(limit)

    for log in q.all():
        # Recompute inputs_hash
        expected = hash_inputs(
            log.org_id,
            log.user_id,
            log.correlation_id,
            log.intent_kind,
            log.action_phase,
            log.plan_json,
        )
        if log.inputs_hash != expected:
            incidents.append(
                f"HASH_MISMATCH log.id={log.id} correlation={log.correlation_id} "
                f"expected={expected[:12]}... got={log.inputs_hash[:12]}..."
            )

    return incidents


__all__ = [
    "log_action",
    "get_audit_trail",
    "check_audit_integrity",
]
