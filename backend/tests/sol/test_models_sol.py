"""
Tests unitaires modèles Sol V1 — Phase 1.

Couvre :
- Sérialisation JSON (plan_json, state_before/after) round-trip
- Contraintes unique (correlation_id, cancellation_token)
- Defaults SolOrgPolicy (0.85, 900, 'vous', 'preview_only')
- Méthode SolOrgPolicy.is_dry_run_active
- Foreign keys org_id, user_id
- Imports publics `from models.sol import ...`
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from models.sol import (
    AppendOnlyViolation,
    SolActionLog,
    SolConfirmationToken,
    SolOrgPolicy,
    SolPendingAction,
)


def test_sol_models_public_imports():
    """Les 5 symboles publics sont importables depuis models.sol."""
    assert SolActionLog.__tablename__ == "sol_action_log"
    assert SolPendingAction.__tablename__ == "sol_pending_action"
    assert SolConfirmationToken.__tablename__ == "sol_confirmation_token"
    assert SolOrgPolicy.__tablename__ == "sol_org_policy"
    assert AppendOnlyViolation is not None


def test_sol_action_log_json_serialization(sol_db, sol_org, sol_user, sol_correlation_id):
    """plan_json, state_before, state_after round-trip correctement."""
    plan = {"intent": "invoice_dispute", "total_eur": 1847.20, "nested": {"x": [1, 2, 3]}}
    state_before = {"invoice_status": "received"}
    state_after = {"invoice_status": "disputed", "message_id": "msg-123"}

    log = SolActionLog(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id=sol_correlation_id,
        intent_kind="invoice_dispute",
        action_phase="proposed",
        inputs_hash="a" * 64,
        plan_json=plan,
        state_before=state_before,
        state_after=state_after,
        confidence=0.94,
    )
    sol_db.add(log)
    sol_db.commit()
    sol_db.refresh(log)

    assert log.plan_json["total_eur"] == 1847.20
    assert log.plan_json["nested"]["x"] == [1, 2, 3]
    assert log.state_before["invoice_status"] == "received"
    assert log.state_after["message_id"] == "msg-123"


def test_sol_action_log_created_at_auto(sol_db, sol_org, sol_user, sol_correlation_id):
    """CreatedAtOnlyMixin pose created_at automatiquement, pas d'updated_at."""
    log = SolActionLog(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id=sol_correlation_id,
        intent_kind="invoice_dispute",
        action_phase="proposed",
        inputs_hash="b" * 64,
        plan_json={},
    )
    sol_db.add(log)
    sol_db.commit()
    sol_db.refresh(log)

    assert log.created_at is not None
    assert isinstance(log.created_at, datetime)
    # Pas d'updated_at exposé sur le modèle append-only
    assert not hasattr(log, "updated_at") or getattr(log, "updated_at", None) is None


def test_sol_pending_action_unique_correlation_id(sol_db, sol_org, sol_user, sol_correlation_id):
    """correlation_id est unique sur sol_pending_action."""
    base = dict(
        org_id=sol_org.id,
        user_id=sol_user.id,
        intent_kind="invoice_dispute",
        plan_json={},
        scheduled_for=datetime.now(timezone.utc) + timedelta(minutes=15),
        cancellation_token="tok_first",
    )
    sol_db.add(SolPendingAction(correlation_id=sol_correlation_id, **base))
    sol_db.commit()

    with pytest.raises(IntegrityError):
        sol_db.add(SolPendingAction(correlation_id=sol_correlation_id, **{**base, "cancellation_token": "tok_second"}))
        sol_db.commit()
    sol_db.rollback()


def test_sol_pending_action_unique_cancellation_token(sol_db, sol_org, sol_user):
    """cancellation_token est unique sur sol_pending_action."""
    base = dict(
        org_id=sol_org.id,
        user_id=sol_user.id,
        intent_kind="exec_report",
        plan_json={},
        scheduled_for=datetime.now(timezone.utc) + timedelta(hours=1),
        cancellation_token="same_token_collision",
    )
    sol_db.add(SolPendingAction(correlation_id="corr-1", **base))
    sol_db.commit()

    with pytest.raises(IntegrityError):
        sol_db.add(SolPendingAction(correlation_id="corr-2", **base))
        sol_db.commit()
    sol_db.rollback()


def test_sol_confirmation_token_pk_and_expiry(sol_db, sol_org, sol_user):
    """Token est PK string — expires_at + consumed tracés."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    tok = SolConfirmationToken(
        token="abc" * 20 + "xyz",  # 63 chars, dans les 64 autorisés
        correlation_id="corr-token-1",
        plan_hash="p" * 64,
        user_id=sol_user.id,
        org_id=sol_org.id,
        expires_at=expires,
    )
    sol_db.add(tok)
    sol_db.commit()

    loaded = sol_db.query(SolConfirmationToken).filter_by(correlation_id="corr-token-1").one()
    assert loaded.consumed is False
    assert loaded.consumed_at is None
    assert loaded.expires_at is not None


def test_sol_confirmation_token_consumed_marked(sol_db, sol_org, sol_user):
    """Consommer un token : consumed=True + consumed_at set."""
    tok = SolConfirmationToken(
        token="tok_to_consume_" + "x" * 40,
        correlation_id="corr-consume-1",
        plan_hash="h" * 64,
        user_id=sol_user.id,
        org_id=sol_org.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    sol_db.add(tok)
    sol_db.commit()

    # Simule consommation
    tok.consumed = True
    tok.consumed_at = datetime.now(timezone.utc)
    sol_db.commit()

    sol_db.refresh(tok)
    assert tok.consumed is True
    assert tok.consumed_at is not None


def test_sol_org_policy_defaults(sol_db, sol_org):
    """Defaults : confidence=0.85, grace=900s, tone=vous, mode=preview_only."""
    policy = SolOrgPolicy(org_id=sol_org.id)
    sol_db.add(policy)
    sol_db.commit()
    sol_db.refresh(policy)

    assert policy.agentic_mode == "preview_only"
    assert float(policy.confidence_threshold) == 0.85
    assert policy.grace_period_seconds == 900
    assert policy.tone_preference == "vous"
    assert policy.dry_run_until is None
    assert policy.dual_validation_threshold is None


def test_sol_org_policy_is_dry_run_active(sol_db, sol_org):
    """Méthode is_dry_run_active : True si dry_run_until dans le futur."""
    policy = SolOrgPolicy(org_id=sol_org.id)
    sol_db.add(policy)
    sol_db.commit()

    now = datetime.now(timezone.utc)

    # Pas de dry_run défini → False
    assert policy.is_dry_run_active(now) is False

    # dry_run_until dans le passé → False
    policy.dry_run_until = now - timedelta(hours=1)
    assert policy.is_dry_run_active(now) is False

    # dry_run_until dans le futur → True
    policy.dry_run_until = now + timedelta(days=1)
    assert policy.is_dry_run_active(now) is True


def test_sol_action_log_org_scoping_fk(sol_db, sol_org, sol_user, sol_correlation_id):
    """La FK org_id est persistée et requêtable."""
    log = SolActionLog(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id=sol_correlation_id,
        intent_kind="dt_action_plan",
        action_phase="proposed",
        inputs_hash="c" * 64,
        plan_json={"plan_id": 1},
    )
    sol_db.add(log)
    sol_db.commit()

    rows = sol_db.query(SolActionLog).filter_by(org_id=sol_org.id).all()
    assert len(rows) == 1
    assert rows[0].correlation_id == sol_correlation_id


def test_sol_action_log_multiple_phases_same_correlation(sol_db, sol_org, sol_user, sol_correlation_id):
    """Plusieurs lignes avec même correlation_id = chaîne des phases."""
    for phase in ("proposed", "previewed", "confirmed", "scheduled", "executed"):
        log = SolActionLog(
            org_id=sol_org.id,
            user_id=sol_user.id,
            correlation_id=sol_correlation_id,
            intent_kind="invoice_dispute",
            action_phase=phase,
            inputs_hash="d" * 64,
            plan_json={"phase": phase},
        )
        sol_db.add(log)
    sol_db.commit()

    chain = (
        sol_db.query(SolActionLog)
        .filter_by(correlation_id=sol_correlation_id)
        .order_by(SolActionLog.id)
        .all()
    )
    assert len(chain) == 5
    assert [r.action_phase for r in chain] == ["proposed", "previewed", "confirmed", "scheduled", "executed"]
