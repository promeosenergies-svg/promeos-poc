"""Tests for CX event logging (Gap #2 + Sprint CX 2.5 hardening F2+S1)."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
from models.iam import AuditLog, User, UserOrgRole, UserRole
from models import Organisation
from middleware.cx_logger import log_cx_event, CX_EVENT_TYPES


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


def _seed_member(db, user_id=1, org_id=1):
    """Seed a user + org + UserOrgRole (member) — required for S1 hardening."""
    user = User(
        id=user_id,
        email=f"u{user_id}@test.io",
        hashed_password="x",
        nom=f"User{user_id}",
        prenom=f"First{user_id}",
    )
    org = Organisation(id=org_id, nom=f"Org{org_id}")
    db.add_all([user, org])
    db.flush()
    role = UserOrgRole(user_id=user_id, org_id=org_id, role=UserRole.DG_OWNER)
    db.add(role)
    db.flush()


def test_log_cx_event_success(db_session):
    _seed_member(db_session, user_id=1, org_id=1)
    log_cx_event(
        db_session, org_id=1, user_id=1, event_type="CX_INSIGHT_CONSULTED", context={"insight_type": "copilot"}
    )
    entry = db_session.query(AuditLog).filter(AuditLog.action == "CX_INSIGHT_CONSULTED").first()
    assert entry is not None
    assert entry.resource_type == "cx_event"
    assert entry.resource_id == "1"
    detail = json.loads(entry.detail_json)
    assert detail["org_id"] == 1
    assert detail["insight_type"] == "copilot"


def test_log_cx_event_invalid_type_silent(db_session):
    log_cx_event(db_session, 1, 1, "INVALID_EVENT")
    count = db_session.query(AuditLog).filter(AuditLog.action == "INVALID_EVENT").count()
    assert count == 0


def test_log_cx_event_no_user(db_session):
    # Pas de user_id → S1 skip la validation membership
    log_cx_event(db_session, 1, None, "CX_MODULE_ACTIVATED", {"module_key": "cockpit"})
    entry = db_session.query(AuditLog).filter(AuditLog.action == "CX_MODULE_ACTIVATED").first()
    assert entry is not None
    assert entry.user_id is None


def test_all_cx_event_types_defined():
    assert len(CX_EVENT_TYPES) == 6
    assert "CX_INSIGHT_CONSULTED" in CX_EVENT_TYPES
    assert "CX_MODULE_ACTIVATED" in CX_EVENT_TYPES
    assert "CX_REPORT_EXPORTED" in CX_EVENT_TYPES
    assert "CX_ONBOARDING_COMPLETED" in CX_EVENT_TYPES
    assert "CX_ACTION_FROM_INSIGHT" in CX_EVENT_TYPES
    assert "CX_DASHBOARD_OPENED" in CX_EVENT_TYPES


def test_log_cx_event_no_context(db_session):
    _seed_member(db_session, user_id=1, org_id=42)
    log_cx_event(db_session, 42, 1, "CX_REPORT_EXPORTED")
    entry = db_session.query(AuditLog).filter(AuditLog.action == "CX_REPORT_EXPORTED").first()
    assert entry is not None
    detail = json.loads(entry.detail_json)
    assert detail == {"org_id": 42}


# ─── Sprint CX 2.5 hardening F2 : db.flush au lieu de db.commit ───────────


def test_log_cx_event_does_not_commit_parent_transaction(db_session):
    """F2: flush() ne commit pas les modifs pending du caller.

    Un caller qui a des modifs pending (pas encore commit) + appelle
    log_cx_event + puis rollback → l'event ET les modifs doivent disparaître.
    """
    _seed_member(db_session, user_id=1, org_id=1)
    # Modif pending côté caller (pas de commit)
    pending = Organisation(nom="org-pending-not-committed")
    db_session.add(pending)
    # log_cx_event fait flush() mais PAS commit()
    log_cx_event(db_session, 1, 1, "CX_INSIGHT_CONSULTED")
    # Rollback du caller → tout disparaît (event + pending org)
    db_session.rollback()
    assert db_session.query(AuditLog).filter(AuditLog.action == "CX_INSIGHT_CONSULTED").count() == 0
    assert db_session.query(Organisation).filter_by(nom="org-pending-not-committed").count() == 0


# ─── Sprint CX 2.5 hardening S1 : validation membership user → org ─────────


def test_s1_event_rejected_when_user_not_member_of_org(db_session):
    """S1: si user_id=X pas membre de org_id=Y, log_cx_event rejette silencieusement."""
    # user 1 est membre de org 1, mais on tente de logger sur org 2
    _seed_member(db_session, user_id=1, org_id=1)
    org2 = Organisation(id=2, nom="Org2")
    db_session.add(org2)
    db_session.flush()

    log_cx_event(db_session, org_id=2, user_id=1, event_type="CX_INSIGHT_CONSULTED")
    db_session.commit()

    # 0 event pour org_id=2 car user 1 n'en est pas membre
    count = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "CX_INSIGHT_CONSULTED", AuditLog.resource_id == "2")
        .count()
    )
    assert count == 0


def test_s1_event_accepted_when_user_is_member_of_org(db_session):
    """S1: user membre de l'org → log normal."""
    _seed_member(db_session, user_id=7, org_id=99)
    log_cx_event(db_session, org_id=99, user_id=7, event_type="CX_DASHBOARD_OPENED")
    db_session.commit()
    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "CX_DASHBOARD_OPENED", AuditLog.resource_id == "99")
        .first()
    )
    assert entry is not None
    assert entry.user_id == 7


def test_s1_event_with_null_user_id_bypasses_membership_check(db_session):
    """S1: user_id=None → pas de check membership (backwards compat DEMO_MODE anonyme)."""
    org5 = Organisation(id=5, nom="Org5")
    db_session.add(org5)
    db_session.flush()
    log_cx_event(db_session, org_id=5, user_id=None, event_type="CX_DASHBOARD_OPENED")
    db_session.commit()
    count = (
        db_session.query(AuditLog).filter(AuditLog.action == "CX_DASHBOARD_OPENED", AuditLog.resource_id == "5").count()
    )
    assert count == 1
