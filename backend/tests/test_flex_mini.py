"""
PROMEOS - Flex Mini V0 Tests
Covers: compute_flex_mini heuristics, endpoint, edge cases.
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from models import Base, Site, TypeSite, ConsumptionInsight
from database import get_db
from services.flex_mini import compute_flex_mini


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    from tests.conftest import seed_org_hierarchy

    _, _, _pf = seed_org_hierarchy(session)
    session._test_pf_id = _pf.id
    client = TestClient(app)
    yield client, session
    app.dependency_overrides.clear()
    session.close()


def _seed_site(db, site_type=TypeSite.BUREAU, nom="Test Site"):
    pf_id = getattr(db, "_test_pf_id", None)
    site = Site(nom=nom, type=site_type, latitude=48.86, longitude=2.35, portefeuille_id=pf_id)
    db.add(site)
    db.flush()
    return site


def _add_insight(db, site_id, itype, severity, metrics, loss_kwh=0, loss_eur=0):
    ci = ConsumptionInsight(
        site_id=site_id,
        type=itype,
        severity=severity,
        message=f"Test {itype}",
        metrics_json=json.dumps(metrics),
        estimated_loss_kwh=loss_kwh,
        estimated_loss_eur=loss_eur,
        recommended_actions_json="[]",
        period_start=datetime(2025, 1, 1),
        period_end=datetime(2025, 1, 31),
    )
    db.add(ci)
    db.flush()
    return ci


class TestFlexMiniService:
    def test_no_insights_low_score(self, db):
        """Without insights, score is low (only archetype bonus if any)."""
        site = _seed_site(db)
        result = compute_flex_mini(db, site.id)
        assert result["flex_potential_score"] <= 15  # archetype-only bonus is small
        assert len(result["levers"]) == 3
        # No insight-driven estimates
        assert all(l["estimate_kw"] is None for l in result["levers"])

    def test_site_not_found(self, db):
        result = compute_flex_mini(db, 9999)
        assert result["error"] == "site_not_found"
        assert result["flex_potential_score"] == 0

    def test_hvac_high_off_hours(self, db):
        site = _seed_site(db, TypeSite.BUREAU)
        _add_insight(
            db,
            site.id,
            "hors_horaires",
            "critical",
            {"off_hours_pct": 55, "avg_off_hour_kw": 20},
            loss_kwh=5000,
            loss_eur=900,
        )
        _add_insight(
            db, site.id, "base_load", "high", {"base_ratio_pct": 55, "base_load_kw": 25}, loss_kwh=3000, loss_eur=540
        )

        result = compute_flex_mini(db, site.id)
        hvac = next(l for l in result["levers"] if l["id"] == "hvac")
        assert hvac["score"] >= 70  # high off-hours + high base + bureau archetype
        assert hvac["estimate_kw"] is not None
        assert hvac["estimate_kw"] > 0
        assert "hors horaires" in hvac["justification"].lower()

    def test_irve_peaks(self, db):
        site = _seed_site(db, TypeSite.COMMERCE)
        _add_insight(
            db,
            site.id,
            "pointe",
            "high",
            {"anomaly_days_count": 8, "max_daily_kwh": 2000, "median_daily_kwh": 1000},
            loss_kwh=4000,
            loss_eur=720,
        )

        result = compute_flex_mini(db, site.id)
        irve = next(l for l in result["levers"] if l["id"] == "irve")
        assert irve["score"] >= 30
        assert "pointe" in irve["justification"].lower()

    def test_froid_archetype(self, db):
        site = _seed_site(db, TypeSite.MAGASIN, nom="Supermarche Froid")
        _add_insight(
            db, site.id, "base_load", "high", {"base_ratio_pct": 65, "base_load_kw": 30}, loss_kwh=6000, loss_eur=1080
        )

        result = compute_flex_mini(db, site.id)
        froid = next(l for l in result["levers"] if l["id"] == "froid")
        assert froid["score"] >= 50  # high base + magasin archetype
        assert "froid" in froid["justification"].lower() or "continu" in froid["justification"].lower()

    def test_score_bounded_0_100(self, db):
        site = _seed_site(db)
        # Add many insights to try to exceed 100
        for i in range(5):
            _add_insight(
                db, site.id, "hors_horaires", "critical", {"off_hours_pct": 80, "avg_off_hour_kw": 50}, loss_kwh=10000
            )
            _add_insight(db, site.id, "base_load", "critical", {"base_ratio_pct": 80, "base_load_kw": 60})
            _add_insight(
                db,
                site.id,
                "pointe",
                "critical",
                {"anomaly_days_count": 20, "max_daily_kwh": 5000, "median_daily_kwh": 1000},
            )

        result = compute_flex_mini(db, site.id)
        assert 0 <= result["flex_potential_score"] <= 100
        assert all(0 <= l["score"] <= 100 for l in result["levers"])

    def test_levers_sorted_by_score_desc(self, db):
        site = _seed_site(db, TypeSite.BUREAU)
        _add_insight(db, site.id, "hors_horaires", "critical", {"off_hours_pct": 60, "avg_off_hour_kw": 30})

        result = compute_flex_mini(db, site.id)
        scores = [l["score"] for l in result["levers"]]
        assert scores == sorted(scores, reverse=True)

    def test_inputs_used_populated(self, db):
        site = _seed_site(db, TypeSite.BUREAU)
        _add_insight(db, site.id, "hors_horaires", "medium", {"off_hours_pct": 25})

        result = compute_flex_mini(db, site.id)
        assert result["inputs_used"]["insights_count"] == 1
        assert result["inputs_used"]["site_type"] == "bureau"


class TestFlexEndpoint:
    def test_endpoint_returns_200(self, env):
        client, db = env
        site = _seed_site(db)
        r = client.get(f"/api/sites/{site.id}/flex/mini")
        assert r.status_code == 200
        data = r.json()
        assert "flex_potential_score" in data
        assert "levers" in data
        assert len(data["levers"]) == 3

    def test_endpoint_with_insights(self, env):
        client, db = env
        site = _seed_site(db, TypeSite.BUREAU)
        _add_insight(db, site.id, "hors_horaires", "high", {"off_hours_pct": 50, "avg_off_hour_kw": 15})
        r = client.get(f"/api/sites/{site.id}/flex/mini")
        assert r.status_code == 200
        data = r.json()
        assert data["flex_potential_score"] > 0
        hvac = next(l for l in data["levers"] if l["id"] == "hvac")
        assert hvac["score"] > 0
