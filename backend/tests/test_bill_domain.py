"""
PROMEOS Bill Intelligence — Tests for domain model.
AC: Invoice, InvoiceComponent, InvoiceAnomaly, ShadowResult validate + serialize OK.
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.bill_intelligence.domain import (
    Invoice,
    InvoiceComponent,
    InvoiceAnomaly,
    ShadowResult,
    AuditReport,
    EnergyType,
    InvoiceStatus,
    ShadowLevel,
    ComponentType,
    AnomalyType,
    AnomalySeverity,
)


# ========================================
# Invoice tests
# ========================================


def test_create_invoice_minimal():
    """Create minimal invoice."""
    inv = Invoice(
        invoice_id="INV-2025-001",
        energy_type=EnergyType.ELEC,
        supplier="EDF Pro",
    )
    assert inv.invoice_id == "INV-2025-001"
    assert inv.energy_type == EnergyType.ELEC
    assert inv.status == InvoiceStatus.IMPORTED
    assert inv.shadow_level == ShadowLevel.L0_READ
    assert inv.components == []
    assert inv.anomalies == []


def test_create_invoice_full():
    """Create invoice with all fields."""
    inv = Invoice(
        invoice_id="INV-2025-002",
        energy_type=EnergyType.GAZ,
        supplier="Engie Pro",
        contract_ref="CTR-12345",
        pdl_pce="GI000456",
        site_id=42,
        invoice_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        period_start=date(2024, 12, 1),
        period_end=date(2024, 12, 31),
        total_ht=1500.00,
        total_tva=300.00,
        total_ttc=1800.00,
        conso_kwh=15000.0,
    )
    assert inv.total_ttc == 1800.00
    assert inv.period_start == date(2024, 12, 1)


def test_invoice_with_components():
    """Invoice with multiple components."""
    inv = Invoice(
        invoice_id="INV-2025-003",
        energy_type=EnergyType.ELEC,
        supplier="TotalEnergies",
        components=[
            InvoiceComponent(
                component_type=ComponentType.ABONNEMENT,
                label="Abonnement mensuel",
                amount_ht=45.00,
                tva_rate=20.0,
                tva_amount=9.00,
            ),
            InvoiceComponent(
                component_type=ComponentType.CONSO_HP,
                label="Consommation heures pleines",
                quantity=1200.0,
                unit="kWh",
                unit_price=0.15,
                amount_ht=180.00,
            ),
            InvoiceComponent(
                component_type=ComponentType.CONSO_HC,
                label="Consommation heures creuses",
                quantity=800.0,
                unit="kWh",
                unit_price=0.12,
                amount_ht=96.00,
            ),
            InvoiceComponent(
                component_type=ComponentType.ACCISE,
                label="Accise sur l'electricite",
                quantity=2000.0,
                unit="kWh",
                unit_price=0.02121,
                amount_ht=42.42,
            ),
        ],
    )
    assert len(inv.components) == 4
    assert inv.components[0].component_type == ComponentType.ABONNEMENT
    assert inv.components[3].unit_price == 0.02121


def test_invoice_to_dict():
    """Serialization to dict."""
    inv = Invoice(
        invoice_id="INV-DICT-001",
        energy_type=EnergyType.ELEC,
        supplier="EDF",
        total_ht=100.0,
        total_ttc=120.0,
        components=[
            InvoiceComponent(
                component_type=ComponentType.ABONNEMENT,
                label="Abo",
                amount_ht=100.0,
            ),
        ],
    )
    d = inv.to_dict()
    assert d["invoice_id"] == "INV-DICT-001"
    assert d["energy_type"] == "elec"
    assert d["nb_components"] == 1
    assert d["nb_anomalies"] == 0
    assert d["components"][0]["component_type"] == "abonnement"


def test_invoice_status_enum():
    """All status values are valid."""
    for status in InvoiceStatus:
        inv = Invoice(invoice_id="test", energy_type=EnergyType.ELEC, supplier="x", status=status)
        assert inv.status == status


def test_shadow_level_enum():
    """All shadow levels."""
    assert ShadowLevel.L0_READ.value == "L0"
    assert ShadowLevel.L1_PARTIAL.value == "L1"
    assert ShadowLevel.L2_COMPONENT.value == "L2"
    assert ShadowLevel.L3_FULL.value == "L3"


# ========================================
# Component tests
# ========================================


def test_component_types_coverage():
    """All expected component types exist."""
    expected = [
        "abonnement",
        "conso_hp",
        "conso_hc",
        "conso_base",
        "turpe_fixe",
        "turpe_puissance",
        "turpe_energie",
        "cta",
        "accise",
        "tva_reduite",
        "tva_normale",
        "terme_fixe",
        "terme_variable",
        "depassement_puissance",
        "reactive",
    ]
    actual = {ct.value for ct in ComponentType}
    for e in expected:
        assert e in actual, f"Missing ComponentType: {e}"


def test_component_with_period():
    """Component with period dates."""
    comp = InvoiceComponent(
        component_type=ComponentType.CONSO_BASE,
        label="Consommation base",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        quantity=500.0,
        unit="kWh",
        unit_price=0.14,
        amount_ht=70.0,
    )
    assert comp.period_start == date(2025, 1, 1)
    assert comp.amount_ht == 70.0


# ========================================
# Anomaly tests
# ========================================


def test_create_anomaly():
    """Create anomaly with rule card reference."""
    anom = InvoiceAnomaly(
        anomaly_id="ANOM-001",
        anomaly_type=AnomalyType.ARITHMETIC_ERROR,
        severity=AnomalySeverity.ERROR,
        message="Somme composantes (321.42) != total HT (320.00)",
        expected_value=320.00,
        actual_value=321.42,
        difference=1.42,
        rule_card_id="RULE_ARITH_TOTAL_HT",
    )
    assert anom.difference == 1.42
    d = anom.to_dict()
    assert d["anomaly_type"] == "arithmetic_error"
    assert d["rule_card_id"] == "RULE_ARITH_TOTAL_HT"


def test_anomaly_types_coverage():
    """All expected anomaly types exist."""
    expected = [
        "arithmetic_error",
        "tva_error",
        "prorata_error",
        "missing_component",
        "duplicate_charge",
        "period_overlap",
        "period_gap",
        "unit_price_anomaly",
        "total_mismatch",
    ]
    actual = {at.value for at in AnomalyType}
    for e in expected:
        assert e in actual, f"Missing AnomalyType: {e}"


# ========================================
# Shadow result tests
# ========================================


def test_shadow_result():
    """Create shadow result."""
    sr = ShadowResult(
        invoice_id="INV-2025-001",
        shadow_level=ShadowLevel.L1_PARTIAL,
        shadow_total_ht=1495.50,
        shadow_total_ttc=1794.60,
        delta_ht=-4.50,
        delta_ttc=-5.40,
        delta_percent=-0.30,
        explain=["TVA recalculee", "Prorata ajuste"],
        why_not_higher="Grilles TURPE non disponibles dans la KB",
        rule_cards_used=["RULE_ARITH_TOTAL_HT", "RULE_TVA_ARITH"],
    )
    d = sr.to_dict()
    assert d["shadow_level"] == "L1"
    assert d["delta_ht"] == -4.50
    assert len(d["explain"]) == 2
    assert len(d["rule_cards_used"]) == 2


def test_shadow_result_l0_minimal():
    """L0 shadow has no calculation."""
    sr = ShadowResult(
        invoice_id="INV-L0",
        shadow_level=ShadowLevel.L0_READ,
        why_not_higher="Facture seulement lue, pas encore auditee",
    )
    assert sr.shadow_total_ht is None
    assert sr.delta_ht is None


# ========================================
# Audit report tests
# ========================================


def test_audit_report():
    """Create audit report."""
    report = AuditReport(
        invoice_id="INV-2025-001",
        coverage_level="L1",
        total_anomalies=3,
        critical_anomalies=1,
        potential_savings_eur=45.20,
    )
    assert report.total_anomalies == 3
    assert report.potential_savings_eur == 45.20


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
