"""Tests validator Sol V1 — 5 exceptions typées + cas success."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

import sol.engines  # noqa: F401
from models.sol import SolConfirmationToken
from sol.planner import propose_plan
from sol.schemas import ActionPlan, IntentKind, SolContextData
from sol.utils import generate_confirmation_token
from sol.validator import (
    ConfidenceTooLow,
    DryRunBlocked,
    DualValidationMissing,
    InvalidToken,
    PlanAltered,
    validate_plan_for_execution,
)
from sol.validator import _plan_hash


@pytest.fixture(autouse=True)
def _ensure_secret():
    os.environ.setdefault("SOL_SECRET_KEY", "test_key_validator_v1")


def _fresh_ctx(sol_org, sol_user, **policy_override):
    policy = {
        "agentic_mode": "preview_only",
        "confidence_threshold": 0.85,
        "grace_period_seconds": 900,
        "dual_validation_threshold": None,
    }
    policy.update(policy_override)
    return SolContextData(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id="99999999-9999-9999-9999-999999999999",
        now=datetime.now(timezone.utc),
        org_policy=policy,
    )


def _create_valid_token(sol_db, ctx: SolContextData, plan: ActionPlan) -> str:
    """Helper : génère + persiste un SolConfirmationToken valide."""
    plan_hash = _plan_hash(plan)
    tok = generate_confirmation_token(plan.correlation_id, plan_hash, ctx.user_id)
    row = SolConfirmationToken(
        token=tok,
        correlation_id=plan.correlation_id,
        plan_hash=plan_hash,
        user_id=ctx.user_id,
        org_id=ctx.org_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    sol_db.add(row)
    sol_db.commit()
    return tok


def test_validate_success(sol_db, sol_org, sol_user):
    ctx = _fresh_ctx(sol_org, sol_user)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    assert isinstance(plan, ActionPlan)
    tok = _create_valid_token(sol_db, ctx, plan)

    # Ne doit PAS lever
    validate_plan_for_execution(sol_db, ctx, plan, tok)


def test_validate_invalid_token_format(sol_db, sol_org, sol_user):
    ctx = _fresh_ctx(sol_org, sol_user)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})

    with pytest.raises(InvalidToken):
        validate_plan_for_execution(sol_db, ctx, plan, "not-a-valid-token-at-all")


def test_validate_expired_token(sol_db, sol_org, sol_user):
    ctx = _fresh_ctx(sol_org, sol_user)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    plan_hash = _plan_hash(plan)
    tok = generate_confirmation_token(plan.correlation_id, plan_hash, ctx.user_id)
    # Insert token avec expires_at passé
    row = SolConfirmationToken(
        token=tok,
        correlation_id=plan.correlation_id,
        plan_hash=plan_hash,
        user_id=ctx.user_id,
        org_id=ctx.org_id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    sol_db.add(row)
    sol_db.commit()

    with pytest.raises(InvalidToken, match="expir"):
        validate_plan_for_execution(sol_db, ctx, plan, tok)


def test_validate_consumed_token(sol_db, sol_org, sol_user):
    ctx = _fresh_ctx(sol_org, sol_user)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    tok = _create_valid_token(sol_db, ctx, plan)

    # Marquer consumed
    row = sol_db.query(SolConfirmationToken).filter_by(token=tok).one()
    row.consumed = True
    row.consumed_at = datetime.now(timezone.utc)
    sol_db.commit()

    with pytest.raises(InvalidToken, match="consomm"):
        validate_plan_for_execution(sol_db, ctx, plan, tok)


def test_validate_plan_altered(sol_db, sol_org, sol_user):
    """Le plan_hash change si on modifie le plan après avoir émis le token."""
    ctx = _fresh_ctx(sol_org, sol_user)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    tok = _create_valid_token(sol_db, ctx, plan)

    # Altérer le plan en mémoire (simulant un tampering entre preview et confirm)
    altered_plan = plan.model_copy(update={"title_fr": "Titre modifié après coup"})

    # verify_confirmation_token va échouer (plan_hash recalculé ≠ signé)
    # et on va lever InvalidToken (car HMAC check utilise le plan_hash calculé)
    with pytest.raises((InvalidToken, PlanAltered)):
        validate_plan_for_execution(sol_db, ctx, altered_plan, tok)


def test_validate_confidence_too_low(sol_db, sol_org, sol_user):
    """Plan avec confidence 0.70 + org_policy threshold 0.85 → rejeté."""
    ctx = _fresh_ctx(sol_org, sol_user, confidence_threshold=0.85)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.70})
    assert isinstance(plan, ActionPlan)
    tok = _create_valid_token(sol_db, ctx, plan)

    with pytest.raises(ConfidenceTooLow):
        validate_plan_for_execution(sol_db, ctx, plan, tok)


def test_validate_dry_run_blocked(sol_db, sol_org, sol_user):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    ctx = _fresh_ctx(sol_org, sol_user, dry_run_until=future)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    tok = _create_valid_token(sol_db, ctx, plan)

    with pytest.raises(DryRunBlocked):
        validate_plan_for_execution(sol_db, ctx, plan, tok)


def test_validate_dual_validation_missing_above_threshold(sol_db, sol_org, sol_user):
    """Plan value 5000 € > seuil 2000 € + requires_dual_validation → besoin 2e validator."""
    from sol.schemas import Source
    ctx = _fresh_ctx(sol_org, sol_user, dual_validation_threshold=2000)

    # Construire manuellement un plan avec requires_dual_validation=True
    # + estimated_value_eur > threshold
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    plan = plan.model_copy(update={"requires_dual_validation": True, "estimated_value_eur": 5000.0})

    tok = _create_valid_token(sol_db, ctx, plan)

    # Sans second_validator_user_id → DualValidationMissing
    with pytest.raises(DualValidationMissing):
        validate_plan_for_execution(sol_db, ctx, plan, tok)

    # Avec même user_id que primaire → DualValidationMissing
    with pytest.raises(DualValidationMissing, match="distincts"):
        validate_plan_for_execution(
            sol_db, ctx, plan, tok, second_validator_user_id=ctx.user_id
        )


def test_validate_dual_validation_below_threshold_ok(sol_db, sol_org, sol_user):
    """Plan value 1000 € < seuil 2000 € → dual pas nécessaire même si requires=True."""
    ctx = _fresh_ctx(sol_org, sol_user, dual_validation_threshold=2000)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    plan = plan.model_copy(update={"requires_dual_validation": True, "estimated_value_eur": 1000.0})
    tok = _create_valid_token(sol_db, ctx, plan)

    # Pas d'erreur attendue
    validate_plan_for_execution(sol_db, ctx, plan, tok)


def test_validate_foreign_org_token_rejected(sol_db, sol_org, sol_user):
    """Token émis pour org A ne peut pas valider un plan pour org B."""
    ctx = _fresh_ctx(sol_org, sol_user)
    plan = propose_plan(sol_db, ctx, IntentKind.DUMMY_NOOP, params={"confidence": 0.95})
    tok = _create_valid_token(sol_db, ctx, plan)

    # Créer une autre org et utiliser son ctx avec le token de la première
    from models.organisation import Organisation
    other_org = Organisation(nom="Foreign Org", actif=True)
    sol_db.add(other_org)
    sol_db.commit()

    foreign_ctx = SolContextData(
        org_id=other_org.id,
        user_id=sol_user.id,
        correlation_id=plan.correlation_id,
        now=datetime.now(timezone.utc),
        org_policy={"confidence_threshold": 0.85},
    )

    with pytest.raises(InvalidToken, match="organisation"):
        validate_plan_for_execution(sol_db, foreign_ctx, plan, tok)
