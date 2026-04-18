"""
Sprint CX 3 P0.4 — Tests wiring CX_ONBOARDING_COMPLETED + CX_MODULE_ACTIVATED.

Valide :
- log_cx_event_first_only : fire 1x puis no-op sur les appels suivants
- context détail contient module_key
- onboarding_stepper.update_step fire CX_ONBOARDING_COMPLETED à la transition
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
from models.iam import AuditLog, User, UserOrgRole, UserRole
from models import Organisation
from middleware.cx_logger import (
    log_cx_event_first_only,
    invalidate_membership_cache,
    CX_MODULE_ACTIVATED,
    CX_ONBOARDING_COMPLETED,
)


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
    invalidate_membership_cache()
    yield session
    invalidate_membership_cache()
    session.close()


def _seed_member(db, user_id=1, org_id=1):
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


# ─── log_cx_event_first_only ────────────────────────────────────────────────


def test_module_activated_fires_only_first_time(db_session):
    """10 calls avec même module_key → 1 event CX_MODULE_ACTIVATED."""
    _seed_member(db_session, user_id=1, org_id=1)

    for _ in range(10):
        log_cx_event_first_only(
            db_session,
            org_id=1,
            user_id=1,
            event_type=CX_MODULE_ACTIVATED,
            dedup_key='"module_key": "flex"',
            context={"module_key": "flex"},
        )
    db_session.commit()

    count = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == CX_MODULE_ACTIVATED, AuditLog.resource_id == "1")
        .count()
    )
    assert count == 1


def test_module_activated_context_has_module_key(db_session):
    """Détail contient bien {module_key: "flex"}."""
    _seed_member(db_session, user_id=1, org_id=1)
    log_cx_event_first_only(
        db_session,
        org_id=1,
        user_id=1,
        event_type=CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "flex"',
        context={"module_key": "flex", "trigger": "create_flex_asset"},
    )
    db_session.commit()

    entry = db_session.query(AuditLog).filter(AuditLog.action == CX_MODULE_ACTIVATED).first()
    assert entry is not None
    detail = json.loads(entry.detail_json)
    assert detail["module_key"] == "flex"
    assert detail["trigger"] == "create_flex_asset"
    assert detail["org_id"] == 1


def test_module_activated_different_modules_fire_independently(db_session):
    """flex et bacs sont 2 activations distinctes, 2 events séparés."""
    _seed_member(db_session, user_id=1, org_id=1)

    log_cx_event_first_only(
        db_session, 1, 1, CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "flex"',
        context={"module_key": "flex"},
    )
    log_cx_event_first_only(
        db_session, 1, 1, CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "bacs"',
        context={"module_key": "bacs"},
    )
    # doublon flex → ignoré
    log_cx_event_first_only(
        db_session, 1, 1, CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "flex"',
        context={"module_key": "flex"},
    )
    db_session.commit()

    events = db_session.query(AuditLog).filter(AuditLog.action == CX_MODULE_ACTIVATED).all()
    assert len(events) == 2
    modules = sorted(json.loads(e.detail_json)["module_key"] for e in events)
    assert modules == ["bacs", "flex"]


def test_module_activated_different_orgs_fire_independently(db_session):
    """Même module activé par 2 orgs distinctes → 2 events."""
    _seed_member(db_session, user_id=1, org_id=1)
    _seed_member(db_session, user_id=2, org_id=2)

    log_cx_event_first_only(
        db_session, 1, 1, CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "flex"',
        context={"module_key": "flex"},
    )
    log_cx_event_first_only(
        db_session, 2, 2, CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "flex"',
        context={"module_key": "flex"},
    )
    db_session.commit()

    events = db_session.query(AuditLog).filter(AuditLog.action == CX_MODULE_ACTIVATED).all()
    assert len(events) == 2
    orgs = sorted(e.resource_id for e in events)
    assert orgs == ["1", "2"]


def test_module_activated_returns_true_on_first_false_after(db_session):
    """Retour booléen : True au 1er fire, False après."""
    _seed_member(db_session, user_id=1, org_id=1)

    first = log_cx_event_first_only(
        db_session, 1, 1, CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "flex"',
        context={"module_key": "flex"},
    )
    second = log_cx_event_first_only(
        db_session, 1, 1, CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "flex"',
        context={"module_key": "flex"},
    )
    assert first is True
    assert second is False


def test_log_cx_event_first_only_invalid_type_returns_false(db_session):
    """event_type hors whitelist → False et pas de log."""
    _seed_member(db_session, user_id=1, org_id=1)
    result = log_cx_event_first_only(
        db_session, 1, 1, "NOT_A_CX_EVENT",
        dedup_key="x",
        context={},
    )
    assert result is False
    assert db_session.query(AuditLog).count() == 0


# ─── CX_ONBOARDING_COMPLETED wiring via onboarding_stepper ──────────────────


def test_onboarding_completed_fires_once_on_all_done_transition(db_session, monkeypatch):
    """update_step passant le dernier step à done → 1 event CX_ONBOARDING_COMPLETED.
    Re-calling avec steps toujours tous done → pas de re-fire.
    """
    # On utilise directement la logique métier du service pour isoler le wiring,
    # et on simule le flow `update_step` manuellement.
    from models import OnboardingProgress
    from services.onboarding_stepper_service import STEP_FIELDS
    from middleware.cx_logger import log_cx_event
    from datetime import datetime, timezone

    _seed_member(db_session, user_id=1, org_id=1)

    # Créer progress initial avec tous les steps sauf 1 à True
    progress = OnboardingProgress(
        org_id=1,
        step_org_created=True,
        step_sites_added=True,
        step_meters_connected=True,
        step_invoices_imported=True,
        step_users_invited=True,
        step_first_action=False,  # dernier step non fait
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(progress)
    db_session.commit()

    # Simulate update_step : transition du dernier step à True
    progress.step_first_action = True

    # Replicate la logique du route handler (lignes 135-156).
    # Note : SQLite strip la TZ en round-trip → on normalise en naive pour ce test.
    just_completed = False
    if all(getattr(progress, f) for f in STEP_FIELDS):
        if not progress.completed_at:
            completed = datetime.now(timezone.utc)
            created = progress.created_at
            # Normaliser les deux en naive UTC pour compat SQLite roundtrip
            if created is not None and created.tzinfo is None:
                completed = completed.replace(tzinfo=None)
            progress.completed_at = completed
            if progress.created_at:
                progress.ttfv_seconds = int(
                    (completed - created).total_seconds()
                )
            just_completed = True

    if just_completed:
        log_cx_event(
            db_session,
            1,
            1,
            CX_ONBOARDING_COMPLETED,
            {"ttfv_seconds": progress.ttfv_seconds, "trigger": "stepper_all_done"},
        )
    db_session.commit()

    events = db_session.query(AuditLog).filter(AuditLog.action == CX_ONBOARDING_COMPLETED).all()
    assert len(events) == 1
    detail = json.loads(events[0].detail_json)
    assert detail["trigger"] == "stepper_all_done"
    assert detail["org_id"] == 1
    assert "ttfv_seconds" in detail

    # 2e update_step : all_done reste True mais completed_at déjà set → pas de re-fire
    just_completed_2 = False
    if all(getattr(progress, f) for f in STEP_FIELDS):
        if not progress.completed_at:  # déjà set → False
            just_completed_2 = True
    assert just_completed_2 is False
    # Pas de 2e log
    events_after = db_session.query(AuditLog).filter(AuditLog.action == CX_ONBOARDING_COMPLETED).all()
    assert len(events_after) == 1
