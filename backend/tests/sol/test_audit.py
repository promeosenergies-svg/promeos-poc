"""Tests audit Sol V1 — log_action, get_audit_trail, check_audit_integrity."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

import sol.engines  # noqa: F401
from models.sol import SolActionLog
from sol.audit import check_audit_integrity, get_audit_trail, log_action
from sol.schemas import (
    ActionPhase,
    ActionPlan,
    ExecutionResult,
    IntentKind,
    PlanRefused,
    SolContextData,
    Source,
)


def _ctx(sol_org, sol_user, correlation_id="12345678-aaaa-bbbb-cccc-000000000000"):
    return SolContextData(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id=correlation_id,
        now=datetime.now(timezone.utc),
    )


def _fake_plan(ctx):
    return ActionPlan(
        correlation_id=ctx.correlation_id,
        intent=IntentKind.DUMMY_NOOP,
        title_fr="Test audit log",
        summary_fr="Plan factice pour tests audit.",
        preview_payload={"dummy": True},
        inputs_hash="a" * 64,
        confidence=0.94,
        grace_period_seconds=60,
        reversible=True,
        sources=[Source(kind="test", ref="unit-test", freshness_hours=0)],
    )


def test_log_action_proposed_creates_row(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan = _fake_plan(ctx)
    log = log_action(sol_db, ctx, ActionPhase.PROPOSED, plan_or_refusal=plan)

    assert log.id is not None
    assert log.action_phase == "proposed"
    assert log.intent_kind == "dummy_noop"
    assert log.plan_json["title_fr"] == "Test audit log"
    assert log.confidence is not None
    assert float(log.confidence) == 0.94


def test_log_action_refused_sets_outcome_message(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    refused = PlanRefused(
        correlation_id=ctx.correlation_id,
        intent=IntentKind.INVOICE_DISPUTE,
        reason_code="missing_data",
        reason_fr="Surface déclarative du bâtiment Marseille non renseignée.",
    )
    log = log_action(sol_db, ctx, ActionPhase.REFUSED, plan_or_refusal=refused)

    assert log.action_phase == "refused"
    assert log.outcome_code == "missing_data"
    assert log.outcome_message == "Surface déclarative du bâtiment Marseille non renseignée."


def test_log_action_executed_with_result(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan = _fake_plan(ctx)
    result = ExecutionResult(
        correlation_id=ctx.correlation_id,
        outcome_code="success",
        outcome_message_fr="Courrier envoyé à edf@pro.",
        state_before={"x": 1},
        state_after={"x": 2},
    )
    log = log_action(sol_db, ctx, ActionPhase.EXECUTED, plan_or_refusal=plan, outcome=result)

    assert log.state_before == {"x": 1}
    assert log.state_after == {"x": 2}
    assert log.outcome_code == "success"


def test_log_action_cancelled_with_dict_outcome(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    log = log_action(
        sol_db,
        ctx,
        ActionPhase.CANCELLED,
        outcome={"outcome_code": "user_cancel", "outcome_message_fr": "Annulation utilisateur."},
    )

    assert log.action_phase == "cancelled"
    assert log.outcome_code == "user_cancel"


def test_get_audit_trail_chain_phases(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user, correlation_id="cha1111a-aaaa-bbbb-cccc-000000000000")
    plan = _fake_plan(ctx)
    log_action(sol_db, ctx, ActionPhase.PROPOSED, plan_or_refusal=plan)
    log_action(sol_db, ctx, ActionPhase.SCHEDULED, plan_or_refusal=plan)
    log_action(sol_db, ctx, ActionPhase.EXECUTED, plan_or_refusal=plan)

    trail = get_audit_trail(sol_db, ctx.org_id, ctx.correlation_id)
    phases = [lg.action_phase for lg in trail]
    assert phases == ["proposed", "scheduled", "executed"]


def test_get_audit_trail_org_scoped(sol_db, sol_org, sol_user):
    """get_audit_trail ne doit pas leak cross-tenant."""
    ctx = _ctx(sol_org, sol_user, correlation_id="sha0000d-aaaa-bbbb-cccc-000000000000")
    plan = _fake_plan(ctx)
    log_action(sol_db, ctx, ActionPhase.PROPOSED, plan_or_refusal=plan)

    # Crée une autre org avec même correlation_id (accidentel)
    from models.organisation import Organisation
    other_org = Organisation(nom="Foreign Audit Org", actif=True)
    sol_db.add(other_org)
    sol_db.commit()

    foreign_ctx = SolContextData(
        org_id=other_org.id,
        user_id=sol_user.id,
        correlation_id=ctx.correlation_id,  # même correlation_id
        now=datetime.now(timezone.utc),
    )
    log_action(sol_db, foreign_ctx, ActionPhase.PROPOSED, plan_or_refusal=plan)

    # Audit trail pour org A ne doit contenir que l'entrée de A
    trail_a = get_audit_trail(sol_db, sol_org.id, ctx.correlation_id)
    assert len(trail_a) == 1
    assert trail_a[0].org_id == sol_org.id

    trail_b = get_audit_trail(sol_db, other_org.id, ctx.correlation_id)
    assert len(trail_b) == 1
    assert trail_b[0].org_id == other_org.id


def test_check_audit_integrity_empty_db_returns_empty(sol_db):
    incidents = check_audit_integrity(sol_db)
    assert incidents == []


def test_check_audit_integrity_clean_after_log(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan = _fake_plan(ctx)
    log_action(sol_db, ctx, ActionPhase.PROPOSED, plan_or_refusal=plan)

    incidents = check_audit_integrity(sol_db, org_id=sol_org.id)
    assert incidents == []
