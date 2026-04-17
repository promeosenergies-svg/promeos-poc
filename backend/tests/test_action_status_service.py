"""
Sprint CX 2.5 hardening F1 — Tests du helper mark_action_done.

Vérifie que les 3 voies de clôture d'action (patch_action, CEE advance,
action_hub auto-close) fire bien CX_ACTION_FROM_INSIGHT via le helper
unifié, et que les seeds bypasse l'event (emit_event=False).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, ActionItem, ActionStatus, ActionSourceType
from models.iam import AuditLog, User, UserOrgRole, UserRole
from models import Organisation
from services.action_status_service import mark_action_done


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_org_and_member(db, org_id=1, user_id=1):
    org = Organisation(id=org_id, nom=f"Org{org_id}")
    user = User(
        id=user_id,
        email=f"u{user_id}@test.io",
        hashed_password="x",
        nom=f"U{user_id}",
        prenom=f"F{user_id}",
    )
    db.add_all([org, user])
    db.flush()
    role = UserOrgRole(user_id=user_id, org_id=org_id, role=UserRole.DG_OWNER)
    db.add(role)
    db.flush()


def _seed_action(db, action_id=100, org_id=1, status=ActionStatus.OPEN):
    action = ActionItem(
        id=action_id,
        org_id=org_id,
        source_type=ActionSourceType.COMPLIANCE,
        source_id="test",
        source_key="test-key",
        title="Test action",
        status=status,
    )
    db.add(action)
    db.flush()
    return action


def test_mark_action_done_sets_status_and_closed_at(db_session):
    _seed_org_and_member(db_session)
    action = _seed_action(db_session)
    assert action.closed_at is None
    mark_action_done(db_session, action, user_id=1)
    db_session.commit()
    assert action.status == ActionStatus.DONE
    assert action.closed_at is not None


def test_mark_action_done_fires_cx_event(db_session):
    _seed_org_and_member(db_session)
    action = _seed_action(db_session, action_id=200)
    mark_action_done(db_session, action, user_id=1, reason="unit_test")
    db_session.commit()
    events = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "CX_ACTION_FROM_INSIGHT", AuditLog.resource_id == "1")
        .all()
    )
    assert len(events) == 1
    detail = json.loads(events[0].detail_json)
    assert detail["action_id"] == 200
    assert detail["reason"] == "unit_test"


def test_mark_action_done_emit_event_false_skips_log(db_session):
    """Seeds et backfills ne doivent pas polluer les stats CX."""
    _seed_org_and_member(db_session)
    action = _seed_action(db_session, action_id=300)
    mark_action_done(db_session, action, emit_event=False)
    db_session.commit()
    events = db_session.query(AuditLog).filter(AuditLog.action == "CX_ACTION_FROM_INSIGHT").count()
    assert events == 0
    # Mais l'action est bien DONE + closed_at set
    assert action.status == ActionStatus.DONE
    assert action.closed_at is not None


def test_mark_action_done_idempotent_closed_at(db_session):
    """Appel 2× ne change pas closed_at une fois set."""
    from datetime import datetime, timezone, timedelta

    _seed_org_and_member(db_session)
    action = _seed_action(db_session, action_id=400)
    # Pre-set closed_at à une date passée (SQLite ne garde pas tzinfo)
    past = (datetime.now(timezone.utc) - timedelta(days=10)).replace(tzinfo=None)
    action.closed_at = past
    db_session.flush()

    mark_action_done(db_session, action, user_id=1)
    db_session.commit()
    # closed_at n'est PAS écrasé (comparer sans tzinfo car SQLite)
    stored = action.closed_at.replace(tzinfo=None) if action.closed_at.tzinfo else action.closed_at
    assert stored == past


def test_mark_action_done_without_user_id(db_session):
    """Auto-close backend (CEE, action_hub) → user_id=None, event fire quand même."""
    _seed_org_and_member(db_session)
    action = _seed_action(db_session, action_id=500)
    mark_action_done(db_session, action, user_id=None, reason="auto_close")
    db_session.commit()
    events = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "CX_ACTION_FROM_INSIGHT")
        .all()
    )
    assert len(events) == 1
    assert events[0].user_id is None


