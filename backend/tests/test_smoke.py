"""
PROMEOS - Smoke Test Suite
Minimal tests that must pass before any deploy/merge.
Tests: health endpoint, DB connectivity, basic CRUD chain.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    """Verify backend is alive and responds correctly."""

    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_returns_healthy(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"

    def test_health_has_version(self, client):
        data = client.get("/health").json()
        assert "version" in data
        assert data["version"]  # non-empty

    def test_root_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_docs_available(self, client):
        r = client.get("/docs")
        assert r.status_code == 200


class TestDBConnectivity:
    """Verify database is reachable and has expected tables."""

    def test_db_session_works(self):
        from database import SessionLocal
        db = SessionLocal()
        try:
            result = db.execute(__import__('sqlalchemy').text("SELECT 1")).scalar()
            assert result == 1
        finally:
            db.close()

    def test_sites_table_exists(self):
        from database import SessionLocal
        from models import Site
        db = SessionLocal()
        try:
            count = db.query(Site).count()
            assert count >= 0  # table exists, may be empty
        finally:
            db.close()

    def test_site_has_expected_columns(self):
        from models import Site
        columns = [c.name for c in Site.__table__.columns]
        assert "id" in columns
        assert "nom" in columns


class TestAPICrudChain:
    """Verify basic API read operations work end-to-end."""

    def test_list_sites(self, client):
        r = client.get("/api/sites")
        assert r.status_code == 200
        data = r.json()
        # API returns either a list or {"sites": [...], "total": N}
        if isinstance(data, dict):
            assert "sites" in data
            assert isinstance(data["sites"], list)
        else:
            assert isinstance(data, list)

    def test_list_compteurs(self, client):
        r = client.get("/api/compteurs")
        assert r.status_code == 200

    def test_cockpit(self, client):
        r = client.get("/api/cockpit")
        assert r.status_code == 200
        data = r.json()
        assert "total_sites" in data or "sites" in data or isinstance(data, dict)

    def test_regops_dashboard(self, client):
        r = client.get("/api/regops/dashboard")
        assert r.status_code == 200

    def test_kb_stats(self, client):
        r = client.get("/api/kb/stats")
        assert r.status_code == 200

    def test_monitoring_alerts(self, client):
        r = client.get("/api/monitoring/alerts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_bill_rules(self, client):
        r = client.get("/api/bill/rules")
        assert r.status_code == 200

    def test_watchers_list(self, client):
        r = client.get("/api/watchers/list")
        assert r.status_code == 200

    def test_connectors_list(self, client):
        r = client.get("/api/connectors/list")
        assert r.status_code == 200

    def test_energy_meters(self, client):
        r = client.get("/api/energy/meters")
        assert r.status_code == 200


class TestOpenAPISchema:
    """Verify OpenAPI spec is valid and complete."""

    def test_openapi_json(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
        assert len(schema["paths"]) > 50  # At least 50 unique paths
