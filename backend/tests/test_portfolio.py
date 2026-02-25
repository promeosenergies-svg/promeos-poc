"""
PROMEOS — Portfolio Consumption V1 Tests
Tests for /api/portfolio/consumption/summary and /sites endpoints.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from models import Base, Site, TypeSite, Meter, MeterReading
from models.energy_models import EnergyVector, FrequencyType
from models.consumption_insight import ConsumptionInsight
from database import get_db


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)

    # Seed 3 sites with varying data
    sites = []
    for i, name in enumerate(["Site Alpha", "Site Beta", "Site Gamma"]):
        s = Site(nom=name, type=TypeSite.BUREAU, actif=True)
        session.add(s)
        session.flush()
        sites.append(s)

        m = Meter(meter_id=f"PRM-PF-{i}", name=f"Meter {i}", site_id=s.id,
                  energy_vector=EnergyVector.ELECTRICITY)
        session.add(m)
        session.flush()

        # Site Alpha: 30 days full data, Site Beta: 10 days, Site Gamma: 0 days
        days_of_data = [30, 10, 0][i]
        for d in range(days_of_data):
            dt = datetime(2025, 3, 1) + timedelta(days=d)
            for h in range(24):
                session.add(MeterReading(
                    meter_id=m.id,
                    timestamp=dt.replace(hour=h),
                    frequency=FrequencyType.HOURLY,
                    value_kwh=10 + h * 0.5 + i * 5,
                ))
        session.flush()

    # Add a consumption insight for Site Alpha
    insight = ConsumptionInsight(
        site_id=sites[0].id,
        type="derive",
        severity="high",
        period_start=datetime(2025, 3, 1),
        period_end=datetime(2025, 3, 15),
        estimated_loss_kwh=500,
        estimated_loss_eur=90,
        message="Test drift insight",
    )
    session.add(insight)
    session.flush()

    yield client, session, sites
    app.dependency_overrides.clear()
    session.close()


class TestPortfolioSummary:
    """GET /api/portfolio/consumption/summary"""

    def test_returns_200(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        assert r.status_code == 200

    def test_schema_keys(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        data = r.json()
        assert "period" in data
        assert "totals" in data
        assert "coverage" in data
        assert "top_drift" in data
        assert "top_base_night" in data
        assert "top_peaks" in data
        assert "top_impact" in data

    def test_totals_kwh_positive(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        data = r.json()
        assert data["totals"]["kwh_total"] > 0
        assert data["totals"]["eur_total"] > 0
        assert data["totals"]["co2_total"] > 0

    def test_coverage_counts(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        data = r.json()
        cov = data["coverage"]
        assert cov["sites_total"] == 3
        assert cov["sites_with_data"] == 2  # Alpha + Beta have data, Gamma has 0

    def test_top_drift_non_empty(self, env):
        """Site Alpha has 1 insight → should appear in top_drift."""
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        data = r.json()
        assert len(data["top_drift"]) >= 1
        assert data["top_drift"][0]["diagnostics_count"] >= 1

    def test_filter_by_site_ids(self, env):
        client, _, sites = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "site_ids": str(sites[0].id),
        })
        data = r.json()
        assert data["coverage"]["sites_total"] == 1

    def test_period_dates(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-15",
        })
        data = r.json()
        assert data["period"]["from"] == "2025-03-01"
        assert data["period"]["to"] == "2025-03-15"
        assert data["period"]["days"] == 14


class TestPortfolioSites:
    """GET /api/portfolio/consumption/sites"""

    def test_returns_200(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        assert r.status_code == 200

    def test_pagination_schema(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        data = r.json()
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "rows" in data
        assert data["total"] == 3

    def test_row_fields(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        data = r.json()
        row = data["rows"][0]
        for key in ["site_id", "site_name", "kwh", "eur", "co2", "confidence",
                     "peak_kw", "base_night_pct", "diagnostics_count",
                     "impact_eur_estimated", "open_actions_count"]:
            assert key in row, f"Missing key: {key}"

    def test_sort_kwh_desc(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "sort": "kwh_desc",
        })
        data = r.json()
        rows = data["rows"]
        kwhs = [r["kwh"] for r in rows]
        assert kwhs == sorted(kwhs, reverse=True)

    def test_filter_confidence(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "confidence": "low",
        })
        data = r.json()
        for row in data["rows"]:
            assert row["confidence"] == "low"

    def test_filter_with_anomalies(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "with_anomalies": True,
        })
        data = r.json()
        for row in data["rows"]:
            assert row["diagnostics_count"] > 0

    def test_search_by_name(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "search": "Alpha",
        })
        data = r.json()
        assert data["total"] == 1
        assert data["rows"][0]["site_name"] == "Site Alpha"

    def test_pagination_limit_offset(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "limit": 2, "offset": 0,
        })
        data = r.json()
        assert len(data["rows"]) == 2
        assert data["total"] == 3

        r2 = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "limit": 2, "offset": 2,
        })
        data2 = r2.json()
        assert len(data2["rows"]) == 1


class TestPortfolioV11:
    """V1.1: impact_eur_estimated, open_actions_count, with_actions filter, impact sort."""

    def test_impact_eur_in_summary_totals(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        data = r.json()
        assert "impact_eur_total" in data["totals"]
        # Site Alpha has insight with estimated_loss_eur=90
        assert data["totals"]["impact_eur_total"] >= 90

    def test_top_impact_list(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/summary", params={
            "from": "2025-03-01", "to": "2025-03-31",
        })
        data = r.json()
        assert len(data["top_impact"]) >= 1
        assert data["top_impact"][0]["impact_eur_estimated"] >= 90

    def test_impact_eur_in_site_row(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "search": "Alpha",
        })
        data = r.json()
        row = data["rows"][0]
        assert row["impact_eur_estimated"] >= 90

    def test_sort_impact_desc(self, env):
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "sort": "impact_desc",
        })
        data = r.json()
        impacts = [r["impact_eur_estimated"] for r in data["rows"]]
        assert impacts == sorted(impacts, reverse=True)

    def test_filter_with_actions_without(self, env):
        """No actions seeded → with_actions='without' should return all sites."""
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "with_actions": "without",
        })
        data = r.json()
        assert data["total"] == 3  # All sites have 0 open actions
        for row in data["rows"]:
            assert row["open_actions_count"] == 0

    def test_filter_with_actions_with(self, env):
        """No actions seeded → with_actions='with' should return 0 sites."""
        client, _, _ = env
        r = client.get("/api/portfolio/consumption/sites", params={
            "from": "2025-03-01", "to": "2025-03-31",
            "with_actions": "with",
        })
        data = r.json()
        assert data["total"] == 0
