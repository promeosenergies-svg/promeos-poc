"""
PROMEOS — Tests V11 C1: KB endpoints smoke test (no 404 on happy path)
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
from database import get_db
from main import app


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestKBEndpointsNoCrash:
    """All KB endpoints return 200 on happy path (both routers)."""

    def test_ping(self, client):
        r = client.get("/api/kb/ping")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_stats_new(self, client):
        r = client.get("/api/kb/stats")
        assert r.status_code == 200

    def test_search_post(self, client):
        r = client.post("/api/kb/search", json={"q": "test", "limit": 10})
        assert r.status_code == 200

    def test_items_list(self, client):
        r = client.get("/api/kb/items")
        assert r.status_code == 200

    def test_archetypes_legacy(self, client):
        r = client.get("/api/kb/archetypes")
        assert r.status_code == 200

    def test_rules_legacy(self, client):
        r = client.get("/api/kb/rules")
        assert r.status_code == 200

    def test_recommendations_legacy(self, client):
        r = client.get("/api/kb/recommendations")
        assert r.status_code == 200

    def test_usages_stats_legacy(self, client):
        r = client.get("/api/kb/usages-stats")
        assert r.status_code == 200
