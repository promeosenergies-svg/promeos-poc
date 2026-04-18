"""
Schemas Pydantic Sol V1.

Types de l'API Sol : IntentKind, ActionPhase, ActionPlan, PlanRefused,
ExecutionResult, SolContext, Source, Warning.

Décisions appliquées :
- Pydantic v2 (confirmé par `requirements.lock.txt`, 2.12.5 installé)
- IntentKind inclut `DUMMY_NOOP` exclusif tests (DÉCISION P1-12)
- ActionPhase : 8 valeurs (proposed → previewed → confirmed → scheduled
  → executed | cancelled | reverted | refused)
- Validations strictes : confidence ∈ [0, 1], grace_period ≥ 0,
  summary/title non vides, longueurs bornées
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────


class IntentKind(str, Enum):
    """
    Les 5 intents V1 + 2 spéciaux.

    Production intents (Sprint 3-6, 1 sprint / engine) :
    - INVOICE_DISPUTE : contestation facture fournisseur
    - EXEC_REPORT : rapport exécutif mensuel (PDF)
    - DT_ACTION_PLAN : plan d'action Décret Tertiaire
    - AO_BUILDER : appel d'offres fournisseurs énergie
    - OPERAT_BUILDER : déclaration OPERAT (CSV v3.2)

    Spéciaux :
    - CONSULTATIVE_ONLY : Sol répond sans agir (Mode 2 conversation)
    - DUMMY_NOOP : engine de test (tests/sol/ uniquement, Sprint 1-2)
    """

    INVOICE_DISPUTE = "invoice_dispute"
    EXEC_REPORT = "exec_report"
    DT_ACTION_PLAN = "dt_action_plan"
    AO_BUILDER = "ao_builder"
    OPERAT_BUILDER = "operat_builder"
    CONSULTATIVE_ONLY = "consultative_only"
    DUMMY_NOOP = "dummy_noop"


class ActionPhase(str, Enum):
    """Cycle de vie d'une action agentique Sol."""

    PROPOSED = "proposed"
    PREVIEWED = "previewed"
    CONFIRMED = "confirmed"
    SCHEDULED = "scheduled"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    REVERTED = "reverted"
    REFUSED = "refused"


class AgenticMode(str, Enum):
    """Mode agentique par organisation (SolOrgPolicy.agentic_mode)."""

    CONSULTATIVE_ONLY = "consultative_only"
    PREVIEW_ONLY = "preview_only"
    FULL_AGENTIC = "full_agentic"
    FULL_AGENTIC_WITH_DUAL_VALIDATION = "full_agentic_with_dual_validation"


# ─────────────────────────────────────────────────────────────────────────────
# Sources & Warnings (sous-structures réutilisées)
# ─────────────────────────────────────────────────────────────────────────────


class Source(BaseModel):
    """Source de données citée dans un ActionPlan (traçabilité L4)."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., min_length=1, max_length=64)  # ex: "facture", "enedis", "shadow_billing"
    ref: str = Field(..., min_length=1, max_length=200)
    freshness_hours: float | None = Field(None, ge=0)
    confidence: float | None = Field(None, ge=0, le=1)


class Warning(BaseModel):  # noqa: A001 — masque builtin intentionnellement (scope Sol)
    """Zone d'incertitude signalée dans un ActionPlan."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=64)
    message_fr: str = Field(..., min_length=1, max_length=500)


# ─────────────────────────────────────────────────────────────────────────────
# ActionPlan — sortie de engine.dry_run() succès
# ─────────────────────────────────────────────────────────────────────────────


class ActionPlan(BaseModel):
    """
    Plan d'une action agentique prête à être prévisualisée + confirmée.

    Émise par `engine.dry_run(ctx, params)` quand le calcul est
    suffisamment confiant (confidence ≥ org_policy.confidence_threshold).
    """

    model_config = ConfigDict(extra="forbid")

    correlation_id: str = Field(..., min_length=36, max_length=36)
    intent: IntentKind
    title_fr: str = Field(..., min_length=5, max_length=120)
    summary_fr: str = Field(..., min_length=10, max_length=500)
    preview_payload: dict[str, Any] = Field(default_factory=dict)
    inputs_hash: str = Field(..., min_length=64, max_length=64)
    confidence: float = Field(..., ge=0, le=1)
    grace_period_seconds: int = Field(..., ge=0)
    reversible: bool
    requires_dual_validation: bool = False
    estimated_value_eur: float | None = Field(None)
    estimated_time_saved_minutes: int | None = Field(None, ge=0)
    sources: list[Source] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)

    @field_validator("inputs_hash")
    @classmethod
    def _validate_hash_hex(cls, v: str) -> str:
        if not all(c in "0123456789abcdef" for c in v):
            raise ValueError("inputs_hash must be lowercase hex SHA256 (64 chars)")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# PlanRefused — sortie de engine.dry_run() quand refus explicite (L5)
# ─────────────────────────────────────────────────────────────────────────────


class PlanRefused(BaseModel):
    """
    Refus explicite émis par un engine : données manquantes, confiance
    insuffisante, hors scope org, etc.

    Porte toujours une `reason_fr` humaine affichable dans l'UI Sol.
    """

    model_config = ConfigDict(extra="forbid")

    correlation_id: str = Field(..., min_length=36, max_length=36)
    intent: IntentKind
    reason_code: str = Field(..., min_length=1, max_length=64)
    reason_fr: str = Field(..., min_length=10, max_length=500)
    remediation_fr: str | None = Field(None, max_length=500)
    missing_data: list[str] | None = None


# ─────────────────────────────────────────────────────────────────────────────
# ExecutionResult — sortie de engine.execute()
# ─────────────────────────────────────────────────────────────────────────────


class ExecutionResult(BaseModel):
    """Résultat de l'exécution réelle d'un plan confirmé."""

    model_config = ConfigDict(extra="forbid")

    correlation_id: str = Field(..., min_length=36, max_length=36)
    outcome_code: str = Field(..., min_length=1, max_length=64)
    outcome_message_fr: str = Field(..., min_length=1, max_length=500)
    state_before: dict[str, Any] = Field(default_factory=dict)
    state_after: dict[str, Any] = Field(default_factory=dict)
    reversal_instructions: dict[str, Any] | None = None


# ─────────────────────────────────────────────────────────────────────────────
# SolContext — contexte d'exécution d'une action (org-scopé)
# ─────────────────────────────────────────────────────────────────────────────


class SolContextData(BaseModel):
    """
    Contexte d'une action Sol. Org-scopé strict, traçable via correlation_id.

    Construit par `backend.sol.context.build_sol_context(request, auth, db)`
    depuis la request FastAPI. Sérialisable pour logs structurés.
    """

    model_config = ConfigDict(extra="forbid")

    org_id: int
    user_id: int
    correlation_id: str = Field(..., min_length=36, max_length=36)
    now: datetime
    org_policy: dict[str, Any] = Field(default_factory=dict)
    scope_site_id: int | None = None
    last_3_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=3)


__all__ = [
    "IntentKind",
    "ActionPhase",
    "AgenticMode",
    "Source",
    "Warning",
    "ActionPlan",
    "PlanRefused",
    "ExecutionResult",
    "SolContextData",
]
