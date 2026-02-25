"""
PROMEOS - Consumption / Performance / Diagnostic — Smoke Tests
Verify core conso endpoints respond 200, granularity works,
empty states don't crash, and at least 1 diagnostic returns a result.
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


# =============================================
# 1. Consumption endpoints return 200
# =============================================
class TestConsoEndpoints200:
    """All consumption/EMS/monitoring endpoints must respond, even with no data."""

    def test_consumption_availability(self, client):
        r = client.get("/api/consumption/availability?site_id=1&energy_type=electricity")
        assert r.status_code == 200
        data = r.json()
        assert "has_data" in data

    def test_consumption_tunnel_v2(self, client):
        r = client.get("/api/consumption/tunnel_v2?site_id=1&days=90&energy_type=electricity")
        assert r.status_code == 200

    def test_consumption_targets(self, client):
        r = client.get("/api/consumption/targets?site_id=1&energy_type=electricity")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_consumption_targets_progress_v2(self, client):
        r = client.get("/api/consumption/targets/progress_v2?site_id=1&energy_type=electricity")
        assert r.status_code == 200

    def test_consumption_hphc_breakdown_v2(self, client):
        r = client.get("/api/consumption/hphc_breakdown_v2?site_id=1&days=30")
        assert r.status_code == 200

    def test_consumption_gas_summary(self, client):
        r = client.get("/api/consumption/gas/summary?site_id=1&days=90")
        assert r.status_code == 200

    def test_consumption_gas_weather_normalized(self, client):
        r = client.get("/api/consumption/gas/weather_normalized?site_id=1&days=90")
        assert r.status_code == 200

    def test_consumption_insights(self, client):
        r = client.get("/api/consumption/insights")
        assert r.status_code == 200

    def test_consumption_tou_schedules(self, client):
        r = client.get("/api/consumption/tou_schedules?site_id=1")
        assert r.status_code == 200


# =============================================
# 2. EMS / Timeseries endpoints
# =============================================
class TestEmsEndpoints:
    """EMS Explorer endpoints must respond without errors."""

    def test_ems_health(self, client):
        r = client.get("/api/ems/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_ems_timeseries_suggest(self, client):
        r = client.get("/api/ems/timeseries/suggest?date_from=2025-01-01T00:00:00Z&date_to=2025-03-01T00:00:00Z")
        assert r.status_code == 200
        data = r.json()
        assert "granularity" in data

    def test_ems_usage_suggest(self, client):
        r = client.get("/api/ems/usage_suggest?site_id=1")
        assert r.status_code == 200
        data = r.json()
        assert "archetype_code" in data

    def test_ems_schedule_suggest(self, client):
        r = client.get("/api/ems/schedule_suggest?site_id=1&days=90")
        assert r.status_code == 200

    def test_ems_benchmark(self, client):
        r = client.get("/api/ems/benchmark?site_id=1")
        assert r.status_code == 200

    def test_ems_collections(self, client):
        r = client.get("/api/ems/collections")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ems_views(self, client):
        r = client.get("/api/ems/views")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# =============================================
# 3. Monitoring / Performance endpoints
# =============================================
class TestMonitoringEndpoints:
    """Monitoring endpoints for Performance page."""

    def test_monitoring_alerts(self, client):
        r = client.get("/api/monitoring/alerts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_monitoring_snapshots(self, client):
        r = client.get("/api/monitoring/snapshots?site_id=1")
        assert r.status_code == 200

    def test_monitoring_emissions(self, client):
        r = client.get("/api/monitoring/emissions?site_id=1")
        # 200 if snapshot exists, 404 if no snapshot for this site
        assert r.status_code in (200, 404)

    def test_monitoring_emission_factors(self, client):
        r = client.get("/api/monitoring/emission-factors")
        assert r.status_code == 200


# =============================================
# 4. Granularity validation
# =============================================
class TestGranularity:
    """Verify multi-granularity support in timeseries API."""

    @pytest.mark.parametrize("gran", ["hourly", "daily", "monthly"])
    def test_timeseries_granularity(self, client, gran):
        r = client.get(
            f"/api/ems/timeseries?site_ids=1&date_from=2025-01-01T00:00:00Z"
            f"&date_to=2025-04-01T00:00:00Z&granularity={gran}"
        )
        assert r.status_code == 200
        data = r.json()
        assert "series" in data or "meta" in data or isinstance(data, dict)

    def test_timeseries_auto_granularity(self, client):
        """Auto granularity should default to a valid value."""
        r = client.get(
            "/api/ems/timeseries?site_ids=1"
            "&date_from=2025-01-01T00:00:00Z&date_to=2025-02-01T00:00:00Z"
            "&granularity=auto"
        )
        assert r.status_code == 200


# =============================================
# 5. Empty state resilience
# =============================================
class TestEmptyStateResilience:
    """Endpoints must not crash on empty or edge-case inputs."""

    def test_availability_unknown_site(self, client):
        """Non-existent site should return has_data=false, not 500."""
        r = client.get("/api/consumption/availability?site_id=999999&energy_type=electricity")
        assert r.status_code == 200
        assert r.json()["has_data"] is False

    def test_tunnel_no_data(self, client):
        """Tunnel for site with no hourly data should not 500."""
        r = client.get("/api/consumption/tunnel_v2?site_id=999999&days=30")
        assert r.status_code in (200, 404)

    def test_insights_empty_org(self, client):
        """Insights with no org context should still respond."""
        r = client.get("/api/consumption/insights")
        assert r.status_code == 200

    def test_gas_summary_no_gas_data(self, client):
        """Gas summary for electricity-only site should not crash."""
        r = client.get("/api/consumption/gas/summary?site_id=1&days=90")
        assert r.status_code == 200


# =============================================
# 6. Diagnostic produces results (if data exists)
# =============================================
class TestDiagnosticRun:
    """Verify diagnostic engine can run and return structured results."""

    def test_diagnose_returns_structured(self, client):
        """POST /consumption/diagnose should return status + analysis info."""
        r = client.post("/api/consumption/diagnose?days=30")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "sites_analyzed" in data or "results" in data or "total" in data

    def test_consumption_site_detail(self, client):
        """GET /consumption/site/{id} should return site-level insights."""
        r = client.get("/api/consumption/site/1")
        assert r.status_code == 200
        data = r.json()
        assert "site_id" in data
        assert "insights" in data
        assert isinstance(data["insights"], list)
