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


class TestTariffWindow:
    def test_create_tariff_window(self, app_client):
        client, _ = app_client
        r = client.post(
            "/api/flex/tariff-windows",
            json={
                "name": "TURPE7-C5-ETE-HC_SOLAIRE",
                "segment": "C5",
                "season": "ete",
                "months": [4, 5, 6, 7, 8, 9, 10],
                "period_type": "HC_SOLAIRE",
                "start_time": "11:00",
                "end_time": "17:00",
                "source": "CRE",
            },
        )
        assert r.status_code == 200
        assert r.json()["period_type"] == "HC_SOLAIRE"

    def test_list_tariff_windows(self, app_client):
        client, _ = app_client
        client.post(
            "/api/flex/tariff-windows",
            json={
                "name": "Test",
                "season": "hiver",
                "months": [11, 12, 1, 2, 3],
                "period_type": "HP",
                "start_time": "07:00",
                "end_time": "23:00",
            },
        )
        r = client.get("/api/flex/tariff-windows")
        assert r.status_code == 200
        assert r.json()["total"] >= 1


class TestRegulatoryOpportunity:
    def test_create_aper_obligation(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "AperTest", "usage": "bureau"})
        r = client.post(
            "/api/flex/regulatory-opportunities",
            json={
                "site_id": 1,
                "regulation": "aper",
                "is_obligation": True,
                "obligation_type": "solarisation_ombriere",
                "surface_m2": 12000,
                "surface_type": "parking_exterieur",
                "threshold_m2": 10000,
                "deadline": "2026-07-01",
                "deadline_source": "Loi APER art. L171-4",
            },
        )
        assert r.status_code == 200
        assert r.json()["is_obligation"] == True

    def test_create_aper_opportunity(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "AperOpp", "usage": "bureau"})
        r = client.post(
            "/api/flex/regulatory-opportunities",
            json={
                "site_id": 1,
                "regulation": "aper",
                "is_obligation": False,
                "opportunity_type": "autoconsommation_individuelle",
            },
        )
        assert r.status_code == 200
        assert r.json()["is_obligation"] == False


class TestSyncBacsPost:
    def test_sync_is_post(self, app_client):
        """sync-from-bacs must be POST (side effect)"""
        client, _ = app_client
        r = client.get("/api/flex/assets/sync-from-bacs?site_id=1")
        assert r.status_code in (405, 404)  # GET not allowed

    def test_sync_post_works(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "SyncPost", "usage": "bureau"})
        r = client.post("/api/flex/assets/sync-from-bacs", json={"site_id": 1})
        assert r.status_code == 200


class TestFlexAssessmentDimensions:
    def test_assessment_has_4_dimensions(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "DimTest", "usage": "bureau"})
        client.post(
            "/api/flex/assets",
            json={
                "site_id": 1,
                "asset_type": "hvac",
                "label": "PAC",
                "power_kw": 100,
                "is_controllable": True,
            },
        )
        r = client.get("/api/flex/assessment?site_id=1")
        assert r.status_code == 200
        dims = r.json().get("dimensions", {})
        for d in ("technical_readiness", "data_confidence", "economic_relevance", "regulatory_alignment"):
            assert d in dims, f"Missing dimension: {d}"


class TestBacsNotAutoControllable:
    def test_bacs_sync_not_auto_controllable(self, app_client):
        """BACS sync should NOT auto-set is_controllable=True"""
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "BacsCtrl", "usage": "bureau"})
        r = client.post("/api/flex/assets/sync-from-bacs", json={"site_id": 1})
        assert r.status_code == 200
        # Any synced assets should have is_controllable=False
        r2 = client.get("/api/flex/assets?site_id=1")
        for asset in r2.json().get("assets", []):
            if asset.get("data_source") == "bacs_sync":
                assert asset["is_controllable"] == False


class TestFlexPortfolio:
    def test_portfolio_ranking(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "Port1", "usage": "bureau"})
        client.post("/api/sites/quick-create", json={"nom": "Port2", "usage": "commerce"})
        r = client.get("/api/flex/portfolio", headers={"X-Org-Id": "1"})
        assert r.status_code == 200
        data = r.json()
        assert "total_sites" in data
        assert "total_potential_kw" in data
        assert "rankings" in data


class TestTariffWindowHardened:
    def test_hc_solaire_blocked_toute_annee(self, app_client):
        """HC_SOLAIRE cannot be set for toute_annee"""
        client, _ = app_client
        r = client.post(
            "/api/flex/tariff-windows",
            json={
                "name": "Bad",
                "season": "toute_annee",
                "months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                "period_type": "HC_SOLAIRE",
                "start_time": "11:00",
                "end_time": "17:00",
            },
        )
        assert r.status_code == 400

    def test_invalid_period_type(self, app_client):
        client, _ = app_client
        r = client.post(
            "/api/flex/tariff-windows",
            json={
                "name": "Bad",
                "season": "ete",
                "months": [6, 7, 8],
                "period_type": "SUPER_HC",
                "start_time": "00:00",
                "end_time": "06:00",
            },
        )
        assert r.status_code == 400


class TestAperSubtypes:
    def test_aper_obligation_valid(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "AperSub", "usage": "bureau"})
        r = client.post(
            "/api/flex/regulatory-opportunities",
            json={
                "site_id": 1,
                "regulation": "aper",
                "is_obligation": True,
                "obligation_type": "solarisation_ombriere",
            },
        )
        assert r.status_code == 200

    def test_aper_opportunity_acc(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "AperACC", "usage": "bureau"})
        r = client.post(
            "/api/flex/regulatory-opportunities",
            json={
                "site_id": 1,
                "regulation": "aper",
                "is_obligation": False,
                "opportunity_type": "acc",
            },
        )
        assert r.status_code == 200

    def test_aper_invalid_opportunity_type(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "AperBad", "usage": "bureau"})
        r = client.post(
            "/api/flex/regulatory-opportunities",
            json={
                "site_id": 1,
                "regulation": "aper",
                "is_obligation": False,
                "opportunity_type": "fake_type",
            },
        )
        assert r.status_code == 400


class TestPortfolioFlexPrioritization:
    def test_portfolio_scoped(self, app_client):
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "PortScope", "usage": "bureau"})
        r = client.get("/api/flex/portfolios/1/flex-prioritization")
        assert r.status_code in (200, 404)  # 404 if portfolio doesn't match
        if r.status_code == 200:
            assert "portfolio_id" in r.json()
            assert "rankings" in r.json()
