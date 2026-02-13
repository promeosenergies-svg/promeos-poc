"""
PROMEOS Bill Intelligence — Golden Tests (Non-Regression)
Compare demo corpus audit results against expected baseline.
Any change to rules or parsing that alters anomaly output will fail here.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path

import pytest

from app.bill_intelligence.parsers.json_parser import (
    load_all_demo_invoices,
    parse_json_file,
)
from app.bill_intelligence.engine import full_pipeline, audit_invoice


# ========================================
# Fixtures
# ========================================

EXPECTED_PATH = Path(__file__).resolve().parent.parent / "data" / "demo" / "expected" / "expected_anomalies.json"


@pytest.fixture(scope="module")
def golden_data():
    """Load expected anomalies baseline."""
    with open(EXPECTED_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def all_reports():
    """Run full pipeline on all demo invoices."""
    invoices = load_all_demo_invoices()
    reports = {}
    for inv in invoices:
        report = full_pipeline(inv)
        reports[report.invoice_id] = {
            "report": report,
            "invoice": inv,
        }
    return reports


# ========================================
# Golden Tests
# ========================================

class TestGoldenCorpus:
    """Verify demo corpus produces expected anomalies."""

    def test_total_invoice_count(self, golden_data, all_reports):
        """Same number of invoices parsed."""
        assert len(all_reports) == golden_data["total_invoices"]

    def test_total_anomaly_count(self, golden_data, all_reports):
        """Total anomalies across corpus matches baseline."""
        expected_total = sum(r["total_anomalies"] for r in golden_data["results"])
        actual_total = sum(r["report"].total_anomalies for r in all_reports.values())
        assert actual_total == expected_total, (
            f"Total anomalies changed: expected {expected_total}, got {actual_total}"
        )

    def test_per_invoice_anomaly_count(self, golden_data, all_reports):
        """Each invoice has the expected number of anomalies."""
        for expected in golden_data["results"]:
            inv_id = expected["invoice_id"]
            assert inv_id in all_reports, f"Invoice {inv_id} missing from results"
            actual = all_reports[inv_id]["report"]
            assert actual.total_anomalies == expected["total_anomalies"], (
                f"Invoice {inv_id}: expected {expected['total_anomalies']} anomalies, "
                f"got {actual.total_anomalies}"
            )

    def test_coverage_level_stable(self, golden_data, all_reports):
        """Coverage level hasn't regressed."""
        for expected in golden_data["results"]:
            inv_id = expected["invoice_id"]
            actual = all_reports[inv_id]["report"]
            assert actual.coverage_level == expected["coverage_level"], (
                f"Invoice {inv_id}: coverage changed from {expected['coverage_level']} "
                f"to {actual.coverage_level}"
            )

    def test_anomaly_types_match(self, golden_data, all_reports):
        """Anomaly types and rule_card_ids match baseline."""
        for expected in golden_data["results"]:
            inv_id = expected["invoice_id"]
            if not expected["anomalies"]:
                continue
            actual_anomalies = all_reports[inv_id]["report"].anomalies
            expected_rules = sorted(a["rule_card_id"] for a in expected["anomalies"])
            actual_rules = sorted(a.get("rule_card_id", "") for a in actual_anomalies)
            assert actual_rules == expected_rules, (
                f"Invoice {inv_id}: rule_card_ids changed.\n"
                f"Expected: {expected_rules}\nActual: {actual_rules}"
            )


class TestGoldenConceptAllocation:
    """Verify concept allocation is stable."""

    def test_every_component_has_allocation(self, all_reports):
        """Every parsed component must have a ConceptAllocation."""
        for inv_id, data in all_reports.items():
            inv = data["invoice"]
            for i, comp in enumerate(inv.components):
                assert comp.allocation is not None, (
                    f"Invoice {inv_id}, component[{i}] ({comp.label}): missing allocation"
                )

    def test_allocation_confidence_range(self, all_reports):
        """All confidence scores are in [0.0, 1.0]."""
        for inv_id, data in all_reports.items():
            inv = data["invoice"]
            for comp in inv.components:
                if comp.allocation:
                    assert 0.0 <= comp.allocation.confidence <= 1.0, (
                        f"Invoice {inv_id}, {comp.label}: confidence={comp.allocation.confidence}"
                    )

    def test_concept_allocations_in_report(self, all_reports):
        """Report contains concept_allocations summary dict."""
        for inv_id, data in all_reports.items():
            report = data["report"]
            assert isinstance(report.concept_allocations, dict), (
                f"Invoice {inv_id}: concept_allocations missing or not dict"
            )

    def test_concept_totals_match_baseline(self, golden_data, all_reports):
        """Concept allocation totals match expected baseline."""
        for expected in golden_data["results"]:
            inv_id = expected["invoice_id"]
            actual = all_reports[inv_id]["report"]
            for concept, exp_total in expected.get("concept_allocations", {}).items():
                act_total = actual.concept_allocations.get(concept, 0.0)
                assert abs(act_total - exp_total) < 0.01, (
                    f"Invoice {inv_id}, concept {concept}: "
                    f"expected {exp_total}, got {act_total}"
                )


class TestGoldenTrapInvoices:
    """Specific tests for known trap invoices in the demo corpus."""

    def test_tva_error_invoice_detected(self, all_reports):
        """The TVA error invoice must trigger R03 and R18."""
        inv_id = "DEMO-ELEC-ERR-TVA"
        if inv_id not in all_reports:
            pytest.skip("TVA error invoice not in corpus")
        report = all_reports[inv_id]["report"]
        assert report.total_anomalies >= 4, (
            f"TVA error invoice should have >= 4 anomalies, got {report.total_anomalies}"
        )
        rule_ids = {a.get("rule_card_id") for a in report.anomalies}
        assert "RULE_R03_TVA_RATE" in rule_ids, "Expected R03 (TVA rate) anomaly"
        assert "RULE_R18_SUM_TVA" in rule_ids, "Expected R18 (sum TVA) anomaly"

    def test_clean_invoice_no_anomaly(self, all_reports):
        """Clean demo invoice must have 0 anomalies."""
        inv_id = "DEMO-ELEC-001"
        if inv_id not in all_reports:
            pytest.skip("Clean invoice not in corpus")
        report = all_reports[inv_id]["report"]
        assert report.total_anomalies == 0, (
            f"Clean invoice should have 0 anomalies, got {report.total_anomalies}"
        )

    def test_gaz_invoice_components(self, all_reports):
        """Gas invoice must have correct energy type."""
        gaz_invoices = [
            data for data in all_reports.values()
            if data["invoice"].energy_type.value == "gaz"
        ]
        assert len(gaz_invoices) > 0, "No gas invoices in corpus"
        for data in gaz_invoices:
            assert data["report"].coverage_level in ("L0", "L1"), (
                f"Gas invoice {data['report'].invoice_id}: unexpected coverage "
                f"{data['report'].coverage_level}"
            )

    def test_opaque_component_flagged(self, all_reports):
        """Invoice with 'autre' component must trigger R09."""
        inv_id = "DEMO-ELEC-ERR-TVA"
        if inv_id not in all_reports:
            pytest.skip("TVA error invoice not in corpus")
        report = all_reports[inv_id]["report"]
        rule_ids = {a.get("rule_card_id") for a in report.anomalies}
        assert "RULE_R09_OPAQUE" in rule_ids, "Expected R09 (opaque component) anomaly"

    def test_potential_savings_on_error_invoice(self, all_reports):
        """Invoice with TVA errors must have potential_savings_eur > 0."""
        inv_id = "DEMO-ELEC-ERR-TVA"
        if inv_id not in all_reports:
            pytest.skip("TVA error invoice not in corpus")
        report = all_reports[inv_id]["report"]
        assert report.potential_savings_eur is not None and report.potential_savings_eur > 0, (
            f"Expected savings > 0, got {report.potential_savings_eur}"
        )
