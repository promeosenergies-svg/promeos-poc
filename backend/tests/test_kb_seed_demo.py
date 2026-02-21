"""
PROMEOS Tests - KB Seed Demo + Empty Returns 200
Tests: seed_demo idempotent, empty list endpoints return 200 with []
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, KBVersion, KBArchetype, KBMappingCode, KBAnomalyRule,
    KBRecommendation, KBStatus, KBConfidence,
)
from database import get_db
from main import app


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
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


# ── Tests: Empty KB returns 200 with [] ───────────────────────────

class TestKBEmptyReturns200:

    def test_archetypes_empty(self, client):
        r = client.get("/api/kb/archetypes")
        assert r.status_code == 200
        assert r.json() == []

    def test_rules_empty(self, client):
        r = client.get("/api/kb/rules")
        assert r.status_code == 200
        assert r.json() == []

    def test_recommendations_empty(self, client):
        r = client.get("/api/kb/recommendations")
        assert r.status_code == 200
        assert r.json() == []

    def test_stats_empty(self, client):
        r = client.get("/api/kb/usages-stats")
        assert r.status_code == 200
        data = r.json()
        assert data["archetypes_count"] == 0
        assert data["anomaly_rules_count"] == 0
        assert data["recommendations_count"] == 0
        assert data["naf_mappings_count"] == 0

    def test_search_empty(self, client):
        r = client.get("/api/kb/search", params={"q": "bureau"})
        assert r.status_code == 200
        data = r.json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_ping_always_ok(self, client):
        r = client.get("/api/kb/ping")
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ── Tests: Seed Demo ─────────────────────────────────────────────

class TestKBSeedDemo:

    def test_seed_creates_items(self, client, db_session):
        r = client.post("/api/kb/seed_demo")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["archetypes_seeded"] == 10
        assert data["rules_seeded"] == 15
        assert data["recommendations_seeded"] == 10
        assert data["naf_mappings_seeded"] == 30

    def test_seed_idempotent(self, client, db_session):
        # First call seeds
        r1 = client.post("/api/kb/seed_demo")
        assert r1.status_code == 200
        assert r1.json()["status"] == "ok"

        # Second call is no-op
        r2 = client.post("/api/kb/seed_demo")
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["status"] == "already_seeded"
        assert data2["archetypes_seeded"] == 0
        assert data2["rules_seeded"] == 0
        assert data2["recommendations_seeded"] == 0
        assert data2["naf_mappings_seeded"] == 0

    def test_seed_then_list_archetypes(self, client, db_session):
        client.post("/api/kb/seed_demo")
        r = client.get("/api/kb/archetypes")
        assert r.status_code == 200
        archetypes = r.json()
        assert len(archetypes) == 10
        codes = {a["code"] for a in archetypes}
        assert "BUREAU_STANDARD" in codes
        assert "DATACENTER" in codes

    def test_seed_then_list_rules(self, client, db_session):
        client.post("/api/kb/seed_demo")
        r = client.get("/api/kb/rules")
        assert r.status_code == 200
        rules = r.json()
        assert len(rules) == 15
        assert any(r["severity"] == "critical" for r in rules)

    def test_seed_then_list_recommendations(self, client, db_session):
        client.post("/api/kb/seed_demo")
        r = client.get("/api/kb/recommendations")
        assert r.status_code == 200
        recos = r.json()
        assert len(recos) == 10
        # ICE scores should be > 0
        assert all(r["ice_score"] > 0 for r in recos)
        # Sorted by ICE score desc
        scores = [r["ice_score"] for r in recos]
        assert scores == sorted(scores, reverse=True)

    def test_seed_then_stats(self, client, db_session):
        client.post("/api/kb/seed_demo")
        r = client.get("/api/kb/usages-stats")
        assert r.status_code == 200
        data = r.json()
        assert data["archetypes_count"] == 10
        assert data["anomaly_rules_count"] == 15
        assert data["recommendations_count"] == 10
        assert data["naf_mappings_count"] == 30
        assert data["kb_doc_id"] == "PROMEOS_DEMO_KB"

    def test_seed_naf_mappings(self, client, db_session):
        client.post("/api/kb/seed_demo")
        # Bureau Standard should have 3 NAF codes
        r = client.get("/api/kb/archetypes")
        bureau = next(a for a in r.json() if a["code"] == "BUREAU_STANDARD")
        assert len(bureau["naf_codes"]) == 3

    def test_seed_then_search(self, client, db_session):
        client.post("/api/kb/seed_demo")
        r = client.get("/api/kb/search", params={"q": "LED"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any("LED" in item["title"] for item in data["results"])

    def test_seed_kb_version_created(self, client, db_session):
        client.post("/api/kb/seed_demo")
        v = db_session.query(KBVersion).filter_by(doc_id="PROMEOS_DEMO_KB").first()
        assert v is not None
        assert v.version == "1.0.0-demo"
        assert v.is_active is True

    def test_seed_archetype_fields(self, client, db_session):
        client.post("/api/kb/seed_demo")
        arch = db_session.query(KBArchetype).filter_by(code="DATACENTER").first()
        assert arch is not None
        assert arch.kwh_m2_min == 500
        assert arch.kwh_m2_max == 3000
        assert arch.kwh_m2_avg == 1200
        assert arch.confidence == KBConfidence.HIGH
        assert arch.status == KBStatus.VALIDATED
