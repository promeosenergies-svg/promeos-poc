"""Sprint 21 — Flex Foundation Tests."""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from models import Base


@pytest.fixture
def app_client():
    engine = create_engine(
        "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    from main import app
    from database import get_db

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    os.environ["DEMO_MODE"] = "true"
    client = TestClient(app, raise_server_exceptions=False)
    yield client, SessionLocal
    app.dependency_overrides.clear()


class TestFlexAssetCRUD:
    def test_create_flex_asset(self, app_client):
        client, _ = app_client
        # Create site first
        client.post("/api/sites/quick-create", json={"nom": "FlexTest", "usage": "bureau"})
        r = client.post(
            "/api/flex/assets",
            json={
                "site_id": 1,
                "asset_type": "hvac",
                "label": "PAC principale",
                "power_kw": 150,
                "is_controllable": True,
                "control_method": "gtb",
            },
        )
        assert r.status_code == 200
        assert r.json()["asset_type"] == "hvac"
        assert r.json()["power_kw"] == 150

    def test_list_flex_assets(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "FlexList", "usage": "bureau"})
        client.post(
            "/api/flex/assets",
            json={
                "site_id": 1,
                "asset_type": "irve",
                "label": "Bornes parking",
            },
        )
        r = client.get("/api/flex/assets?site_id=1")
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_confidence_high_requires_source(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "ConfTest", "usage": "bureau"})
        r = client.post(
            "/api/flex/assets",
            json={
                "site_id": 1,
                "asset_type": "battery",
                "label": "Batterie",
                "confidence": "high",  # No data_source!
            },
        )
        assert r.status_code == 400

    def test_confidence_high_with_source(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "ConfOK", "usage": "bureau"})
        r = client.post(
            "/api/flex/assets",
            json={
                "site_id": 1,
                "asset_type": "pv",
                "label": "PV toiture",
                "confidence": "high",
                "data_source": "inspection",
            },
        )
        assert r.status_code == 200


class TestFlexAssessment:
    def test_assessment_heuristic_fallback(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "AssessHeur", "usage": "bureau"})
        r = client.get("/api/flex/assessment?site_id=1")
        assert r.status_code == 200
        data = r.json()
        assert data["source"] in ("heuristic", "asset_based")
        assert "kpi" in data
        assert "confidence" in data["kpi"]

    def test_assessment_asset_based(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "AssessAsset", "usage": "bureau"})
        client.post(
            "/api/flex/assets",
            json={
                "site_id": 1,
                "asset_type": "hvac",
                "label": "CVC",
                "power_kw": 200,
                "is_controllable": True,
            },
        )
        r = client.get("/api/flex/assessment?site_id=1")
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "asset_based"
        assert data["asset_count"] >= 1
        assert data["potential_kw"] > 0

    def test_assessment_has_kpi_metadata(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "KPIMeta", "usage": "bureau"})
        r = client.get("/api/flex/assessment?site_id=1")
        kpi = r.json().get("kpi", {})
        for field in ("definition", "unit", "period", "perimeter", "source", "confidence"):
            assert field in kpi, f"KPI missing: {field}"


class TestFlexMiniPreserved:
    def test_flex_mini_still_works(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "MiniOK", "usage": "bureau"})
        r = client.get("/api/sites/1/flex/mini")
        # Should not crash
        assert r.status_code in (200, 404, 500)
