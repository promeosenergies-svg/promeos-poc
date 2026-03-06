"""
PROMEOS - Tests Sprint 8: Achat Energie V1
Models, service (estimate, scenarios, recommend), endpoints, seed demo.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from unittest.mock import patch
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    EnergyContract,
    EnergyInvoice,
    SiteOperatingSchedule,
    PurchaseAssumptionSet,
    PurchasePreference,
    PurchaseScenarioResult,
    PurchaseStrategy,
    PurchaseRecoStatus,
    BillingEnergyType,
    BillingInvoiceStatus,
    TypeSite,
)
from database import get_db
from main import app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org_site(db, surface=2000):
    """Helper: create org + site."""
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Test PF")
    db.add(pf)
    db.flush()
    site = Site(
        nom="Site A",
        type=TypeSite.BUREAU,
        adresse="1 rue Test",
        code_postal="75001",
        ville="Paris",
        surface_m2=surface,
        portefeuille_id=pf.id,
    )
    db.add(site)
    db.flush()
    return org, site


def _create_two_sites(db):
    """Helper: create org + 2 sites."""
    org, site_a = _create_org_site(db)
    site_b = Site(
        nom="Site B",
        type=TypeSite.ENTREPOT,
        adresse="2 rue Test",
        code_postal="69001",
        ville="Lyon",
        surface_m2=5000,
        portefeuille_id=site_a.portefeuille_id,
    )
    db.add(site_b)
    db.flush()
    return org, site_a, site_b


# ========================================
# Model tests
# ========================================


class TestModels:
    def test_create_assumption_set(self, db_session):
        _, site = _create_org_site(db_session)
        assumption = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=500000,
        )
        db_session.add(assumption)
        db_session.commit()
        assert assumption.id is not None
        assert assumption.profile_factor == 1.0
        assert assumption.horizon_months == 24

    def test_create_preference(self, db_session):
        pref = PurchasePreference(
            org_id=1,
            risk_tolerance="low",
            budget_priority=0.3,
        )
        db_session.add(pref)
        db_session.commit()
        assert pref.id is not None
        assert pref.risk_tolerance == "low"
        assert pref.green_preference is False

    def test_create_scenario_result(self, db_session):
        _, site = _create_org_site(db_session)
        assumption = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=500000,
        )
        db_session.add(assumption)
        db_session.flush()
        result = PurchaseScenarioResult(
            assumption_set_id=assumption.id,
            strategy=PurchaseStrategy.FIXE,
            price_eur_per_kwh=0.189,
            total_annual_eur=94500,
            risk_score=15,
        )
        db_session.add(result)
        db_session.commit()
        assert result.id is not None
        assert result.reco_status == PurchaseRecoStatus.DRAFT
        assert result.is_recommended is False


# ========================================
# Service tests
# ========================================


class TestPurchaseService:
    def test_estimate_from_invoices(self, db_session):
        from services.purchase_service import estimate_consumption

        _, site = _create_org_site(db_session)
        # Create an invoice within last 12 months
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            price_ref_eur_per_kwh=0.18,
        )
        db_session.add(contract)
        db_session.flush()
        inv = EnergyInvoice(
            site_id=site.id,
            contract_id=contract.id,
            invoice_number="TEST-001",
            period_start=date.today() - timedelta(days=60),
            period_end=date.today() - timedelta(days=30),
            total_eur=1800,
            energy_kwh=10000,
            status=BillingInvoiceStatus.IMPORTED,
        )
        db_session.add(inv)
        db_session.commit()

        result = estimate_consumption(db_session, site.id)
        assert result["source"] == "invoices"
        assert result["volume_kwh_an"] > 0
        assert result["months_covered"] >= 1

    def test_estimate_fallback(self, db_session):
        from services.purchase_service import estimate_consumption

        _, site = _create_org_site(db_session)
        result = estimate_consumption(db_session, site.id)
        assert result["source"] == "default"
        assert result["volume_kwh_an"] == 500000
        assert result["months_covered"] == 0

    def test_compute_scenarios_4_strategies(self, db_session):
        from services.purchase_service import compute_scenarios

        _, site = _create_org_site(db_session)
        scenarios = compute_scenarios(db_session, site.id, volume_kwh_an=500000)
        assert len(scenarios) == 4
        strategies = {s["strategy"] for s in scenarios}
        assert strategies == {"fixe", "indexe", "spot", "reflex_solar"}
        # Fixe should have lowest risk
        fixe = next(s for s in scenarios if s["strategy"] == "fixe")
        spot = next(s for s in scenarios if s["strategy"] == "spot")
        assert fixe["risk_score"] < spot["risk_score"]
        # All have savings computed
        for s in scenarios:
            assert "savings_vs_current_pct" in s

    def test_recommend_low_risk(self, db_session):
        from services.purchase_service import recommend_scenario

        scenarios = [
            {
                "strategy": "fixe",
                "risk_score": 15,
                "savings_vs_current_pct": -5,
                "total_annual_eur": 105000,
                "price_eur_per_kwh": 0.189,
            },
            {
                "strategy": "indexe",
                "risk_score": 45,
                "savings_vs_current_pct": 5,
                "total_annual_eur": 95000,
                "price_eur_per_kwh": 0.171,
            },
            {
                "strategy": "spot",
                "risk_score": 75,
                "savings_vs_current_pct": 12,
                "total_annual_eur": 88000,
                "price_eur_per_kwh": 0.1584,
            },
        ]
        result = recommend_scenario(scenarios, risk_tolerance="low", budget_priority=0.5)
        # Spot should be excluded (risk > 50)
        recommended = [s for s in result if s.get("is_recommended")]
        assert len(recommended) == 1
        assert recommended[0]["strategy"] != "spot"


# ========================================
# API tests
# ========================================


class TestPurchaseAPI:
    def test_estimate_endpoint(self, client, db_session):
        _, site = _create_org_site(db_session)
        resp = client.get(f"/api/purchase/estimate/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "volume_kwh_an" in data
        assert "profile_factor" in data
        assert "source" in data

    def test_put_get_assumptions(self, client, db_session):
        _, site = _create_org_site(db_session)
        # PUT
        resp = client.put(
            f"/api/purchase/assumptions/{site.id}",
            json={
                "energy_type": "elec",
                "volume_kwh_an": 750000,
                "horizon_months": 36,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"
        # GET
        resp = client.get(f"/api/purchase/assumptions/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["volume_kwh_an"] == 750000
        assert data["horizon_months"] == 36

    def test_put_get_preferences(self, client, db_session):
        # PUT (org_id required when no auth)
        resp = client.put(
            "/api/purchase/preferences?org_id=1",
            json={
                "risk_tolerance": "low",
                "budget_priority": 0.3,
                "green_preference": True,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"
        # GET
        resp = client.get("/api/purchase/preferences?org_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_tolerance"] == "low"
        assert data["budget_priority"] == 0.3
        assert data["green_preference"] is True

    def test_compute_and_results(self, client, db_session):
        _, site = _create_org_site(db_session)
        # Compute
        resp = client.post(f"/api/purchase/compute/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scenarios"]) == 4
        assert data["assumption_set_id"] is not None
        # Check one is recommended
        reco = [s for s in data["scenarios"] if s.get("is_recommended")]
        assert len(reco) == 1
        # Get results
        resp = client.get(f"/api/purchase/results/{site.id}")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results["scenarios"]) == 4

    def test_accept_result(self, client, db_session):
        _, site = _create_org_site(db_session)
        # Compute first
        resp = client.post(f"/api/purchase/compute/{site.id}")
        scenarios = resp.json()["scenarios"]
        reco = next(s for s in scenarios if s.get("is_recommended"))
        # Accept
        resp = client.patch(f"/api/purchase/results/{reco['id']}/accept")
        assert resp.status_code == 200
        assert resp.json()["reco_status"] == "accepted"

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_demo(self, client, db_session):
        # Need at least 2 sites
        org, site_a = _create_org_site(db_session)
        site_b = Site(
            nom="Site B",
            type=TypeSite.ENTREPOT,
            adresse="2 rue Test",
            code_postal="69001",
            ville="Lyon",
            surface_m2=5000,
            portefeuille_id=site_a.portefeuille_id,
        )
        db_session.add(site_b)
        db_session.commit()
        resp = client.post("/api/purchase/seed-demo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["assumptions_created"] == 2
        assert data["scenarios_created"] == 8
        assert len(data["sites_used"]) == 2


# ========================================
# V1.1 Model tests
# ========================================


class TestV11Models:
    def test_energy_contract_notice_period(self, db_session):
        """EnergyContract with custom notice_period_days and auto_renew."""
        _, site = _create_org_site(db_session)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            price_ref_eur_per_kwh=0.18,
            start_date=date.today() - timedelta(days=300),
            end_date=date.today() + timedelta(days=45),
            notice_period_days=60,
            auto_renew=False,
        )
        db_session.add(contract)
        db_session.commit()
        assert contract.id is not None
        assert contract.notice_period_days == 60
        assert contract.auto_renew is False

    def test_energy_contract_defaults(self, db_session):
        """EnergyContract default values: notice_period_days=90, auto_renew=False."""
        _, site = _create_org_site(db_session)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.GAZ,
            supplier_name="Engie",
        )
        db_session.add(contract)
        db_session.commit()
        assert contract.notice_period_days == 90
        assert contract.auto_renew is False

    def test_scenario_result_run_fields(self, db_session):
        """PurchaseScenarioResult with run_id, batch_id, inputs_hash."""
        _, site = _create_org_site(db_session)
        assumption = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=500000,
        )
        db_session.add(assumption)
        db_session.flush()
        result = PurchaseScenarioResult(
            assumption_set_id=assumption.id,
            run_id="aaaa-bbbb-cccc",
            batch_id="dddd-eeee-ffff",
            inputs_hash="abc123",
            strategy=PurchaseStrategy.FIXE,
            price_eur_per_kwh=0.189,
            total_annual_eur=94500,
            risk_score=15,
        )
        db_session.add(result)
        db_session.commit()
        assert result.run_id == "aaaa-bbbb-cccc"
        assert result.batch_id == "dddd-eeee-ffff"
        assert result.inputs_hash == "abc123"


# ========================================
# V1.1 API tests
# ========================================


class TestV11API:
    def _seed_contracts(self, db_session):
        """Helper: create org + 2 sites + 2 contracts."""
        org, site_a, site_b = _create_two_sites(db_session)
        c1 = EnergyContract(
            site_id=site_a.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF Entreprises",
            start_date=date.today() - timedelta(days=300),
            end_date=date.today() + timedelta(days=45),
            price_ref_eur_per_kwh=0.18,
            notice_period_days=60,
            auto_renew=False,
        )
        c2 = EnergyContract(
            site_id=site_b.id,
            energy_type=BillingEnergyType.GAZ,
            supplier_name="Engie Pro",
            start_date=date.today() - timedelta(days=185),
            end_date=date.today() + timedelta(days=180),
            price_ref_eur_per_kwh=0.09,
            notice_period_days=90,
            auto_renew=True,
        )
        db_session.add_all([c1, c2])
        db_session.commit()
        return org, site_a, site_b

    def test_renewals_endpoint(self, client, db_session):
        """GET /renewals returns contracts with urgency."""
        org, site_a, site_b = self._seed_contracts(db_session)
        resp = client.get(f"/api/purchase/renewals?org_id={org.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        for r in data["renewals"]:
            assert "urgency" in r
            assert "days_until_expiry" in r
            assert "notice_deadline" in r
            assert "auto_renew" in r

    def test_history_endpoint(self, client, db_session):
        """Compute 2 times, history shows 2 runs."""
        _, site = _create_org_site(db_session)
        # Compute twice
        resp1 = client.post(f"/api/purchase/compute/{site.id}")
        assert resp1.status_code == 200
        run_id_1 = resp1.json()["run_id"]
        resp2 = client.post(f"/api/purchase/compute/{site.id}")
        assert resp2.status_code == 200
        run_id_2 = resp2.json()["run_id"]
        assert run_id_1 != run_id_2
        # Check history
        resp = client.get(f"/api/purchase/history/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 2
        assert len(data["runs"]) == 2
        # Each run has 4 scenarios and a summary
        for run in data["runs"]:
            assert len(run["scenarios"]) == 4
            assert "summary" in run
            assert run["run_id"] is not None

    def test_history_empty(self, client, db_session):
        """History returns empty for site without results."""
        _, site = _create_org_site(db_session)
        resp = client.get(f"/api/purchase/history/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 0
        assert data["runs"] == []

    def test_actions_endpoint(self, client, db_session):
        """GET /actions returns actions with contracts + scenarios seeded."""
        org, site_a, site_b = self._seed_contracts(db_session)
        # Compute scenarios to create draft recommendations
        client.post(f"/api/purchase/compute/{site_a.id}")
        resp = client.get(f"/api/purchase/actions?org_id={org.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_actions" in data
        assert "actions" in data
        assert "gain_potentiel_eur" in data
        assert data["total_actions"] >= 1
        # Each action has required fields
        for a in data["actions"]:
            assert "type" in a
            assert "priority" in a
            assert "label" in a
            assert "severity" in a

    def test_portfolio_compute(self, client, db_session):
        """POST /compute?org_id=X&scope=org computes for all org sites."""
        org, site_a, site_b = _create_two_sites(db_session)
        resp = client.post(f"/api/purchase/compute?org_id={org.id}&scope=org")
        assert resp.status_code == 200
        data = resp.json()
        assert "batch_id" in data
        assert data["org_id"] == org.id
        assert len(data["sites"]) == 2
        assert "portfolio" in data
        assert data["portfolio"]["sites_count"] == 2
        assert data["portfolio"]["total_annual_cost_eur"] > 0
        # Each site has run_id + 4 scenarios
        for s in data["sites"]:
            assert "run_id" in s
            assert len(s["scenarios"]) == 4

    def test_portfolio_results(self, client, db_session):
        """GET /results?org_id=X returns aggregated portfolio after compute."""
        org, site_a, site_b = _create_two_sites(db_session)
        # First compute
        client.post(f"/api/purchase/compute?org_id={org.id}&scope=org")
        # Then get results
        resp = client.get(f"/api/purchase/results?org_id={org.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_id"] == org.id
        assert data["portfolio"] is not None
        assert data["portfolio"]["sites_count"] == 2
        assert len(data["sites"]) == 2

    def test_dashboard_2min_v11_fields(self, client, db_session):
        """Dashboard 2min includes gain_potentiel_eur + prochain_renouvellement."""
        org, site_a, site_b = self._seed_contracts(db_session)
        # Compute scenarios so there are recommended draft results
        client.post(f"/api/purchase/compute/{site_a.id}")
        resp = client.get("/api/dashboard/2min")
        assert resp.status_code == 200
        data = resp.json()
        assert "achat" in data
        if data["achat"]:
            assert "gain_potentiel_eur" in data["achat"]
            assert "prochain_renouvellement" in data["achat"]
            # prochain_renouvellement should have contract info
            if data["achat"]["prochain_renouvellement"]:
                pr = data["achat"]["prochain_renouvellement"]
                assert "end_date" in pr
                assert "site_nom" in pr
                assert "days_remaining" in pr

    def test_compute_preserves_history(self, client, db_session):
        """Computing twice does NOT delete old results (V1.1 history preservation)."""
        _, site = _create_org_site(db_session)
        # Compute first time
        resp1 = client.post(f"/api/purchase/compute/{site.id}")
        assert resp1.status_code == 200
        ids_1 = [s["id"] for s in resp1.json()["scenarios"]]
        # Compute second time
        resp2 = client.post(f"/api/purchase/compute/{site.id}")
        assert resp2.status_code == 200
        ids_2 = [s["id"] for s in resp2.json()["scenarios"]]
        # IDs should be different (new records)
        assert set(ids_1).isdisjoint(set(ids_2))
        # Total results should be 8 (4+4), not 4
        count = db_session.query(PurchaseScenarioResult).count()
        assert count == 8

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_demo_v11(self, client, db_session):
        """Seed demo V1.1 creates contracts."""
        org, site_a = _create_org_site(db_session)
        site_b = Site(
            nom="Site B",
            type=TypeSite.ENTREPOT,
            adresse="2 rue Test",
            code_postal="69001",
            ville="Lyon",
            surface_m2=5000,
            portefeuille_id=site_a.portefeuille_id,
        )
        db_session.add(site_b)
        db_session.commit()
        resp = client.post("/api/purchase/seed-demo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["contracts_created"] == 2
        # Verify contracts in DB
        contracts = db_session.query(EnergyContract).all()
        assert len(contracts) >= 2


# ========================================
# Brique 3: Energy Gate tests
# ========================================

# ========================================
# P0-3: Assistant endpoint tests
# ========================================


class TestAssistantEndpoint:
    def test_assistant_returns_200(self, client, db_session):
        """GET /purchase/assistant returns 200."""
        resp = client.get("/api/purchase/assistant")
        assert resp.status_code == 200

    def test_assistant_demo_fallback(self, client, db_session):
        """Without org sites, returns demo seed with is_demo=true."""
        resp = client.get("/api/purchase/assistant")
        data = resp.json()
        assert data["is_demo"] is True
        assert len(data["sites"]) >= 5
        assert data["total_sites"] == len(data["sites"])
        assert data["total_annual_kwh"] > 0

    def test_assistant_with_real_org(self, client, db_session):
        """With org + sites, returns real data with is_demo=false."""
        org, site = _create_org_site(db_session)
        resp = client.get(f"/api/purchase/assistant?org_id={org.id}")
        data = resp.json()
        assert data["is_demo"] is False
        assert data["org_id"] == org.id
        assert len(data["sites"]) >= 1
        assert data["sites"][0]["name"] == "Site A"

    def test_assistant_demo_sites_structure(self, client, db_session):
        """Demo sites have required fields."""
        resp = client.get("/api/purchase/assistant")
        data = resp.json()
        for site in data["sites"]:
            assert "id" in site
            assert "name" in site
            assert "city" in site
            assert "energy_type" in site
            assert "annual_kwh" in site
            assert "source" in site


class TestEnergyGate:
    """Energy Gate: only ELEC energy type is allowed for purchase scenarios."""

    def test_put_assumptions_gaz_rejected(self, client, db_session):
        """PUT assumptions with energy_type=gaz returns 422."""
        _, site = _create_org_site(db_session)
        resp = client.put(
            f"/api/purchase/assumptions/{site.id}",
            json={
                "energy_type": "gaz",
                "volume_kwh_an": 300000,
                "horizon_months": 24,
            },
        )
        assert resp.status_code == 422
        assert "non supportee" in resp.json()["detail"]
        assert "elec" in resp.json()["detail"]

    def test_put_assumptions_elec_accepted(self, client, db_session):
        """PUT assumptions with energy_type=elec succeeds."""
        _, site = _create_org_site(db_session)
        resp = client.put(
            f"/api/purchase/assumptions/{site.id}",
            json={
                "energy_type": "elec",
                "volume_kwh_an": 500000,
                "horizon_months": 24,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] in ("created", "updated")

    def test_compute_gaz_assumption_rejected(self, client, db_session):
        """Compute rejects site with existing GAZ assumption."""
        _, site = _create_org_site(db_session)
        # Directly insert a GAZ assumption (bypassing the PUT gate)
        assumption = PurchaseAssumptionSet(
            site_id=site.id,
            energy_type=BillingEnergyType.GAZ,
            volume_kwh_an=300000,
        )
        db_session.add(assumption)
        db_session.commit()

        resp = client.post(f"/api/purchase/compute/{site.id}")
        assert resp.status_code == 422
        assert "non supportee" in resp.json()["detail"]

    def test_compute_elec_succeeds(self, client, db_session):
        """Compute succeeds for ELEC site."""
        _, site = _create_org_site(db_session)
        resp = client.post(f"/api/purchase/compute/{site.id}")
        assert resp.status_code == 200
        assert len(resp.json()["scenarios"]) == 4

    def test_portfolio_skips_gaz_sites(self, client, db_session):
        """Portfolio compute skips GAZ sites and only processes ELEC."""
        org, site_a, site_b = _create_two_sites(db_session)
        # Site A: ELEC assumption
        a_elec = PurchaseAssumptionSet(
            site_id=site_a.id,
            energy_type=BillingEnergyType.ELEC,
            volume_kwh_an=500000,
            profile_factor=1.0,
        )
        # Site B: GAZ assumption (should be skipped)
        b_gaz = PurchaseAssumptionSet(
            site_id=site_b.id,
            energy_type=BillingEnergyType.GAZ,
            volume_kwh_an=300000,
            profile_factor=1.0,
        )
        db_session.add_all([a_elec, b_gaz])
        db_session.commit()

        resp = client.post(f"/api/purchase/compute?org_id={org.id}&scope=org")
        assert resp.status_code == 200
        data = resp.json()
        # Only 1 site should be in results (ELEC only)
        assert len(data["sites"]) == 1
        assert data["sites"][0]["site_id"] == site_a.id

    def test_allowed_energy_types_constant(self):
        """ALLOWED_ENERGY_TYPES contains only 'elec'."""
        from routes.purchase import ALLOWED_ENERGY_TYPES

        assert ALLOWED_ENERGY_TYPES == {"elec"}
        assert "gaz" not in ALLOWED_ENERGY_TYPES

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_demo_elec_only(self, client, db_session):
        """Seed demo creates ELEC assumptions for both sites (post-Energy Gate)."""
        org, site_a = _create_org_site(db_session)
        site_b = Site(
            nom="Site B",
            type=TypeSite.ENTREPOT,
            adresse="2 rue Test",
            code_postal="69001",
            ville="Lyon",
            surface_m2=5000,
            portefeuille_id=site_a.portefeuille_id,
        )
        db_session.add(site_b)
        db_session.commit()
        resp = client.post("/api/purchase/seed-demo")
        assert resp.status_code == 200
        # Verify all assumptions are ELEC
        assumptions = db_session.query(PurchaseAssumptionSet).all()
        for a in assumptions:
            assert a.energy_type == BillingEnergyType.ELEC


# ========================================
# Brique 3: WOW multi-site dataset tests
# ========================================


class TestWowDatasets:
    """WOW multi-site datasets: happy + dirty modes."""

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_wow_happy(self, client, db_session):
        """Happy dataset creates 15 sites with full scenarios."""
        resp = client.post("/api/purchase/seed-wow-happy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "happy"
        assert data["sites_created"] == 15
        assert data["assumptions_created"] == 15
        assert data["scenarios_created"] == 60  # 15 sites * 4 strategies
        assert data["contracts_created"] == 15
        assert data["org_id"] is not None

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_wow_happy_all_elec(self, client, db_session):
        """Happy dataset: all assumptions are ELEC (Energy Gate)."""
        client.post("/api/purchase/seed-wow-happy")
        assumptions = db_session.query(PurchaseAssumptionSet).all()
        for a in assumptions:
            assert a.energy_type == BillingEnergyType.ELEC

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_wow_happy_varied_volumes(self, client, db_session):
        """Happy dataset has varied volumes (small to large sites)."""
        client.post("/api/purchase/seed-wow-happy")
        assumptions = db_session.query(PurchaseAssumptionSet).all()
        volumes = [a.volume_kwh_an for a in assumptions]
        assert min(volumes) < 500_000  # Small site
        assert max(volumes) >= 2_000_000  # Large industrial

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_wow_dirty(self, client, db_session):
        """Dirty dataset creates 15 sites with edge cases."""
        resp = client.post("/api/purchase/seed-wow-dirty")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "dirty"
        assert data["sites_created"] == 15
        # 2 sites skipped (orphans) → 13 assumptions
        assert data["assumptions_created"] == 13
        assert data["scenarios_created"] == 52  # 13 * 4
        assert "warnings" in data
        assert len(data["warnings"]) > 0

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_wow_dirty_edge_volumes(self, client, db_session):
        """Dirty dataset has zero-volume and extreme-volume sites."""
        client.post("/api/purchase/seed-wow-dirty")
        assumptions = db_session.query(PurchaseAssumptionSet).all()
        volumes = [a.volume_kwh_an for a in assumptions]
        assert 0 in volumes  # Zero-volume site
        assert 50 in volumes  # Tiny site
        assert 50_000_000 in volumes  # Absurdly large

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_wow_dirty_missing_contracts(self, client, db_session):
        """Dirty dataset: some sites have no contracts."""
        client.post("/api/purchase/seed-wow-dirty")
        data_resp = client.post("/api/purchase/seed-wow-dirty")
        data = data_resp.json()
        # contracts_created < sites_created (some missing)
        assert data["contracts_created"] < data["sites_created"]

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_wow_portfolio_compute(self, client, db_session):
        """Can compute portfolio on WOW happy dataset."""
        seed_resp = client.post("/api/purchase/seed-wow-happy")
        org_id = seed_resp.json()["org_id"]
        resp = client.post(f"/api/purchase/compute?org_id={org_id}&scope=org")
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio"]["sites_count"] == 15
        assert data["portfolio"]["total_annual_cost_eur"] > 0
