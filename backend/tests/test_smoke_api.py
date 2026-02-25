"""
PROMEOS - Smoke Tests: OpenAPI schema + router mount verification.
Fast (<2s), no running server needed (uses TestClient).
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


class TestOpenAPISmoke:
    """Verify OpenAPI spec is valid and all critical routers are mounted."""

    def test_openapi_returns_200_with_paths(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
        assert len(schema["paths"]) > 0

    def test_tertiaire_router_mounted(self, client):
        schema = client.get("/openapi.json").json()
        paths = list(schema["paths"].keys())
        tertiaire_paths = [p for p in paths if p.startswith("/api/tertiaire")]
        assert len(tertiaire_paths) > 0, (
            "Router tertiaire not mounted — no paths starting with /api/tertiaire "
            f"(total paths: {len(paths)})"
        )

    def test_billing_router_mounted(self, client):
        schema = client.get("/openapi.json").json()
        paths = list(schema["paths"].keys())
        billing_paths = [p for p in paths if p.startswith("/api/billing")]
        assert len(billing_paths) > 0, "Router billing not mounted"

    def test_docs_returns_200_or_redirect(self, client):
        r = client.get("/docs")
        assert r.status_code in (200, 307)


class TestTertiaireEndpoints:
    """Verify tertiaire endpoints respond (not 404/405)."""

    def test_tertiaire_dashboard(self, client):
        r = client.get("/api/tertiaire/dashboard")
        assert r.status_code != 404, "Tertiaire dashboard endpoint not found (404)"
        assert r.status_code != 405, "Tertiaire dashboard method not allowed (405)"

    def test_tertiaire_efa_list(self, client):
        r = client.get("/api/tertiaire/efa")
        assert r.status_code != 404, "Tertiaire EFA list endpoint not found (404)"
        assert r.status_code != 405, "Tertiaire EFA list method not allowed (405)"

    def test_tertiaire_catalog(self, client):
        r = client.get("/api/tertiaire/catalog")
        assert r.status_code != 404, "Tertiaire catalog endpoint not found (404)"
        assert r.status_code != 405, "Tertiaire catalog method not allowed (405)"


class TestBillingEndpoints:
    """Verify billing endpoints respond (not 404/405)."""

    def test_billing_insights(self, client):
        r = client.get("/api/billing/insights")
        assert r.status_code != 404, "Billing insights endpoint not found (404)"
        assert r.status_code != 405, "Billing insights method not allowed (405)"

    def test_billing_rules(self, client):
        r = client.get("/api/billing/rules")
        assert r.status_code != 404, "Billing rules endpoint not found (404)"
        assert r.status_code != 405, "Billing rules method not allowed (405)"
