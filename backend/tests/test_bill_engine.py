"""
PROMEOS Bill Intelligence — Tests for engine pipeline.
AC: parser, 20 rules, shadow billing, CSV export, HTML report all work.
"""

import sys
import os
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.bill_intelligence.parsers.json_parser import (
    parse_json_file,
    parse_json_invoice,
    list_demo_invoices,
    load_all_demo_invoices,
)
from app.bill_intelligence.rules.audit_rules_v0 import run_all_rules, ALL_RULES
from app.bill_intelligence.engine import (
    audit_invoice,
    shadow_billing_l1,
    full_pipeline,
    anomalies_to_csv,
    report_to_html,
)
from app.bill_intelligence.domain import (
    Invoice,
    InvoiceComponent,
    EnergyType,
    ShadowLevel,
    ComponentType,
    AnomalyType,
    InvoiceStatus,
)


DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices", "demo")


# ========================================
# Parser tests
# ========================================


def test_list_demo_invoices():
    """Demo invoice files exist."""
    files = list_demo_invoices()
    assert len(files) >= 3


def test_parse_demo_elec():
    """Parse demo elec invoice."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_edf_2025_01.json"))
    assert inv.invoice_id == "DEMO-ELEC-001"
    assert inv.energy_type == EnergyType.ELEC
    assert inv.supplier == "EDF Entreprises"
    assert inv.total_ttc == 3293.87
    assert len(inv.components) >= 7
    assert inv.status == InvoiceStatus.PARSED
    assert inv.parsing_confidence == 1.0


def test_parse_demo_gaz():
    """Parse demo gaz invoice."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_gaz_engie_2025_01.json"))
    assert inv.invoice_id == "DEMO-GAZ-001"
    assert inv.energy_type == EnergyType.GAZ
    assert len(inv.components) >= 6


def test_parse_json_string():
    """Parse from JSON string."""
    data = {
        "invoice_id": "TEST-001",
        "energy_type": "elec",
        "supplier": "Test",
        "total_ht": 100.0,
        "total_ttc": 120.0,
        "total_tva": 20.0,
        "components": [{"component_type": "abonnement", "label": "Abo", "amount_ht": 100.0}],
    }
    inv = parse_json_invoice(json.dumps(data))
    assert inv.invoice_id == "TEST-001"
    assert len(inv.components) == 1


def test_load_all_demo():
    """Load all demo invoices."""
    invoices = load_all_demo_invoices()
    assert len(invoices) >= 3


# ========================================
# Audit rules tests
# ========================================


def test_all_rules_registered():
    """20 audit rules registered."""
    assert len(ALL_RULES) == 20


def test_rules_clean_invoice():
    """Clean invoice produces few/no anomalies."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_edf_2025_01.json"))
    anomalies = run_all_rules(inv)
    # Clean invoice may have some INFO-level anomalies
    errors = [a for a in anomalies if a.severity.value in ("error", "critical")]
    # Should have no critical/error on a well-formed demo invoice
    assert len(errors) == 0, f"Unexpected errors: {[a.message for a in errors]}"


def test_rules_detect_tva_errors():
    """Error invoice triggers TVA anomalies."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_erreur_tva_2025_03.json"))
    anomalies = run_all_rules(inv)
    tva_errors = [a for a in anomalies if a.anomaly_type == AnomalyType.TVA_ERROR]
    assert len(tva_errors) >= 2, f"Expected TVA errors, got {len(tva_errors)}"


def test_rules_detect_opaque_component():
    """Error invoice has opaque component."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_erreur_tva_2025_03.json"))
    anomalies = run_all_rules(inv)
    opaque = [a for a in anomalies if a.rule_card_id == "RULE_R09_OPAQUE"]
    assert len(opaque) >= 1


def test_rule_sum_ht():
    """R01: detect HT sum mismatch."""
    inv = Invoice(
        invoice_id="TEST-SUM",
        energy_type=EnergyType.ELEC,
        supplier="Test",
        total_ht=100.0,
        components=[
            InvoiceComponent(component_type=ComponentType.ABONNEMENT, label="Abo", amount_ht=50.0),
            InvoiceComponent(component_type=ComponentType.CONSO_BASE, label="Conso", amount_ht=60.0),
        ],
    )
    from app.bill_intelligence.rules.audit_rules_v0 import rule_r01_sum_ht

    anomalies = rule_r01_sum_ht(inv)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.ARITHMETIC_ERROR


def test_rule_ttc():
    """R02: detect TTC mismatch."""
    inv = Invoice(
        invoice_id="TEST-TTC",
        energy_type=EnergyType.ELEC,
        supplier="Test",
        total_ht=100.0,
        total_tva=20.0,
        total_ttc=125.0,  # Should be 120
    )
    from app.bill_intelligence.rules.audit_rules_v0 import rule_r02_ttc_check

    anomalies = rule_r02_ttc_check(inv)
    assert len(anomalies) == 1


def test_rule_empty_invoice():
    """R15: detect empty invoice."""
    inv = Invoice(
        invoice_id="TEST-EMPTY",
        energy_type=EnergyType.ELEC,
        supplier="Test",
    )
    from app.bill_intelligence.rules.audit_rules_v0 import rule_r15_empty_invoice

    anomalies = rule_r15_empty_invoice(inv)
    assert len(anomalies) == 1
    assert anomalies[0].severity.value == "critical"


# ========================================
# Engine pipeline tests
# ========================================


def test_audit_invoice():
    """Audit sets status and shadow level."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_edf_2025_01.json"))
    inv = audit_invoice(inv)
    assert inv.status == InvoiceStatus.AUDITED
    assert inv.shadow_level == ShadowLevel.L1_PARTIAL
    assert inv.engine_version is not None


def test_shadow_billing_l1():
    """Shadow billing L1 produces result."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_edf_2025_01.json"))
    shadow = shadow_billing_l1(inv)
    assert shadow.shadow_level == ShadowLevel.L1_PARTIAL
    assert shadow.shadow_total_ht is not None
    assert shadow.shadow_total_ttc is not None
    assert shadow.delta_ht is not None


def test_full_pipeline():
    """Full pipeline returns AuditReport."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_edf_2025_01.json"))
    report = full_pipeline(inv)
    assert report.invoice_id == "DEMO-ELEC-001"
    assert report.coverage_level == "L1"
    assert report.engine_version is not None
    assert report.generated_at is not None


def test_full_pipeline_error_invoice():
    """Pipeline on error invoice detects anomalies."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_erreur_tva_2025_03.json"))
    report = full_pipeline(inv)
    assert report.total_anomalies >= 3
    assert report.coverage_level == "L1"


# ========================================
# Export tests
# ========================================


def test_anomalies_csv():
    """CSV export produces valid CSV."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_erreur_tva_2025_03.json"))
    inv = audit_invoice(inv)
    csv_str = anomalies_to_csv([a.to_dict() for a in inv.anomalies], inv.invoice_id)
    lines = csv_str.strip().split("\n")
    assert len(lines) >= 2  # header + at least 1 anomaly
    assert "invoice_id" in lines[0]


def test_report_html():
    """HTML report generates valid HTML."""
    inv = parse_json_file(os.path.join(DEMO_DIR, "facture_elec_edf_2025_01.json"))
    report = full_pipeline(inv)
    html = report_to_html(report)
    assert "<!DOCTYPE html>" in html
    assert "PROMEOS Bill Intelligence" in html
    assert "DEMO-ELEC-001" in html
    assert "EDF Entreprises" in html


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
