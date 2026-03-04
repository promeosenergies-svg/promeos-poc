"""
PROMEOS — V66 Billing Rules R11+R12 + ActionItem Bridge Tests
Tests for: R11 TTC coherence, R12 contract expiry, persist_insights ActionItem bridge.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timedelta
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
    EnergyContract,
    EnergyInvoice,
    EnergyInvoiceLine,
    BillingInsight,
    BillingInvoiceStatus,
    BillingImportBatch,
    InsightStatus,
    ActionItem,
)
from models.billing_models import BillingEnergyType, InvoiceLineType
from models.enums import ActionSourceType


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


def _make_site(db):
    """Create minimal org→EJ→Portefeuille→Site; returns site."""
    org = Organisation(nom="Checks Org", type_client="bureau", actif=True, siren="500000001")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ Checks", siren="500000001")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Checks")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site Checks",
        type=TypeSite.BUREAU,
        adresse="1 rue Checks",
        code_postal="75001",
        ville="Paris",
        surface_m2=100,
        actif=True,
    )
    db.add(site)
    db.commit()
    return site


# ========================================
# R11 — TTC Coherence
# ========================================


class TestR11TtcCoherence:
    def _make_invoice_with_lines(self, db, site_id, total_eur, ht_amount, tva_amount):
        inv = EnergyInvoice(
            site_id=site_id,
            invoice_number=f"INV-R11-{id(total_eur)}",
            total_eur=total_eur,
            energy_kwh=5000.0,
            status=BillingInvoiceStatus.IMPORTED,
            source="csv",
        )
        db.add(inv)
        db.flush()
        db.add(
            EnergyInvoiceLine(
                invoice_id=inv.id,
                line_type=InvoiceLineType.ENERGY,
                label="HT",
                amount_eur=ht_amount,
            )
        )
        db.add(
            EnergyInvoiceLine(
                invoice_id=inv.id,
                line_type=InvoiceLineType.TAX,
                label="TVA",
                amount_eur=tva_amount,
            )
        )
        db.flush()
        return inv

    def test_ttc_mismatch_above_2pct_generates_anomaly(self, db):
        """R11: TTC facturé 1000 vs HT(900)+TVA(50)=950 → delta 5% → anomalie."""
        from services.billing_service import _rule_ttc_coherence

        site = _make_site(db)
        inv = self._make_invoice_with_lines(db, site.id, 1000.0, 900.0, 50.0)
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = _rule_ttc_coherence(inv, None, lines)
        assert result is not None
        assert result["type"] == "ttc_mismatch"
        assert result["severity"] == "high"
        assert result["estimated_loss_eur"] > 0

    def test_ttc_coherent_within_2pct_no_anomaly(self, db):
        """R11: TTC 1000 vs HT(900)+TVA(100)=1000 → no anomalie."""
        from services.billing_service import _rule_ttc_coherence

        site = _make_site(db)
        inv = self._make_invoice_with_lines(db, site.id, 1000.0, 900.0, 100.0)
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        result = _rule_ttc_coherence(inv, None, lines)
        assert result is None

    def test_ttc_no_lines_no_anomaly(self, db):
        """R11: no lines → skip rule."""
        from services.billing_service import _rule_ttc_coherence

        site = _make_site(db)
        inv = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-NOLINES",
            total_eur=1000.0,
            status=BillingInvoiceStatus.IMPORTED,
            source="csv",
        )
        db.add(inv)
        db.flush()
        result = _rule_ttc_coherence(inv, None, [])
        assert result is None


# ========================================
# R12 — Contract Expiry
# ========================================


class TestR12ContractExpiry:
    def _make_contract(self, db, site_id, end_date):
        contract = EnergyContract(
            site_id=site_id,
            supplier_name="EDF Test",
            energy_type=BillingEnergyType.ELEC,
            end_date=end_date,
        )
        db.add(contract)
        db.flush()
        return contract

    def _make_invoice(self, db, site_id, contract_id=None):
        inv = EnergyInvoice(
            site_id=site_id,
            invoice_number=f"INV-R12-{id(site_id)}",
            total_eur=500.0,
            status=BillingInvoiceStatus.IMPORTED,
            source="csv",
        )
        if contract_id:
            inv.contract_id = contract_id
        db.add(inv)
        db.flush()
        return inv

    def test_expired_contract_generates_critical(self, db):
        """R12: contrat expiré hier → CRITICAL."""
        from services.billing_service import _rule_contract_expiry

        site = _make_site(db)
        yesterday = date.today() - timedelta(days=1)
        contract = self._make_contract(db, site.id, yesterday)
        inv = self._make_invoice(db, site.id, contract.id)
        result = _rule_contract_expiry(inv, contract, [])
        assert result is not None
        assert result["type"] == "contract_expired"
        assert result["severity"] == "critical"

    def test_contract_expiry_soon_generates_high(self, db):
        """R12: contrat expire dans 30 jours → HIGH."""
        from services.billing_service import _rule_contract_expiry

        site = _make_site(db)
        soon = date.today() + timedelta(days=30)
        contract = self._make_contract(db, site.id, soon)
        inv = self._make_invoice(db, site.id, contract.id)
        result = _rule_contract_expiry(inv, contract, [])
        assert result is not None
        assert result["type"] == "contract_expiry_soon"
        assert result["severity"] == "high"

    def test_valid_contract_no_anomaly(self, db):
        """R12: contrat expire dans 200 jours → pas d'anomalie."""
        from services.billing_service import _rule_contract_expiry

        site = _make_site(db)
        future = date.today() + timedelta(days=200)
        contract = self._make_contract(db, site.id, future)
        inv = self._make_invoice(db, site.id, contract.id)
        result = _rule_contract_expiry(inv, contract, [])
        assert result is None

    def test_no_contract_no_anomaly(self, db):
        """R12: pas de contrat → skip rule."""
        from services.billing_service import _rule_contract_expiry

        site = _make_site(db)
        inv = self._make_invoice(db, site.id)
        result = _rule_contract_expiry(inv, None, [])
        assert result is None


# ========================================
# ActionItem Bridge
# ========================================


class TestActionItemBridge:
    def test_persist_insights_creates_action_item(self, db):
        """persist_insights creates ActionItem for each anomaly (idempotent)."""
        from services.billing_service import persist_insights

        site = _make_site(db)
        inv = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-ACTION-001",
            total_eur=1000.0,
            status=BillingInvoiceStatus.IMPORTED,
            source="csv",
        )
        db.add(inv)
        db.flush()

        anomalies = [
            {
                "type": "shadow_gap",
                "severity": "high",
                "message": "Test anomaly for bridge",
                "estimated_loss_eur": 150.0,
                "metrics": {},
            }
        ]

        persist_insights(db, inv, anomalies)

        # Verify ActionItem was created
        actions = db.query(ActionItem).filter(ActionItem.source_type == ActionSourceType.BILLING).all()
        assert len(actions) == 1
        assert actions[0].idempotency_key == f"billing:{inv.id}:shadow_gap"

    def test_persist_insights_idempotent_no_duplicate(self, db):
        """Calling persist_insights twice does not create duplicate ActionItems."""
        from services.billing_service import persist_insights

        site = _make_site(db)
        inv = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-ACTION-002",
            total_eur=1000.0,
            status=BillingInvoiceStatus.IMPORTED,
            source="csv",
        )
        db.add(inv)
        db.flush()

        anomalies = [
            {
                "type": "unit_price_high",
                "severity": "high",
                "message": "Prix unitaire eleve",
                "estimated_loss_eur": 80.0,
                "metrics": {},
            }
        ]

        persist_insights(db, inv, anomalies)
        persist_insights(db, inv, anomalies)

        # Should still be only 1 action (idempotency_key dedup)
        actions = db.query(ActionItem).filter(ActionItem.idempotency_key == f"billing:{inv.id}:unit_price_high").all()
        assert len(actions) == 1
