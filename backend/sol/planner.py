"""
Planner Sol V1 — dispatcher engine par intent + gouvernance org policy.

Entry point : `propose_plan(db, ctx, intent, params)`.

Responsabilités :
1. Vérifier org_policy.agentic_mode — si consultative_only et intent ≠
   CONSULTATIVE_ONLY / DUMMY_NOOP → PlanRefused.
2. Dispatcher vers engine.dry_run(ctx, params).
3. Logger append-only : phase=PROPOSED pour ActionPlan, phase=REFUSED
   pour PlanRefused.
4. Retourner résultat au caller.

Déterministe : 0 LLM, 0 effet de bord (sauf log audit INSERT).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .audit import log_action
from .engines.base import EngineNotFoundError, get_engine
from .schemas import ActionPhase, ActionPlan, IntentKind, PlanRefused, SolContextData


def propose_plan(
    db: Session,
    ctx: SolContextData,
    intent: IntentKind,
    params: Any = None,
) -> ActionPlan | PlanRefused:
    """
    Propose un plan pour un intent donné, scoped à ctx.org_id.

    Flux :
    1. Check org_policy.agentic_mode (consultative_only bloque non-consultative)
    2. Get engine by intent (EngineNotFoundError → PlanRefused 'unknown_intent')
    3. Engine.dry_run(ctx, params) → ActionPlan | PlanRefused
    4. Log append-only phase=PROPOSED ou phase=REFUSED
    5. Return

    Args:
        db: SQLAlchemy Session (pour log audit).
        ctx: SolContextData org-scopé (construit via build_sol_context).
        intent: IntentKind demandé.
        params: dict de paramètres spécifiques à l'engine (facture_id, etc.).

    Returns:
        ActionPlan (succès) ou PlanRefused (échec cadré avec reason_fr).
    """
    agentic_mode = ctx.org_policy.get("agentic_mode", "preview_only")
    non_agentic_intents = {IntentKind.CONSULTATIVE_ONLY, IntentKind.DUMMY_NOOP}
    if agentic_mode == "consultative_only" and intent not in non_agentic_intents:
        refused = PlanRefused(
            correlation_id=ctx.correlation_id,
            intent=intent,
            reason_code="agentic_disabled",
            reason_fr=(
                "Votre organisation a activé le mode consultatif. "
                "Je prépare les dossiers mais je ne les envoie pas — "
                "vous gardez toujours la main sur l'exécution."
            ),
        )
        # commit=True : log_action standalone dans propose_plan, caller
        # FastAPI route n'a pas forcément un commit englobant.
        log_action(db, ctx, ActionPhase.REFUSED, plan_or_refusal=refused, commit=True)
        return refused

    # Dispatch vers engine
    try:
        engine = get_engine(intent)
    except EngineNotFoundError:
        refused = PlanRefused(
            correlation_id=ctx.correlation_id,
            intent=intent,
            reason_code="unknown_intent",
            reason_fr=(
                f"L'intention {intent.value} n'a pas d'engine disponible en V1. "
                f"Essayez une action prise en charge : contestation facture, "
                f"rapport exécutif, plan DT, appel d'offres, ou déclaration OPERAT."
            ),
        )
        log_action(db, ctx, ActionPhase.REFUSED, plan_or_refusal=refused, commit=True)
        return refused

    # Appel engine.dry_run déterministe
    result = engine.dry_run(ctx, params)

    if isinstance(result, ActionPlan):
        log_action(db, ctx, ActionPhase.PROPOSED, plan_or_refusal=result, commit=True)
    else:
        log_action(db, ctx, ActionPhase.REFUSED, plan_or_refusal=result, commit=True)

    return result


__all__ = ["propose_plan"]
