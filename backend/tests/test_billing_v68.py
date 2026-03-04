"""
PROMEOS — V68 Billing Unified Tests
Couvre: InvoiceNormalized, Shadow V2, R13/R14, Seed 36 mois, endpoint /invoices/normalized.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    TypeSite,
    EnergyInvoice,
    EnergyInvoiceLine,
    EnergyContract,
    BillingEnergyType,
    InvoiceLineType,
    BillingInvoiceStatus,
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


def _make_org_site(db, nom="OrgTest", siren="600000001"):
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
        portefeuille_id=pf.id,
        nom=f"Site {nom}",
        type=TypeSite.BUREAU,
        adresse="1 rue Test",
        code_postal="75001",
        ville="Paris",
        surface_m2=200,
        actif=True,
    )
    db.add(site)
    db.commit()
    return org, site


def _make_contract(db, site_id, energy_type=BillingEnergyType.ELEC, supplier="EDF Test", price_ref=0.18):
    c = EnergyContract(
        site_id=site_id,
        energy_type=energy_type,
        supplier_name=supplier,
        price_ref_eur_per_kwh=price_ref,
    )
    db.add(c)
    db.flush()
    return c


def _make_invoice_with_lines(
    db,
    site_id,
    contract_id=None,
    period_start=date(2024, 1, 1),
    period_end=date(2024, 1, 31),
    total_eur=1620.0,
    kwh=9000,
    energy_amt=1020.0,
    network_amt=400.0,
    tax_amt=200.0,
    number=None,
):
    import random

    inv = EnergyInvoice(
        site_id=site_id,
        contract_id=contract_id,
        invoice_number=number or f"INV-{random.randint(10000, 99999)}",
        period_start=period_start,
        period_end=period_end,
        issue_date=date(2024, 2, 5),
        total_eur=total_eur,
        energy_kwh=kwh,
        status=BillingInvoiceStatus.IMPORTED,
        source="test",
    )
    db.add(inv)
    db.flush()
    db.add(
        EnergyInvoiceLine(invoice_id=inv.id, line_type=InvoiceLineType.ENERGY, label="Energie", amount_eur=energy_amt)
    )
    db.add(
        EnergyInvoiceLine(invoice_id=inv.id, line_type=InvoiceLineType.NETWORK, label="Réseau", amount_eur=network_amt)
    )
    db.add(EnergyInvoiceLine(invoice_id=inv.id, line_type=InvoiceLineType.TAX, label="Taxes", amount_eur=tax_amt))
    db.flush()
    return inv


def _h(org_id):
    return {"X-Org-Id": str(org_id)}


# ========================================
# TestInvoiceNormalized
# ========================================


class TestInvoiceNormalized:
    def test_normalize_with_lines(self, db):
        """ht/tva/fournisseur/energie calculés correctement."""
        from services.billing_normalization import normalize_invoice

        org, site = _make_org_site(db, "OrgNorm", "600001001")
        contract = _make_contract(db, site.id, supplier="EDF ENR", price_ref=0.18)
        inv = _make_invoice_with_lines(
            db, site.id, contract.id, energy_amt=1020.0, network_amt=400.0, tax_amt=200.0, total_eur=1620.0, kwh=9000
        )
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = normalize_invoice(inv, lines, contract, org.id)
        assert result.ht == 1420.0  # 1020 + 400
        assert result.tva == 200.0
        assert result.ht_fourniture == 1020.0
        assert result.ht_reseau == 400.0
        assert result.ttc == 1620.0
        assert result.fournisseur == "EDF ENR"
        assert result.energie == "ELEC"
        assert result.org_id == org.id

    def test_normalize_no_contract(self, db):
        """Fournisseur=None, energie=None si pas de contrat."""
        from services.billing_normalization import normalize_invoice

        org, site = _make_org_site(db, "OrgNoContract", "600001002")
        inv = _make_invoice_with_lines(db, site.id)
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = normalize_invoice(inv, lines, None, org.id)
        assert result.fournisseur is None
        assert result.energie is None
        assert result.ht == 1420.0

    def test_normalize_month_key_from_period(self, db):
        """month_key dérivé de period_start."""
        from services.billing_normalization import normalize_invoice

        org, site = _make_org_site(db, "OrgMK1", "600001003")
        inv = _make_invoice_with_lines(db, site.id, period_start=date(2024, 3, 1), period_end=date(2024, 3, 31))
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = normalize_invoice(inv, lines, None, org.id)
        assert result.month_key == "2024-03"

    def test_normalize_month_key_fallback(self, db):
        """month_key utilise issue_date si period_start absent."""
        from services.billing_normalization import normalize_invoice

        org, site = _make_org_site(db, "OrgMK2", "600001004")
        inv = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-MK-001",
            period_start=None,
            period_end=None,
            issue_date=date(2024, 5, 10),
            total_eur=100.0,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(inv)
        db.flush()
        result = normalize_invoice(inv, [], None, org.id)
        assert result.month_key == "2024-05"

    def test_endpoint_org_scoped(self, client, db):
        """org_a voit ses factures, org_b ne voit rien."""
        org_a, site_a = _make_org_site(db, "OrgA", "600002001")
        org_b, site_b = _make_org_site(db, "OrgB", "600002002")
        _make_invoice_with_lines(db, site_a.id)
        _make_invoice_with_lines(db, site_b.id)

        r_a = client.get("/api/billing/invoices/normalized", headers=_h(org_a.id))
        r_b = client.get("/api/billing/invoices/normalized", headers=_h(org_b.id))
        assert r_a.status_code == 200
        assert r_b.status_code == 200
        assert len(r_a.json()["invoices"]) == 1
        assert len(r_b.json()["invoices"]) == 1
        assert r_a.json()["invoices"][0]["org_id"] == org_a.id

    def test_endpoint_month_key_filter(self, client, db):
        """?month_key=2024-01 filtre correctement."""
        org, site = _make_org_site(db, "OrgMKF", "600002003")
        _make_invoice_with_lines(db, site.id, period_start=date(2024, 1, 1), period_end=date(2024, 1, 31))
        _make_invoice_with_lines(db, site.id, period_start=date(2024, 2, 1), period_end=date(2024, 2, 28))

        r = client.get("/api/billing/invoices/normalized?month_key=2024-01", headers=_h(org.id))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["invoices"][0]["month_key"] == "2024-01"


# ========================================
# TestShadowBillingV2
# ========================================


class TestShadowBillingV2:
    def _fake_inv(self, kwh=9000, total_eur=1620.0):
        class Inv:
            pass

        Inv.energy_kwh = kwh
        Inv.total_eur = total_eur
        return Inv()

    def _fake_contract(self, energy_type="elec", price_ref=0.18):
        """energy_type must use lowercase enum value: 'elec' or 'gaz'."""

        class C:
            pass

        c = C()
        c.price_ref_eur_per_kwh = price_ref

        class ET:
            value = energy_type

        c.energy_type = ET()
        return c

    def _fake_lines(self, energy=1020.0, network=400.0, tax=200.0):
        """line_type values must use lowercase enum values: 'energy', 'network', 'tax'."""
        lines = []
        for lt_val, amt in [("energy", energy), ("network", network), ("tax", tax)]:

            class L:
                pass

            l = L()
            l.amount_eur = amt

            class LT:
                value = lt_val

            l.line_type = LT()
            lines.append(l)
        return lines

    def test_shadow_v2_elec_components(self):
        """TURPE + CSPE + TVA calculés correctement pour elec."""
        from services.billing_shadow_v2 import shadow_billing_v2, TURPE_EUR_KWH_ELEC, CSPE_EUR_KWH_ELEC

        inv = self._fake_inv(kwh=9000, total_eur=1620.0)
        contract = self._fake_contract("elec", 0.18)
        lines = self._fake_lines(1020.0, 400.0, 200.0)
        res = shadow_billing_v2(inv, lines, contract)
        assert res["energy_type"] == "ELEC"
        assert res["expected_fourniture_ht"] == round(9000 * 0.18, 2)
        assert res["expected_reseau_ht"] == round(9000 * TURPE_EUR_KWH_ELEC, 2)
        assert res["expected_taxes_ht"] == round(9000 * CSPE_EUR_KWH_ELEC, 2)
        assert res["method"] == "shadow_v2_catalog"

    def test_shadow_v2_gaz_components(self):
        """ATRD + ATRT + TICGN calculés correctement pour gaz."""
        from services.billing_shadow_v2 import shadow_billing_v2, ATRD_EUR_KWH_GAZ, ATRT_EUR_KWH_GAZ, TICGN_EUR_KWH_GAZ

        inv = self._fake_inv(kwh=6000, total_eur=540.0)
        contract = self._fake_contract("gaz", 0.09)
        lines = self._fake_lines(192.0, 220.0, 128.0)
        res = shadow_billing_v2(inv, lines, contract)
        assert res["energy_type"] == "GAZ"
        assert res["expected_reseau_ht"] == round(6000 * (ATRD_EUR_KWH_GAZ + ATRT_EUR_KWH_GAZ), 2)
        assert res["expected_taxes_ht"] == round(6000 * TICGN_EUR_KWH_GAZ, 2)

    def test_shadow_v2_delta_reseau_above_threshold(self):
        """delta_reseau significatif quand NETWORK ligne inflée × 2.3."""
        from services.billing_shadow_v2 import shadow_billing_v2, TURPE_EUR_KWH_ELEC

        inv = self._fake_inv(kwh=9000, total_eur=2600.0)
        contract = self._fake_contract("elec", 0.18)
        inflated_network = round(9000 * TURPE_EUR_KWH_ELEC * 2.3, 2)
        lines = self._fake_lines(energy=1020.0, network=inflated_network, tax=200.0)
        res = shadow_billing_v2(inv, lines, contract)
        pct = abs(res["delta_reseau"] / res["expected_reseau_ht"] * 100)
        assert pct > 20  # doit déclencher R13 HIGH

    def test_shadow_v2_delta_taxes_above_threshold(self):
        """delta_taxes > 5% quand TAX ligne = CSPE × 1.08."""
        from services.billing_shadow_v2 import shadow_billing_v2, CSPE_EUR_KWH_ELEC

        inv = self._fake_inv(kwh=9000, total_eur=1639.0)
        contract = self._fake_contract("elec", 0.18)
        inflated_tax = round(9000 * CSPE_EUR_KWH_ELEC * 1.08, 2)
        lines = self._fake_lines(energy=1020.0, network=400.0, tax=inflated_tax)
        res = shadow_billing_v2(inv, lines, contract)
        pct = abs(res["delta_taxes"] / res["expected_taxes_ht"] * 100)
        assert pct > 5  # doit déclencher R14

    def test_shadow_v2_no_anomaly_within_threshold(self):
        """Pas d'anomalie réseau/taxes dans les seuils normaux."""
        from services.billing_shadow_v2 import shadow_billing_v2, TURPE_EUR_KWH_ELEC, CSPE_EUR_KWH_ELEC

        inv = self._fake_inv(kwh=9000, total_eur=1620.0)
        contract = self._fake_contract("elec", 0.18)
        # Normal lines (within 2% of expected)
        lines = self._fake_lines(
            energy=1020.0,
            network=round(9000 * TURPE_EUR_KWH_ELEC * 0.99, 2),
            tax=round(9000 * CSPE_EUR_KWH_ELEC * 0.99, 2),
        )
        res = shadow_billing_v2(inv, lines, contract)
        pct_reseau = abs(res["delta_reseau"] / res["expected_reseau_ht"] * 100)
        pct_taxes = abs(res["delta_taxes"] / res["expected_taxes_ht"] * 100)
        assert pct_reseau < 10
        assert pct_taxes < 5


# ========================================
# TestR13R14
# ========================================


class TestR13R14:
    def _make_full_invoice(self, db, site_id, contract_id, energy_amt, network_amt, tax_amt, total_eur, kwh=9000):
        inv = EnergyInvoice(
            site_id=site_id,
            contract_id=contract_id,
            invoice_number=f"R13R14-{network_amt:.0f}",
            period_start=date(2024, 4, 1),
            period_end=date(2024, 4, 30),
            total_eur=total_eur,
            energy_kwh=kwh,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(inv)
        db.flush()
        for lt, lbl, amt in [
            (InvoiceLineType.ENERGY, "Energie", energy_amt),
            (InvoiceLineType.NETWORK, "Réseau", network_amt),
            (InvoiceLineType.TAX, "Taxes", tax_amt),
        ]:
            db.add(EnergyInvoiceLine(invoice_id=inv.id, line_type=lt, label=lbl, amount_eur=amt))
        db.flush()
        return inv

    def test_r13_high_above_20pct(self, db):
        """R13 HIGH quand réseau > 20% au-dessus attendu."""
        from services.billing_service import _rule_reseau_mismatch
        from services.billing_shadow_v2 import TURPE_EUR_KWH_ELEC

        org, site = _make_org_site(db, "OrgR13H", "600003001")
        contract = _make_contract(db, site.id)
        inflated_network = round(9000 * TURPE_EUR_KWH_ELEC * 2.3, 2)
        total = round(1020 + inflated_network + 200, 2)
        inv = self._make_full_invoice(
            db, site.id, contract.id, energy_amt=1020, network_amt=inflated_network, tax_amt=200, total_eur=total
        )
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = _rule_reseau_mismatch(inv, contract, lines)
        assert result is not None
        assert result["type"] == "reseau_mismatch"
        assert result["severity"] == "high"

    def test_r13_medium_10_to_20pct(self, db):
        """R13 MEDIUM quand réseau entre 10% et 20% au-dessus attendu."""
        from services.billing_service import _rule_reseau_mismatch
        from services.billing_shadow_v2 import TURPE_EUR_KWH_ELEC

        org, site = _make_org_site(db, "OrgR13M", "600003002")
        contract = _make_contract(db, site.id)
        # 15% above expected
        network = round(9000 * TURPE_EUR_KWH_ELEC * 1.15, 2)
        total = round(1020 + network + 200, 2)
        inv = self._make_full_invoice(
            db, site.id, contract.id, energy_amt=1020, network_amt=network, tax_amt=200, total_eur=total
        )
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = _rule_reseau_mismatch(inv, contract, lines)
        assert result is not None
        assert result["severity"] == "medium"

    def test_r13_no_anomaly_below_10pct(self, db):
        """R13 = None quand réseau dans seuil (< 10%)."""
        from services.billing_service import _rule_reseau_mismatch
        from services.billing_shadow_v2 import TURPE_EUR_KWH_ELEC

        org, site = _make_org_site(db, "OrgR13N", "600003003")
        contract = _make_contract(db, site.id)
        # 2% above expected (normal)
        network = round(9000 * TURPE_EUR_KWH_ELEC * 1.02, 2)
        total = round(1020 + network + 200, 2)
        inv = self._make_full_invoice(
            db, site.id, contract.id, energy_amt=1020, network_amt=network, tax_amt=200, total_eur=total
        )
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = _rule_reseau_mismatch(inv, contract, lines)
        assert result is None

    def test_r14_medium_above_5pct(self, db):
        """R14 MEDIUM quand taxes > 5% au-dessus attendu."""
        from services.billing_service import _rule_taxes_mismatch
        from services.billing_shadow_v2 import CSPE_EUR_KWH_ELEC

        org, site = _make_org_site(db, "OrgR14M", "600003004")
        contract = _make_contract(db, site.id)
        # 8% above expected CSPE
        tax = round(9000 * CSPE_EUR_KWH_ELEC * 1.08, 2)
        total = round(1020 + 400 + tax, 2)
        inv = self._make_full_invoice(
            db, site.id, contract.id, energy_amt=1020, network_amt=400, tax_amt=tax, total_eur=total
        )
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = _rule_taxes_mismatch(inv, contract, lines)
        assert result is not None
        assert result["type"] == "taxes_mismatch"
        assert result["severity"] == "medium"


# ========================================
# TestSeedAndCoverage
# ========================================


class TestSeedAndCoverage:
    def test_seed_creates_expected_invoices(self, db):
        """Seed 36 mois crée ~67 factures (36 elec - 3 gaps + 36 gaz - 1 gap = 68)."""
        from services.billing_seed import seed_billing_demo

        # Need 2+ sites
        _, site_a = _make_org_site(db, "SeedOrg", "600004001")
        _, site_b = _make_org_site(db, "SeedOrg2", "600004002")
        result = seed_billing_demo(db)
        assert "error" not in result
        assert result.get("invoices_created", 0) > 0
        assert result.get("contracts_created") == 2

    def test_seed_is_idempotent(self, db):
        """Appeler seed_billing_demo deux fois → skip au second appel."""
        from services.billing_seed import seed_billing_demo

        _make_org_site(db, "SeedIdmp1", "600004010")
        _make_org_site(db, "SeedIdmp2", "600004011")
        r1 = seed_billing_demo(db)
        r2 = seed_billing_demo(db)
        assert "error" not in r1
        assert r2.get("skipped") is True

    def test_seed_has_controlled_gaps(self, db):
        """2023-03 et 2024-09 manquants pour site_a."""
        from services.billing_seed import seed_billing_demo, SOURCE_TAG

        _make_org_site(db, "SeedGap1", "600004020")
        _make_org_site(db, "SeedGap2", "600004021")
        seed_billing_demo(db)
        gap_mar = (
            db.query(EnergyInvoice)
            .filter(
                EnergyInvoice.source == SOURCE_TAG,
                EnergyInvoice.invoice_number == "EDF-2023-03",
            )
            .count()
        )
        gap_sep = (
            db.query(EnergyInvoice)
            .filter(
                EnergyInvoice.source == SOURCE_TAG,
                EnergyInvoice.invoice_number == "EDF-2024-09",
            )
            .count()
        )
        assert gap_mar == 0
        assert gap_sep == 0

    def test_seed_has_partial_months(self, db):
        """2023-06 → facture partielle (period_end = 15)."""
        from services.billing_seed import seed_billing_demo, SOURCE_TAG

        _make_org_site(db, "SeedPart1", "600004030")
        _make_org_site(db, "SeedPart2", "600004031")
        seed_billing_demo(db)
        inv = (
            db.query(EnergyInvoice)
            .filter(
                EnergyInvoice.source == SOURCE_TAG,
                EnergyInvoice.invoice_number == "EDF-2023-06",
            )
            .first()
        )
        assert inv is not None
        assert inv.period_end.day == 15

    def test_empty_org_returns_200_not_error(self, client, db):
        """Org sans factures → /invoices/normalized retourne 200 + empty, pas d'erreur."""
        org, _ = _make_org_site(db, "OrgEmpty", "600005001")
        r = client.get("/api/billing/invoices/normalized", headers=_h(org.id))
        assert r.status_code == 200
        data = r.json()
        assert data["invoices"] == []
        assert data["total"] == 0


# ========================================
# TestPDFImportDoD — 3 smoke tests E2E
# ========================================


class TestPDFImportDoD:
    """DoD P0 smoke tests — vérifie le flux PDF import complet."""

    def _fake_invoice_domain(self):
        """Construit un faux Invoice domain avec 2 composantes (CONSO_BASE + TURPE_FIXE)."""
        from app.bill_intelligence.domain import (
            Invoice,
            InvoiceComponent,
            InvoiceStatus,
            EnergyType,
            ComponentType,
        )
        from datetime import date

        comp1 = InvoiceComponent(
            component_type=ComponentType.CONSO_BASE,
            label="Energie base",
            quantity=4500.0,
            unit="kWh",
            unit_price=0.18,
            amount_ht=810.0,
            tva_rate=20.0,
        )
        comp2 = InvoiceComponent(
            component_type=ComponentType.TURPE_FIXE,
            label="TURPE gestion",
            amount_ht=150.0,
            tva_rate=5.5,
        )
        comp3 = InvoiceComponent(
            component_type=ComponentType.ACCISE,
            label="Accise electricite",
            amount_ht=101.25,
            tva_rate=20.0,
        )
        return Invoice(
            invoice_id="TEST-2024-01",
            energy_type=EnergyType.ELEC,
            supplier="EDF Test",
            pdl_pce="12345678901234",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            invoice_date=date(2024, 2, 5),
            total_ht=1061.25,
            total_ttc=1291.25,
            conso_kwh=4500.0,
            components=[comp1, comp2, comp3],
            status=InvoiceStatus.PARSED,
            parsing_confidence=0.92,
        )

    def test_pdf_import_creates_invoice_lines(self, client, db):
        """P0-1 : POST /billing/import-pdf crée des EnergyInvoiceLine depuis les composantes."""
        from unittest.mock import patch, MagicMock

        org, site = _make_org_site(db, "OrgPDF1", "600006001")
        fake_domain = self._fake_invoice_domain()

        fake_bytes = b"%PDF-1.4 fake"
        with patch(
            "app.bill_intelligence.parsers.pdf_parser.parse_pdf_bytes",
            return_value=fake_domain,
        ):
            r = client.post(
                f"/api/billing/import-pdf?site_id={site.id}",
                files={"file": ("facture.pdf", fake_bytes, "application/pdf")},
                headers=_h(org.id),
            )

        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "imported"
        invoice_id = data["invoice_id"]

        # Vérifier que les lignes ont été créées (P0-1)
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == invoice_id).all()
        assert len(lines) == 3, f"Attendu 3 lignes, eu {len(lines)}"

        line_types = {l.line_type for l in lines}
        assert InvoiceLineType.ENERGY in line_types
        assert InvoiceLineType.NETWORK in line_types
        assert InvoiceLineType.TAX in line_types

    def test_billing_periods_returns_kwh(self, client, db):
        """P0-2 : GET /billing/periods retourne energy_kwh pour chaque période."""
        org, site = _make_org_site(db, "OrgPDF2", "600006002")
        # Créer une facture avec kWh
        inv = EnergyInvoice(
            site_id=site.id,
            invoice_number="TEST-KWH-2024-01",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            issue_date=date(2024, 2, 5),
            total_eur=1291.25,
            energy_kwh=4500.0,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(inv)
        db.commit()

        r = client.get(f"/api/billing/periods?site_id={site.id}", headers=_h(org.id))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] >= 1
        period = data["periods"][0]
        assert "energy_kwh" in period, "Champ energy_kwh manquant dans /billing/periods"
        assert period["energy_kwh"] == 4500.0

    def test_pdf_import_kb_updated_flag(self, client, db):
        """P0-5 : POST /billing/import-pdf retourne kb_updated=True si run_audit=True."""
        from unittest.mock import patch

        org, site = _make_org_site(db, "OrgPDF3", "600006003")
        fake_domain = self._fake_invoice_domain()

        fake_bytes = b"%PDF-1.4 fake"
        with patch(
            "app.bill_intelligence.parsers.pdf_parser.parse_pdf_bytes",
            return_value=fake_domain,
        ):
            r = client.post(
                f"/api/billing/import-pdf?site_id={site.id}&run_audit=true",
                files={"file": ("facture.pdf", fake_bytes, "application/pdf")},
                headers=_h(org.id),
            )

        assert r.status_code == 200, r.text
        data = r.json()
        assert "kb_updated" in data, "Champ kb_updated manquant dans la réponse import-pdf"
        assert data["kb_updated"] is True
        assert "kb_rules_applied" in data
        assert isinstance(data["kb_rules_applied"], list)


# ========================================
# TestTimelineAllSites
# ========================================


class TestTimelineAllSites:
    def test_billing_periods_no_site_id_returns_data(self, client, db):
        """GET /billing/periods sans site_id retourne des périodes quand des factures existent."""
        org, site = _make_org_site(db, "OrgTimeline1", "600007001")
        inv = EnergyInvoice(
            site_id=site.id,
            invoice_number="TIMELINE-TEST-001",
            period_start=date(2024, 3, 1),
            period_end=date(2024, 3, 31),
            issue_date=date(2024, 4, 5),
            total_eur=800.0,
            energy_kwh=3200.0,
            status=BillingInvoiceStatus.IMPORTED,
            source="test",
        )
        db.add(inv)
        db.commit()

        # Sans site_id → agrégation all-org (root cause fix : front ne doit plus envoyer site_id=None)
        r = client.get("/api/billing/periods", headers=_h(org.id))
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "periods" in data, "Champ 'periods' absent de la réponse"
        assert data["total"] >= 1, "Aucune période retournée alors qu'une facture existe"
        # Vérifier que les champs DoD sont présents
        period = data["periods"][0]
        assert "energy_kwh" in period, "Champ energy_kwh absent de la période"
