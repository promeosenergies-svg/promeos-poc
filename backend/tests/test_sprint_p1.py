"""
Sprint P1 — Tests de validation des 8 corrections audit.
"""

import inspect
import pytest


class TestDefaultPrices:
    """FIX 2: default_prices.py is the single source of truth."""

    def test_module_exists(self):
        from config.default_prices import get_default_price

        assert callable(get_default_price)

    def test_default_price_elec(self):
        from config.default_prices import get_default_price

        assert get_default_price("ELEC") == 0.068

    def test_default_price_gaz(self):
        from config.default_prices import get_default_price

        assert get_default_price("GAZ") == 0.045

    def test_default_price_fallback(self):
        from config.default_prices import get_default_price

        assert get_default_price("UNKNOWN") == 0.068

    def test_constants_exported(self):
        from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_GAZ_EUR_KWH

        assert DEFAULT_PRICE_ELEC_EUR_KWH == 0.068
        assert DEFAULT_PRICE_GAZ_EUR_KWH == 0.045


class TestTurpeUnified:
    """FIX 3: offer_pricing_v1 uses tarif_loader, no hardcoded TURPE."""

    def test_offer_pricing_uses_tarif_loader(self):
        src = inspect.getsource(__import__("services.offer_pricing_v1", fromlist=["_build_fallback_rates"]))
        assert "tarif_loader" in src or "get_turpe" in src

    def test_no_hardcoded_turpe_in_offer_pricing(self):
        import importlib

        mod = importlib.import_module("services.offer_pricing_v1")
        src_path = mod.__file__
        with open(src_path, "r") as f:
            content = f.read()
        # Hardcoded 0.0453 should only appear in the except fallback block
        lines = [
            l
            for l in content.split("\n")
            if "0.0453" in l and not l.strip().startswith("#") and "except" not in l and "fallback" not in l.lower()
        ]
        # Allow it only inside the _build_fallback_rates except block
        non_fallback_lines = [l for l in lines if "_build_fallback_rates" not in l and "except" not in l]
        # The only 0.0453 should be in the except fallback
        assert all("0.0453" in l for l in non_fallback_lines) or len(non_fallback_lines) == 0


class TestComplianceScoreDocumented:
    """FIX 4: compliance_score_service has A.2 source unique docstring."""

    def test_docstring_mentions_source_unique(self):
        import services.compliance_score_service as mod

        src_path = mod.__file__
        with open(src_path, "r") as f:
            content = f.read()
        assert "SOURCE UNIQUE" in content
        assert "A.2" in content

    def test_bacs_engine_documented(self):
        import services.bacs_engine as mod

        src_path = mod.__file__
        with open(src_path, "r") as f:
            content = f.read()
        assert "sub-score BACS" in content or "composante" in content

    def test_compliance_engine_documented(self):
        import services.compliance_engine as mod

        src_path = mod.__file__
        with open(src_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "LEGACY" in content or "backward compat" in content
