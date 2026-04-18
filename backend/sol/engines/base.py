"""
Contrat abstrait SolEngine + registry dynamique.

Chaque intent Sol V1 = 1 engine concret hérite SolEngine.
Enregistrement via `register_engine(engine)` à l'import du module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..schemas import ActionPlan, ExecutionResult, IntentKind, PlanRefused, SolContextData


class NotReversibleError(Exception):
    """Levée quand revert() appelé sur un engine non reversible."""


class EngineNotFoundError(KeyError):
    """Levée quand un intent n'a pas d'engine registré."""


class SolEngine(ABC):
    """
    Contrat abstrait pour tous les engines Sol V1.

    Attributs de classe (override dans chaque engine concret) :
    - KIND : IntentKind que cet engine traite
    - MIN_CONFIDENCE : seuil absolu minimum pour qu'un plan soit éligible
      exécution. Le seuil effectif est max(MIN_CONFIDENCE,
      ctx.org_policy.confidence_threshold).
    - GRACE_PERIOD_SECONDS : délai de grâce par défaut avant exécution
      (override possible dans dry_run via ActionPlan.grace_period_seconds).
    - REVERSIBLE : si True, revert() doit être implémenté.
    """

    KIND: IntentKind
    MIN_CONFIDENCE: float = 0.85
    GRACE_PERIOD_SECONDS: int = 900
    REVERSIBLE: bool = True

    @abstractmethod
    def dry_run(self, ctx: SolContextData, params: Any) -> ActionPlan | PlanRefused:
        """
        Génère un ActionPlan sans aucun effet de bord.

        Déterministe : mêmes inputs → même output. Appelable plusieurs fois
        pour idempotence des prévisualisations.

        Peut échouer avec PlanRefused :
        - reason_code='missing_data' si données insuffisantes
        - reason_code='confidence_low' si confiance < MIN_CONFIDENCE
        - reason_code='out_of_scope' si demande hors compétence engine
        """
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        ctx: SolContextData,
        plan: ActionPlan,
        confirmation_token: str,
    ) -> ExecutionResult:
        """
        Exécution réelle après validation + grace period.

        Transactionnelle + idempotente via correlation_id. Appelée par le
        worker JobOutbox quand scheduled_for <= now et pending_action
        status='waiting'.
        """
        raise NotImplementedError

    def revert(
        self,
        ctx: SolContextData,
        log_entry: Any,
        reason: str,
    ) -> ExecutionResult:
        """
        Revert d'une action exécutée (si REVERSIBLE=True).

        Default : NotReversibleError. Override dans l'engine concret si
        REVERSIBLE=True (ex: email rétractation pour invoice_dispute).
        """
        raise NotReversibleError(
            f"{self.KIND.value} engine is not reversible. Override revert() if needed."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Registry dynamique
# ─────────────────────────────────────────────────────────────────────────────


ENGINE_REGISTRY: dict[IntentKind, SolEngine] = {}


def register_engine(engine: SolEngine) -> None:
    """
    Enregistre un engine dans le registry global.

    Idempotent — si un engine du même KIND est déjà registré,
    on l'override (pratique pour les tests avec fake engines).

    Appelé au module-level depuis chaque engine :
        # backend/sol/engines/invoice_dispute.py
        register_engine(InvoiceDisputeEngine())
    """
    ENGINE_REGISTRY[engine.KIND] = engine


def get_engine(intent: IntentKind) -> SolEngine:
    """
    Lookup un engine par IntentKind. Lève EngineNotFoundError si absent.

    Utilisé par `planner.propose_plan(ctx, intent, params)`.
    """
    engine = ENGINE_REGISTRY.get(intent)
    if engine is None:
        raise EngineNotFoundError(
            f"No engine registered for intent {intent.value}. "
            f"Available : {[k.value for k in ENGINE_REGISTRY.keys()]}"
        )
    return engine


def clear_registry() -> None:
    """Vide le registry. Usage tests uniquement (fixture teardown)."""
    ENGINE_REGISTRY.clear()


__all__ = [
    "SolEngine",
    "ENGINE_REGISTRY",
    "register_engine",
    "get_engine",
    "clear_registry",
    "NotReversibleError",
    "EngineNotFoundError",
]
