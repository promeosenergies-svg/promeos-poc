"""Tests schemas Pydantic Sol V1 — IntentKind, ActionPhase, ActionPlan, PlanRefused, ExecutionResult."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sol.schemas import (
    ActionPhase,
    ActionPlan,
    AgenticMode,
    ExecutionResult,
    IntentKind,
    PlanRefused,
    SolContextData,
    Source,
    Warning,
)


def _valid_plan_kwargs():
    return dict(
        correlation_id="12345678-1234-1234-1234-123456789012",
        intent=IntentKind.INVOICE_DISPUTE,
        title_fr="Contester la facture Lyon",
        summary_fr="Récupération estimée 1 847 euros HT.",
        preview_payload={},
        inputs_hash="a" * 64,
        confidence=0.94,
        grace_period_seconds=86400,
        reversible=True,
    )


def test_intent_kind_has_dummy_noop():
    assert IntentKind.DUMMY_NOOP.value == "dummy_noop"


def test_intent_kind_has_5_production_intents():
    prod = {
        IntentKind.INVOICE_DISPUTE,
        IntentKind.EXEC_REPORT,
        IntentKind.DT_ACTION_PLAN,
        IntentKind.AO_BUILDER,
        IntentKind.OPERAT_BUILDER,
    }
    assert all(i in IntentKind for i in prod)


def test_action_phase_has_8_values():
    expected = {"proposed", "previewed", "confirmed", "scheduled", "executed", "cancelled", "reverted", "refused"}
    assert {p.value for p in ActionPhase} == expected


def test_agentic_mode_has_4_values():
    expected = {"consultative_only", "preview_only", "full_agentic", "full_agentic_with_dual_validation"}
    assert {m.value for m in AgenticMode} == expected


def test_action_plan_valid():
    plan = ActionPlan(**_valid_plan_kwargs())
    assert plan.intent == IntentKind.INVOICE_DISPUTE
    assert plan.confidence == 0.94


def test_action_plan_confidence_bounds():
    with pytest.raises(ValidationError):
        ActionPlan(**{**_valid_plan_kwargs(), "confidence": 1.5})
    with pytest.raises(ValidationError):
        ActionPlan(**{**_valid_plan_kwargs(), "confidence": -0.1})


def test_action_plan_grace_period_non_negative():
    with pytest.raises(ValidationError):
        ActionPlan(**{**_valid_plan_kwargs(), "grace_period_seconds": -1})


def test_action_plan_inputs_hash_must_be_hex():
    with pytest.raises(ValidationError, match="hex SHA256"):
        ActionPlan(**{**_valid_plan_kwargs(), "inputs_hash": "Z" * 64})


def test_action_plan_inputs_hash_length():
    with pytest.raises(ValidationError):
        ActionPlan(**{**_valid_plan_kwargs(), "inputs_hash": "a" * 32})


def test_action_plan_title_length_bounds():
    # Trop court
    with pytest.raises(ValidationError):
        ActionPlan(**{**_valid_plan_kwargs(), "title_fr": "abc"})
    # Trop long (>120)
    with pytest.raises(ValidationError):
        ActionPlan(**{**_valid_plan_kwargs(), "title_fr": "a" * 121})


def test_action_plan_sources_typed():
    plan = ActionPlan(
        **_valid_plan_kwargs(),
        sources=[Source(kind="facture", ref="F-2026-03", freshness_hours=12)],
    )
    assert plan.sources[0].kind == "facture"


def test_action_plan_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ActionPlan(**_valid_plan_kwargs(), injected_field="forbidden")


def test_plan_refused_valid():
    pr = PlanRefused(
        correlation_id="12345678-1234-1234-1234-123456789012",
        intent=IntentKind.INVOICE_DISPUTE,
        reason_code="confidence_low",
        reason_fr="La confiance du calcul est sous le seuil requis.",
    )
    assert pr.reason_code == "confidence_low"


def test_plan_refused_reason_fr_required():
    with pytest.raises(ValidationError):
        PlanRefused(
            correlation_id="12345678-1234-1234-1234-123456789012",
            intent=IntentKind.INVOICE_DISPUTE,
            reason_code="confidence_low",
            reason_fr="",
        )


def test_execution_result_valid():
    er = ExecutionResult(
        correlation_id="12345678-1234-1234-1234-123456789012",
        outcome_code="success",
        outcome_message_fr="Courrier envoyé.",
    )
    assert er.outcome_code == "success"
    assert er.state_before == {}


def test_source_confidence_bounds():
    with pytest.raises(ValidationError):
        Source(kind="x", ref="y", confidence=2.0)


def test_warning_shape():
    w = Warning(code="accent_missing", message_fr="Le champ manque.")
    assert w.code == "accent_missing"


def test_sol_context_data_valid():
    ctx = SolContextData(
        org_id=1,
        user_id=42,
        correlation_id="12345678-1234-1234-1234-123456789012",
        now=datetime.now(timezone.utc),
        org_policy={"confidence_threshold": 0.85},
    )
    assert ctx.org_id == 1


def test_sol_context_data_last_3_actions_cap():
    # max_length=3 enforced
    with pytest.raises(ValidationError):
        SolContextData(
            org_id=1,
            user_id=42,
            correlation_id="12345678-1234-1234-1234-123456789012",
            now=datetime.now(timezone.utc),
            last_3_actions=[{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}],
        )
