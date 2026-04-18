"""Tests planner Sol V1 — dispatch + org_policy enforcement + audit log."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import sol.engines  # noqa: F401 — register DummyEngine
from models.sol import SolActionLog
from sol.planner import propose_plan
from sol.schemas import ActionPlan, IntentKind, PlanRefused, SolContextData


def _make_ctx(sol_org, sol_user, policy_override=None):
    policy = {
        "agentic_mode": "preview_only",
        "confidence_threshold": 0.85,
        "grace_period_seconds": 900,
        "tone_preference": "vous",
    }
    if policy_override:
        policy.update(policy_override)
    return SolContextData(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id="12345678-1234-1234-1234-123456789012",
        now=datetime.now(timezone.utc),
        org_policy=policy,
    )


def test_propose_dummy_success_logs_proposed(sol_db, sol_org, sol_user):
    ctx = _make_ctx(sol_org, sol_user)
    result = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})

    assert isinstance(result, ActionPlan)
    assert result.intent == IntentKind.DUMMY_NOOP

    logs = sol_db.query(SolActionLog).filter_by(correlation_id=ctx.correlation_id).all()
    assert len(logs) == 1
    assert logs[0].action_phase == "proposed"


def test_propose_dummy_refuse_logs_refused(sol_db, sol_org, sol_user):
    ctx = _make_ctx(sol_org, sol_user)
    result = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"should_refuse": True})

    assert isinstance(result, PlanRefused)
    assert result.reason_code == "confidence_low"

    logs = sol_db.query(SolActionLog).filter_by(correlation_id=ctx.correlation_id).all()
    assert len(logs) == 1
    assert logs[0].action_phase == "refused"


def test_propose_unknown_intent_refuses(sol_db, sol_org, sol_user):
    ctx = _make_ctx(sol_org, sol_user)
    # INVOICE_DISPUTE n'a pas d'engine en Phase 3
    result = propose_plan(sol_db, ctx, IntentKind.INVOICE_DISPUTE, params={})

    assert isinstance(result, PlanRefused)
    assert result.reason_code == "unknown_intent"


def test_propose_consultative_only_mode_blocks_non_consultative(sol_db, sol_org, sol_user):
    ctx = _make_ctx(sol_org, sol_user, policy_override={"agentic_mode": "consultative_only"})
    # DUMMY_NOOP est toléré comme CONSULTATIVE_ONLY — on teste avec INVOICE_DISPUTE
    result = propose_plan(sol_db, ctx, IntentKind.INVOICE_DISPUTE, params={})

    assert isinstance(result, PlanRefused)
    # Note : peut être agentic_disabled OU unknown_intent selon ordre checks.
    # Le planner check agentic mode AVANT engine lookup → agentic_disabled attendu
    assert result.reason_code == "agentic_disabled"


def test_propose_consultative_only_allows_dummy_noop(sol_db, sol_org, sol_user):
    ctx = _make_ctx(sol_org, sol_user, policy_override={"agentic_mode": "consultative_only"})
    result = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={})

    assert isinstance(result, ActionPlan)
    assert result.intent == IntentKind.DUMMY_NOOP


def test_propose_logs_org_scoped(sol_db, sol_org, sol_user):
    """Le log porte bien org_id du ctx."""
    ctx = _make_ctx(sol_org, sol_user)
    propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={})

    logs = sol_db.query(SolActionLog).filter_by(org_id=sol_org.id).all()
    assert len(logs) >= 1
    assert logs[0].user_id == sol_user.id
