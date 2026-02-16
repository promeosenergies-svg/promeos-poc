"""
PROMEOS - Unified demo reset tests
Covers: reset-pack canonical endpoint, auth/reset-demo legacy alias, IAM cleanup.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models import Base, Site, Organisation, Meter, MeterReading, User, UserOrgRole
from database import get_db
from main import app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed(db, pack="tertiaire", size="S"):
    from services.demo_seed import SeedOrchestrator
    orch = SeedOrchestrator(db)
    return orch.seed(pack=pack, size=size, rng_seed=42, days=30)


class TestResetPackEndpoint:
    def test_soft_reset_via_endpoint(self, client, db_session):
        _seed(db_session)
        assert db_session.query(Site).count() > 0
        resp = client.post("/api/demo/reset-pack", json={"mode": "soft"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert db_session.query(Site).count() == 0

    def test_hard_reset_requires_confirm(self, client):
        resp = client.post("/api/demo/reset-pack", json={"mode": "hard", "confirm": False})
        assert resp.status_code == 400

    def test_hard_reset_with_confirm(self, client, db_session):
        _seed(db_session)
        resp = client.post("/api/demo/reset-pack", json={"mode": "hard", "confirm": True})
        assert resp.status_code == 200
        assert db_session.query(Site).count() == 0

    def test_hard_reset_clears_iam_demo_users(self, client, db_session):
        _seed(db_session)
        # Verify IAM users exist after seed
        demo_users = db_session.query(User).filter(User.email.like("%@atlas.demo")).all()
        # May or may not have demo users depending on seed, but test the cleanup path
        resp = client.post("/api/demo/reset-pack", json={"mode": "hard", "confirm": True})
        assert resp.status_code == 200
        remaining = db_session.query(User).filter(User.email.like("%@atlas.demo")).all()
        assert len(remaining) == 0

    def test_seed_reset_soft_reseed_cycle(self, client, db_session):
        """seed → reset-pack soft → reseed OK."""
        # 1. Seed
        r1 = _seed(db_session)
        assert r1["status"] == "ok"
        count1 = db_session.query(Site).count()
        assert count1 > 0

        # 2. Soft reset
        resp = client.post("/api/demo/reset-pack", json={"mode": "soft"})
        assert resp.status_code == 200
        assert db_session.query(Site).count() == 0

        # 3. Reseed
        r2 = _seed(db_session)
        assert r2["status"] == "ok"
        assert db_session.query(Site).count() == count1


class TestLegacyAuthResetDemo:
    def test_legacy_alias_produces_soft_reset(self, client, db_session):
        """POST /api/auth/reset-demo delegates to canonical soft reset."""
        _seed(db_session)
        assert db_session.query(Site).count() > 0
        resp = client.post("/api/auth/reset-demo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("reset", "ok")
        assert db_session.query(Site).count() == 0


class TestStatusAlias:
    def test_status_pack_returns_counts(self, client, db_session):
        _seed(db_session)
        resp = client.get("/api/demo/status-pack")
        assert resp.status_code == 200
        data = resp.json()
        assert "counts" in data
        assert "total_rows" in data
        assert data["total_rows"] > 0

    def test_status_pack_empty_db_returns_200(self, client):
        """GET /api/demo/status-pack returns 200 even on empty DB."""
        resp = client.get("/api/demo/status-pack")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 0
        for val in data["counts"].values():
            assert val == 0
