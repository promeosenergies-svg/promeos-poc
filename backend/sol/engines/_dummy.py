"""
DummyEngine — engine de test Sol V1 Phase 3.

Implémentation minimale de SolEngine pour valider le cycle
propose → schedule → execute sans engine métier réel.

Kind : IntentKind.DUMMY_NOOP (exclusif tests, voir DECISIONS_LOG P1-12).

⚠️ NE PAS UTILISER EN PRODUCTION. Sprint 3-6 remplaceront par :
    invoice_dispute.py, exec_report.py, dt_action_plan.py, ao_builder.py,
    operat_builder.py.
"""

from __future__ import annotations

from typing import Any

from ..schemas import ActionPlan, ExecutionResult, IntentKind, PlanRefused, SolContextData, Source
from ..utils import hash_inputs
from .base import SolEngine, register_engine


class DummyEngine(SolEngine):
    """
    Engine de test sans effet de bord.

    Paramètres attendus dans `params` (dict) :
    - confidence : float — confiance à retourner dans le plan (default 0.94)
    - should_refuse : bool — si True, retourne PlanRefused (default False)
    - refuse_reason : str — reason_code pour PlanRefused (default 'confidence_low')

    Utilisé dans tests/sol/ pour valider planner / validator / scheduler.
    """

    KIND = IntentKind.DUMMY_NOOP
    MIN_CONFIDENCE = 0.85
    GRACE_PERIOD_SECONDS = 60  # grace court en tests (1 min)
    REVERSIBLE = True

    def dry_run(self, ctx: SolContextData, params: Any) -> ActionPlan | PlanRefused:
        params = params or {}
        should_refuse = bool(params.get("should_refuse", False))
        if should_refuse:
            return PlanRefused(
                correlation_id=ctx.correlation_id,
                intent=self.KIND,
                reason_code=params.get("refuse_reason", "confidence_low"),
                reason_fr="Test refuse déclenché volontairement par les paramètres dummy.",
            )

        confidence = float(params.get("confidence", 0.94))
        return ActionPlan(
            correlation_id=ctx.correlation_id,
            intent=self.KIND,
            title_fr="Action dummy — ne fait rien",
            summary_fr="Engine de test. Aucun effet de bord. Utilisé par tests/sol/ uniquement.",
            preview_payload={"dummy": True, "params": params},
            inputs_hash=hash_inputs(ctx.correlation_id, params),
            confidence=confidence,
            grace_period_seconds=self.GRACE_PERIOD_SECONDS,
            reversible=True,
            requires_dual_validation=False,
            sources=[Source(kind="test", ref="dummy-engine", freshness_hours=0)],
        )

    def execute(
        self,
        ctx: SolContextData,
        plan: ActionPlan,
        confirmation_token: str,  # noqa: ARG002 — API contract
    ) -> ExecutionResult:
        """Retourne un succès trivial, log state_before/after pour inspection."""
        return ExecutionResult(
            correlation_id=plan.correlation_id,
            outcome_code="dummy_success",
            outcome_message_fr="Action dummy exécutée (aucun effet réel).",
            state_before={"dummy_state": "before"},
            state_after={"dummy_state": "after", "executed_at_ctx_now": ctx.now.isoformat()},
        )

    def revert(
        self,
        ctx: SolContextData,
        log_entry: Any,  # noqa: ARG002
        reason: str,
    ) -> ExecutionResult:
        """Dummy revert : trivial, retourne un résultat de rollback fictif."""
        return ExecutionResult(
            correlation_id=getattr(log_entry, "correlation_id", ctx.correlation_id),
            outcome_code="dummy_reverted",
            outcome_message_fr=f"Action dummy révertée : {reason}",
            state_before={"dummy_state": "after"},
            state_after={"dummy_state": "before", "revert_reason": reason},
        )


# Auto-register au module import — side-effect intentionnel
register_engine(DummyEngine())


__all__ = ["DummyEngine"]
