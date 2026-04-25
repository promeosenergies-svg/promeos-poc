"""
PROMEOS — Tests NPS micro-survey (Sprint CX P1 residual)

Couvre :
  - POST /api/nps/submit : score valide → recorded + event CX_NPS_SUBMITTED
  - Score hors range (-1, 11) → 422 pydantic
  - Deuxième submit dans 90j → already_submitted
  - Classification promoter/passive/detractor
  - Event fire avec context {score, has_verbatim, category}
"""

import json
import os
import sys
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["PROMEOS_DEMO_MODE"] = "true"

from models import Base  # noqa: E402
from models.iam import AuditLog  # noqa: E402
from middleware.cx_logger import CX_NPS_SUBMITTED, invalidate_membership_cache  # noqa: E402


@pytest.fixture
def client_and_db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    from main import app
    from database import get_db

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    invalidate_membership_cache()
    client = TestClient(app, raise_server_exceptions=False)
    yield client, SessionLocal
    app.dependency_overrides.clear()
    invalidate_membership_cache()


def test_submit_valid_score_records_event(client_and_db):
    client, SessionLocal = client_and_db
    r = client.post("/api/nps/submit?org_id=1", json={"score": 9, "verbatim": "Super produit"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "recorded"
    assert body["category"] == "promoter"

    db = SessionLocal()
    try:
        entry = db.query(AuditLog).filter(AuditLog.action == CX_NPS_SUBMITTED).first()
        assert entry is not None
        assert entry.resource_type == "cx_event"
        assert entry.resource_id == "1"
        detail = json.loads(entry.detail_json)
        assert detail["score"] == 9
        assert detail["has_verbatim"] is True
        assert detail["category"] == "promoter"
    finally:
        db.close()


def test_submit_without_verbatim(client_and_db):
    client, SessionLocal = client_and_db
    r = client.post("/api/nps/submit?org_id=1", json={"score": 7})
    assert r.status_code == 200
    assert r.json()["category"] == "passive"

    db = SessionLocal()
    try:
        entry = db.query(AuditLog).filter(AuditLog.action == CX_NPS_SUBMITTED).first()
        detail = json.loads(entry.detail_json)
        assert detail["has_verbatim"] is False
        assert detail["category"] == "passive"
    finally:
        db.close()


def test_submit_detractor_category(client_and_db):
    client, _ = client_and_db
    r = client.post("/api/nps/submit?org_id=1", json={"score": 3})
    assert r.status_code == 200
    assert r.json()["category"] == "detractor"


def test_submit_score_out_of_range_rejected(client_and_db):
    client, _ = client_and_db
    # Score négatif
    r = client.post("/api/nps/submit?org_id=1", json={"score": -1})
    assert r.status_code == 422
    # Score > 10
    r = client.post("/api/nps/submit?org_id=1", json={"score": 11})
    assert r.status_code == 422


def test_submit_boundaries_accepted(client_and_db):
    client, _ = client_and_db
    # Score = 0 (détracteur extrême) accepté
    r = client.post("/api/nps/submit?org_id=1", json={"score": 0})
    assert r.status_code == 200
    assert r.json()["category"] == "detractor"


def test_second_submit_within_90d_returns_already_submitted(client_and_db):
    """
    Anti-flood: un user ayant soumis < 90j ne peut resoumettre.
    On simule en créant directement un AuditLog avec user_id connu,
    puis en authentifiant via dépendance override.
    """
    client, SessionLocal = client_and_db

    from middleware.auth import get_optional_auth, AuthContext
    from models.iam import User, UserOrgRole, UserRole
    from models import Organisation

    db = SessionLocal()
    try:
        user = User(id=42, email="u@test.io", hashed_password="x", nom="U", prenom="U")
        org = Organisation(id=1, nom="Org1")
        db.add_all([user, org])
        db.flush()
        role = UserOrgRole(user_id=42, org_id=1, role=UserRole.DG_OWNER)
        db.add(role)
        db.commit()
    finally:
        db.close()

    def fake_auth():
        db2 = SessionLocal()
        user = db2.query(User).filter_by(id=42).first()
        uor = db2.query(UserOrgRole).filter_by(user_id=42, org_id=1).first()
        db2.close()
        return AuthContext(user=user, user_org_role=uor, org_id=1, role=UserRole.DG_OWNER, site_ids=[])

    from main import app

    app.dependency_overrides[get_optional_auth] = fake_auth

    try:
        r1 = client.post("/api/nps/submit", json={"score": 8})
        assert r1.status_code == 200
        assert r1.json()["status"] == "recorded"

        r2 = client.post("/api/nps/submit", json={"score": 9})
        assert r2.status_code == 200
        assert r2.json()["status"] == "already_submitted"
    finally:
        app.dependency_overrides.pop(get_optional_auth, None)


def test_submit_beyond_90d_allowed(client_and_db):
    """Un event > 90 jours ne bloque pas une nouvelle submission."""
    client, SessionLocal = client_and_db

    from middleware.auth import get_optional_auth, AuthContext
    from models.iam import User, UserOrgRole, UserRole
    from models import Organisation

    db = SessionLocal()
    try:
        user = User(id=99, email="v@test.io", hashed_password="x", nom="V", prenom="V")
        org = Organisation(id=2, nom="Org2")
        db.add_all([user, org])
        db.flush()
        role = UserOrgRole(user_id=99, org_id=2, role=UserRole.DG_OWNER)
        db.add(role)
        # Event vieux de 100 jours
        old = AuditLog(
            user_id=99,
            action=CX_NPS_SUBMITTED,
            resource_type="cx_event",
            resource_id="2",
            detail_json='{"score": 5}',
            created_at=datetime.utcnow() - timedelta(days=100),
        )
        db.add(old)
        db.commit()
    finally:
        db.close()

    def fake_auth():
        db2 = SessionLocal()
        user = db2.query(User).filter_by(id=99).first()
        uor = db2.query(UserOrgRole).filter_by(user_id=99, org_id=2).first()
        db2.close()
        return AuthContext(user=user, user_org_role=uor, org_id=2, role=UserRole.DG_OWNER, site_ids=[])

    from main import app

    app.dependency_overrides[get_optional_auth] = fake_auth

    try:
        r = client.post("/api/nps/submit", json={"score": 10})
        assert r.status_code == 200
        assert r.json()["status"] == "recorded"
        assert r.json()["category"] == "promoter"
    finally:
        app.dependency_overrides.pop(get_optional_auth, None)
