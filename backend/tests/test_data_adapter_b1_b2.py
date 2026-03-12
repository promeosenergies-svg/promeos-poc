"""
PROMEOS — DataAdapter Contract Tests: B1 (Billing) → B2 (Purchase) Bridge
Validates that the purchase module correctly uses billing data (contracts,
reference prices, invoices) as inputs for scenario computation.

Brique 3: Leader du Marche
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
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
    SiteTariffProfile,
    PurchaseAssumptionSet,
    PurchaseScenarioResult,
    BillingEnergyType,
    BillingInvoiceStatus,
    TypeSite,
)
from database import get_db
from main import app


@pytest.fixture
def db():
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
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org_site(db, surface=2000):
    org = Organisation(nom="B1B2 Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="111222333")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        nom="Site Test B1B2",
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


# ═══════════════════════════════════════════════
# Contract: get_reference_price resolution chain
# ═══════════════════════════════════════════════


class TestReferencePrice:
    """B1→B2 bridge: reference price resolution priority chain."""

    def test_price_from_contract(self, db):
        """Priority 1: price comes from active EnergyContract."""
        from services.billing_service import get_reference_price

        _, site = _create_org_site(db)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            price_ref_eur_per_kwh=0.165,
        )
        db.add(contract)
        db.commit()

        price, source = get_reference_price(db, site.id, "elec")
        assert price == 0.165
        assert "contract:" in source

    def test_price_from_tariff_profile(self, db):
        """Priority 2: price from SiteTariffProfile when no contract."""
        from services.billing_service import get_reference_price

        _, site = _create_org_site(db)
        tariff = SiteTariffProfile(
            site_id=site.id,
            price_ref_eur_per_kwh=0.175,
        )
        db.add(tariff)
        db.commit()

        price, source = get_reference_price(db, site.id, "elec")
        assert price == 0.175
        assert source == "site_tariff_profile"

    def test_price_default_fallback(self, db):
        """Priority 3: default price when no contract or tariff."""
        from services.billing_service import get_reference_price

        _, site = _create_org_site(db)
        db.commit()

        price, source = get_reference_price(db, site.id, "elec")
        assert price == 0.15  # Default fallback price (PROMEOS_DEFAULT_PRICE_ELEC)
        assert source == "default_elec"

    def test_contract_beats_tariff(self, db):
        """Contract price takes precedence over tariff profile."""
        from services.billing_service import get_reference_price

        _, site = _create_org_site(db)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            price_ref_eur_per_kwh=0.165,
        )
        tariff = SiteTariffProfile(
            site_id=site.id,
            price_ref_eur_per_kwh=0.190,
        )
        db.add_all([contract, tariff])
        db.commit()

        price, source = get_reference_price(db, site.id, "elec")
        assert price == 0.165
        assert "contract:" in source

    def test_contract_period_overlap(self, db):
        """Contract with period dates: only matches if period overlaps."""
        from services.billing_service import get_reference_price

        _, site = _create_org_site(db)
        today = date.today()
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            price_ref_eur_per_kwh=0.165,
            start_date=today - timedelta(days=365),
            end_date=today + timedelta(days=30),
        )
        db.add(contract)
        db.commit()

        # Within period — should match
        price, source = get_reference_price(
            db,
            site.id,
            "elec",
            period_start=today - timedelta(days=10),
            period_end=today,
        )
        assert price == 0.165
        assert "contract:" in source


# ═══════════════════════════════════════════════
# Contract: estimate_consumption from B1 data
# ═══════════════════════════════════════════════


class TestConsumptionEstimate:
    """B1→B2 bridge: consumption estimate from invoices/readings."""

    def test_estimate_from_invoices(self, db):
        """Purchase estimate uses B1 invoice data."""
        from services.purchase_service import estimate_consumption

        _, site = _create_org_site(db)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            price_ref_eur_per_kwh=0.18,
        )
        db.add(contract)
        db.flush()

        # Create 3 months of invoices
        for i in range(3):
            inv = EnergyInvoice(
                site_id=site.id,
                contract_id=contract.id,
                invoice_number=f"INV-{i}",
                period_start=date.today() - timedelta(days=90 - i * 30),
                period_end=date.today() - timedelta(days=60 - i * 30),
                total_eur=3600,
                energy_kwh=20000,
                status=BillingInvoiceStatus.IMPORTED,
            )
            db.add(inv)
        db.commit()

        result = estimate_consumption(db, site.id)
        assert result["source"] == "invoices"
        assert result["volume_kwh_an"] > 0
        assert result["months_covered"] >= 1

    def test_estimate_fallback_no_data(self, db):
        """Falls back to 500k kWh default when no B1 data."""
        from services.purchase_service import estimate_consumption

        _, site = _create_org_site(db)
        db.commit()

        result = estimate_consumption(db, site.id)
        assert result["source"] == "default"
        assert result["volume_kwh_an"] == 500_000


# ═══════════════════════════════════════════════
# Contract: scenarios use correct reference price
# ═══════════════════════════════════════════════


class TestScenariosUseRefPrice:
    """B1→B2 bridge: computed scenarios use the correct reference price from billing."""

    def test_scenarios_use_contract_price(self, db):
        """Scenarios reflect the contract reference price, not default."""
        from services.purchase_service import compute_scenarios

        _, site = _create_org_site(db)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF Premium",
            price_ref_eur_per_kwh=0.22,
        )
        db.add(contract)
        db.commit()

        scenarios = compute_scenarios(db, site.id, volume_kwh_an=500_000, energy_type="elec")
        fixe = next(s for s in scenarios if s["strategy"] == "fixe")
        # ref_price comes from contract, price_eur_per_kwh is market-based (since V23)
        assert fixe["ref_price"] == 0.22
        assert fixe["price_eur_per_kwh"] > 0  # market-based price
        assert fixe["ref_price_source"].startswith("contract:")

    def test_scenarios_use_default_price(self, db):
        """Without contract, scenarios use the configured default price."""
        from services.purchase_service import compute_scenarios
        from services.billing_service import DEFAULT_PRICE_ELEC

        _, site = _create_org_site(db)
        db.commit()

        scenarios = compute_scenarios(db, site.id, volume_kwh_an=500_000, energy_type="elec")
        fixe = next(s for s in scenarios if s["strategy"] == "fixe")
        assert fixe["ref_price"] == DEFAULT_PRICE_ELEC
        assert fixe["ref_price_source"] == "default_elec"

    def test_four_strategies_generated(self, db):
        """Always generates exactly 4 strategies (V79: + reflex_solar)."""
        from services.purchase_service import compute_scenarios

        _, site = _create_org_site(db)
        db.commit()

        scenarios = compute_scenarios(db, site.id, volume_kwh_an=500_000)
        assert len(scenarios) == 4
        strategies = {s["strategy"] for s in scenarios}
        assert strategies == {"fixe", "indexe", "spot", "reflex_solar"}

    def test_risk_ordering(self, db):
        """Fixe < Indexe < Spot risk ordering."""
        from services.purchase_service import compute_scenarios

        _, site = _create_org_site(db)
        db.commit()

        scenarios = compute_scenarios(db, site.id, volume_kwh_an=500_000)
        fixe = next(s for s in scenarios if s["strategy"] == "fixe")
        indexe = next(s for s in scenarios if s["strategy"] == "indexe")
        spot = next(s for s in scenarios if s["strategy"] == "spot")
        assert fixe["risk_score"] < indexe["risk_score"] < spot["risk_score"]


# ═══════════════════════════════════════════════
# Contract: end-to-end compute via API
# ═══════════════════════════════════════════════


class TestEndToEndCompute:
    """B1→B2 bridge: full endpoint test with billing data present."""

    def test_compute_with_contract(self, client, db):
        """POST /compute uses contract price in scenario generation."""
        _, site = _create_org_site(db)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Vattenfall",
            price_ref_eur_per_kwh=0.195,
        )
        db.add(contract)
        db.commit()

        resp = client.post(f"/api/purchase/compute/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scenarios"]) == 4  # V79: + reflex_solar
        fixe = next(s for s in data["scenarios"] if s["strategy"] == "fixe")
        # ref_price comes from contract, price_eur_per_kwh is market-based (since V23)
        assert fixe["ref_price"] == 0.195
        assert fixe["price_eur_per_kwh"] > 0

    def test_compute_without_contract(self, client, db):
        """POST /compute uses default price when no contract."""
        from services.billing_service import DEFAULT_PRICE_ELEC

        _, site = _create_org_site(db)
        db.commit()

        resp = client.post(f"/api/purchase/compute/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        fixe = next(s for s in data["scenarios"] if s["strategy"] == "fixe")
        assert fixe["ref_price"] == DEFAULT_PRICE_ELEC
        assert fixe["price_eur_per_kwh"] > 0

    def test_renewals_show_b1_contracts(self, client, db):
        """GET /renewals reflects B1 contract data."""
        org, site = _create_org_site(db)
        today = date.today()
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            price_ref_eur_per_kwh=0.18,
            start_date=today - timedelta(days=300),
            end_date=today + timedelta(days=45),
            notice_period_days=60,
        )
        db.add(contract)
        db.commit()

        resp = client.get(f"/api/purchase/renewals?org_id={org.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        renewal = next(r for r in data["renewals"] if r["contract_id"] == contract.id)
        assert renewal["supplier_name"] == "EDF"
        assert renewal["energy_type"] == "elec"
        assert renewal["days_until_expiry"] > 0

    def test_energy_gate_blocks_gaz_in_adapter(self, client, db):
        """Energy Gate: even with GAZ contract, assumptions must be ELEC."""
        _, site = _create_org_site(db)
        # GAZ contract exists in B1
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.GAZ,
            supplier_name="Engie",
            price_ref_eur_per_kwh=0.09,
        )
        db.add(contract)
        db.commit()

        # Try to create GAZ assumption → should be blocked
        resp = client.put(
            f"/api/purchase/assumptions/{site.id}",
            json={
                "energy_type": "gaz",
                "volume_kwh_an": 300000,
            },
        )
        assert resp.status_code == 422
        assert "non supportee" in resp.json()["detail"]
