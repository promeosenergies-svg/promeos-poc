"""
Tests for enriched shadow breakdown payload (P0/P1 fixes).
Validates: identification fields, reconstitution meta, confidence,
component statuses, prorata format, CEE informational, expert section.
"""

import pytest
from datetime import date


# ── Fake objects ──────────────────────────────────────────────────────────────


class FakeInvoice:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.site_id = kwargs.get("site_id", 1)
        self.contract_id = kwargs.get("contract_id", 1)
        self.energy_kwh = kwargs.get("energy_kwh", 5000.0)
        self.total_eur = kwargs.get("total_eur", 900.0)
        self.period_start = kwargs.get("period_start", date(2025, 9, 1))
        self.period_end = kwargs.get("period_end", date(2025, 9, 29))
        self.invoice_number = kwargs.get("invoice_number", "EDF-2025-09-SB")
        self.issue_date = kwargs.get("issue_date", date(2025, 10, 1))
        self.status = None
        self.raw_json = kwargs.get("raw_json", '{"pdl_prm": "12345678901234"}')
        self.lines = []


class FakeContract:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.energy_type = type("E", (), {"value": kwargs.get("energy_type", "elec")})()
        self.price_ref_eur_per_kwh = kwargs.get("price_ref", None)  # None = missing price
        self.fixed_fee_eur_per_month = kwargs.get("fixed_fee", 10.0)
        self.subscribed_power_kva = kwargs.get("subscribed_power_kva", 108)
        self.supplier_name = kwargs.get("supplier_name", "EDF")


class FakeContractWithPrice(FakeContract):
    def __init__(self, **kwargs):
        kwargs.setdefault("price_ref", 0.145)
        super().__init__(**kwargs)


class FakeSite:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.nom = kwargs.get("nom", "Siège & Bureaux")
        self.name = kwargs.get("nom", "Siège & Bureaux")
        self.pdl = kwargs.get("pdl", None)
        self.organisation = type("O", (), {"nom": "Groupe HELIOS"})()


class FakeLine:
    def __init__(self, line_type, amount_eur, label=""):
        self.line_type = type("LT", (), {"value": line_type})()
        self.amount_eur = amount_eur
        self.label = label
        self.concept = ""


class FakeDB:
    """Minimal fake DB session that returns nothing."""

    def query(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []

    def limit(self, *args):
        return self


# ── Helpers ───────────────────────────────────────────────────────────────────


def _call_shadow_v2(invoice, lines, contract, db=None):
    from services.billing_shadow_v2 import shadow_billing_v2

    return shadow_billing_v2(invoice, lines, contract, db=db)


def _call_compute_breakdown_with_fake_db(invoice, contract, site, lines):
    """Bypass the DB-dependent compute_shadow_breakdown by calling shadow_billing_v2 + enrichment helpers."""
    from services.billing_shadow_v2 import (
        shadow_billing_v2,
        _compute_reconstitution_meta,
        _extract_pdl_prm,
        _build_breakdown_component,
    )

    v2 = shadow_billing_v2(invoice, lines, contract)

    # Simulate enriched components like compute_shadow_breakdown does
    price_source = v2["price_source"]
    fourniture_is_missing = price_source == "catalog_default"

    components = [
        _build_breakdown_component(
            "fourniture",
            "Fourniture d'énergie",
            None if fourniture_is_missing else v2["expected_fourniture_ht"],
            None,
            "formula",
            {},
            status_override="missing_price" if fourniture_is_missing else None,
            status_message="Prix non disponible" if fourniture_is_missing else None,
        ),
        _build_breakdown_component(
            "turpe",
            "Acheminement (TURPE)",
            v2["expected_reseau_ht"],
            None,
            "formula",
            {},
        ),
        _build_breakdown_component(
            "taxes",
            "Taxes",
            v2["expected_taxes_ht"],
            None,
            "formula",
            {},
        ),
    ]

    meta = _compute_reconstitution_meta(components)
    pdl = _extract_pdl_prm(invoice, site)

    return {
        "components": components,
        "meta": meta,
        "pdl_prm": pdl,
        "v2": v2,
    }


# ══════════════════════════════════════════════════════════════════════════════
# A. IDENTIFICATION FACTURE (P0.1)
# ══════════════════════════════════════════════════════════════════════════════


class TestIdentificationFields:
    def test_pdl_prm_extracted_from_raw_json(self):
        from services.billing_shadow_v2 import _extract_pdl_prm

        inv = FakeInvoice(raw_json='{"pdl_prm": "12345678901234"}')
        assert _extract_pdl_prm(inv) == "12345678901234"

    def test_pdl_prm_fallback_to_site(self):
        from services.billing_shadow_v2 import _extract_pdl_prm

        inv = FakeInvoice(raw_json="{}")
        site = FakeSite(pdl="98765432109876")
        assert _extract_pdl_prm(inv, site) == "98765432109876"

    def test_pdl_prm_none_when_unavailable(self):
        from services.billing_shadow_v2 import _extract_pdl_prm

        inv = FakeInvoice(raw_json="{}")
        assert _extract_pdl_prm(inv) is None


# ══════════════════════════════════════════════════════════════════════════════
# B. ATTENDU UNIFIÉ — PAS DE DOUBLE CONTRADICTOIRE (P0.2)
# ══════════════════════════════════════════════════════════════════════════════


class TestNoContradictoryAttendu:
    def test_missing_price_has_null_attendu(self):
        """P0.2 — Si composante missing_price, attendu_eur DOIT être None."""
        result = _call_compute_breakdown_with_fake_db(FakeInvoice(), FakeContract(price_ref=None), FakeSite(), [])
        fourniture = next(c for c in result["components"] if c["name"] == "fourniture")
        assert fourniture["status"] == "missing_price"
        assert fourniture["expected_eur"] is None

    def test_with_contract_price_has_attendu(self):
        """Si prix contrat dispo, attendu_eur doit être > 0."""
        result = _call_compute_breakdown_with_fake_db(FakeInvoice(), FakeContractWithPrice(), FakeSite(), [])
        fourniture = next(c for c in result["components"] if c["name"] == "fourniture")
        assert fourniture["status"] != "missing_price"
        assert fourniture["expected_eur"] is not None
        assert fourniture["expected_eur"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# C. RECONSTITUTION STATUS (P0.3)
# ══════════════════════════════════════════════════════════════════════════════


class TestReconstitutionStatus:
    def test_complete_when_no_missing(self):
        from services.billing_shadow_v2 import _compute_reconstitution_meta

        components = [
            {"label": "A", "status": "ok", "expected_eur": 100, "invoice_eur": 100},
            {"label": "B", "status": "ok", "expected_eur": 200, "invoice_eur": 210},
        ]
        meta = _compute_reconstitution_meta(components)
        assert meta["reconstitution_status"] == "complete"
        assert meta["confidence"] == "elevee"

    def test_partial_when_some_missing(self):
        from services.billing_shadow_v2 import _compute_reconstitution_meta

        components = [
            {"label": "Fourniture", "status": "missing_price", "expected_eur": None, "invoice_eur": 500},
            {"label": "TURPE", "status": "ok", "expected_eur": 200, "invoice_eur": 210},
            {"label": "Taxes", "status": "ok", "expected_eur": 100, "invoice_eur": 100},
        ]
        meta = _compute_reconstitution_meta(components)
        assert meta["reconstitution_status"] != "complete"
        assert "Fourniture" in meta["missing_components"]

    def test_minimal_when_majority_missing(self):
        from services.billing_shadow_v2 import _compute_reconstitution_meta

        # 80% of invoiced value is missing
        components = [
            {"label": "Fourniture", "status": "missing_price", "expected_eur": None, "invoice_eur": 800},
            {"label": "TURPE", "status": "ok", "expected_eur": 200, "invoice_eur": 200},
        ]
        meta = _compute_reconstitution_meta(components)
        assert meta["reconstitution_status"] == "minimal"
        assert meta["confidence"] in ("faible", "tres_faible")


# ══════════════════════════════════════════════════════════════════════════════
# D. CONFIDENCE (P0.4)
# ══════════════════════════════════════════════════════════════════════════════


class TestConfidence:
    def test_elevee_when_complete(self):
        from services.billing_shadow_v2 import _compute_reconstitution_meta

        components = [
            {"label": "A", "status": "ok", "expected_eur": 100, "invoice_eur": 100},
        ]
        meta = _compute_reconstitution_meta(components)
        assert meta["confidence"] == "elevee"
        assert meta["confidence_label"] == "Élevée"

    def test_tres_faible_when_70pct_missing(self):
        from services.billing_shadow_v2 import _compute_reconstitution_meta

        components = [
            {"label": "Fourniture", "status": "missing_price", "expected_eur": None, "invoice_eur": 700},
            {"label": "TURPE", "status": "ok", "expected_eur": 300, "invoice_eur": 300},
        ]
        meta = _compute_reconstitution_meta(components)
        assert meta["confidence"] == "tres_faible"
        assert meta["confidence_label"] == "Très faible"


# ══════════════════════════════════════════════════════════════════════════════
# E. PRORATA LISIBLE (P1.3)
# ══════════════════════════════════════════════════════════════════════════════


class TestProrataHumanReadable:
    def test_prorata_display_has_fraction(self):
        from services.billing_shadow_v2 import _build_breakdown_component

        comp = _build_breakdown_component(
            "abonnement",
            "Abonnement",
            14.30,
            None,
            "meth",
            {},
            prorata_display="29/365 jours",
            formula="180,00 €/mois × 29/365 jours = 14,30 € HT",
        )
        assert comp["prorata_display"] == "29/365 jours"
        assert "/" in comp["prorata_display"]
        assert "0.0" not in comp["prorata_display"]

    def test_formula_contains_jours(self):
        from services.billing_shadow_v2 import _build_breakdown_component

        comp = _build_breakdown_component(
            "abonnement",
            "Abonnement",
            14.30,
            None,
            "meth",
            {},
            prorata_display="29/365 jours",
            formula="180,00 €/mois × 29/365 jours = 14,30 € HT",
        )
        assert "jours" in comp["formula"]
        assert "0.0795" not in comp["formula"]


# ══════════════════════════════════════════════════════════════════════════════
# F. CEE INFORMATIONAL (P1.4)
# ══════════════════════════════════════════════════════════════════════════════


class TestCEEInformational:
    def test_cee_informational_has_null_attendu(self):
        from services.billing_shadow_v2 import _build_breakdown_component

        comp = _build_breakdown_component(
            "cee_implicite",
            "CEE (implicite)",
            None,
            None,
            "estimation",
            {},
            status_override="informational",
            status_message="Estimé à 358,55 €",
        )
        assert comp["expected_eur"] is None
        assert comp["status"] == "informational"
        assert "Estimé" in comp["status_message"]


# ══════════════════════════════════════════════════════════════════════════════
# G. EXPERT SECTION (P1.7)
# ══════════════════════════════════════════════════════════════════════════════


class TestExpertSection:
    def test_shadow_v2_has_meta_fields(self):
        inv = FakeInvoice()
        c = FakeContractWithPrice()
        lines = [FakeLine("energy", 450.0)]
        result = _call_shadow_v2(inv, lines, c)
        assert "method" in result
        assert "segment" in result
        assert "tariff_source" in result
        assert "price_source" in result


# ══════════════════════════════════════════════════════════════════════════════
# H. BUILD COMPONENT STATUS
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildComponentStatus:
    def test_missing_invoice_detail_when_invoice_null(self):
        from services.billing_shadow_v2 import _build_breakdown_component

        comp = _build_breakdown_component(
            "turpe",
            "TURPE",
            200.0,
            None,
            "meth",
            {},
        )
        assert comp["status"] == "missing_invoice_detail"
        assert comp["expected_eur"] == 200.0
        assert comp["gap_eur"] is None

    def test_ok_when_small_gap(self):
        from services.billing_shadow_v2 import _build_breakdown_component

        comp = _build_breakdown_component(
            "turpe",
            "TURPE",
            200.0,
            205.0,
            "meth",
            {},
        )
        assert comp["status"] == "ok"
        assert comp["gap_eur"] == 5.0

    def test_alert_when_large_gap(self):
        from services.billing_shadow_v2 import _build_breakdown_component

        comp = _build_breakdown_component(
            "turpe",
            "TURPE",
            200.0,
            280.0,
            "meth",
            {},
        )
        assert comp["status"] == "alert"
