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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app
from models import Base
from database import get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def isolated_client():
    """Client with isolated in-memory DB for write tests."""
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
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()


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


class TestBillingRouterMount:
    """Verify billing router is registered and insight detail uses GET."""

    def test_billing_router_mounted(self, client):
        """OpenAPI schema must contain /api/billing/ paths."""
        schema = client.get("/openapi.json").json()
        billing_paths = [p for p in schema["paths"] if "/api/billing/" in p]
        assert len(billing_paths) >= 1, "billing router not mounted — check imports"

    def test_insight_detail_is_get(self, client):
        """The insight detail route must accept GET, not POST."""
        schema = client.get("/openapi.json").json()
        path = "/api/billing/insights/{insight_id}"
        assert path in schema["paths"], f"{path} not in OpenAPI"
        assert "get" in schema["paths"][path], f"{path} does not accept GET"

    def test_insight_detail_returns_404_for_missing(self, client):
        """GET /api/billing/insights/999999 should return 404, not 405."""
        r = client.get("/api/billing/insights/999999")
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"

    def test_import_sites_router_mounted(self, client):
        """import_sites router must not crash (Python 3.14 Optional fix)."""
        schema = client.get("/openapi.json").json()
        import_paths = [p for p in schema["paths"] if "/api/import/" in p]
        assert len(import_paths) >= 1, "import router not mounted — Optional import missing?"

    def test_insight_detail_returns_breakdown(self, client):
        """GET insight detail must include V2 breakdown keys when invoice has lines."""
        # Get first available insight
        r = client.get("/api/billing/insights")
        if r.status_code != 200:
            pytest.skip("No billing insights endpoint")
        data = r.json()
        if not data.get("insights"):
            pytest.skip("No insights in DB")
        iid = data["insights"][0]["id"]
        r2 = client.get(f"/api/billing/insights/{iid}")
        assert r2.status_code == 200
        detail = r2.json()
        m = detail.get("metrics", {})
        # V2 breakdown keys must be present after on-demand recalculation
        assert m.get("expected_ttc") is not None, "expected_ttc missing"
        assert m.get("expected_fourniture_ht") is not None, "expected_fourniture_ht missing"
        assert m.get("delta_pct") is not None, "delta_pct missing"
        assert m.get("confidence") is not None, "confidence missing"


class TestOpenAPISchema:
    """Verify OpenAPI spec is valid and complete."""

    def test_openapi_json(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
        assert len(schema["paths"]) > 50  # At least 50 unique paths


class TestAPICreateChain:
    """Verify write operations: create Org + Site via onboarding API."""

    def test_onboarding_creates_org_and_site(self, isolated_client):
        r = isolated_client.post("/api/onboarding", json={
            "organisation": {"nom": "Smoke Corp", "siren": "999999999", "type_client": "bureau"},
            "sites": [{"nom": "Smoke Site", "type": "bureau", "surface_m2": 1500}],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["organisation_id"] is not None
        assert data["sites_created"] == 1

    def test_onboarding_status_reflects_creation(self, isolated_client):
        # Create
        isolated_client.post("/api/onboarding", json={
            "organisation": {"nom": "Status Corp"},
            "sites": [{"nom": "Site A", "type": "bureau"}],
        })
        # Check status
        r = isolated_client.get("/api/onboarding/status")
        assert r.status_code == 200
        data = r.json()
        assert data["has_organisation"] is True
        assert data["onboarding_complete"] is True
        assert data["total_sites"] >= 1
