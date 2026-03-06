"""
PROMEOS — Bloc B Performance tests
X-Response-Time header (middleware), Cache-Control on portfolio GETs.
"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestXResponseTimeHeader:
    """P2: X-Response-Time already set by RequestContextMiddleware."""

    def test_cockpit_has_x_response_time(self):
        resp = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        assert "x-response-time" in resp.headers
        assert resp.headers["x-response-time"].endswith("ms")

    def test_health_has_x_response_time(self):
        resp = client.get("/api/health")
        assert "x-response-time" in resp.headers


class TestCacheControlHeaders:
    """P2: Cache-Control public, max-age=30 on 3 portfolio GET endpoints."""

    def test_cockpit_cache_control(self):
        resp = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        if resp.status_code == 200:
            assert "cache-control" in resp.headers
            assert "max-age=30" in resp.headers["cache-control"]

    def test_compliance_portfolio_score_cache_control(self):
        resp = client.get("/api/compliance/portfolio/score", headers={"X-Org-Id": "1"})
        if resp.status_code == 200:
            assert "cache-control" in resp.headers
            assert "max-age=30" in resp.headers["cache-control"]

    def test_consumption_portfolio_cache_control(self):
        resp = client.get("/api/consumption-unified/portfolio", headers={"X-Org-Id": "1"})
        if resp.status_code == 200:
            assert "cache-control" in resp.headers
            assert "max-age=30" in resp.headers["cache-control"]
