"""
PROMEOS — V66 Billing Org Scoping Tests
Proves: resolve_org_id added to billing routes — no cross-org data leakage.

Setup: 2 orgs (Alpha, Bravo), each with EJ → Portefeuille → Site.
Alpha has invoices and insights; Bravo has none.
All tests use X-Org-Id header to simulate org context.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    TypeSite,
    EnergyInvoice,
    EnergyContract,
    BillingInsight,
    BillingInvoiceStatus,
    InsightStatus,
    BillingImportBatch,
)
from models.billing_models import BillingEnergyType
from database import get_db
from main import app


# ========================================
# Fixtures
# ========================================


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


def _create_two_orgs_with_billing(db):
    """Create 2 org hierarchies; Alpha has invoices + insights, Bravo is empty."""
    # ── Org Alpha ──
    org_a = Organisation(nom="Billing Alpha", type_client="bureau", actif=True, siren="300000001")
    db.add(org_a)
    db.flush()
    ej_a = EntiteJuridique(organisation_id=org_a.id, nom="EJ Alpha", siren="300000001")
    db.add(ej_a)
    db.flush()
    pf_a = Portefeuille(entite_juridique_id=ej_a.id, nom="PF Alpha")
    db.add(pf_a)
    db.flush()
    site_a = Site(
        portefeuille_id=pf_a.id,
        nom="Site Alpha",
        type=TypeSite.BUREAU,
        adresse="1 rue Alpha",
        code_postal="75001",
        ville="Paris",
        surface_m2=500,
        actif=True,
    )
    db.add(site_a)
    db.flush()

    # Alpha's invoice + insight
    inv_a = EnergyInvoice(
        site_id=site_a.id,
        invoice_number="FA-ALPHA-001",
        total_eur=1200.0,
        energy_kwh=5000.0,
        status=BillingInvoiceStatus.ANOMALY,
        source="csv",
    )
    db.add(inv_a)
    db.flush()
    insight_a = BillingInsight(
        site_id=site_a.id,
        invoice_id=inv_a.id,
        type="shadow_gap",
        severity="high",
        message="Ecart alpha test",
        insight_status=InsightStatus.OPEN,
    )
    db.add(insight_a)

    # ── Org Bravo ──
    org_b = Organisation(nom="Billing Bravo", type_client="industrie", actif=True, siren="300000002")
    db.add(org_b)
    db.flush()
    ej_b = EntiteJuridique(organisation_id=org_b.id, nom="EJ Bravo", siren="300000002")
    db.add(ej_b)
    db.flush()
    pf_b = Portefeuille(entite_juridique_id=ej_b.id, nom="PF Bravo")
    db.add(pf_b)
    db.flush()
    site_b = Site(
        portefeuille_id=pf_b.id,
        nom="Site Bravo",
        type=TypeSite.BUREAU,
        adresse="2 rue Bravo",
        code_postal="69001",
        ville="Lyon",
        surface_m2=400,
        actif=True,
    )
    db.add(site_b)
    db.flush()

    db.commit()
    return {
        "org_a": org_a,
        "site_a": site_a,
        "inv_a": inv_a,
        "insight_a": insight_a,
        "org_b": org_b,
        "site_b": site_b,
    }


def _h(org_id: int) -> dict:
    return {"X-Org-Id": str(org_id)}


# ========================================
# Tests
# ========================================


class TestBillingOrgScoping:
    def test_invoices_only_return_own_org(self, client, db):
        """GET /invoices scoped to org_a returns Alpha's invoices only."""
        d = _create_two_orgs_with_billing(db)
        r = client.get("/api/billing/invoices", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 1
        for inv in data["invoices"]:
            assert inv["site_id"] == d["site_a"].id

    def test_invoices_cross_org_returns_empty(self, client, db):
        """GET /invoices scoped to org_b returns empty list (Alpha's data invisible)."""
        d = _create_two_orgs_with_billing(db)
        r = client.get("/api/billing/invoices", headers=_h(d["org_b"].id))
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 0
        assert data["invoices"] == []

    def test_insights_cross_org_returns_empty(self, client, db):
        """GET /insights scoped to org_b returns empty list."""
        d = _create_two_orgs_with_billing(db)
        r = client.get("/api/billing/insights", headers=_h(d["org_b"].id))
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 0

    def test_summary_shows_own_org_data(self, client, db):
        """GET /summary scoped to org_a returns non-zero counts."""
        d = _create_two_orgs_with_billing(db)
        r_a = client.get("/api/billing/summary", headers=_h(d["org_a"].id))
        assert r_a.status_code == 200
        data_a = r_a.json()
        assert data_a["total_invoices"] >= 1

        # Org_b sees nothing
        r_b = client.get("/api/billing/summary", headers=_h(d["org_b"].id))
        assert r_b.status_code == 200
        data_b = r_b.json()
        assert data_b["total_invoices"] == 0

    def test_site_billing_cross_org_returns_404(self, client, db):
        """GET /site/{site_id} for a site belonging to org_a, accessed via org_b → 404."""
        d = _create_two_orgs_with_billing(db)
        r = client.get(
            f"/api/billing/site/{d['site_a'].id}",
            headers=_h(d["org_b"].id),
        )
        assert r.status_code == 404
