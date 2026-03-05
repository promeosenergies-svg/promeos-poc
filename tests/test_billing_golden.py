"""
test_billing_golden.py — Golden tests for billing PDF extraction.

For each PDF in tests/billing_golden/expected/:
1. Load PDF, run golden_build.build_golden() → "actual" JSON
2. Load expected JSON from tests/billing_golden/expected/
3. Compare totals with 0.01 EUR tolerance
4. Verify arithmetic coherence:
   - HTVA == supply_ht + network_ht + taxes_ht
   - TVA sum == total TVA per vat_breakdown
   - TTC == HTVA + sum(vat_breakdown amounts)
5. Verify line sums match category totals
6. Verify tax_code mapping (ACCISE_ELEC, CTA)
7. Verify negative lines are accepted (EDF Reprise)
"""

import json
import sys
import os
import pytest
from pathlib import Path

# Add project root and tools to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "billing"))

from golden_build import build_golden

EXPECTED_DIR = ROOT / "tests" / "billing_golden" / "expected"
PDF_DIR = Path(os.environ.get("GOLDEN_PDF_DIR", str(Path.home() / "Downloads")))

TOLERANCE = 0.01  # EUR


def _load_expected(name: str) -> dict:
    """Load expected golden JSON."""
    path = EXPECTED_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _pdf_path(source_file: str) -> Path:
    """Resolve PDF path from source_file name."""
    return PDF_DIR / source_file


def _approx(a, b, tol=TOLERANCE):
    """Check if two floats are approximately equal."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


# ======================================================================
# Parametrized golden test: one test per expected JSON file
# ======================================================================


def _golden_cases():
    """Discover expected JSON files and pair with PDF paths."""
    cases = []
    if not EXPECTED_DIR.exists():
        return cases
    for json_path in sorted(EXPECTED_DIR.glob("*.json")):
        with open(json_path, encoding="utf-8") as f:
            expected = json.load(f)
        source_file = expected["invoice_meta"]["source_file"]
        pdf_path = _pdf_path(source_file)
        if pdf_path.exists():
            cases.append(pytest.param(
                str(pdf_path), expected, json_path.stem,
                id=json_path.stem,
            ))
    return cases


@pytest.mark.parametrize("pdf_path,expected,name", _golden_cases())
class TestBillingGolden:
    """Golden tests: extract PDF → compare to expected JSON."""

    def _actual(self, pdf_path):
        return build_golden(pdf_path)

    # --- Totals comparison ---

    def test_totals_supply_ht(self, pdf_path, expected, name):
        actual = self._actual(pdf_path)
        assert _approx(actual["totals"]["supply_ht"], expected["totals"]["supply_ht"]), \
            f"supply_ht: {actual['totals']['supply_ht']} != {expected['totals']['supply_ht']}"

    def test_totals_network_ht(self, pdf_path, expected, name):
        actual = self._actual(pdf_path)
        assert _approx(actual["totals"]["network_ht"], expected["totals"]["network_ht"]), \
            f"network_ht: {actual['totals']['network_ht']} != {expected['totals']['network_ht']}"

    def test_totals_taxes_ht(self, pdf_path, expected, name):
        actual = self._actual(pdf_path)
        assert _approx(actual["totals"]["taxes_ht"], expected["totals"]["taxes_ht"]), \
            f"taxes_ht: {actual['totals']['taxes_ht']} != {expected['totals']['taxes_ht']}"

    def test_totals_htva(self, pdf_path, expected, name):
        actual = self._actual(pdf_path)
        assert _approx(actual["totals"]["htva"], expected["totals"]["htva"]), \
            f"htva: {actual['totals']['htva']} != {expected['totals']['htva']}"

    def test_totals_ttc(self, pdf_path, expected, name):
        actual = self._actual(pdf_path)
        assert _approx(actual["totals"]["ttc"], expected["totals"]["ttc"]), \
            f"ttc: {actual['totals']['ttc']} != {expected['totals']['ttc']}"

    # --- Arithmetic coherence ---

    def test_htva_equals_sum_categories(self, pdf_path, expected, name):
        """HTVA == supply_ht + network_ht + taxes_ht + other_ht."""
        actual = self._actual(pdf_path)
        t = actual["totals"]
        computed = (t["supply_ht"] or 0) + (t["network_ht"] or 0) + (t["taxes_ht"] or 0) + (t.get("other_ht") or 0)
        assert _approx(t["htva"], computed), \
            f"HTVA {t['htva']} != supply({t['supply_ht']})+network({t['network_ht']})+taxes({t['taxes_ht']})+other({t.get('other_ht')})={computed}"

    def test_vat_sum_coherence(self, pdf_path, expected, name):
        """Sum of vat_breakdown amounts should be consistent."""
        actual = self._actual(pdf_path)
        t = actual["totals"]
        if t["vat_breakdown"] and not t.get("other_ht"):
            vat_sum = sum(v["amount"] for v in t["vat_breakdown"])
            # TTC = HTVA + VAT
            computed_ttc = (t["htva"] or 0) + vat_sum
            assert _approx(t["ttc"], computed_ttc), \
                f"TTC {t['ttc']} != HTVA({t['htva']})+VAT({vat_sum})={computed_ttc}"

    def test_ttc_equals_htva_plus_vat(self, pdf_path, expected, name):
        """TTC == HTVA + total TVA."""
        actual = self._actual(pdf_path)
        t = actual["totals"]
        # Skip if other_ht present (services/penalties have separate TVA treatment)
        if t["vat_breakdown"] and not t.get("other_ht"):
            total_vat = sum(v["amount"] for v in t["vat_breakdown"])
            computed = (t["htva"] or 0) + total_vat
            assert _approx(t["ttc"], computed), \
                f"TTC {t['ttc']} != HTVA({t['htva']})+TVA({total_vat})={computed}"

    # --- Line sums vs category totals ---

    def test_lines_sum_supply(self, pdf_path, expected, name):
        """Sum of SUPPLY lines == supply_ht."""
        actual = self._actual(pdf_path)
        line_sum = sum(l["amount_ht"] for l in actual["lines"] if l["category"] == "SUPPLY")
        assert _approx(line_sum, actual["totals"]["supply_ht"]), \
            f"SUPPLY lines sum {line_sum} != {actual['totals']['supply_ht']}"

    def test_lines_sum_network(self, pdf_path, expected, name):
        """Sum of NETWORK lines == network_ht."""
        actual = self._actual(pdf_path)
        line_sum = sum(l["amount_ht"] for l in actual["lines"] if l["category"] == "NETWORK")
        assert _approx(line_sum, actual["totals"]["network_ht"]), \
            f"NETWORK lines sum {line_sum} != {actual['totals']['network_ht']}"

    def test_lines_sum_taxes(self, pdf_path, expected, name):
        """Sum of TAX lines == taxes_ht."""
        actual = self._actual(pdf_path)
        line_sum = sum(l["amount_ht"] for l in actual["lines"] if l["category"] == "TAX")
        assert _approx(line_sum, actual["totals"]["taxes_ht"]), \
            f"TAX lines sum {line_sum} != {actual['totals']['taxes_ht']}"

    # --- Tax code mapping ---

    def test_accise_elec_mapped(self, pdf_path, expected, name):
        """At least one TAX line has tax_code=ACCISE_ELEC."""
        actual = self._actual(pdf_path)
        accise_lines = [l for l in actual["lines"] if l.get("tax_code") == "ACCISE_ELEC"]
        assert len(accise_lines) >= 1, "No ACCISE_ELEC tax_code found in lines"

    def test_cta_mapped(self, pdf_path, expected, name):
        """At least one TAX line has tax_code=CTA."""
        actual = self._actual(pdf_path)
        cta_lines = [l for l in actual["lines"] if l.get("tax_code") == "CTA"]
        assert len(cta_lines) >= 1, "No CTA tax_code found in lines"

    # --- Negative lines (EDF Reprise) ---

    def test_negative_lines_accepted(self, pdf_path, expected, name):
        """Negative amount_ht lines are preserved (EDF Reprise pattern)."""
        actual = self._actual(pdf_path)
        if actual["invoice_meta"]["supplier"] == "EDF":
            neg_lines = [l for l in actual["lines"] if (l["amount_ht"] or 0) < 0]
            assert len(neg_lines) >= 1, "EDF invoice should have Reprise (negative) lines"

    # --- Line count ---

    def test_line_count(self, pdf_path, expected, name):
        """Actual line count matches expected."""
        actual = self._actual(pdf_path)
        assert len(actual["lines"]) == len(expected["lines"]), \
            f"Line count: {len(actual['lines'])} != {len(expected['lines'])}"

    # --- Invoice meta ---

    def test_invoice_id(self, pdf_path, expected, name):
        actual = self._actual(pdf_path)
        assert actual["invoice_meta"]["invoice_id"] == expected["invoice_meta"]["invoice_id"]

    def test_pdl(self, pdf_path, expected, name):
        actual = self._actual(pdf_path)
        assert actual["invoice_meta"]["pdl"] == expected["invoice_meta"]["pdl"]

    def test_supplier(self, pdf_path, expected, name):
        actual = self._actual(pdf_path)
        assert actual["invoice_meta"]["supplier"] == expected["invoice_meta"]["supplier"]
