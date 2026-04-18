"""Tests engine base + registry + DummyEngine."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sol.engines.base import (
    ENGINE_REGISTRY,
    EngineNotFoundError,
    NotReversibleError,
    SolEngine,
    clear_registry,
    get_engine,
    register_engine,
)
from sol.engines._dummy import DummyEngine
from sol.schemas import ActionPlan, ExecutionResult, IntentKind, PlanRefused, SolContextData

from datetime import datetime, timezone


def _make_ctx(correlation_id: str = "12345678-1234-1234-1234-123456789012") -> SolContextData:
    return SolContextData(
        org_id=1,
        user_id=1,
        correlation_id=correlation_id,
        now=datetime.now(timezone.utc),
    )


def test_dummy_engine_registered_on_import():
    # _dummy.py auto-register au module import
    import sol.engines  # noqa: F401
    assert IntentKind.DUMMY_NOOP in ENGINE_REGISTRY
    assert isinstance(ENGINE_REGISTRY[IntentKind.DUMMY_NOOP], DummyEngine)


def test_get_engine_dummy():
    engine = get_engine(IntentKind.DUMMY_NOOP)
    assert isinstance(engine, DummyEngine)


def test_get_engine_unknown_raises():
    with pytest.raises(EngineNotFoundError):
        get_engine(IntentKind.INVOICE_DISPUTE)


def test_dummy_engine_dry_run_success():
    engine = DummyEngine()
    ctx = _make_ctx()
    plan = engine.dry_run(ctx, {"confidence": 0.95})
    assert isinstance(plan, ActionPlan)
    assert plan.intent == IntentKind.DUMMY_NOOP
    assert plan.confidence == 0.95
    assert plan.reversible is True


def test_dummy_engine_dry_run_refuse():
    engine = DummyEngine()
    ctx = _make_ctx()
    refused = engine.dry_run(ctx, {"should_refuse": True})
    assert isinstance(refused, PlanRefused)
    assert refused.reason_code == "confidence_low"


def test_dummy_engine_execute():
    engine = DummyEngine()
    ctx = _make_ctx()
    plan = engine.dry_run(ctx, {})
    assert isinstance(plan, ActionPlan)
    result = engine.execute(ctx, plan, confirmation_token="fake-token")
    assert isinstance(result, ExecutionResult)
    assert result.outcome_code == "dummy_success"


def test_dummy_engine_revert():
    engine = DummyEngine()
    ctx = _make_ctx()
    fake_log = SimpleNamespace(correlation_id=ctx.correlation_id)
    result = engine.revert(ctx, fake_log, reason="test revert")
    assert result.outcome_code == "dummy_reverted"


class _NonReversibleEngine(SolEngine):
    KIND = IntentKind.INVOICE_DISPUTE  # bidon, juste pour tests
    REVERSIBLE = False

    def dry_run(self, ctx, params):
        return None  # noqa

    def execute(self, ctx, plan, confirmation_token):
        return None  # noqa


def test_default_revert_raises_not_reversible(sol_db):  # noqa: ARG001 — pas de DB nécessaire
    engine = _NonReversibleEngine()
    ctx = _make_ctx()
    with pytest.raises(NotReversibleError):
        engine.revert(ctx, object(), reason="test")


def test_register_engine_idempotent_override():
    """register_engine override si même KIND (utile tests)."""
    orig_count = len(ENGINE_REGISTRY)
    register_engine(DummyEngine())  # re-register same kind
    assert len(ENGINE_REGISTRY) == orig_count


def test_clear_registry_and_restore():
    import sol.engines._dummy  # noqa: F401
    initial = dict(ENGINE_REGISTRY)
    clear_registry()
    assert len(ENGINE_REGISTRY) == 0
    # Restore DummyEngine pour que les autres tests continuent
    for kind, engine in initial.items():
        register_engine(engine)
    assert IntentKind.DUMMY_NOOP in ENGINE_REGISTRY
