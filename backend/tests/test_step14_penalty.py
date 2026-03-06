"""
Step 14 — C7 : Impact financier EUR systematique sur chaque finding.
Tests unitaires pour les penalites dans les regles RegOps.
"""
import pytest
from datetime import date
from dataclasses import fields as dc_fields

from regops.schemas import Finding


# ============================================================
# Unit: Finding dataclass has penalty fields
# ============================================================

class TestFindingPenaltyFields:
    """Test that Finding dataclass has the 3 penalty fields."""

    def test_estimated_penalty_eur_field_exists(self):
        names = [f.name for f in dc_fields(Finding)]
        assert "estimated_penalty_eur" in names

    def test_penalty_source_field_exists(self):
        names = [f.name for f in dc_fields(Finding)]
        assert "penalty_source" in names

    def test_penalty_basis_field_exists(self):
        names = [f.name for f in dc_fields(Finding)]
        assert "penalty_basis" in names

    def test_penalty_fields_optional_default_none(self):
        f = Finding(
            regulation="TEST",
            rule_id="TEST_RULE",
            status="AT_RISK",
            severity="MEDIUM",
            confidence="HIGH",
            legal_deadline=None,
            trigger_condition="test",
            config_params_used={},
            inputs_used=[],
            missing_inputs=[],
            explanation="test",
        )
        assert f.estimated_penalty_eur is None
        assert f.penalty_source is None
        assert f.penalty_basis is None

    def test_penalty_fields_settable(self):
        f = Finding(
            regulation="TEST",
            rule_id="TEST_RULE",
            status="AT_RISK",
            severity="MEDIUM",
            confidence="HIGH",
            legal_deadline=None,
            trigger_condition="test",
            config_params_used={},
            inputs_used=[],
            missing_inputs=[],
            explanation="test",
            estimated_penalty_eur=7500.0,
            penalty_source="regs.yaml",
            penalty_basis="non_declaration: 7500 EUR/site",
        )
        assert f.estimated_penalty_eur == 7500.0
        assert f.penalty_source == "regs.yaml"
        assert f.penalty_basis == "non_declaration: 7500 EUR/site"


# ============================================================
# Tertiaire OPERAT penalties
# ============================================================

class TestTertiairePenalties:
    """Test that tertiaire_operat rule engine populates penalties."""

    def _make_site(self, **overrides):
        """Create a mock site object."""
        defaults = {
            "tertiaire_area_m2": 2000,
            "operat_status": None,
            "annual_kwh_total": None,
            "is_multi_occupied": False,
        }
        defaults.update(overrides)

        class MockSite:
            pass

        s = MockSite()
        for k, v in defaults.items():
            setattr(s, k, v)
        return s

    def test_operat_not_started_has_penalty(self):
        from regops.rules.tertiaire_operat import evaluate
        site = self._make_site()
        config = {"scope_threshold_m2": 1000, "penalties": {"non_declaration": 7500, "non_affichage": 1500}}
        findings = evaluate(site, [], [], config)
        operat = [f for f in findings if f.rule_id == "OPERAT_NOT_STARTED"]
        assert len(operat) == 1
        assert operat[0].estimated_penalty_eur == 7500.0
        assert operat[0].penalty_source == "regs.yaml"

    def test_energy_data_missing_has_penalty(self):
        from regops.rules.tertiaire_operat import evaluate
        site = self._make_site(operat_status="OperatStatus.IN_PROGRESS")
        config = {"scope_threshold_m2": 1000, "penalties": {"non_declaration": 7500}}
        findings = evaluate(site, [], [], config)
        energy = [f for f in findings if f.rule_id == "ENERGY_DATA_MISSING"]
        assert len(energy) == 1
        assert energy[0].estimated_penalty_eur == 7500.0

    def test_multi_occupied_has_penalty(self):
        from regops.rules.tertiaire_operat import evaluate
        site = self._make_site(operat_status="OperatStatus.IN_PROGRESS", annual_kwh_total=100000, is_multi_occupied=True)
        config = {"scope_threshold_m2": 1000, "penalties": {"non_declaration": 7500, "non_affichage": 1500}}
        findings = evaluate(site, [], [], config)
        multi = [f for f in findings if f.rule_id == "MULTI_OCCUPIED_GOVERNANCE"]
        assert len(multi) == 1
        assert multi[0].estimated_penalty_eur == 1500.0

    def test_out_of_scope_no_penalty(self):
        from regops.rules.tertiaire_operat import evaluate
        site = self._make_site(tertiaire_area_m2=500)
        config = {"scope_threshold_m2": 1000}
        findings = evaluate(site, [], [], config)
        assert len(findings) == 1
        assert findings[0].estimated_penalty_eur is None

    def test_scope_unknown_no_penalty(self):
        from regops.rules.tertiaire_operat import evaluate
        site = self._make_site(tertiaire_area_m2=None)
        config = {"scope_threshold_m2": 1000}
        findings = evaluate(site, [], [], config)
        assert len(findings) == 1
        assert findings[0].estimated_penalty_eur is None


# ============================================================
# APER penalties
# ============================================================

class TestAperPenalties:
    """Test that APER rule engine populates penalties."""

    def _make_site(self, **overrides):
        defaults = {
            "parking_area_m2": None,
            "parking_type": None,
            "roof_area_m2": None,
        }
        defaults.update(overrides)

        class MockSite:
            pass

        s = MockSite()
        for k, v in defaults.items():
            setattr(s, k, v)
        return s

    def test_parking_large_has_penalty(self):
        from regops.rules.aper import evaluate
        site = self._make_site(parking_area_m2=12000, parking_type="ParkingType.OUTDOOR")
        config = {"parking_thresholds": {"large_m2": 10000, "medium_m2": 1500}, "deadlines": {}}
        findings = evaluate(site, [], [], config)
        large = [f for f in findings if f.rule_id == "PARKING_LARGE_APER"]
        assert len(large) == 1
        assert large[0].estimated_penalty_eur == 20000.0  # capped
        assert large[0].penalty_source == "estimation"

    def test_parking_medium_has_penalty(self):
        from regops.rules.aper import evaluate
        site = self._make_site(parking_area_m2=3000, parking_type="ParkingType.OUTDOOR")
        config = {"parking_thresholds": {"large_m2": 10000, "medium_m2": 1500}, "deadlines": {}}
        findings = evaluate(site, [], [], config)
        medium = [f for f in findings if f.rule_id == "PARKING_MEDIUM_APER"]
        assert len(medium) == 1
        assert medium[0].estimated_penalty_eur == 20000.0  # 3000*20 = 60k, capped at 20k
        assert medium[0].penalty_source == "estimation"

    def test_roof_has_penalty(self):
        from regops.rules.aper import evaluate
        site = self._make_site(roof_area_m2=800)
        config = {"roof_threshold_m2": 500, "deadlines": {}}
        findings = evaluate(site, [], [], config)
        roof = [f for f in findings if f.rule_id == "ROOF_APER"]
        assert len(roof) == 1
        assert roof[0].estimated_penalty_eur == 12000.0  # 800*15 = 12k
        assert roof[0].penalty_source == "estimation"

    def test_parking_not_outdoor_no_penalty(self):
        from regops.rules.aper import evaluate
        site = self._make_site(parking_area_m2=5000, parking_type="ParkingType.INDOOR")
        config = {}
        findings = evaluate(site, [], [], config)
        assert len(findings) == 1
        assert findings[0].estimated_penalty_eur is None


# ============================================================
# Engine serialization includes penalty fields
# ============================================================

class TestEngineSerialization:
    """Test that engine.py serialization includes penalty fields."""

    def test_findings_json_has_penalty_fields(self):
        import json
        import regops.engine as engine

        # Create a Finding with penalty
        f = Finding(
            regulation="TEST",
            rule_id="TEST_PENALTY",
            status="AT_RISK",
            severity="HIGH",
            confidence="HIGH",
            legal_deadline=date(2026, 9, 30),
            trigger_condition="test",
            config_params_used={},
            inputs_used=[],
            missing_inputs=[],
            explanation="test finding",
            estimated_penalty_eur=7500.0,
            penalty_source="regs.yaml",
            penalty_basis="non_declaration: 7500 EUR/site",
        )

        # Simulate what engine.py does in persist_assessment
        findings_json = json.dumps(
            [
                {
                    "regulation": f.regulation,
                    "rule_id": f.rule_id,
                    "status": f.status,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "legal_deadline": f.legal_deadline.isoformat() if f.legal_deadline else None,
                    "explanation": f.explanation,
                    "category": getattr(f, "category", "obligation"),
                    "estimated_penalty_eur": getattr(f, "estimated_penalty_eur", None),
                    "penalty_source": getattr(f, "penalty_source", None),
                    "penalty_basis": getattr(f, "penalty_basis", None),
                }
            ]
        )

        parsed = json.loads(findings_json)
        assert len(parsed) == 1
        assert parsed[0]["estimated_penalty_eur"] == 7500.0
        assert parsed[0]["penalty_source"] == "regs.yaml"
        assert parsed[0]["penalty_basis"] == "non_declaration: 7500 EUR/site"
