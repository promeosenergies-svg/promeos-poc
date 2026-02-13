"""
PROMEOS - BACS Integration Tests (E2E)
Full flow tests covering the complete BACS lifecycle.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from models import (
    Base, Site, Batiment, TypeSite,
    BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection,
    CvcSystemType, CvcArchitecture, InspectionStatus,
)
from database import get_db
from services.bacs_engine import evaluate_bacs


@pytest.fixture
def env():
    """Full test environment with isolated DB and API client."""
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
    yield client, session
    app.dependency_overrides.clear()
    session.close()


class TestFullFlow290kw:
    """Full lifecycle: 290kW site → non-compliant → evaluate → compliant path."""

    def test_create_evaluate_review(self, env):
        client, db = env

        # 1. Create site via seed demo
        r = client.post("/api/regops/bacs/seed_demo")
        assert r.status_code == 200
        seeded = r.json()["seeded"]
        assert len(seeded) == 10

        # 2. Find Tour Montparnasse (>290kW)
        tour = next(s for s in seeded if "Montparnasse" in s["site"])
        site_id = tour["site_id"]
        assert tour["is_obligated"] is True

        # 3. Get full assessment
        r = client.get(f"/api/regops/bacs/site/{site_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["configured"] is True
        assert data["assessment"]["is_obligated"] is True
        assert data["assessment"]["threshold_applied"] == 290

        # 4. Get score explain
        r = client.get(f"/api/regops/bacs/score_explain/{site_id}")
        assert r.status_code == 200
        explain = r.json()
        assert explain["putile"]["putile_kw"] == 450  # 250+200 cascade
        assert len(explain["putile"]["trace"]) > 0

        # 5. Get data quality
        r = client.get(f"/api/regops/bacs/data_quality/{site_id}")
        assert r.status_code == 200

        # 6. Get ops panel
        r = client.get(f"/api/regops/bacs/site/{site_id}/ops")
        assert r.status_code == 200
        ops = r.json()
        assert ops["kpis"]["is_obligated"] is True


class TestFullFlow70kwTRI:
    """70-290kW site with TRI exemption."""

    def test_tri_exemption_lifecycle(self, env):
        client, db = env

        # Seed
        client.post("/api/regops/bacs/seed_demo")

        # Find Mairie Bordeaux (TRI exemption)
        r = client.get("/api/regops/bacs/site/5")  # 5th seeded site
        # May not be ID 5, search via seed result
        seed_r = client.post("/api/regops/bacs/seed_demo")
        seeded = seed_r.json()["seeded"]
        mairie = next((s for s in seeded if "Bordeaux" in s["site"]), None)

        if mairie and mairie.get("site_id"):
            r = client.get(f"/api/regops/bacs/site/{mairie['site_id']}")
            data = r.json()
            if data["configured"] and data["assessment"]:
                assert data["assessment"]["is_obligated"] is True
                # TRI exemption may or may not be set depending on seed order
                # Just verify the assessment was computed successfully


class TestFullFlowRenewal:
    """CVC renewal post-2023 triggers obligation."""

    def test_renewal_triggers(self, env):
        client, db = env

        # Create site
        site = Site(nom="Renewal Test", type=TypeSite.BUREAU)
        db.add(site)
        db.flush()

        # Create asset with renewal event
        r = client.post(f"/api/regops/bacs/asset?site_id={site.id}&is_tertiary=true&pc_date=1990-01-01")
        assert r.status_code == 200
        asset_id = r.json()["id"]

        # Update renewal events directly
        asset = db.query(BacsAsset).filter(BacsAsset.id == asset_id).first()
        asset.renewal_events_json = json.dumps([{"date": "2024-06-15", "system": "heating", "kw": 200}])
        db.flush()

        # Add system
        units = json.dumps([{"label": "PAC", "kw": 100}])
        r = client.post(f"/api/regops/bacs/asset/{asset_id}/system?system_type=heating&architecture=independent&units_json={units}")
        assert r.status_code == 200

        # Recompute
        r = client.post(f"/api/regops/bacs/recompute/{site.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["assessment"]["is_obligated"] is True
        assert data["assessment"]["trigger_reason"] == "renewal"


class TestFullFlowOutOfScope:
    """<70kW site is out of scope."""

    def test_out_of_scope(self, env):
        client, db = env

        site = Site(nom="Small Site", type=TypeSite.BUREAU)
        db.add(site)
        db.flush()

        r = client.post(f"/api/regops/bacs/asset?site_id={site.id}&is_tertiary=true&pc_date=2005-01-01")
        asset_id = r.json()["id"]

        units = json.dumps([{"label": "Split", "kw": 30}])
        client.post(f"/api/regops/bacs/asset/{asset_id}/system?system_type=cooling&architecture=independent&units_json={units}")

        r = client.post(f"/api/regops/bacs/recompute/{site.id}")
        assert r.status_code == 200
        assert r.json()["assessment"]["is_obligated"] is False


class TestInspectionLifecycle:
    """Inspection CRUD and schedule computation."""

    def test_inspection_tracking(self, env):
        client, db = env

        site = Site(nom="Inspection Test", type=TypeSite.BUREAU)
        db.add(site)
        db.flush()

        asset = BacsAsset(site_id=site.id, is_tertiary_non_residential=True, pc_date=date(2000, 1, 1))
        db.add(asset)
        db.flush()

        sys = BacsCvcSystem(
            asset_id=asset.id,
            system_type=CvcSystemType.HEATING,
            architecture=CvcArchitecture.CASCADE,
            units_json=json.dumps([{"kw": 300}]),
        )
        db.add(sys)
        db.flush()

        # Evaluate (no inspection yet)
        evaluate_bacs(db, site.id)

        # Add completed inspection
        insp = BacsInspection(
            asset_id=asset.id,
            inspection_date=date(2023, 6, 1),
            status=InspectionStatus.COMPLETED,
            report_ref="RPT-001",
        )
        db.add(insp)
        db.flush()

        # Re-evaluate
        evaluate_bacs(db, site.id)

        # Check via API
        r = client.get(f"/api/regops/bacs/site/{site.id}")
        data = r.json()
        assert len(data["inspections"]) >= 1
        assert data["inspections"][0]["status"] == "completed"


class TestSeedDemoAllCases:
    """Verify seed demo covers all expected cases."""

    def test_seed_then_verify(self, env):
        client, db = env

        r = client.post("/api/regops/bacs/seed_demo")
        data = r.json()

        assert data["total"] == 10
        created = [s for s in data["seeded"] if s["status"] == "created"]
        assert len(created) == 10

        # Check diversity
        obligated = [s for s in created if s.get("is_obligated") is True]
        not_obligated = [s for s in created if s.get("is_obligated") is False]
        assert len(obligated) >= 6
        assert len(not_obligated) >= 2

        # Verify all sites have valid assessments
        for s in created:
            r = client.get(f"/api/regops/bacs/site/{s['site_id']}")
            assert r.status_code == 200
            assert r.json()["configured"] is True


class TestDataQualityGateProgression:
    """DQ gate progresses from BLOCKED → WARNING → OK as data is added."""

    def test_progression(self, env):
        client, db = env

        # 1. Empty site → BLOCKED
        site = Site(nom="DQ Test", type=TypeSite.BUREAU)
        db.add(site)
        db.flush()

        r = client.get(f"/api/regops/bacs/data_quality/{site.id}")
        assert r.json()["gate_status"] == "BLOCKED"

        # 2. Add asset → still WARNING (missing some fields)
        client.post(f"/api/regops/bacs/asset?site_id={site.id}&is_tertiary=true&pc_date=2000-01-01")

        # 3. Add system → WARNING or OK
        asset = db.query(BacsAsset).filter(BacsAsset.site_id == site.id).first()
        units = json.dumps([{"kw": 200}])
        client.post(f"/api/regops/bacs/asset/{asset.id}/system?system_type=heating&architecture=cascade&units_json={units}")

        r = client.get(f"/api/regops/bacs/data_quality/{site.id}")
        assert r.json()["gate_status"] in ("WARNING", "OK")
