"""
Tests unitaires modèles Sol V1 — Phase 1.

Couvre :
- Sérialisation JSON round-trip
- Contraintes unique (correlation_id, cancellation_token) — parametrize
- Defaults SolOrgPolicy (0.85, 900, 'vous', 'preview_only')
- Méthode SolOrgPolicy.is_dry_run_active
- Confidence bornes [0, 1] (+ None autorisé)
- SolPendingAction statuts (waiting/executing/executed/cancelled)
- Foreign keys org_id, user_id
- Imports publics `from models.sol import ...`
- Migration idempotente _migrate_sol_v1_foundations
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
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


def test_sol_action_log_json_serialization(sol_action_log_factory):
    """plan_json, state_before, state_after round-trip correctement."""
    plan = {"intent": "invoice_dispute", "total_eur": 1847.20, "nested": {"x": [1, 2, 3]}}
    log = sol_action_log_factory(plan_json=plan, outcome_code="success", confidence=0.94)

    assert log.plan_json["total_eur"] == 1847.20
    assert log.plan_json["nested"]["x"] == [1, 2, 3]
    assert log.outcome_code == "success"


def test_sol_action_log_created_at_auto(sol_action_log_factory):
    """CreatedAtOnlyMixin pose created_at automatiquement."""
    log = sol_action_log_factory()
    assert log.created_at is not None
    assert isinstance(log.created_at, datetime)


@pytest.mark.parametrize(
    "confidence",
    [Decimal("0.00"), Decimal("0.50"), Decimal("0.85"), Decimal("1.00"), None],
)
def test_sol_action_log_confidence_valid_range(sol_action_log_factory, confidence):
    """Confidence accepte [0, 1] et None. (SQLite ignore CheckConstraint
    mais Postgres appliquera — test documente le contrat applicatif.)"""
    log = sol_action_log_factory(confidence=confidence)
    if confidence is None:
        assert log.confidence is None
    else:
        assert Decimal(str(log.confidence)) == confidence


@pytest.mark.parametrize(
    "duplicate_field",
    ["correlation_id", "cancellation_token"],
)
def test_sol_pending_action_unique_fields(sol_db, sol_org, sol_user, duplicate_field):
    """correlation_id ET cancellation_token sont UNIQUE."""
    common = dict(
        org_id=sol_org.id,
        user_id=sol_user.id,
        intent_kind="invoice_dispute",
        plan_json={},
        scheduled_for=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    first = SolPendingAction(
        correlation_id="corr-unique-1",
        cancellation_token="tok-unique-1",
        **common,
    )
    sol_db.add(first)
    sol_db.commit()

    # Tentative violation unicité sur le field paramétré
    kwargs = dict(
        correlation_id="corr-unique-2",
        cancellation_token="tok-unique-2",
        **common,
    )
    # Force la collision sur le field testé
    if duplicate_field == "correlation_id":
        kwargs["correlation_id"] = "corr-unique-1"
    else:
        kwargs["cancellation_token"] = "tok-unique-1"

    with pytest.raises(IntegrityError):
        sol_db.add(SolPendingAction(**kwargs))
        sol_db.commit()
    sol_db.rollback()


@pytest.mark.parametrize(
    "status",
    ["waiting", "executing", "executed", "cancelled"],
)
def test_sol_pending_action_status_round_trip(sol_db, sol_org, sol_user, status):
    """Chaque valeur de status round-trip correctement (pas de validation DB,
    validation applicative Phase 3 via enum Pydantic)."""
    action = SolPendingAction(
        correlation_id=f"corr-status-{status}",
        org_id=sol_org.id,
        user_id=sol_user.id,
        intent_kind="invoice_dispute",
        plan_json={},
        scheduled_for=datetime.now(timezone.utc) + timedelta(minutes=15),
        cancellation_token=f"tok-status-{status}",
        status=status,
    )
    sol_db.add(action)
    sol_db.commit()
    sol_db.refresh(action)
    assert action.status == status


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
    # updated_at posé automatiquement même sans set explicite
    assert policy.updated_at is not None


def test_sol_org_policy_is_dry_run_active(sol_db, sol_org):
    """Méthode is_dry_run_active : True si dry_run_until dans le futur."""
    policy = SolOrgPolicy(org_id=sol_org.id)
    sol_db.add(policy)
    sol_db.commit()

    now = datetime.now(timezone.utc)
    assert policy.is_dry_run_active(now) is False  # pas de dry_run

    policy.dry_run_until = now - timedelta(hours=1)
    assert policy.is_dry_run_active(now) is False  # passé

    policy.dry_run_until = now + timedelta(days=1)
    assert policy.is_dry_run_active(now) is True  # futur


def test_sol_action_log_org_scoping_fk(sol_db, sol_org, sol_user):
    """La FK org_id est persistée et requêtable."""
    log = SolActionLog(
        org_id=sol_org.id,
        user_id=sol_user.id,
        correlation_id="corr-scope-1",
        intent_kind="dt_action_plan",
        action_phase="proposed",
        inputs_hash="c" * 64,
        plan_json={"plan_id": 1},
    )
    sol_db.add(log)
    sol_db.commit()

    rows = sol_db.query(SolActionLog).filter_by(org_id=sol_org.id).all()
    assert len(rows) == 1
    assert rows[0].correlation_id == "corr-scope-1"


def test_sol_action_log_multiple_phases_same_correlation(sol_db, sol_org, sol_user):
    """Plusieurs lignes avec même correlation_id = chaîne des phases."""
    correlation_id = "corr-chain-1"
    for phase in ("proposed", "previewed", "confirmed", "scheduled", "executed"):
        log = SolActionLog(
            org_id=sol_org.id,
            user_id=sol_user.id,
            correlation_id=correlation_id,
            intent_kind="invoice_dispute",
            action_phase=phase,
            inputs_hash="d" * 64,
            plan_json={"phase": phase},
        )
        sol_db.add(log)
    sol_db.commit()

    chain = (
        sol_db.query(SolActionLog)
        .filter_by(correlation_id=correlation_id)
        .order_by(SolActionLog.id)
        .all()
    )
    assert len(chain) == 5
    assert [r.action_phase for r in chain] == ["proposed", "previewed", "confirmed", "scheduled", "executed"]


def test_migration_sol_v1_foundations_idempotent():
    """_migrate_sol_v1_foundations peut être appelée plusieurs fois sans erreur."""
    from sqlalchemy.pool import StaticPool
    from database.migrations import _migrate_sol_v1_foundations
    from models import Base
    import models.sol  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    # Les tables FK (organisations, users) doivent exister pour satisfaire les FK
    Base.metadata.create_all(bind=engine)

    # 1er run : devrait créer les 4 tables
    _migrate_sol_v1_foundations(engine)
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(engine)
    for t in ("sol_action_log", "sol_pending_action", "sol_confirmation_token", "sol_org_policy"):
        assert insp.has_table(t), f"Table {t} not created by migration"

    # 2nd run : ne doit pas lever (early return sur missing=[])
    _migrate_sol_v1_foundations(engine)
    _migrate_sol_v1_foundations(engine)

    engine.dispose()
