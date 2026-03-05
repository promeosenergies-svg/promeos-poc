"""
PROMEOS Bill Intelligence — Tests for PDF parser templates.
AC: parse 1 template elec + 1 template gaz from extracted text.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.bill_intelligence.parsers.pdf_parser import (
    parse_pdf_text,
    parse_edf_elec,
    parse_engie_gaz,
    detect_template,
    list_templates,
    _find_float,
    _find_date,
    extract_text_from_pdf,
)
from app.bill_intelligence.domain import EnergyType, InvoiceStatus, ComponentType


PDF_DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices", "pdf_demo")

EDF_TEXT = open(os.path.join(PDF_DEMO_DIR, "edf_elec_sample.txt"), encoding="utf-8").read()
ENGIE_TEXT = open(os.path.join(PDF_DEMO_DIR, "engie_gaz_sample.txt"), encoding="utf-8").read()


# ========================================
# Template detection tests
# ========================================


def test_detect_edf_template():
    """EDF template detected from text."""
    tpl = detect_template(EDF_TEXT)
    assert tpl is not None
    assert tpl.template_id == "edf_elec_v1"
    assert tpl.energy_type == EnergyType.ELEC


def test_detect_engie_template():
    """Engie template detected from text."""
    tpl = detect_template(ENGIE_TEXT)
    assert tpl is not None
    assert tpl.template_id == "engie_gaz_v1"
    assert tpl.energy_type == EnergyType.GAZ


def test_detect_unknown_template():
    """Unknown text returns None."""
    tpl = detect_template("Random text with no supplier info")
    assert tpl is None


def test_list_templates():
    """Templates are listed."""
    templates = list_templates()
    assert len(templates) == 3
    ids = [t["template_id"] for t in templates]
    assert "edf_elec_v1" in ids
    assert "engie_elec_v1" in ids
    assert "engie_gaz_v1" in ids


# ========================================
# Regex helper tests
# ========================================


def test_find_float_comma():
    """Float extraction with French comma."""
    val = _find_float("Total HT : 2772,41 EUR", r"Total\s+HT\s*:\s*([\d\s,.]+)\s*EUR")
    assert val == 2772.41


def test_find_float_dot():
    """Float extraction with dot."""
    val = _find_float("Amount: 123.45 EUR", r"Amount:\s*([\d.]+)\s*EUR")
    assert val == 123.45


def test_find_date():
    """Date extraction."""
    d = _find_date("Date facture : 15/01/2025", r"Date\s+facture\s*:\s*(\d{2}/\d{2}/\d{4})")
    assert d is not None
    assert d.year == 2025
    assert d.month == 1
    assert d.day == 15


# ========================================
# EDF Elec parser tests
# ========================================


def test_parse_edf_invoice_id():
    """EDF invoice ID extracted."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.invoice_id == "EDF-2024-12345"


def test_parse_edf_energy_type():
    """EDF energy type is ELEC."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.energy_type == EnergyType.ELEC


def test_parse_edf_supplier():
    """EDF supplier set."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.supplier == "EDF Entreprises"


def test_parse_edf_contract():
    """EDF contract ref extracted."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.contract_ref == "CTR-EDF-PRO-789"


def test_parse_edf_pdl():
    """EDF PDL extracted."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.pdl_pce == "30001234567890"


def test_parse_edf_dates():
    """EDF dates extracted."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.invoice_date is not None
    assert inv.invoice_date.year == 2025
    assert inv.period_start is not None
    assert inv.period_end is not None


def test_parse_edf_totals():
    """EDF totals extracted."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.total_ht == 2772.41
    assert inv.total_tva == 521.46
    assert inv.total_ttc == 3293.87


def test_parse_edf_consumption():
    """EDF consumption extracted."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.conso_kwh == 18500.0
    assert inv.puissance_souscrite_kva == 120.0


def test_parse_edf_components():
    """EDF components extracted."""
    inv = parse_edf_elec(EDF_TEXT)
    assert len(inv.components) >= 5
    types = [c.component_type for c in inv.components]
    assert ComponentType.ABONNEMENT in types
    assert ComponentType.CTA in types
    assert ComponentType.ACCISE in types


def test_parse_edf_status():
    """EDF parsed status."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.status == InvoiceStatus.PARSED
    assert inv.source_format == "pdf"


def test_parse_edf_confidence():
    """EDF confidence score computed."""
    inv = parse_edf_elec(EDF_TEXT)
    assert inv.parsing_confidence is not None
    assert inv.parsing_confidence > 0.5


# ========================================
# Engie Gaz parser tests
# ========================================


def test_parse_engie_invoice_id():
    """Engie invoice ID extracted."""
    inv = parse_engie_gaz(ENGIE_TEXT)
    assert inv.invoice_id == "ENGIE-2025-GAZ-001"


def test_parse_engie_energy_type():
    """Engie energy type is GAZ."""
    inv = parse_engie_gaz(ENGIE_TEXT)
    assert inv.energy_type == EnergyType.GAZ


def test_parse_engie_pce():
    """Engie PCE extracted."""
    inv = parse_engie_gaz(ENGIE_TEXT)
    assert inv.pdl_pce == "GI000789012345"


def test_parse_engie_totals():
    """Engie totals extracted."""
    inv = parse_engie_gaz(ENGIE_TEXT)
    assert inv.total_ht == 1423.67
    assert inv.total_tva == 269.34
    assert inv.total_ttc == 1693.01


def test_parse_engie_components():
    """Engie components extracted."""
    inv = parse_engie_gaz(ENGIE_TEXT)
    assert len(inv.components) >= 4
    types = [c.component_type for c in inv.components]
    assert ComponentType.ABONNEMENT in types
    assert ComponentType.CTA in types
    assert ComponentType.ACCISE in types


def test_parse_engie_confidence():
    """Engie confidence score."""
    inv = parse_engie_gaz(ENGIE_TEXT)
    assert inv.parsing_confidence > 0.5


# ========================================
# Auto-detect parser tests
# ========================================


def test_auto_detect_edf():
    """Auto-detect parses EDF text correctly."""
    inv = parse_pdf_text(EDF_TEXT)
    assert inv.energy_type == EnergyType.ELEC
    assert inv.supplier == "EDF Entreprises"


def test_auto_detect_engie():
    """Auto-detect parses Engie text correctly."""
    inv = parse_pdf_text(ENGIE_TEXT)
    assert inv.energy_type == EnergyType.GAZ
    assert inv.supplier == "Engie Entreprises"


def test_auto_detect_unknown_raises():
    """Auto-detect raises on unknown text."""
    with pytest.raises(ValueError, match="No matching PDF template"):
        parse_pdf_text("This is an unknown document with no supplier information")


# ========================================
# Text extraction fallback
# ========================================


def test_extract_text_from_txt_file():
    """extract_text_from_pdf works on .txt demo files."""
    text = extract_text_from_pdf(os.path.join(PDF_DEMO_DIR, "edf_elec_sample.txt"))
    assert "EDF" in text
    assert "kWh" in text


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
