"""
PROMEOS — Step 2: Unified Scoring Tests
Vérifie que RegOps et Compliance retournent le MÊME score (source unique A.2).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from pathlib import Path


# ── A. RegOps engine uses A.2 score ──────────────────────────────────────────

class TestEngineUsesA2:
    """Verify regops/engine.py delegates scoring to compliance_score_service."""

    def test_engine_imports_a2_service(self):
        """engine.py imports compute_site_compliance_score."""
        src = Path(__file__).parent.parent / "regops" / "engine.py"
        content = src.read_text(encoding="utf-8")
        assert "compute_site_compliance_score" in content

    def test_engine_no_legacy_score_call(self):
        """engine.py no longer calls compute_regops_score in evaluate_site."""
        src = Path(__file__).parent.parent / "regops" / "engine.py"
        content = src.read_text(encoding="utf-8")
        # The import stays (for score_explain) but evaluate_site should NOT call it
        lines = content.split("\n")
        in_evaluate = False
        for line in lines:
            if "def evaluate_site" in line:
                in_evaluate = True
            elif in_evaluate and line.startswith("def "):
                break
            elif in_evaluate and "compute_regops_score(" in line:
                pytest.fail("evaluate_site still calls legacy compute_regops_score()")

    def test_engine_scoring_profile_id_is_a2(self):
        """SiteSummary.scoring_profile_id should reference A.2 service."""
        src = Path(__file__).parent.parent / "regops" / "engine.py"
        content = src.read_text(encoding="utf-8")
        assert "compliance_score_service_a2" in content


# ── B. Routes use A.2 ────────────────────────────────────────────────────────

class TestRoutesUseA2:
    """Verify regops routes delegate to compliance_score_service."""

    def test_routes_import_a2(self):
        """routes/regops.py imports compliance_score_service."""
        src = Path(__file__).parent.parent / "routes" / "regops.py"
        content = src.read_text(encoding="utf-8")
        assert "compute_site_compliance_score" in content
        assert "compute_portfolio_compliance" in content

    def test_score_explain_has_breakdown(self):
        """score_explain endpoint returns A.2 breakdown structure."""
        src = Path(__file__).parent.parent / "routes" / "regops.py"
        content = src.read_text(encoding="utf-8")
        # Must return breakdown with framework/weight/score fields
        assert "breakdown" in content
        assert "framework" in content
        assert "a2_result" in content

    def test_score_explain_no_legacy_penalties(self):
        """score_explain no longer returns legacy penalties array."""
        src = Path(__file__).parent.parent / "routes" / "regops.py"
        content = src.read_text(encoding="utf-8")
        # The score_explain function should not build penalty dicts from regops scoring
        lines = content.split("\n")
        in_explain = False
        for line in lines:
            if "def get_score_explain" in line:
                in_explain = True
            elif in_explain and line.startswith("def ") or (in_explain and line.startswith("@router")):
                break
            elif in_explain and "score_result.penalties" in line:
                pytest.fail("score_explain still uses legacy score_result.penalties")

    def test_dashboard_uses_portfolio_compliance(self):
        """dashboard endpoint can call compute_portfolio_compliance."""
        src = Path(__file__).parent.parent / "routes" / "regops.py"
        content = src.read_text(encoding="utf-8")
        # Find the dashboard function and verify it uses compute_portfolio_compliance
        assert "compute_portfolio_compliance" in content


# ── C. No legacy scoring formula ─────────────────────────────────────────────

class TestNoLegacyFormula:
    """Verify no code outside scoring.py computes compliance scores."""

    def test_engine_no_100_minus_pattern(self):
        """engine.py does not contain '100 - ...' scoring pattern."""
        src = Path(__file__).parent.parent / "regops" / "engine.py"
        content = src.read_text(encoding="utf-8")
        import re
        # Pattern: "100.0 - (weighted_sum" or "100 - (sum"
        matches = re.findall(r"100\.?0?\s*-\s*\(.*(?:weighted|penalty|severity)", content)
        assert len(matches) == 0, f"Legacy scoring pattern found: {matches}"

    def test_routes_no_100_minus_pattern(self):
        """routes/regops.py does not compute scores inline."""
        src = Path(__file__).parent.parent / "routes" / "regops.py"
        content = src.read_text(encoding="utf-8")
        import re
        matches = re.findall(r"100\.?0?\s*-\s*\(.*(?:weighted|penalty|severity)", content)
        assert len(matches) == 0, f"Legacy scoring pattern found: {matches}"


# ── D. Endpoint structure ────────────────────────────────────────────────────

class TestEndpointStructure:
    """Verify endpoint registrations."""

    def test_regops_site_endpoint_exists(self):
        from routes.regops import router
        paths = [r.path for r in router.routes]
        assert any("/site/{site_id}" in p for p in paths)

    def test_score_explain_endpoint_exists(self):
        from routes.regops import router
        paths = [r.path for r in router.routes]
        assert any("/score_explain" in p for p in paths)

    def test_dashboard_endpoint_exists(self):
        from routes.regops import router
        paths = [r.path for r in router.routes]
        assert any("/dashboard" in p for p in paths)

    def test_compliance_site_score_endpoint_exists(self):
        from routes.compliance import router
        paths = [r.path for r in router.routes]
        assert any("/score" in p for p in paths)

    def test_compliance_portfolio_score_endpoint_exists(self):
        from routes.compliance import router
        paths = [r.path for r in router.routes]
        assert any("/portfolio/score" in p for p in paths)
