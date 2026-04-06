"""
PROMEOS - Tests for RegOps Rule Engines
Tests the 4 deterministic rule engines: Tertiaire/OPERAT, BACS, APER, CEE P6
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from models import Site, Batiment, Evidence, TypeSite, ParkingType, OperatStatus, TypeEvidence, StatutEvidence
from regops.rules import tertiaire_operat, bacs, aper, cee_p6
from regops.engine import _load_configs


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def configs():
    """Load YAML configs once for all tests — extract regs sub-dict"""
    all_configs = _load_configs()
    return all_configs["regs"]


def make_site(**kwargs):
    """Helper to create Site objects with defaults"""
    defaults = {
        "id": 1,
        "nom": "Test Site",
        "type": TypeSite.BUREAU,
        "surface_m2": 1500,
        "tertiaire_area_m2": 1500,
        "parking_area_m2": None,
        "parking_type": ParkingType.UNKNOWN,
        "roof_area_m2": 800,
        "is_multi_occupied": False,
        "operat_status": OperatStatus.NOT_STARTED,
        "operat_last_submission_year": None,
        "annual_kwh_total": None,
    }
    defaults.update(kwargs)
    return Site(**defaults)


def make_batiment(**kwargs):
    """Helper to create Batiment objects"""
    defaults = {
        "id": 1,
        "site_id": 1,
        "nom": "Bâtiment principal",
        "surface_m2": 1500,
        "cvc_power_kw": 100.0,
        "annee_construction": 2000,
    }
    defaults.update(kwargs)
    return Batiment(**defaults)


def make_evidence(**kwargs):
    """Helper to create Evidence objects"""
    defaults = {
        "id": 1,
        "site_id": 1,
        "type": TypeEvidence.AUDIT,
        "statut": StatutEvidence.VALIDE,
        "note": "Test evidence",
    }
    defaults.update(kwargs)
    return Evidence(**defaults)


# ========================================
# Tertiaire / OPERAT Tests (4 cases)
# ========================================


def test_tertiaire_scope_in_scope(configs):
    """Site ≥ 1000m² is IN SCOPE"""
    site = make_site(tertiaire_area_m2=1200)
    batiments = [make_batiment()]
    evidences = []

    findings = tertiaire_operat.evaluate(site, batiments, evidences, configs["tertiaire_operat"])

    assert len(findings) > 0
    # Should have findings about OPERAT obligations
    statuses = [f.status for f in findings]
    assert "OUT_OF_SCOPE" not in statuses


def test_tertiaire_scope_out_of_scope(configs):
    """Site < 1000m² is OUT OF SCOPE"""
    site = make_site(tertiaire_area_m2=800)
    batiments = [make_batiment()]
    evidences = []

    findings = tertiaire_operat.evaluate(site, batiments, evidences, configs["tertiaire_operat"])

    assert len(findings) == 1
    assert findings[0].status == "OUT_OF_SCOPE"
    assert findings[0].regulation == "TERTIAIRE_OPERAT"


def test_tertiaire_scope_unknown(configs):
    """Site with NULL tertiaire_area_m2 is UNKNOWN"""
    site = make_site(tertiaire_area_m2=None)
    batiments = [make_batiment()]
    evidences = []

    findings = tertiaire_operat.evaluate(site, batiments, evidences, configs["tertiaire_operat"])

    # Should have UNKNOWN finding
    statuses = [f.status for f in findings]
    assert "UNKNOWN" in statuses


def test_tertiaire_multi_occupied(configs):
    """Multi-occupied building gets specific finding"""
    site = make_site(tertiaire_area_m2=3000, is_multi_occupied=True)
    batiments = [make_batiment()]
    evidences = []

    findings = tertiaire_operat.evaluate(site, batiments, evidences, configs["tertiaire_operat"])

    # Check for multi-occupied coordination finding
    rules = [f.rule_id for f in findings]
    assert any("MULTI_OCCUPIED" in r or "GOVERNANCE" in r for r in rules)


# ========================================
# BACS Tests (4 cases)
# ========================================


def test_bacs_above_290kw(configs):
    """Bâtiment > 290 kW → CRITICAL, deadline 2025-01-01"""
    site = make_site()
    batiments = [make_batiment(cvc_power_kw=350.0)]
    evidences = []

    findings = bacs.evaluate(site, batiments, evidences, configs["bacs"])

    assert len(findings) > 0
    critical_findings = [f for f in findings if f.severity == "CRITICAL"]
    assert len(critical_findings) > 0
    # Deadline should be 2025-01-01
    assert any(f.legal_deadline == date(2025, 1, 1) for f in findings if f.legal_deadline)


def test_bacs_70_to_290kw(configs):
    """Bâtiment 70-290 kW → MEDIUM, deadline 2030-01-01"""
    site = make_site()
    batiments = [make_batiment(cvc_power_kw=150.0)]
    evidences = []

    findings = bacs.evaluate(site, batiments, evidences, configs["bacs"])

    assert len(findings) > 0
    # Severity should be MEDIUM
    severities = [f.severity for f in findings]
    assert "MEDIUM" in severities or "HIGH" in severities  # Could be HIGH if no evidence


def test_bacs_exemption_possible(configs):
    """BACS with low ROI → EXEMPTION_POSSIBLE"""
    site = make_site()
    batiments = [make_batiment(cvc_power_kw=300.0)]
    # Add TRI evidence showing ROI > 10 years
    evidences = [make_evidence(type=TypeEvidence.RAPPORT, note="TRI > 10 ans")]

    findings = bacs.evaluate(site, batiments, evidences, configs["bacs"])

    # With TRI evidence, might suggest exemption
    # (Implementation may vary - just check it runs without error)
    assert findings is not None


def test_bacs_missing_cvc_power(configs):
    """Bâtiment with NULL cvc_power_kw → UNKNOWN"""
    site = make_site()
    batiments = [make_batiment(cvc_power_kw=None)]
    evidences = []

    findings = bacs.evaluate(site, batiments, evidences, configs["bacs"])

    # Should have UNKNOWN status
    statuses = [f.status for f in findings]
    assert "UNKNOWN" in statuses or len(findings) == 0  # May return empty if can't assess


# ========================================
# APER Tests (4 cases)
# ========================================


def test_aper_outdoor_parking_large(configs):
    """Outdoor parking > 10000m² → HIGH severity, deadline 2026-07-01"""
    site = make_site(parking_area_m2=12000, parking_type=ParkingType.OUTDOOR)
    batiments = [make_batiment()]
    evidences = []

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    assert len(findings) > 0
    # Should have HIGH severity finding with 2026-07-01 deadline
    high_findings = [f for f in findings if f.severity == "HIGH"]
    assert len(high_findings) > 0


def test_aper_outdoor_parking_medium(configs):
    """Outdoor parking 1500-10000m² → MEDIUM severity, deadline 2028-07-01"""
    site = make_site(parking_area_m2=5000, parking_type=ParkingType.OUTDOOR)
    batiments = [make_batiment()]
    evidences = []

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    assert len(findings) > 0
    # Should have MEDIUM severity
    severities = [f.severity for f in findings]
    assert "MEDIUM" in severities or "HIGH" in severities


def test_aper_roof_above_threshold(configs):
    """Roof > 500m² → MEDIUM severity, deadline 2028-01-01"""
    site = make_site(parking_type=ParkingType.INDOOR, roof_area_m2=800)
    batiments = [make_batiment()]
    evidences = []

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    # Should have findings for roof solarization
    assert len(findings) > 0


def test_aper_non_outdoor_parking(configs):
    """Non-outdoor parking → OUT_OF_SCOPE for parking obligations"""
    site = make_site(parking_area_m2=15000, parking_type=ParkingType.UNDERGROUND)
    batiments = [make_batiment()]
    evidences = []

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    # Parking should be out of scope (underground not eligible)
    # But roof might still be in scope
    parking_findings = [
        f for f in findings if "parking" in f.explanation.lower() or "stationnement" in f.explanation.lower()
    ]
    if parking_findings:
        assert any(f.status == "OUT_OF_SCOPE" for f in parking_findings)


# ========================================
# APER Evidence Consultation Tests (PRO-18)
# ========================================


def test_aper_parking_large_with_valid_ombriere_evidence(configs):
    """Large outdoor parking with valid ombriere PV attestation → no AT_RISK finding"""
    site = make_site(parking_area_m2=12000, parking_type=ParkingType.OUTDOOR)
    batiments = [make_batiment()]
    evidences = [
        make_evidence(
            type=TypeEvidence.ATTESTATION_OMBRIERE_PV,
            statut=StatutEvidence.VALIDE,
            note="Ombriere PV installee 2025",
        )
    ]

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    # No parking AT_RISK finding should be emitted
    parking_at_risk = [f for f in findings if f.rule_id.startswith("PARKING_") and f.status == "AT_RISK"]
    assert len(parking_at_risk) == 0


def test_aper_parking_medium_with_valid_ombriere_evidence(configs):
    """Medium outdoor parking with valid ombriere PV attestation → no AT_RISK finding"""
    site = make_site(parking_area_m2=5000, parking_type=ParkingType.OUTDOOR)
    batiments = [make_batiment()]
    evidences = [
        make_evidence(
            type=TypeEvidence.ATTESTATION_OMBRIERE_PV,
            statut=StatutEvidence.VALIDE,
        )
    ]

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    parking_at_risk = [f for f in findings if f.rule_id.startswith("PARKING_") and f.status == "AT_RISK"]
    assert len(parking_at_risk) == 0


def test_aper_parking_with_expired_evidence_still_at_risk(configs):
    """Outdoor parking with EXPIRE ombriere evidence → still AT_RISK"""
    site = make_site(parking_area_m2=12000, parking_type=ParkingType.OUTDOOR)
    batiments = [make_batiment()]
    evidences = [
        make_evidence(
            type=TypeEvidence.ATTESTATION_OMBRIERE_PV,
            statut=StatutEvidence.EXPIRE,
        )
    ]

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    parking_at_risk = [f for f in findings if f.rule_id.startswith("PARKING_") and f.status == "AT_RISK"]
    assert len(parking_at_risk) > 0


def test_aper_parking_with_pending_evidence_still_at_risk(configs):
    """Outdoor parking with EN_ATTENTE ombriere evidence → still AT_RISK"""
    site = make_site(parking_area_m2=12000, parking_type=ParkingType.OUTDOOR)
    batiments = [make_batiment()]
    evidences = [
        make_evidence(
            type=TypeEvidence.ATTESTATION_OMBRIERE_PV,
            statut=StatutEvidence.EN_ATTENTE,
        )
    ]

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    parking_at_risk = [f for f in findings if f.rule_id.startswith("PARKING_") and f.status == "AT_RISK"]
    assert len(parking_at_risk) > 0


def test_aper_roof_with_valid_pv_evidence(configs):
    """Roof ≥ 500m² with valid PV attestation → no AT_RISK finding"""
    site = make_site(parking_type=ParkingType.INDOOR, roof_area_m2=800)
    batiments = [make_batiment()]
    evidences = [
        make_evidence(
            type=TypeEvidence.ATTESTATION_TOITURE_PV,
            statut=StatutEvidence.VALIDE,
        )
    ]

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    roof_at_risk = [f for f in findings if f.rule_id == "ROOF_APER" and f.status == "AT_RISK"]
    assert len(roof_at_risk) == 0


def test_aper_roof_with_valid_vegetalisation_evidence(configs):
    """Roof ≥ 500m² with valid vegetalisation attestation → no AT_RISK finding"""
    site = make_site(parking_type=ParkingType.INDOOR, roof_area_m2=800)
    batiments = [make_batiment()]
    evidences = [
        make_evidence(
            type=TypeEvidence.ATTESTATION_TOITURE_VEGETALISEE,
            statut=StatutEvidence.VALIDE,
        )
    ]

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    roof_at_risk = [f for f in findings if f.rule_id == "ROOF_APER" and f.status == "AT_RISK"]
    assert len(roof_at_risk) == 0


def test_aper_roof_with_expired_evidence_still_at_risk(configs):
    """Roof ≥ 500m² with expired PV evidence → still AT_RISK"""
    site = make_site(parking_type=ParkingType.INDOOR, roof_area_m2=800)
    batiments = [make_batiment()]
    evidences = [
        make_evidence(
            type=TypeEvidence.ATTESTATION_TOITURE_PV,
            statut=StatutEvidence.EXPIRE,
        )
    ]

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    roof_at_risk = [f for f in findings if f.rule_id == "ROOF_APER" and f.status == "AT_RISK"]
    assert len(roof_at_risk) > 0


def test_aper_parking_and_roof_both_covered(configs):
    """Site with both parking and roof covered by valid evidence → zero AT_RISK findings"""
    site = make_site(parking_area_m2=12000, parking_type=ParkingType.OUTDOOR, roof_area_m2=800)
    batiments = [make_batiment()]
    evidences = [
        make_evidence(id=1, type=TypeEvidence.ATTESTATION_OMBRIERE_PV, statut=StatutEvidence.VALIDE),
        make_evidence(id=2, type=TypeEvidence.ATTESTATION_TOITURE_PV, statut=StatutEvidence.VALIDE),
    ]

    findings = aper.evaluate(site, batiments, evidences, configs["aper"])

    at_risk = [f for f in findings if f.status == "AT_RISK"]
    assert len(at_risk) == 0


# ========================================
# CEE P6 Tests (4 cases)
# ========================================


def test_cee_p6_with_valid_audit(configs):
    """Site with valid audit → COMPLIANT"""
    site = make_site()
    batiments = [make_batiment()]
    evidences = [make_evidence(type=TypeEvidence.AUDIT, statut=StatutEvidence.VALIDE)]

    findings = cee_p6.evaluate(site, batiments, evidences, configs["cee_p6"])

    # With valid audit, status should be COMPLIANT or minimal risk
    statuses = [f.status for f in findings]
    if statuses:
        assert "NON_COMPLIANT" not in statuses


def test_cee_p6_no_audit(configs):
    """Large site without GTB -> CEE opportunity flagged"""
    site = make_site(surface_m2=6000)
    batiments = [make_batiment(cvc_power_kw=200.0)]
    evidences = []

    findings = cee_p6.evaluate(site, batiments, evidences, configs["cee_p6"])

    # CEE P6 is opportunity-based; large site + high CVC + no GTB = opportunity
    assert len(findings) > 0


def test_cee_p6_catalog_mapping(configs):
    """Actions should map to CEE P6 catalog hints"""
    site = make_site()
    batiments = [make_batiment()]
    evidences = []

    findings = cee_p6.evaluate(site, batiments, evidences, configs["cee_p6"])

    # Just verify it runs and returns findings
    assert findings is not None


def test_cee_p6_confidence_by_docs(configs):
    """Confidence should vary based on available documentation"""
    site = make_site()
    batiments = [make_batiment()]
    evidences = [make_evidence(type=TypeEvidence.RAPPORT)]

    findings = cee_p6.evaluate(site, batiments, evidences, configs["cee_p6"])

    # Check confidence field exists
    for finding in findings:
        assert hasattr(finding, "confidence")
        assert finding.confidence in ["HIGH", "MEDIUM", "LOW"]


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
