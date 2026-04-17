"""Tests for CX event logging (Gap #2)."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
from models.iam import AuditLog
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


def test_log_cx_event_success(db_session):
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
    log_cx_event(db_session, 1, None, "CX_MODULE_ACTIVATED", {"module_key": "cockpit"})
    entry = db_session.query(AuditLog).filter(AuditLog.action == "CX_MODULE_ACTIVATED").first()
    assert entry is not None
    assert entry.user_id is None


def test_all_cx_event_types_defined():
    assert len(CX_EVENT_TYPES) == 5
    assert "CX_INSIGHT_CONSULTED" in CX_EVENT_TYPES
    assert "CX_MODULE_ACTIVATED" in CX_EVENT_TYPES
    assert "CX_REPORT_EXPORTED" in CX_EVENT_TYPES
    assert "CX_ONBOARDING_COMPLETED" in CX_EVENT_TYPES
    assert "CX_ACTION_FROM_INSIGHT" in CX_EVENT_TYPES


def test_log_cx_event_no_context(db_session):
    log_cx_event(db_session, 42, 1, "CX_REPORT_EXPORTED")
    entry = db_session.query(AuditLog).filter(AuditLog.action == "CX_REPORT_EXPORTED").first()
    assert entry is not None
    detail = json.loads(entry.detail_json)
    assert detail == {"org_id": 42}
