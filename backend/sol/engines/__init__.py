"""
Sol V1 engines — moteurs déterministes par intent.

Chaque engine = module Python isolé implémentant SolEngine ABC :
- dry_run(ctx, params) → ActionPlan | PlanRefused (pas d'effets de bord)
- execute(ctx, plan, confirmation_token) → ExecutionResult
- revert(ctx, log_entry, reason) → ExecutionResult (si REVERSIBLE=True)

Registry dynamique `ENGINE_REGISTRY` : mapping IntentKind → SolEngine instance,
peuplé via `register_engine(engine)` à l'import du module engine.

Phase 3 (Sprint 1-2) : seulement `_dummy.py` (DummyEngine.KIND = DUMMY_NOOP)
pour valider le cycle propose → schedule → execute sans engine métier.

Phase 3-6 à venir : invoice_dispute.py, exec_report.py, dt_action_plan.py,
ao_builder.py, operat_builder.py (1 sprint par engine).
"""

# Import déclenche l'auto-registration des engines via register_engine()
from . import _dummy  # noqa: F401 — side-effect register
