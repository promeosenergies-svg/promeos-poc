"""Tests scheduler Sol V1 — schedule_pending + cancel + execute_due + cycle E2E."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

import sol.engines  # noqa: F401
from models import JobOutbox, JobStatus, JobType
from models.sol import SolActionLog, SolConfirmationToken, SolPendingAction
from sol.planner import propose_plan
from sol.scheduler import (
    PendingActionNotCancellable,
    PendingActionNotFound,
    cancel_pending_action,
    execute_due_sol_action,
    schedule_pending_action,
)
from sol.schemas import ActionPlan, IntentKind, SolContextData
from sol.utils import generate_confirmation_token
from sol.validator import _plan_hash


@pytest.fixture(autouse=True)
def _ensure_secret():
    os.environ.setdefault("SOL_SECRET_KEY", "test_key_scheduler_v1")


def _ctx(sol_org, sol_user, correlation_id="aaaaaaaa-1234-1234-1234-aaaaaaaaaaaa"):
    return SolContextData(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id=correlation_id,
        now=datetime.now(timezone.utc),
        org_policy={"confidence_threshold": 0.85, "grace_period_seconds": 60},
    )


def _propose_and_tokenize(sol_db, ctx) -> tuple[ActionPlan, str]:
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    assert isinstance(plan, ActionPlan)
    plan_hash = _plan_hash(plan)
    tok = generate_confirmation_token(plan.correlation_id, plan_hash, ctx.user_id)
    sol_db.add(
        SolConfirmationToken(
            token=tok,
            correlation_id=plan.correlation_id,
            plan_hash=plan_hash,
            user_id=ctx.user_id,
            org_id=ctx.org_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    sol_db.commit()
    return plan, tok


# ─────────────────────────────────────────────────────────────────────────────
# schedule_pending_action
# ─────────────────────────────────────────────────────────────────────────────


def test_schedule_creates_pending_and_job(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan, tok = _propose_and_tokenize(sol_db, ctx)

    pending = schedule_pending_action(sol_db, ctx, plan, tok)

    assert pending.status == "waiting"
    assert pending.correlation_id == plan.correlation_id
    assert pending.cancellation_token is not None
    # JobOutbox créé
    jobs = sol_db.query(JobOutbox).filter_by(job_type=JobType.SOL_EXECUTE_PENDING_ACTION).all()
    assert len(jobs) == 1
    # Token consumed
    tok_row = sol_db.query(SolConfirmationToken).filter_by(token=tok).one()
    assert tok_row.consumed is True
    # Audit log phase=scheduled
    logs = sol_db.query(SolActionLog).filter_by(
        correlation_id=plan.correlation_id, action_phase="scheduled"
    ).all()
    assert len(logs) == 1


def test_schedule_unknown_token_raises(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan, _ = _propose_and_tokenize(sol_db, ctx)

    with pytest.raises(PendingActionNotFound):
        schedule_pending_action(sol_db, ctx, plan, "ghost-token-nonexistent")


# ─────────────────────────────────────────────────────────────────────────────
# cancel_pending_action
# ─────────────────────────────────────────────────────────────────────────────


def test_cancel_pending_success(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan, tok = _propose_and_tokenize(sol_db, ctx)
    pending = schedule_pending_action(sol_db, ctx, plan, tok)

    cancelled = cancel_pending_action(sol_db, pending.cancellation_token, user_id=sol_user.id)

    assert cancelled.status == "cancelled"
    assert cancelled.cancelled_at is not None
    assert cancelled.cancelled_by == sol_user.id
    # Audit log phase=cancelled
    logs = sol_db.query(SolActionLog).filter_by(
        correlation_id=plan.correlation_id, action_phase="cancelled"
    ).all()
    assert len(logs) == 1


def test_cancel_unknown_token_raises(sol_db):
    with pytest.raises(PendingActionNotFound):
        cancel_pending_action(sol_db, "nonexistent-cancel-token")


def test_cancel_already_cancelled_raises(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan, tok = _propose_and_tokenize(sol_db, ctx)
    pending = schedule_pending_action(sol_db, ctx, plan, tok)
    cancel_pending_action(sol_db, pending.cancellation_token)

    with pytest.raises(PendingActionNotCancellable):
        cancel_pending_action(sol_db, pending.cancellation_token)


# ─────────────────────────────────────────────────────────────────────────────
# execute_due_sol_action
# ─────────────────────────────────────────────────────────────────────────────


def test_execute_due_before_scheduled_returns_none(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan, tok = _propose_and_tokenize(sol_db, ctx)
    pending = schedule_pending_action(sol_db, ctx, plan, tok)
    # scheduled_for = now + 60s → now < scheduled_for
    result = execute_due_sol_action(sol_db, plan.correlation_id)
    assert result is None
    sol_db.refresh(pending)
    assert pending.status == "waiting"


def test_execute_due_after_grace_runs_engine(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan, tok = _propose_and_tokenize(sol_db, ctx)
    pending = schedule_pending_action(sol_db, ctx, plan, tok)

    # Avancer le temps au-delà du grace period
    with freeze_time(datetime.now(timezone.utc) + timedelta(seconds=120)):
        result = execute_due_sol_action(sol_db, plan.correlation_id)

    assert result is not None
    assert result.outcome_code == "dummy_success"
    sol_db.refresh(pending)
    assert pending.status == "executed"
    assert pending.executed_at is not None
    # Audit log phase=executed
    logs = sol_db.query(SolActionLog).filter_by(
        correlation_id=plan.correlation_id, action_phase="executed"
    ).all()
    assert len(logs) == 1


def test_execute_due_skip_if_cancelled(sol_db, sol_org, sol_user):
    ctx = _ctx(sol_org, sol_user)
    plan, tok = _propose_and_tokenize(sol_db, ctx)
    pending = schedule_pending_action(sol_db, ctx, plan, tok)
    cancel_pending_action(sol_db, pending.cancellation_token)

    # Même après grace period, une action cancelled ne s'exécute pas
    with freeze_time(datetime.now(timezone.utc) + timedelta(seconds=120)):
        result = execute_due_sol_action(sol_db, plan.correlation_id)

    assert result is None
    sol_db.refresh(pending)
    assert pending.status == "cancelled"


def test_execute_due_unknown_correlation_raises(sol_db):
    with pytest.raises(PendingActionNotFound):
        execute_due_sol_action(sol_db, "nonexistent-correlation-id")


# ─────────────────────────────────────────────────────────────────────────────
# Cycle E2E propose → schedule → cancel
# ─────────────────────────────────────────────────────────────────────────────


def test_full_cycle_propose_schedule_cancel(sol_db, sol_org, sol_user):
    """Cycle complet : propose → schedule → cancel. Audit trail 3 phases."""
    ctx = _ctx(sol_org, sol_user, correlation_id="ca1e0e12-aaaa-bbbb-cccc-000000000001")
    plan, tok = _propose_and_tokenize(sol_db, ctx)
    pending = schedule_pending_action(sol_db, ctx, plan, tok)
    cancel_pending_action(sol_db, pending.cancellation_token, user_id=sol_user.id)

    # Audit trail doit contenir : proposed, scheduled, cancelled
    logs = (
        sol_db.query(SolActionLog)
        .filter_by(correlation_id=plan.correlation_id)
        .order_by(SolActionLog.id.asc())
        .all()
    )
    phases = [lg.action_phase for lg in logs]
    assert phases == ["proposed", "scheduled", "cancelled"]


def test_full_cycle_propose_schedule_execute(sol_db, sol_org, sol_user):
    """Cycle complet : propose → schedule → execute (freeze time)."""
    ctx = _ctx(sol_org, sol_user, correlation_id="e1e1e1e1-aaaa-bbbb-cccc-000000000002")
    plan, tok = _propose_and_tokenize(sol_db, ctx)
    schedule_pending_action(sol_db, ctx, plan, tok)

    with freeze_time(datetime.now(timezone.utc) + timedelta(seconds=120)):
        result = execute_due_sol_action(sol_db, plan.correlation_id)

    assert result.outcome_code == "dummy_success"
    logs = (
        sol_db.query(SolActionLog)
        .filter_by(correlation_id=plan.correlation_id)
        .order_by(SolActionLog.id.asc())
        .all()
    )
    phases = [lg.action_phase for lg in logs]
    assert phases == ["proposed", "scheduled", "executed"]


# ─────────────────────────────────────────────────────────────────────────────
# Tests P3 ajoutés post-audit : branches exception + edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_execute_due_engine_raises_marks_failed(sol_db, sol_org, sol_user, monkeypatch):
    """Engine.execute qui lève → pending.status='failed' + audit outcome_code='execution_failed'."""
    from sol.engines._dummy import DummyEngine

    def _boom(self, ctx, plan, confirmation_token):  # noqa: ARG001
        raise RuntimeError("engine crash simulé")

    monkeypatch.setattr(DummyEngine, "execute", _boom)

    ctx = _ctx(sol_org, sol_user, correlation_id="fa11fa11-aaaa-bbbb-cccc-000000000003")
    plan, tok = _propose_and_tokenize(sol_db, ctx)
    schedule_pending_action(sol_db, ctx, plan, tok)

    with freeze_time(datetime.now(timezone.utc) + timedelta(seconds=120)):
        with pytest.raises(RuntimeError, match="engine crash"):
            execute_due_sol_action(sol_db, plan.correlation_id)

    # Vérifier état final : status='failed' + audit log 'executed' avec outcome 'execution_failed'
    pending = sol_db.query(SolPendingAction).filter_by(correlation_id=plan.correlation_id).one()
    assert pending.status == "failed"

    failure_log = (
        sol_db.query(SolActionLog)
        .filter_by(correlation_id=plan.correlation_id, action_phase="executed")
        .one()
    )
    assert failure_log.outcome_code == "execution_failed"
    assert "RuntimeError" in (failure_log.outcome_message or "")


def test_schedule_atomicity_rollback_on_log_failure(sol_db, sol_org, sol_user, monkeypatch):
    """P0-2 atomicité : si log_action lève pendant schedule, tout rollback
    (token non consommé, pending non créé, JobOutbox absent)."""
    ctx = _ctx(sol_org, sol_user, correlation_id="a70117c0-aaaa-bbbb-cccc-000000000004")
    plan, tok = _propose_and_tokenize(sol_db, ctx)

    # Snapshot état avant schedule
    from models.sol import SolConfirmationToken as _Sct
    token_row_before = sol_db.query(_Sct).filter_by(token=tok).one()
    assert token_row_before.consumed is False

    # Monkeypatch log_action via sol.scheduler pour lever
    def _boom(*args, **kwargs):  # noqa: ARG001
        raise RuntimeError("simulated log_action crash")

    monkeypatch.setattr("sol.scheduler.log_action", _boom)

    with pytest.raises(RuntimeError, match="simulated log_action crash"):
        schedule_pending_action(sol_db, ctx, plan, tok)

    sol_db.rollback()  # cleanup session
    # Invariants : rien persisté
    token_after = sol_db.query(_Sct).filter_by(token=tok).one()
    assert token_after.consumed is False, "token ne doit PAS être consommé"

    pending_count = (
        sol_db.query(SolPendingAction).filter_by(correlation_id=plan.correlation_id).count()
    )
    assert pending_count == 0

    from models import JobOutbox as _Jo
    job_count = sol_db.query(_Jo).filter_by(job_type=JobType.SOL_EXECUTE_PENDING_ACTION).count()
    assert job_count == 0
