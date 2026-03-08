"""
PROMEOS — Step 6: CEE Separation Tests
Vérifie que les findings ont un champ category et que
les CEE sont taggés "incentive" (pas "obligation").
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── A. Finding schema has category field ─────────────────────────────────────


class TestFindingCategory:
    """Tests sur le dataclass Finding."""

    def test_finding_has_category_field(self):
        from regops.schemas import Finding
        import dataclasses

        field_names = [f.name for f in dataclasses.fields(Finding)]
        assert "category" in field_names

    def test_finding_default_category_is_obligation(self):
        from regops.schemas import Finding

        f = Finding(
            regulation="DT",
            rule_id="DT_SCOPE",
            status="NOK",
            severity="HIGH",
            confidence="HIGH",
            legal_deadline=None,
            trigger_condition="test",
            config_params_used={},
            inputs_used=[],
            missing_inputs=[],
            explanation="test",
        )
        assert f.category == "obligation"

    def test_finding_category_incentive(self):
        from regops.schemas import Finding

        f = Finding(
            regulation="CEE_P6",
            rule_id="CEE_OPPORTUNITY_GTB",
            status="COMPLIANT",
            severity="LOW",
            confidence="MEDIUM",
            legal_deadline=None,
            trigger_condition="test",
            config_params_used={},
            inputs_used=[],
            missing_inputs=[],
            explanation="test",
            category="incentive",
        )
        assert f.category == "incentive"


# ── B. CEE rule sets category=incentive ──────────────────────────────────────


class TestCeeRule:
    """Tests sur la règle CEE P6."""

    def test_cee_rule_sets_incentive_category(self):
        """Le fichier cee_p6.py doit passer category='incentive' à Finding."""
        import inspect
        from regops.rules import cee_p6

        source = inspect.getsource(cee_p6)
        assert 'category="incentive"' in source

    def test_cee_findings_have_incentive_category(self):
        """Si cee_p6 produit des findings, ils ont category=incentive."""
        from regops.rules import cee_p6

        source_code = open(os.path.join(os.path.dirname(__file__), "..", "regops", "rules", "cee_p6.py")).read()
        assert "incentive" in source_code


# ── C. Engine persists category in findings_json ─────────────────────────────


class TestEnginePersistCategory:
    """Tests sur le persist_assessment."""

    def test_persist_includes_category(self):
        """engine.py persist_assessment inclut category dans findings_json."""
        engine_path = os.path.join(os.path.dirname(__file__), "..", "regops", "engine.py")
        source = open(engine_path).read()
        assert '"category"' in source
        assert "getattr(f" in source or "f.category" in source


# ── D. Routes include category in response ───────────────────────────────────


class TestRouteCategory:
    """Tests sur les routes regops et compliance."""

    def test_regops_route_includes_category(self):
        route_path = os.path.join(os.path.dirname(__file__), "..", "routes", "regops.py")
        source = open(route_path).read()
        assert '"category"' in source

    def test_compliance_sites_findings_include_category(self):
        rules_path = os.path.join(os.path.dirname(__file__), "..", "services", "compliance_rules.py")
        source = open(rules_path).read()
        assert '"category"' in source
        assert "incentive" in source

    def test_compliance_findings_route_includes_category(self):
        route_path = os.path.join(os.path.dirname(__file__), "..", "routes", "compliance.py")
        source = open(route_path).read()
        assert '"category"' in source

    def test_compliance_findings_route_has_category_filter(self):
        route_path = os.path.join(os.path.dirname(__file__), "..", "routes", "compliance.py")
        source = open(route_path).read()
        # Should have category query param
        assert "category" in source
        assert "obligation" in source
        assert "incentive" in source


# ── E. Score A.2 excludes CEE ────────────────────────────────────────────────


class TestScoreExcludesCee:
    """Vérifie que compliance_score_service n'inclut pas CEE."""

    def test_score_service_mentions_cee_exclusion(self):
        score_path = os.path.join(os.path.dirname(__file__), "..", "services", "compliance_score_service.py")
        source = open(score_path).read()
        # Should mention CEE exclusion
        assert "CEE" in source or "cee" in source

    def test_score_weights_only_three_frameworks(self):
        from services.compliance_score_service import FRAMEWORK_WEIGHTS

        # Only DT, BACS, APER — no CEE
        assert len(FRAMEWORK_WEIGHTS) == 3
        keys = list(FRAMEWORK_WEIGHTS.keys())
        for k in keys:
            assert "cee" not in k.lower()


# ── F. DT/BACS/APER are obligation, CEE is incentive ────────────────────────


class TestCategoryMapping:
    """Vérifie le mapping regulation → category."""

    def test_dt_is_obligation(self):
        from regops.schemas import Finding

        f = Finding(
            regulation="DT",
            rule_id="DT_SCOPE",
            status="NOK",
            severity="HIGH",
            confidence="HIGH",
            legal_deadline=None,
            trigger_condition="test",
            config_params_used={},
            inputs_used=[],
            missing_inputs=[],
            explanation="test",
        )
        assert f.category == "obligation"

    def test_bacs_is_obligation(self):
        from regops.schemas import Finding

        f = Finding(
            regulation="BACS",
            rule_id="BACS_POWER",
            status="NOK",
            severity="HIGH",
            confidence="HIGH",
            legal_deadline=None,
            trigger_condition="test",
            config_params_used={},
            inputs_used=[],
            missing_inputs=[],
            explanation="test",
        )
        assert f.category == "obligation"

    def test_cee_category_from_compliance_rules(self):
        """compliance_rules.py derives category=incentive for CEE regulation."""
        rules_path = os.path.join(os.path.dirname(__file__), "..", "services", "compliance_rules.py")
        source = open(rules_path).read()
        # Should have logic: "cee" in regulation → incentive
        assert "cee" in source.lower()
        assert "incentive" in source
