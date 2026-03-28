"""
PROMEOS — Phase 1 ELEC Trust Gate (backend)
Tests: insight status validation, shadow V2 energy_type, active loss semantics.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import date
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
    EnergyInvoiceLine,
    BillingInsight,
    BillingEnergyType,
    InvoiceLineType,
    BillingInvoiceStatus,
    InsightStatus,
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


def _create_org_site_insight(db, status="open"):
    """Helper: org + site + 1 insight."""
    org = Organisation(nom="Trust Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="Trust Corp", siren="999999999")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="PF")
    db.add(pf)
    db.flush()
    site = Site(
        nom="Site Trust",
        type=TypeSite.BUREAU,
        adresse="1 rue Trust",
        code_postal="75001",
        ville="Paris",
        surface_m2=1000,
        portefeuille_id=pf.id,
    )
    db.add(site)
    db.flush()
    insight = BillingInsight(
        site_id=site.id,
        type="shadow_gap",
        severity="high",
        message="Test insight",
        metrics_json=json.dumps({"delta_ttc": 100}),
        estimated_loss_eur=100.0,
        insight_status=InsightStatus(status),
    )
    db.add(insight)
    db.commit()
    return org, site, insight


class TestInsightStatusValidation:
    """PATCH /api/billing/insights/{id} — status validation."""

    def test_valid_status_accepted(self, db_session, client):
        _, site, insight = _create_org_site_insight(db_session, "open")
        resp = client.patch(
            f"/api/billing/insights/{insight.id}",
            json={"status": "resolved"},
        )
        assert resp.status_code == 200
        assert resp.json()["insight_status"] == "resolved"

    def test_invalid_status_rejected(self, db_session, client):
        _, site, insight = _create_org_site_insight(db_session, "open")
        resp = client.patch(
            f"/api/billing/insights/{insight.id}",
            json={"status": "bogus_status"},
        )
        assert resp.status_code == 400
        body = resp.json()
        detail_str = str(body.get("message", body.get("detail", ""))).lower()
        assert "invalide" in detail_str or "statut" in detail_str

    def test_all_four_statuses_accepted(self, db_session, client):
        _, site, insight = _create_org_site_insight(db_session, "open")
        for status in ["open", "ack", "resolved", "false_positive"]:
            resp = client.patch(
                f"/api/billing/insights/{insight.id}",
                json={"status": status},
            )
            assert resp.status_code == 200, f"Status '{status}' should be accepted"
            assert resp.json()["insight_status"] == status


class TestShadowV2EnergyType:
    """shadow_billing_v2 returns energy_type in result."""

    def test_shadow_v2_includes_energy_type(self):
        from services.billing_shadow_v2 import shadow_billing_v2

        # Create minimal invoice + contract for testing
        class FakeInvoice:
            total_eur = 1000
            energy_kwh = 5000
            period_start = date(2025, 1, 1)
            period_end = date(2025, 1, 31)
            site_id = 1

        class FakeContract:
            id = 1
            energy_type = BillingEnergyType.ELEC
            price_ref_eur_per_kwh = 0.15
            turpe_annual_eur = 500
            fixed_fee_eur_per_month = 10

        class FakeLine:
            line_type = InvoiceLineType.ENERGY
            amount_eur = 800
            kwh = 5000
            prix_unitaire = 0.16
            tva_pct = 20

        result = shadow_billing_v2(FakeInvoice(), [FakeLine()], FakeContract())
        assert "energy_type" in result
        assert result["energy_type"] == "ELEC"


class TestActiveLossSemantics:
    """isActiveInsight semantics — only open/ack are active."""

    def test_open_is_active(self, db_session):
        org, site, insight = _create_org_site_insight(db_session, "open")
        assert insight.insight_status == InsightStatus.OPEN

    def test_resolved_is_not_active(self, db_session):
        org, site, insight = _create_org_site_insight(db_session, "resolved")
        assert insight.insight_status == InsightStatus.RESOLVED
        # resolved insights should not count in active loss
        assert insight.insight_status not in (InsightStatus.OPEN, InsightStatus.ACK)
