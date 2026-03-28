"""
Source guards — conformite/RegOps.
Empeche toute regression sur les seuils reglementaires et le scoring.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import pytest


def _load_regs():
    with open("regops/config/regs.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestScoringWeightsGuards:
    """Les poids scoring doivent etre alignes partout."""

    def test_regs_yaml_weights_sum_to_100(self):
        """Poids actifs dans regs.yaml doivent sommer a 1.0."""
        config = _load_regs()
        weights = config["scoring"]["framework_weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"Total poids = {total}, attendu 1.0. Weights: {weights}"

    def test_dt_weight_is_045(self):
        config = _load_regs()
        dt = config["scoring"]["framework_weights"]["tertiaire_operat"]
        assert dt == 0.45, f"DT weight = {dt}, attendu 0.45"

    def test_bacs_weight_is_030(self):
        config = _load_regs()
        bacs = config["scoring"]["framework_weights"]["bacs"]
        assert bacs == 0.30, f"BACS weight = {bacs}, attendu 0.30"

    def test_aper_weight_is_025(self):
        config = _load_regs()
        aper = config["scoring"]["framework_weights"]["aper"]
        assert aper == 0.25, f"APER weight = {aper}, attendu 0.25"

    def test_no_dpe_csrd_weights(self):
        """DPE et CSRD ne doivent pas avoir de poids tant que non implementes."""
        config = _load_regs()
        weights = config["scoring"]["framework_weights"]
        assert "dpe_tertiaire" not in weights, "DPE should not have weight (not implemented)"
        assert "csrd" not in weights, "CSRD should not have weight (not implemented)"

    def test_critical_penalty_max_20(self):
        config = _load_regs()
        max_pts = config["scoring"]["critical_penalty"]["max_pts"]
        assert max_pts == 20.0, f"Max critical penalty = {max_pts}, attendu 20.0"

    def test_critical_penalty_per_finding_5(self):
        config = _load_regs()
        per_finding = config["scoring"]["critical_penalty"]["per_finding_pts"]
        assert per_finding == 5.0, f"Per finding penalty = {per_finding}, attendu 5.0"


class TestRegulatoryThresholdsGuards:
    """Seuils reglementaires ne doivent pas changer sans raison."""

    def test_dt_surface_threshold_1000(self):
        config = _load_regs()
        threshold = config["tertiaire_operat"]["scope_threshold_m2"]
        assert threshold == 1000, f"DT surface threshold = {threshold}, attendu 1000"

    def test_dt_reduction_2030_minus40(self):
        config = _load_regs()
        red = config["tertiaire_operat"]["deadlines"]["reduction_2030"]
        assert red == -0.40, f"DT reduction 2030 = {red}, attendu -0.40"

    def test_dt_reduction_2040_minus50(self):
        config = _load_regs()
        red = config["tertiaire_operat"]["deadlines"]["reduction_2040"]
        assert red == -0.50, f"DT reduction 2040 = {red}, attendu -0.50"

    def test_dt_reduction_2050_minus60(self):
        config = _load_regs()
        red = config["tertiaire_operat"]["deadlines"]["reduction_2050"]
        assert red == -0.60, f"DT reduction 2050 = {red}, attendu -0.60"

    def test_dt_penalty_non_declaration_7500(self):
        config = _load_regs()
        penalty = config["tertiaire_operat"]["penalties"]["non_declaration"]
        assert penalty == 7500, f"DT penalty non-declaration = {penalty}, attendu 7500"

    def test_bacs_high_threshold_290(self):
        config = _load_regs()
        high = config["bacs"]["thresholds"]["high_kw"]
        assert high == 290, f"BACS seuil haut = {high}, attendu 290"

    def test_bacs_low_threshold_70(self):
        config = _load_regs()
        low = config["bacs"]["thresholds"]["low_kw"]
        assert low == 70, f"BACS seuil bas = {low}, attendu 70"

    def test_bacs_exemption_tri_10_years(self):
        config = _load_regs()
        tri = config["bacs"]["exemption"]["tri_max_years"]
        assert tri == 10, f"BACS TRI exemption = {tri}, attendu 10"

    def test_bacs_inspection_5_years(self):
        config = _load_regs()
        period = config["bacs"]["inspection_periodicity_years"]
        assert period == 5, f"BACS inspection period = {period}, attendu 5"

    def test_aper_parking_large_10000(self):
        config = _load_regs()
        large = config["aper"]["parking_thresholds"]["large_m2"]
        assert large == 10000, f"APER parking large = {large}, attendu 10000"

    def test_aper_parking_medium_1500(self):
        config = _load_regs()
        medium = config["aper"]["parking_thresholds"]["medium_m2"]
        assert medium == 1500, f"APER parking medium = {medium}, attendu 1500"

    def test_aper_roof_500(self):
        config = _load_regs()
        roof = config["aper"]["roof_threshold_m2"]
        assert roof == 500, f"APER roof threshold = {roof}, attendu 500"

    def test_aper_coverage_50_pct(self):
        config = _load_regs()
        coverage = config["aper"]["coverage_pct_required"]
        assert coverage == 50, f"APER coverage = {coverage}, attendu 50"


class TestScoringServiceConsistency:
    """compliance_score_service doit lire regs.yaml."""

    def test_framework_weights_match_yaml(self):
        from services.compliance_score_service import FRAMEWORK_WEIGHTS

        config = _load_regs()
        yaml_weights = config["scoring"]["framework_weights"]
        assert FRAMEWORK_WEIGHTS == yaml_weights, (
            f"FRAMEWORK_WEIGHTS mismatch: code={FRAMEWORK_WEIGHTS}, yaml={yaml_weights}"
        )

    def test_formula_mentions_45_30_25(self):
        from services.compliance_score_service import ComplianceScoreResult

        formula = ComplianceScoreResult(score=0.0).formula
        assert "45%" in formula, f"Formula should mention 45%: {formula}"
        assert "30%" in formula, f"Formula should mention 30%: {formula}"
        assert "25%" in formula, f"Formula should mention 25%: {formula}"
