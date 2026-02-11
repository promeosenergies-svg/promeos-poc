"""
PROMEOS - Tests Sprint 7: Bill Intelligence V1
Models, CSV import, shadow billing, anomaly engine, read endpoints, seed demo.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import json
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight,
    BillingEnergyType, InvoiceLineType, BillingInvoiceStatus,
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
        nom="Site A", type=TypeSite.BUREAU,
        adresse="1 rue Test", code_postal="75001", ville="Paris",
        surface_m2=surface, portefeuille_id=pf.id,
    )
    db.add(site)
    db.flush()
    return org, site


def _create_two_sites(db):
    """Helper: create org + 2 sites."""
    org, site_a = _create_org_site(db)
    site_b = Site(
        nom="Site B", type=TypeSite.ENTREPOT,
        adresse="2 rue Test", code_postal="69001", ville="Lyon",
        surface_m2=5000, portefeuille_id=site_a.portefeuille_id,
    )
    db.add(site_b)
    db.flush()
    return org, site_a, site_b


# ========================================
# Model tests
# ========================================

class TestModels:
    def test_create_contract(self, db_session):
        _, site = _create_org_site(db_session)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            price_ref_eur_per_kwh=0.18,
        )
        db_session.add(contract)
        db_session.commit()
        assert contract.id is not None
        assert contract.energy_type == BillingEnergyType.ELEC

    def test_create_invoice_with_lines(self, db_session):
        _, site = _create_org_site(db_session)
        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number="TEST-001",
            total_eur=1000.0,
            energy_kwh=5000,
            status=BillingInvoiceStatus.IMPORTED,
        )
        db_session.add(invoice)
        db_session.flush()

        line = EnergyInvoiceLine(
            invoice_id=invoice.id,
            line_type=InvoiceLineType.ENERGY,
            label="Consommation",
            qty=5000, unit="kWh", unit_price=0.18, amount_eur=900,
        )
        db_session.add(line)
        db_session.commit()

        assert invoice.id is not None
        assert len(invoice.lines) == 1
        assert invoice.lines[0].line_type == InvoiceLineType.ENERGY

    def test_create_billing_insight(self, db_session):
        _, site = _create_org_site(db_session)
        invoice = EnergyInvoice(
            site_id=site.id, invoice_number="TEST-002",
            total_eur=500, energy_kwh=2000,
        )
        db_session.add(invoice)
        db_session.flush()

        insight = BillingInsight(
            site_id=site.id, invoice_id=invoice.id,
            type="shadow_gap", severity="high",
            message="Ecart shadow billing de +25%",
            estimated_loss_eur=125.0,
        )
        db_session.add(insight)
        db_session.commit()
        assert insight.id is not None

    def test_billing_enums(self):
        assert BillingEnergyType.ELEC.value == "elec"
        assert BillingEnergyType.GAZ.value == "gaz"
        assert InvoiceLineType.ENERGY.value == "energy"
        assert InvoiceLineType.TAX.value == "tax"
        assert BillingInvoiceStatus.ANOMALY.value == "anomaly"


# ========================================
# Service tests
# ========================================

class TestBillingService:
    def test_shadow_billing_simple(self, db_session):
        from services.billing_service import shadow_billing_simple
        _, site = _create_org_site(db_session)
        contract = EnergyContract(
            site_id=site.id, energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF", price_ref_eur_per_kwh=0.20,
        )
        db_session.add(contract)
        db_session.flush()

        invoice = EnergyInvoice(
            site_id=site.id, contract_id=contract.id,
            invoice_number="SH-001",
            total_eur=1200, energy_kwh=5000,
        )
        db_session.add(invoice)
        db_session.commit()

        result = shadow_billing_simple(invoice, contract)
        assert result["method"] == "simple"
        assert result["shadow_total_eur"] == 1000.0  # 5000 * 0.20
        assert result["delta_eur"] == 200.0  # 1200 - 1000
        assert result["delta_pct"] == 20.0

    def test_shadow_billing_no_kwh(self, db_session):
        from services.billing_service import shadow_billing_simple
        _, site = _create_org_site(db_session)
        invoice = EnergyInvoice(
            site_id=site.id, invoice_number="SH-002",
            total_eur=1000, energy_kwh=None,
        )
        db_session.add(invoice)
        db_session.commit()

        result = shadow_billing_simple(invoice, None)
        assert result["method"] == "skip"

    def test_anomaly_engine_shadow_gap(self, db_session):
        from services.billing_service import run_anomaly_engine
        _, site = _create_org_site(db_session)
        contract = EnergyContract(
            site_id=site.id, energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF", price_ref_eur_per_kwh=0.18,
        )
        db_session.add(contract)
        db_session.flush()

        # Invoice with 30% overcharge
        invoice = EnergyInvoice(
            site_id=site.id, contract_id=contract.id,
            invoice_number="ANO-001",
            total_eur=1170, energy_kwh=5000,
            period_start=date(2025, 1, 1), period_end=date(2025, 1, 31),
        )
        db_session.add(invoice)
        db_session.commit()

        anomalies = run_anomaly_engine(invoice, [], contract, db_session)
        types = [a["type"] for a in anomalies]
        assert "shadow_gap" in types
        assert "price_drift" in types  # 0.234 vs 0.18 = +30%

    def test_anomaly_engine_period_too_long(self, db_session):
        from services.billing_service import run_anomaly_engine
        _, site = _create_org_site(db_session)
        invoice = EnergyInvoice(
            site_id=site.id, invoice_number="ANO-002",
            total_eur=500, energy_kwh=3000,
            period_start=date(2025, 1, 1), period_end=date(2025, 4, 30),
        )
        db_session.add(invoice)
        db_session.commit()

        anomalies = run_anomaly_engine(invoice, [], None, db_session)
        types = [a["type"] for a in anomalies]
        assert "period_too_long" in types

    def test_anomaly_engine_negative_kwh(self, db_session):
        from services.billing_service import run_anomaly_engine
        _, site = _create_org_site(db_session)
        invoice = EnergyInvoice(
            site_id=site.id, invoice_number="ANO-003",
            total_eur=100, energy_kwh=-500,
            period_start=date(2025, 1, 1), period_end=date(2025, 1, 31),
        )
        db_session.add(invoice)
        db_session.commit()

        anomalies = run_anomaly_engine(invoice, [], None, db_session)
        types = [a["type"] for a in anomalies]
        assert "negative_kwh" in types

    def test_anomaly_engine_lines_mismatch(self, db_session):
        from services.billing_service import run_anomaly_engine
        _, site = _create_org_site(db_session)
        invoice = EnergyInvoice(
            site_id=site.id, invoice_number="ANO-004",
            total_eur=1000, energy_kwh=5000,
            period_start=date(2025, 1, 1), period_end=date(2025, 1, 31),
        )
        db_session.add(invoice)
        db_session.flush()

        lines = [
            EnergyInvoiceLine(
                invoice_id=invoice.id, line_type=InvoiceLineType.ENERGY,
                label="Conso", amount_eur=700,
            ),
        ]
        for l in lines:
            db_session.add(l)
        db_session.commit()

        anomalies = run_anomaly_engine(invoice, lines, None, db_session)
        types = [a["type"] for a in anomalies]
        assert "lines_sum_mismatch" in types

    def test_audit_full_pipeline(self, db_session):
        from services.billing_service import audit_invoice_full
        _, site = _create_org_site(db_session)
        invoice = EnergyInvoice(
            site_id=site.id, invoice_number="PIPE-001",
            total_eur=2000, energy_kwh=5000,
            period_start=date(2025, 1, 1), period_end=date(2025, 1, 31),
        )
        db_session.add(invoice)
        db_session.commit()

        result = audit_invoice_full(db_session, invoice.id)
        assert "error" not in result
        assert result["invoice_id"] == invoice.id
        assert "shadow" in result
        assert "anomalies" in result

    def test_billing_summary(self, db_session):
        from services.billing_service import get_billing_summary
        _, site = _create_org_site(db_session)

        invoice = EnergyInvoice(
            site_id=site.id, invoice_number="SUM-001",
            total_eur=1000, energy_kwh=5000,
        )
        db_session.add(invoice)
        db_session.commit()

        summary = get_billing_summary(db_session)
        assert summary["total_invoices"] == 1
        assert summary["total_eur"] == 1000.0

    def test_site_billing(self, db_session):
        from services.billing_service import get_site_billing
        _, site = _create_org_site(db_session)

        contract = EnergyContract(
            site_id=site.id, energy_type=BillingEnergyType.GAZ,
            supplier_name="Engie", price_ref_eur_per_kwh=0.09,
        )
        db_session.add(contract)
        db_session.flush()

        invoice = EnergyInvoice(
            site_id=site.id, contract_id=contract.id,
            invoice_number="SITE-001", total_eur=540, energy_kwh=6000,
        )
        db_session.add(invoice)
        db_session.commit()

        result = get_site_billing(db_session, site.id)
        assert result["site_id"] == site.id
        assert len(result["contracts"]) == 1
        assert len(result["invoices"]) == 1


# ========================================
# API endpoint tests
# ========================================

class TestBillingAPI:
    def test_create_contract(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()

        r = client.post("/api/billing/contracts", json={
            "site_id": site.id,
            "energy_type": "elec",
            "supplier_name": "EDF",
            "price_ref_eur_per_kwh": 0.18,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "created"

    def test_list_contracts(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.add(EnergyContract(
            site_id=site.id, energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF", price_ref_eur_per_kwh=0.18,
        ))
        db_session.commit()

        r = client.get("/api/billing/contracts")
        assert r.status_code == 200
        assert r.json()["count"] == 1

    def test_create_invoice(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()

        r = client.post("/api/billing/invoices", json={
            "site_id": site.id,
            "invoice_number": "API-001",
            "total_eur": 1500,
            "energy_kwh": 8000,
            "lines": [
                {"line_type": "energy", "label": "HP", "qty": 5000, "unit": "kWh", "unit_price": 0.20, "amount_eur": 1000},
                {"line_type": "tax", "label": "CSPE", "amount_eur": 50},
            ],
        })
        assert r.status_code == 200
        assert r.json()["status"] == "created"

    def test_list_invoices(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.add(EnergyInvoice(
            site_id=site.id, invoice_number="LIST-001",
            total_eur=1000, energy_kwh=5000,
        ))
        db_session.commit()

        r = client.get("/api/billing/invoices")
        assert r.status_code == 200
        assert r.json()["count"] == 1

    def test_audit_invoice(self, client, db_session):
        _, site = _create_org_site(db_session)
        invoice = EnergyInvoice(
            site_id=site.id, invoice_number="AUD-001",
            total_eur=2000, energy_kwh=5000,
            period_start=date(2025, 1, 1), period_end=date(2025, 1, 31),
        )
        db_session.add(invoice)
        db_session.commit()

        r = client.post(f"/api/billing/audit/{invoice.id}")
        assert r.status_code == 200
        assert "anomalies_count" in r.json()

    def test_audit_all(self, client, db_session):
        _, site = _create_org_site(db_session)
        for i in range(3):
            db_session.add(EnergyInvoice(
                site_id=site.id, invoice_number=f"BATCH-{i:03d}",
                total_eur=1000 + i * 100, energy_kwh=5000,
            ))
        db_session.commit()

        r = client.post("/api/billing/audit-all")
        assert r.status_code == 200
        assert r.json()["audited"] == 3

    def test_billing_summary(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.add(EnergyInvoice(
            site_id=site.id, invoice_number="SUM-001",
            total_eur=1500, energy_kwh=8000,
        ))
        db_session.commit()

        r = client.get("/api/billing/summary")
        assert r.status_code == 200
        assert r.json()["total_invoices"] == 1
        assert r.json()["total_eur"] == 1500.0

    def test_billing_insights_empty(self, client, db_session):
        _create_org_site(db_session)
        db_session.commit()
        r = client.get("/api/billing/insights")
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_site_billing(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.add(EnergyInvoice(
            site_id=site.id, invoice_number="SITE-001",
            total_eur=800, energy_kwh=4000,
        ))
        db_session.commit()

        r = client.get(f"/api/billing/site/{site.id}")
        assert r.status_code == 200
        assert r.json()["site_id"] == site.id

    def test_list_rules(self, client):
        r = client.get("/api/billing/rules")
        assert r.status_code == 200
        assert r.json()["count"] == 10

    def test_csv_import(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()

        csv_content = f"site_id,invoice_number,period_start,period_end,total_eur,energy_kwh\n{site.id},CSV-001,2025-01-01,2025-01-31,1200,6000\n{site.id},CSV-002,2025-02-01,2025-02-28,1100,5500\n"
        r = client.post(
            "/api/billing/import-csv",
            files={"file": ("invoices.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["imported"] == 2
        assert data["error_count"] == 0

    def test_csv_import_duplicate_rejected(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.add(EnergyInvoice(
            site_id=site.id, invoice_number="DUP-001",
            total_eur=1000, energy_kwh=5000,
        ))
        db_session.commit()

        csv_content = f"site_id,invoice_number,total_eur,energy_kwh\n{site.id},DUP-001,1000,5000\n"
        r = client.post(
            "/api/billing/import-csv",
            files={"file": ("invoices.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert r.status_code == 200
        assert r.json()["imported"] == 0
        assert r.json()["error_count"] == 1

    def test_csv_import_bad_site(self, client, db_session):
        _create_org_site(db_session)
        db_session.commit()

        csv_content = "site_id,invoice_number,total_eur,energy_kwh\n99999,BAD-001,1000,5000\n"
        r = client.post(
            "/api/billing/import-csv",
            files={"file": ("invoices.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert r.status_code == 200
        assert r.json()["imported"] == 0
        assert r.json()["error_count"] == 1

    def test_seed_demo(self, client, db_session):
        _create_two_sites(db_session)
        db_session.commit()

        r = client.post("/api/billing/seed-demo")
        assert r.status_code == 200
        data = r.json()
        assert data["invoices_created"] == 5
        assert data["good_invoices"] == 3
        assert data["bad_invoices"] == 2

    def test_seed_then_audit_then_summary(self, client, db_session):
        """Integration: seed → audit-all → verify insights created."""
        _create_two_sites(db_session)
        db_session.commit()

        # Seed
        r = client.post("/api/billing/seed-demo")
        assert r.status_code == 200

        # Audit all
        r = client.post("/api/billing/audit-all")
        assert r.status_code == 200
        assert r.json()["total_anomalies"] > 0

        # Check insights persisted
        r = client.get("/api/billing/insights")
        assert r.status_code == 200
        assert r.json()["count"] > 0

        # Check summary
        r = client.get("/api/billing/summary")
        assert r.status_code == 200
        s = r.json()
        assert s["total_invoices"] == 5
        assert s["total_insights"] > 0
        assert s["total_estimated_loss_eur"] > 0

    def test_dashboard_2min_includes_billing(self, client, db_session):
        """Dashboard 2min should include billing section after seed."""
        _create_two_sites(db_session)
        db_session.commit()

        # Seed billing
        client.post("/api/billing/seed-demo")

        r = client.get("/api/dashboard/2min")
        assert r.status_code == 200
        data = r.json()
        assert "billing" in data
        assert data["billing"]["total_invoices"] == 5
