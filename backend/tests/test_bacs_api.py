"""
PROMEOS - Tests for BACS API endpoints
15+ integration tests covering full API surface.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base, Site, TypeSite, BacsAsset, BacsCvcSystem, CvcSystemType, CvcArchitecture
from database import get_db


@pytest.fixture
def client():
    """Client with isolated in-memory DB."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app), session
    app.dependency_overrides.clear()
    session.close()


def _seed_site(session, name="Test Site", cvc_kw=300, arch=CvcArchitecture.CASCADE):
    """Helper to create a site with BacsAsset and one CVC system."""
    from datetime import date
    site = Site(nom=name, type=TypeSite.BUREAU, surface_m2=2000, actif=True)
    session.add(site)
    session.flush()
    asset = BacsAsset(
        site_id=site.id,
        is_tertiary_non_residential=True,
        pc_date=date(2000, 1, 1),
    )
    session.add(asset)
    session.flush()
    sys = BacsCvcSystem(
        asset_id=asset.id,
        system_type=CvcSystemType.HEATING,
        architecture=arch,
        units_json=json.dumps([{"label": "PAC", "kw": cvc_kw}]),
    )
    session.add(sys)
    session.flush()
    return site, asset, sys


class TestGetAssessment:

    def test_full_290kw(self, client):
        c, session = client
        site, asset, _ = _seed_site(session, cvc_kw=450)
        # Recompute first
        r = c.post(f"/api/regops/bacs/recompute/{site.id}")
        assert r.status_code == 200
        # Get assessment
        r = c.get(f"/api/regops/bacs/site/{site.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["configured"] is True
        assert data["assessment"]["is_obligated"] is True
        assert data["assessment"]["threshold_applied"] == 290

    def test_out_of_scope(self, client):
        c, session = client
        site, _, _ = _seed_site(session, cvc_kw=40)
        c.post(f"/api/regops/bacs/recompute/{site.id}")
        r = c.get(f"/api/regops/bacs/site/{site.id}")
        data = r.json()
        assert data["assessment"]["is_obligated"] is False

    def test_not_configured(self, client):
        c, session = client
        site = Site(nom="Empty", type=TypeSite.BUREAU)
        session.add(site)
        session.flush()
        r = c.get(f"/api/regops/bacs/site/{site.id}")
        assert r.status_code == 200
        assert r.json()["configured"] is False

    def test_site_not_found(self, client):
        c, _ = client
        r = c.get("/api/regops/bacs/site/99999")
        assert r.status_code == 404


class TestRecompute:

    def test_recompute_updates(self, client):
        c, session = client
        site, _, _ = _seed_site(session, cvc_kw=150)
        r = c.post(f"/api/regops/bacs/recompute/{site.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["assessment"]["is_obligated"] is True
        assert data["assessment"]["threshold_applied"] == 70


class TestScoreExplain:

    def test_shows_putile_trace(self, client):
        c, session = client
        site, _, _ = _seed_site(session, cvc_kw=300)
        c.post(f"/api/regops/bacs/recompute/{site.id}")
        r = c.get(f"/api/regops/bacs/score_explain/{site.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["putile"]["putile_kw"] == 300
        assert len(data["putile"]["trace"]) > 0


class TestDataQuality:

    def test_blocked_no_asset(self, client):
        c, session = client
        site = Site(nom="NoAsset", type=TypeSite.BUREAU)
        session.add(site)
        session.flush()
        r = c.get(f"/api/regops/bacs/data_quality/{site.id}")
        assert r.status_code == 200
        assert r.json()["gate_status"] == "BLOCKED"

    def test_warning_with_asset(self, client):
        c, session = client
        site, _, _ = _seed_site(session, cvc_kw=200)
        r = c.get(f"/api/regops/bacs/data_quality/{site.id}")
        data = r.json()
        assert data["gate_status"] in ("WARNING", "OK")


class TestAssetCrud:

    def test_create_asset(self, client):
        c, session = client
        site = Site(nom="New", type=TypeSite.BUREAU)
        session.add(site)
        session.flush()
        r = c.post(f"/api/regops/bacs/asset?site_id={site.id}&is_tertiary=true&pc_date=2005-01-01")
        assert r.status_code == 200
        assert r.json()["site_id"] == site.id
        assert r.json()["pc_date"] == "2005-01-01"

    def test_create_duplicate_409(self, client):
        c, session = client
        site, _, _ = _seed_site(session)
        r = c.post(f"/api/regops/bacs/asset?site_id={site.id}")
        assert r.status_code == 409

    def test_add_cvc_system(self, client):
        c, session = client
        site, asset, _ = _seed_site(session)
        units = json.dumps([{"label": "New Unit", "kw": 100}])
        r = c.post(
            f"/api/regops/bacs/asset/{asset.id}/system"
            f"?system_type=cooling&architecture=independent&units_json={units}"
        )
        assert r.status_code == 200
        assert r.json()["system_type"] == "cooling"

    def test_update_cvc_system(self, client):
        c, session = client
        site, _, sys = _seed_site(session)
        new_units = json.dumps([{"label": "Updated", "kw": 500}])
        r = c.put(f"/api/regops/bacs/system/{sys.id}?units_json={new_units}")
        assert r.status_code == 200

    def test_delete_cvc_system(self, client):
        c, session = client
        site, _, sys = _seed_site(session)
        r = c.delete(f"/api/regops/bacs/system/{sys.id}")
        assert r.status_code == 200
        assert r.json()["deleted"] == sys.id


class TestSeedDemo:

    def test_seed_creates_assets(self, client):
        c, session = client
        r = c.post("/api/regops/bacs/seed_demo")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 10
        created = [s for s in data["seeded"] if s["status"] == "created"]
        assert len(created) == 10

    def test_seed_idempotent(self, client):
        c, session = client
        c.post("/api/regops/bacs/seed_demo")
        r = c.post("/api/regops/bacs/seed_demo")
        data = r.json()
        skipped = [s for s in data["seeded"] if s["status"] == "skipped"]
        assert len(skipped) == 10

    def test_seed_covers_all_cases(self, client):
        c, session = client
        r = c.post("/api/regops/bacs/seed_demo")
        data = r.json()
        statuses = {s.get("is_obligated") for s in data["seeded"] if s["status"] == "created"}
        assert True in statuses
        assert False in statuses
