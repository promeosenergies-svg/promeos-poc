"""
Tests for CX Dashboard drivers: T2V, IAR, WAU/MAU.
Uses isolated in-memory DB + TestClient + DEMO_MODE lenient auth.
"""

import json
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


# ─── Helper _percentile (unit tests) ────────────────────────────────────────
from routes.cx_dashboard import _percentile  # noqa: E402


class TestPercentile:
    def test_empty_returns_none(self):
        assert _percentile([], 0.5) is None

    def test_single_value_any_p(self):
        assert _percentile([42.0], 0.0) == 42.0
        assert _percentile([42.0], 0.5) == 42.0
        assert _percentile([42.0], 1.0) == 42.0

    def test_p_zero_returns_min(self):
        assert _percentile([1.0, 2.0, 3.0, 10.0], 0.0) == 1.0

    def test_p_one_returns_max(self):
        assert _percentile([1.0, 2.0, 3.0, 10.0], 1.0) == 10.0

    def test_p50_interpolation(self):
        # Avec 4 valeurs, p50 interpole entre index 1 (=2) et 2 (=3) avec k=1.5
        # Résultat : 2 + (3 - 2) * 0.5 = 2.5
        assert _percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5

    def test_p95_on_large_sample(self):
        values = list(range(101))  # 0..100
        values.sort()
        p95 = _percentile(values, 0.95)
        # k = 100 * 0.95 = 95, donc valeur exacte à l'index 95
        assert p95 == 95.0

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base
from models.iam import AuditLog, User
from database import get_db


@pytest.fixture
def isolated_client():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app), session
    app.dependency_overrides.clear()
    session.close()


def _seed_user(db, user_id: int, created_days_ago: int) -> User:
    created_at = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
    u = User(
        id=user_id,
        email=f"u{user_id}@test.promeos.io",
        hashed_password="x",
        nom=f"User {user_id}",
        prenom=f"First{user_id}",
        created_at=created_at,
    )
    db.add(u)
    db.commit()
    return u


def _seed_event(db, user_id, org_id, event_type, days_ago):
    entry = AuditLog(
        user_id=user_id,
        action=event_type,
        resource_type="cx_event",
        resource_id=str(org_id),
        detail_json=json.dumps({"org_id": org_id}),
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db.add(entry)
    db.commit()


# ─── T2V ────────────────────────────────────────────────────────────────────


class TestT2V:
    def test_empty_db_returns_zero_sample(self, isolated_client):
        client, _ = isolated_client
        r = client.get("/api/admin/cx-dashboard/t2v")
        assert r.status_code == 200
        body = r.json()
        assert body["sample_size"] == 0
        assert body["p50_days"] is None

    def test_single_user_single_action(self, isolated_client):
        client, db = isolated_client
        _seed_user(db, user_id=1, created_days_ago=10)
        _seed_event(db, user_id=1, org_id=42, event_type="CX_ACTION_FROM_INSIGHT", days_ago=5)

        r = client.get("/api/admin/cx-dashboard/t2v")
        body = r.json()
        assert body["sample_size"] == 1
        assert 4.5 < body["p50_days"] < 5.5  # ~5 jours
        assert "42" in body["by_org"]

    def test_action_before_user_creation_excluded(self, isolated_client):
        client, db = isolated_client
        _seed_user(db, user_id=1, created_days_ago=2)
        _seed_event(db, user_id=1, org_id=1, event_type="CX_ACTION_FROM_INSIGHT", days_ago=10)

        r = client.get("/api/admin/cx-dashboard/t2v")
        assert r.json()["sample_size"] == 0

    def test_only_first_action_counts_per_user_org(self, isolated_client):
        client, db = isolated_client
        _seed_user(db, user_id=1, created_days_ago=30)
        _seed_event(db, user_id=1, org_id=1, event_type="CX_ACTION_FROM_INSIGHT", days_ago=25)
        _seed_event(db, user_id=1, org_id=1, event_type="CX_ACTION_FROM_INSIGHT", days_ago=5)

        r = client.get("/api/admin/cx-dashboard/t2v")
        body = r.json()
        assert body["sample_size"] == 1
        assert 4.5 < body["p50_days"] < 5.5  # min = 5j (pas 25)


# ─── IAR ────────────────────────────────────────────────────────────────────


class TestIAR:
    def test_empty_returns_null_ratio(self, isolated_client):
        client, _ = isolated_client
        r = client.get("/api/admin/cx-dashboard/iar")
        body = r.json()
        assert body["global"]["iar"] is None
        assert body["global"]["insights_consulted"] == 0
        assert body["global"]["actions_validated"] == 0

    def test_ratio_computed_correctly(self, isolated_client):
        client, db = isolated_client
        for _ in range(10):
            _seed_event(db, 1, 1, "CX_INSIGHT_CONSULTED", 2)
        for _ in range(3):
            _seed_event(db, 1, 1, "CX_ACTION_FROM_INSIGHT", 1)

        r = client.get("/api/admin/cx-dashboard/iar")
        body = r.json()
        assert body["global"]["iar"] == 0.3
        assert body["by_org"]["1"]["iar"] == 0.3

    def test_excludes_events_outside_window(self, isolated_client):
        client, db = isolated_client
        _seed_event(db, 1, 1, "CX_INSIGHT_CONSULTED", 50)  # hors fenêtre 30j
        _seed_event(db, 1, 1, "CX_ACTION_FROM_INSIGHT", 5)

        r = client.get("/api/admin/cx-dashboard/iar?days=30")
        body = r.json()
        assert body["global"]["insights_consulted"] == 0
        assert body["global"]["iar"] is None  # dénominateur=0


# ─── WAU/MAU ────────────────────────────────────────────────────────────────


class TestWauMau:
    def test_empty_returns_zero(self, isolated_client):
        client, _ = isolated_client
        r = client.get("/api/admin/cx-dashboard/wau-mau")
        body = r.json()
        assert body["wau"] == 0
        assert body["mau"] == 0
        assert body["stickiness_ratio"] is None

    def test_wau_counts_distinct_users_last_7d(self, isolated_client):
        client, db = isolated_client
        _seed_event(db, 1, 1, "CX_DASHBOARD_OPENED", 2)
        _seed_event(db, 2, 1, "CX_INSIGHT_CONSULTED", 3)
        _seed_event(db, 1, 1, "CX_DASHBOARD_OPENED", 4)  # doublon user 1
        _seed_event(db, 3, 1, "CX_DASHBOARD_OPENED", 15)  # hors WAU

        r = client.get("/api/admin/cx-dashboard/wau-mau")
        body = r.json()
        assert body["wau"] == 2  # users 1+2
        assert body["mau"] == 3  # users 1+2+3

    def test_null_user_excluded(self, isolated_client):
        client, db = isolated_client
        _seed_event(db, None, 1, "CX_DASHBOARD_OPENED", 2)
        _seed_event(db, 1, 1, "CX_DASHBOARD_OPENED", 2)

        r = client.get("/api/admin/cx-dashboard/wau-mau")
        assert r.json()["wau"] == 1

    def test_interpretation_tiers(self, isolated_client):
        client, db = isolated_client
        # 2 WAU users, 4 MAU users → ratio = 0.5 → excellent
        for uid in (1, 2):
            _seed_event(db, uid, 1, "CX_DASHBOARD_OPENED", 2)
        for uid in (3, 4):
            _seed_event(db, uid, 1, "CX_DASHBOARD_OPENED", 15)

        r = client.get("/api/admin/cx-dashboard/wau-mau")
        body = r.json()
        assert body["stickiness_ratio"] == 0.5
        assert body["interpretation"] == "excellent"
