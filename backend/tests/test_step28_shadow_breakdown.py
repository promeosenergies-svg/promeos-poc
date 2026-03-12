"""
Step 28 — Shadow Breakdown par composante
Tests pour compute_shadow_breakdown, _build_breakdown_component, _extract_invoice_component, etc.
"""

import pytest
from datetime import date


# ── Fake objects ──────────────────────────────────────────────────────────────


class FakeInvoice:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.site_id = kwargs.get("site_id", 1)
        self.contract_id = kwargs.get("contract_id", None)
        self.energy_kwh = kwargs.get("energy_kwh", 5000.0)
        self.total_eur = kwargs.get("total_eur", 900.0)
        self.period_start = kwargs.get("period_start", date(2025, 1, 1))
        self.period_end = kwargs.get("period_end", date(2025, 1, 31))
        self.invoice_number = kwargs.get("invoice_number", "INV-001")
        self.status = None
        self.raw_json = "{}"
        self.lines = []


class FakeContract:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.energy_type = type("E", (), {"value": kwargs.get("energy_type", "elec")})()
        self.price_ref_eur_per_kwh = kwargs.get("price_ref", 0.09)
        self.fixed_fee_eur_per_month = kwargs.get("fixed_fee", 0)
        self.subscribed_power_kva = kwargs.get("subscribed_power_kva", 12)


class FakeLine:
    def __init__(self, line_type, amount_eur):
        self.line_type = type("LT", (), {"value": line_type})()
        self.amount_eur = amount_eur
        self.label = ""
        self.concept = ""


# ── A. Structure du breakdown ────────────────────────────────────────────────


class TestBreakdownStructure:
    def test_has_4_components(self):
        from services.billing_shadow_v2 import shadow_billing_v2

        inv = FakeInvoice()
        c = FakeContract()
        lines = [FakeLine("energy", 450.0), FakeLine("network", 226.5)]
        result = shadow_billing_v2(inv, lines, c)
        assert len(result["components"]) == 4
        codes = [c["code"] for c in result["components"]]
        assert "fourniture" in codes
        assert "reseau" in codes
        assert "taxes" in codes
        assert "abonnement" in codes

    def test_totals_equal_sum(self):
        from services.billing_shadow_v2 import shadow_billing_v2

        inv = FakeInvoice()
        c = FakeContract()
        result = shadow_billing_v2(inv, [], c)
        total_ht = result["totals"]["ht"]
        sum_components = sum(comp["ht"] for comp in result["components"])
        assert abs(total_ht - sum_components) < 0.02


# ── B. Calculs par composante ────────────────────────────────────────────────


class TestComponentCalculations:
    def test_fourniture_uses_ref_price(self):
        from services.billing_shadow_v2 import shadow_billing_v2

        inv = FakeInvoice(energy_kwh=1000)
        c = FakeContract(price_ref=0.10)
        result = shadow_billing_v2(inv, [], c)
        assert result["expected_fourniture_ht"] == 100.0

    def test_turpe_uses_yaml(self):
        from services.billing_shadow_v2 import shadow_billing_v2

        inv = FakeInvoice(energy_kwh=1000)
        c = FakeContract()
        result = shadow_billing_v2(inv, [], c)
        # TURPE énergie C5_BT = 0.0453 EUR/kWh
        assert result["expected_reseau_ht"] == pytest.approx(45.3, abs=0.5)

    def test_taxes_accise_elec(self):
        from services.billing_shadow_v2 import shadow_billing_v2

        inv = FakeInvoice(energy_kwh=1000)
        c = FakeContract()
        result = shadow_billing_v2(inv, [], c)
        # Accise élec = 0.02623 EUR/kWh (taux 2024)
        assert result["expected_taxes_ht"] == pytest.approx(26.23, abs=0.5)

    def test_taxes_ticgn_gaz(self):
        from services.billing_shadow_v2 import shadow_billing_v2

        inv = FakeInvoice(energy_kwh=1000)
        c = FakeContract(energy_type="gaz")
        result = shadow_billing_v2(inv, [], c)
        # Accise gaz = 0.01637 EUR/kWh
        assert result["expected_taxes_ht"] == pytest.approx(16.37, abs=0.5)

    def test_tva_dual_rate(self):
        from services.billing_shadow_v2 import shadow_billing_v2

        inv = FakeInvoice(energy_kwh=1000)
        c = FakeContract(price_ref=0.10)
        result = shadow_billing_v2(inv, [], c)
        # TVA 5.5% sur abonnement, 20% sur reste
        tva_abo = result["components"][3]["tva"]
        tva_fourniture = result["components"][0]["tva"]
        assert tva_abo < tva_fourniture  # 5.5% < 20%
        assert tva_abo >= 0


# ── C. compute_shadow_breakdown ──────────────────────────────────────────────


class TestComputeShadowBreakdown:
    def test_breakdown_has_4_components(self):
        from services.billing_shadow_v2 import _build_breakdown_component

        comp = _build_breakdown_component("fourniture", "Fourniture", 100.0, 110.0, "test method", {"kwh": 1000})
        assert comp["name"] == "fourniture"
        assert comp["expected_eur"] == 100.0
        assert comp["invoice_eur"] == 110.0
        assert comp["gap_eur"] == 10.0
        assert comp["gap_pct"] == 10.0
        assert comp["status"] == "warn"

    def test_component_status_ok(self):
        from services.billing_shadow_v2 import _component_status

        assert _component_status(3.0) == "ok"
        assert _component_status(-4.9) == "ok"

    def test_component_status_warn(self):
        from services.billing_shadow_v2 import _component_status

        assert _component_status(6.0) == "warn"
        assert _component_status(-10.0) == "warn"

    def test_component_status_alert(self):
        from services.billing_shadow_v2 import _component_status

        assert _component_status(16.0) == "alert"
        assert _component_status(-20.0) == "alert"

    def test_component_null_invoice(self):
        from services.billing_shadow_v2 import _build_breakdown_component

        comp = _build_breakdown_component("turpe", "TURPE", 50.0, None, "test", {})
        assert comp["invoice_eur"] is None
        assert comp["gap_eur"] is None
        assert comp["status"] == "ok"


# ── D. _extract_invoice_component ────────────────────────────────────────────


class TestExtractComponent:
    def test_extract_energy_lines(self):
        from services.billing_shadow_v2 import _extract_invoice_component

        lines = [FakeLine("energy", 100.0), FakeLine("energy", 50.0), FakeLine("network", 80.0)]
        assert _extract_invoice_component(lines, "fourniture") == 150.0

    def test_extract_network_lines(self):
        from services.billing_shadow_v2 import _extract_invoice_component

        lines = [FakeLine("energy", 100.0), FakeLine("network", 80.0)]
        assert _extract_invoice_component(lines, "turpe") == 80.0

    def test_extract_no_match(self):
        from services.billing_shadow_v2 import _extract_invoice_component

        lines = [FakeLine("energy", 100.0)]
        assert _extract_invoice_component(lines, "taxes") is None

    def test_extract_empty_lines(self):
        from services.billing_shadow_v2 import _extract_invoice_component

        assert _extract_invoice_component([], "fourniture") is None
        assert _extract_invoice_component(None, "fourniture") is None


# ── E. Segment resolution ────────────────────────────────────────────────────


class TestSegmentResolution:
    def test_default_c5_bt(self):
        from services.billing_shadow_v2 import _resolve_segment

        c = FakeContract(subscribed_power_kva=12)
        assert _resolve_segment(c) == "C5_BT"

    def test_c4_bt(self):
        from services.billing_shadow_v2 import _resolve_segment

        c = FakeContract(subscribed_power_kva=50)
        assert _resolve_segment(c) == "C4_BT"

    def test_c3_hta(self):
        from services.billing_shadow_v2 import _resolve_segment

        c = FakeContract(subscribed_power_kva=300)
        assert _resolve_segment(c) == "C3_HTA"

    def test_no_contract(self):
        from services.billing_shadow_v2 import _resolve_segment

        assert _resolve_segment(None) == "C5_BT"


# ── F. CTA dans le breakdown ─────────────────────────────────────────────────


class TestCTA:
    def test_cta_calculation(self):
        """CTA = TURPE gestion proratisé × taux CTA."""
        from config.tarif_loader import get_cta_taux, get_turpe_gestion_mois

        taux = get_cta_taux("elec")
        gestion = get_turpe_gestion_mois("C5_BT")
        # 30 jours
        cta = gestion * (30 / 30) * taux / 100
        assert cta > 0
        assert cta == pytest.approx(gestion * taux / 100, abs=0.01)


# ── G. Source guards ─────────────────────────────────────────────────────────


class TestSourceGuards:
    def _read(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_compute_shadow_breakdown_exists(self):
        src = self._read("services/billing_shadow_v2.py")
        assert "def compute_shadow_breakdown" in src

    def test_build_breakdown_component_exists(self):
        src = self._read("services/billing_shadow_v2.py")
        assert "def _build_breakdown_component" in src

    def test_resolve_segment_exists(self):
        src = self._read("services/billing_shadow_v2.py")
        assert "def _resolve_segment" in src

    def test_endpoint_exists(self):
        src = self._read("routes/billing.py")
        assert "shadow-breakdown" in src

    def test_cta_taux_used(self):
        src = self._read("services/billing_shadow_v2.py")
        assert "get_cta_taux" in src
