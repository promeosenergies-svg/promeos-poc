"""
PROMEOS — Achat Energie V75 — Backend tests
report_pct in compute endpoint, portfolio site_nom, compute_scenarios with report.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock

_MOCK_MARKET_CTX = {
    "spot_avg_30d_eur_mwh": 60.0,
    "spot_avg_12m_eur_mwh": 55.0,
    "spot_current_eur_mwh": 62.0,
    "volatility_12m_eur_mwh": 8.0,
    "trend_30d_vs_12m_pct": 9.1,
}


def _mock_purchase():
    """Context manager that patches get_reference_price and get_market_context."""
    return (
        patch("services.purchase_service.get_reference_price", return_value=(0.10, "market")),
        patch("services.purchase_service.get_market_context", return_value=_MOCK_MARKET_CTX),
    )


# ========================================
# A. compute_scenarios accepts report_pct
# ========================================
class TestComputeScenariosReportPct:
    def test_default_report_pct_is_zero(self):
        from services.purchase_service import compute_scenarios

        p1, p2 = _mock_purchase()
        with p1, p2:
            db = MagicMock()
            scenarios = compute_scenarios(db, site_id=1, volume_kwh_an=500_000)
            reflex = next(s for s in scenarios if s["strategy"] == "reflex_solar")
            assert reflex["report_pct"] == 0.0

    def test_report_pct_passed_to_reflex(self):
        from services.purchase_service import compute_scenarios

        p1, p2 = _mock_purchase()
        with p1, p2:
            db = MagicMock()
            scenarios = compute_scenarios(db, site_id=1, volume_kwh_an=500_000, report_pct=0.15)
            reflex = next(s for s in scenarios if s["strategy"] == "reflex_solar")
            assert reflex["report_pct"] == 15.0

    def test_report_pct_affects_effort_score(self):
        from services.purchase_service import compute_scenarios

        p1, p2 = _mock_purchase()
        with p1, p2:
            db = MagicMock()
            no_report = compute_scenarios(db, site_id=1, volume_kwh_an=500_000, report_pct=0.0)
            with_report = compute_scenarios(db, site_id=1, volume_kwh_an=500_000, report_pct=0.15)
            r0 = next(s for s in no_report if s["strategy"] == "reflex_solar")
            r1 = next(s for s in with_report if s["strategy"] == "reflex_solar")
            assert r0["effort_score"] == 20
            assert r1["effort_score"] > 20

    def test_report_pct_lowers_reflex_cost(self):
        from services.purchase_service import compute_scenarios

        p1, p2 = _mock_purchase()
        with p1, p2:
            db = MagicMock()
            no_report = compute_scenarios(db, site_id=1, volume_kwh_an=500_000, report_pct=0.0)
            with_report = compute_scenarios(db, site_id=1, volume_kwh_an=500_000, report_pct=0.10)
            r0 = next(s for s in no_report if s["strategy"] == "reflex_solar")
            r1 = next(s for s in with_report if s["strategy"] == "reflex_solar")
            assert r1["total_annual_eur"] < r0["total_annual_eur"]

    def test_non_reflex_scenarios_unaffected(self):
        from services.purchase_service import compute_scenarios

        p1, p2 = _mock_purchase()
        with p1, p2:
            db = MagicMock()
            no_report = compute_scenarios(db, site_id=1, volume_kwh_an=500_000, report_pct=0.0)
            with_report = compute_scenarios(db, site_id=1, volume_kwh_an=500_000, report_pct=0.15)
            for strat in ["fixe", "indexe", "spot"]:
                s0 = next(s for s in no_report if s["strategy"] == strat)
                s1 = next(s for s in with_report if s["strategy"] == strat)
                assert s0["total_annual_eur"] == s1["total_annual_eur"]


# ========================================
# B. Compute endpoint accepts report_pct
# ========================================
class TestComputeEndpointReportPct:
    @pytest.fixture
    def db_and_client(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from models import Base, Site, Organisation, EntiteJuridique, Portefeuille, TypeSite
        from database import get_db
        from main import app
        from fastapi.testclient import TestClient

        engine = create_engine(
            "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
        session.add(org)
        session.flush()
        ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
        session.add(ej)
        session.flush()
        pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Test PF")
        session.add(pf)
        session.flush()
        site = Site(
            nom="Site A",
            type=TypeSite.BUREAU,
            adresse="1 rue Test",
            code_postal="75001",
            ville="Paris",
            surface_m2=2000,
            portefeuille_id=pf.id,
        )
        session.add(site)
        session.flush()
        session.commit()

        def _override():
            try:
                yield session
            finally:
                pass

        app.dependency_overrides[get_db] = _override
        client = TestClient(app)
        yield session, client, site, org
        app.dependency_overrides.clear()
        session.close()

    def test_compute_default_report_pct(self, db_and_client):
        _, client, site, _ = db_and_client
        resp = client.post(f"/api/purchase/compute/{site.id}")
        assert resp.status_code == 200
        reflex = next(s for s in resp.json()["scenarios"] if s["strategy"] == "reflex_solar")
        assert reflex["report_pct"] == 0.0

    def test_compute_with_report_pct(self, db_and_client):
        _, client, site, _ = db_and_client
        resp = client.post(f"/api/purchase/compute/{site.id}?report_pct=0.15")
        assert resp.status_code == 200
        reflex = next(s for s in resp.json()["scenarios"] if s["strategy"] == "reflex_solar")
        assert reflex["report_pct"] == 15.0
        assert reflex["effort_score"] > 20

    def test_compute_report_pct_validation(self, db_and_client):
        _, client, site, _ = db_and_client
        resp = client.post(f"/api/purchase/compute/{site.id}?report_pct=1.5")
        assert resp.status_code == 422  # validation error


# ========================================
# C. Portfolio includes site_nom
# ========================================
class TestPortfolioSiteNom:
    @pytest.fixture
    def db_and_client(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from models import Base, Site, Organisation, EntiteJuridique, Portefeuille, TypeSite
        from database import get_db
        from main import app
        from fastapi.testclient import TestClient

        engine = create_engine(
            "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
        session.add(org)
        session.flush()
        ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
        session.add(ej)
        session.flush()
        pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Test PF")
        session.add(pf)
        session.flush()
        site = Site(
            nom="Magasin Paris",
            type=TypeSite.BUREAU,
            adresse="1 rue Test",
            code_postal="75001",
            ville="Paris",
            surface_m2=2000,
            portefeuille_id=pf.id,
        )
        session.add(site)
        session.flush()
        session.commit()

        def _override():
            try:
                yield session
            finally:
                pass

        app.dependency_overrides[get_db] = _override
        client = TestClient(app)
        yield session, client, site, org
        app.dependency_overrides.clear()
        session.close()

    def test_portfolio_site_nom(self, db_and_client):
        _, client, site, org = db_and_client
        resp = client.post(f"/api/purchase/compute?org_id={org.id}&scope=org")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sites"]) == 1
        assert data["sites"][0]["site_nom"] == "Magasin Paris"

    def test_portfolio_site_has_reflex(self, db_and_client):
        _, client, _, org = db_and_client
        resp = client.post(f"/api/purchase/compute?org_id={org.id}&scope=org")
        assert resp.status_code == 200
        site_data = resp.json()["sites"][0]
        strategies = {s["strategy"] for s in site_data["scenarios"]}
        assert "reflex_solar" in strategies
