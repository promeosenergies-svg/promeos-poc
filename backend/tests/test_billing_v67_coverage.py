"""
PROMEOS — V67 Billing Coverage Tests
Tests pour: compute_coverage, compute_range, endpoints /periods /coverage-summary /missing-periods.
Couvre: covered/partial/missing, avoirs, fallback issue_date, chevauchements, multi-org, pagination.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timedelta
from calendar import monthrange
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models import (
    Base, Organisation, EntiteJuridique, Portefeuille,
    Site, TypeSite, EnergyInvoice, BillingInvoiceStatus,
)
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


def _make_org_site(db, nom="Org Test", siren="600000001"):
    org = Organisation(nom=nom, type_client="bureau", actif=True, siren=siren)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom=f"EJ {nom}", siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom=f"PF {nom}")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id, nom=f"Site {nom}", type=TypeSite.BUREAU,
        adresse="1 rue Test", code_postal="75001", ville="Paris",
        surface_m2=200, actif=True,
    )
    db.add(site)
    db.commit()
    return org, site


def _make_invoice(db, site_id, period_start=None, period_end=None, issue_date=None,
                  total_eur=1000.0, number=None):
    import random
    num = number or f"INV-COV-{random.randint(10000, 99999)}"
    inv = EnergyInvoice(
        site_id=site_id,
        invoice_number=num,
        period_start=period_start,
        period_end=period_end,
        issue_date=issue_date,
        total_eur=total_eur,
        status=BillingInvoiceStatus.IMPORTED,
        source="csv",
    )
    db.add(inv)
    db.flush()
    return inv


def _h(org_id):
    return {"X-Org-Id": str(org_id)}


# ========================================
# Unit tests — Coverage Engine
# ========================================

class TestCoverageEngine:

    def test_covered_month_full(self):
        """Facture couvrant tout janvier → 'covered'."""
        from services.billing_coverage import compute_coverage

        class FakeInv:
            id = 1
            period_start = date(2024, 1, 1)
            period_end = date(2024, 1, 31)
            issue_date = None
            total_eur = 1000.0

        months = compute_coverage([FakeInv()], date(2024, 1, 1), date(2024, 1, 31))
        assert len(months) == 1
        assert months[0].coverage_status == "covered"
        assert months[0].coverage_ratio == 1.0
        assert months[0].invoices_count == 1
        assert months[0].total_ttc == 1000.0

    def test_partial_month_below_threshold(self):
        """Facture couvrant 10/31 jours → 'partial'."""
        from services.billing_coverage import compute_coverage

        class FakeInv:
            id = 2
            period_start = date(2024, 1, 1)
            period_end = date(2024, 1, 10)
            issue_date = None
            total_eur = 500.0

        months = compute_coverage([FakeInv()], date(2024, 1, 1), date(2024, 1, 31))
        assert months[0].coverage_status == "partial"
        assert months[0].coverage_ratio < 0.80

    def test_missing_month_no_invoices(self):
        """Aucune facture pour un mois → 'missing'."""
        from services.billing_coverage import compute_coverage

        months = compute_coverage([], date(2024, 3, 1), date(2024, 3, 31))
        assert len(months) == 1
        assert months[0].coverage_status == "missing"
        assert months[0].invoices_count == 0
        assert months[0].missing_reason is not None

    def test_avoir_excluded_from_coverage(self):
        """Avoir (total_eur <= 0) ne contribue pas à la couverture."""
        from services.billing_coverage import compute_coverage

        class AvoirInv:
            id = 3
            period_start = date(2024, 2, 1)
            period_end = date(2024, 2, 29)
            issue_date = None
            total_eur = -200.0  # Avoir

        months = compute_coverage([AvoirInv()], date(2024, 2, 1), date(2024, 2, 29))
        assert months[0].coverage_status == "missing"  # Avoir n'apporte pas de couverture
        assert months[0].invoices_count == 1  # Mais compté dans les factures
        assert months[0].total_ttc == -200.0  # Et dans les totaux

    def test_fallback_to_issue_date(self):
        """Sans period_start/end, issue_date → mois entier utilisé."""
        from services.billing_coverage import compute_coverage

        class NoDateInv:
            id = 4
            period_start = None
            period_end = None
            issue_date = date(2024, 5, 15)  # Milieu du mois
            total_eur = 800.0

        months = compute_coverage([NoDateInv()], date(2024, 5, 1), date(2024, 5, 31))
        # Issue_date → couvre tout le mois de mai → covered
        assert months[0].coverage_status == "covered"

    def test_overlapping_invoices_no_double_count(self):
        """2 factures qui se chevauchent → pas de double-comptage des jours."""
        from services.billing_coverage import compute_coverage

        class Inv1:
            id = 5
            period_start = date(2024, 6, 1)
            period_end = date(2024, 6, 20)
            issue_date = None
            total_eur = 600.0

        class Inv2:
            id = 6
            period_start = date(2024, 6, 10)  # Chevauchement avec Inv1
            period_end = date(2024, 6, 30)
            issue_date = None
            total_eur = 400.0

        months = compute_coverage([Inv1(), Inv2()], date(2024, 6, 1), date(2024, 6, 30))
        assert months[0].coverage_status == "covered"
        assert months[0].coverage_ratio == 1.0  # Tout le mois couvert, sans double-comptage

    def test_multimonth_invoice_covers_three_months(self):
        """1 facture sur 3 mois → 3 mois couverts."""
        from services.billing_coverage import compute_coverage

        class LongInv:
            id = 7
            period_start = date(2024, 1, 1)
            period_end = date(2024, 3, 31)
            issue_date = None
            total_eur = 3000.0

        months = compute_coverage([LongInv()], date(2024, 1, 1), date(2024, 3, 31))
        assert len(months) == 3
        assert all(mc.coverage_status == "covered" for mc in months)

    def test_missing_reason_text(self):
        """missing_reason est une chaîne explicite pour les cas 'missing'."""
        from services.billing_coverage import compute_coverage

        months = compute_coverage([], date(2024, 7, 1), date(2024, 7, 31))
        assert months[0].missing_reason is not None
        assert len(months[0].missing_reason) > 5


# ========================================
# Integration tests — Endpoints
# ========================================

class TestCoverageEndpoints:

    def test_periods_empty_returns_empty(self, client, db):
        """GET /periods sans factures → periods=[], total=0."""
        org, site = _make_org_site(db, "Org Periods Empty", "600000010")
        r = client.get("/api/billing/periods", headers=_h(org.id))
        assert r.status_code == 200
        data = r.json()
        assert data["periods"] == []
        assert data["total"] == 0

    def test_periods_with_invoices_returns_months(self, client, db):
        """GET /periods avec 2 factures → liste de mois couverts."""
        org, site = _make_org_site(db, "Org Periods OK", "600000011")
        _make_invoice(db, site.id, period_start=date(2024, 1, 1), period_end=date(2024, 1, 31), number="INV-P001")
        _make_invoice(db, site.id, period_start=date(2024, 2, 1), period_end=date(2024, 2, 29), number="INV-P002")
        db.commit()

        r = client.get("/api/billing/periods", headers=_h(org.id))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 2
        assert len(data["periods"]) >= 1
        # Chaque période a les champs requis
        for p in data["periods"]:
            assert "month_key" in p
            assert "coverage_status" in p
            assert p["coverage_status"] in ("covered", "partial", "missing")

    def test_periods_pagination(self, client, db):
        """GET /periods avec limit=1&offset=0 vs offset=1 → slices différents."""
        org, site = _make_org_site(db, "Org Paginate", "600000012")
        _make_invoice(db, site.id, period_start=date(2024, 1, 1), period_end=date(2024, 1, 31), number="INV-PG1")
        _make_invoice(db, site.id, period_start=date(2024, 2, 1), period_end=date(2024, 2, 29), number="INV-PG2")
        _make_invoice(db, site.id, period_start=date(2024, 3, 1), period_end=date(2024, 3, 31), number="INV-PG3")
        db.commit()

        r1 = client.get("/api/billing/periods?limit=1&offset=0", headers=_h(org.id))
        r2 = client.get("/api/billing/periods?limit=1&offset=1", headers=_h(org.id))
        assert r1.status_code == 200
        assert r2.status_code == 200
        d1, d2 = r1.json(), r2.json()
        assert len(d1["periods"]) == 1
        assert len(d2["periods"]) == 1
        assert d1["periods"][0]["month_key"] != d2["periods"][0]["month_key"]

    def test_coverage_summary_org_a_vs_b(self, client, db):
        """GET /coverage-summary : org_a voit ses données, org_b voit zéro."""
        org_a, site_a = _make_org_site(db, "Org Summary A", "600000020")
        org_b, site_b = _make_org_site(db, "Org Summary B", "600000021")

        _make_invoice(db, site_a.id, period_start=date(2024, 1, 1), period_end=date(2024, 1, 31), number="INV-SUM-A1")
        _make_invoice(db, site_a.id, period_start=date(2024, 3, 1), period_end=date(2024, 3, 31), number="INV-SUM-A2")
        db.commit()

        r_a = client.get("/api/billing/coverage-summary", headers=_h(org_a.id))
        r_b = client.get("/api/billing/coverage-summary", headers=_h(org_b.id))

        assert r_a.status_code == 200
        assert r_b.status_code == 200

        data_a = r_a.json()
        data_b = r_b.json()

        assert data_a["months_total"] >= 2  # Janv + Fév (manquant) + Mars au moins
        assert data_b["months_total"] == 0  # Org_b n'a aucune facture
        assert data_b["range"] is None

    def test_missing_periods_cross_org_empty(self, client, db):
        """GET /missing-periods pour org sans factures → items=[]."""
        org, site = _make_org_site(db, "Org Missing Empty", "600000030")
        r = client.get("/api/billing/missing-periods", headers=_h(org.id))
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_missing_periods_detects_gap(self, client, db):
        """GET /missing-periods détecte un trou entre 2 factures."""
        org, site = _make_org_site(db, "Org Gap", "600000031")
        # Janv + Mars couverts, Fév manquant
        _make_invoice(db, site.id, period_start=date(2024, 1, 1), period_end=date(2024, 1, 31), number="INV-GAP1")
        _make_invoice(db, site.id, period_start=date(2024, 3, 1), period_end=date(2024, 3, 31), number="INV-GAP3")
        db.commit()

        r = client.get("/api/billing/missing-periods", headers=_h(org.id))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        month_keys = [item["month_key"] for item in data["items"]]
        assert "2024-02" in month_keys
        # Chaque item a les champs requis
        for item in data["items"]:
            assert "site_id" in item
            assert "cta_url" in item
            assert "regulatory_impact" in item
            assert item["regulatory_impact"]["framework"] == "FACTURATION"
