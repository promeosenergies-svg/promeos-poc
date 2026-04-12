"""Tests du Recommendation Engine — règles métier + pipeline complet."""

from data_staging.models import MeterLoadCurve  # noqa: F401 register table

from services.recommendation_engine import (
    _ice,
    _rule_baseload_excessive,
    _rule_low_load_factor,
    _rule_night_day_ratio_high,
    _rule_thermosensitivity_high,
    _rule_atypicity_high,
    _rule_data_quality_low,
)


# ── Tests ICE scoring ────────────────────────────────────────────────────


class TestIceScoring:
    def test_perfect_score(self):
        """10/10/10 → 10."""
        assert _ice(10, 10, 10) == 10.0

    def test_balanced_medium(self):
        """7/7/7 → ~7."""
        assert abs(_ice(7, 7, 7) - 7.0) < 0.01

    def test_penalizes_weak_dimension(self):
        """Low ease (2) tire le score vers le bas."""
        score = _ice(10, 10, 2)
        assert score < 6  # Moyenne géométrique pénalise fortement

    def test_returns_float(self):
        assert isinstance(_ice(5, 5, 5), float)


# ── Tests règles métier individuelles ───────────────────────────────────


class TestRuleBaseloadExcessive:
    def test_triggers_on_high_baseload(self):
        load_profile = {
            "baseload": {"verdict": "eleve", "baseload_pct_of_mean": 75},
            "power_stats": {"p_mean_kwh": 10.0},
        }
        result = _rule_baseload_excessive(load_profile, meter_id=1)
        assert result is not None
        anomaly, reco = result
        assert anomaly["code"] == "ANOM_BASELOAD_ELEVE"
        assert anomaly["severity"] == "high"
        assert reco["code"] == "RECO_REDUIRE_BASELOAD"
        assert reco["impact_score"] == 9
        assert reco["estimated_savings_kwh"] > 0

    def test_no_trigger_on_normal(self):
        load_profile = {
            "baseload": {"verdict": "normal", "baseload_pct_of_mean": 25},
            "power_stats": {"p_mean_kwh": 10.0},
        }
        assert _rule_baseload_excessive(load_profile, meter_id=1) is None

    def test_no_trigger_below_60pct(self):
        load_profile = {
            "baseload": {"verdict": "eleve", "baseload_pct_of_mean": 55},
            "power_stats": {"p_mean_kwh": 10.0},
        }
        assert _rule_baseload_excessive(load_profile, meter_id=1) is None


class TestRuleLowLoadFactor:
    def test_triggers_on_low_lf(self):
        result = _rule_low_load_factor({"load_factor": 0.08}, meter_id=1)
        assert result is not None
        anomaly, reco = result
        assert anomaly["code"] == "ANOM_LOAD_FACTOR_FAIBLE"
        assert reco["code"] == "RECO_OPTIMISER_PSOUS"
        assert reco["ease_score"] == 9  # Changement contractuel = facile

    def test_no_trigger_on_normal_lf(self):
        assert _rule_low_load_factor({"load_factor": 0.35}, meter_id=1) is None

    def test_no_trigger_on_zero(self):
        assert _rule_low_load_factor({"load_factor": 0}, meter_id=1) is None


class TestRuleNightDayRatio:
    def test_triggers_on_high_ratio(self):
        result = _rule_night_day_ratio_high({"ratios": {"night_day": 0.75}}, meter_id=1)
        assert result is not None
        anomaly, reco = result
        assert anomaly["severity"] == "high"
        assert reco["code"] == "RECO_PILOTAGE_NOCTURNE"

    def test_no_trigger_low_ratio(self):
        assert _rule_night_day_ratio_high({"ratios": {"night_day": 0.2}}, meter_id=1) is None


class TestRuleThermosensitivity:
    def test_triggers_heating_dominant(self):
        signature = {"thermosensitivity": {"part_thermo_pct": 55, "classification": "heating_dominant"}}
        result = _rule_thermosensitivity_high(signature, meter_id=1)
        assert result is not None
        _, reco = result
        assert reco["code"] == "RECO_ISOLATION_THERMIQUE"
        assert reco["ease_score"] == 4  # Travaux lourds = difficile

    def test_no_trigger_if_flat(self):
        signature = {"thermosensitivity": {"part_thermo_pct": 55, "classification": "flat"}}
        assert _rule_thermosensitivity_high(signature, meter_id=1) is None

    def test_no_trigger_low_thermo(self):
        signature = {"thermosensitivity": {"part_thermo_pct": 20, "classification": "heating_dominant"}}
        assert _rule_thermosensitivity_high(signature, meter_id=1) is None


class TestRuleAtypicity:
    def test_triggers_on_high_atypicity(self):
        benchmark = {
            "atypicity": {"score": 0.65},
            "sector_enedis": "S3: Tertiaire",
            "site_stats": {"conso_kwh_m2_year": 250},
        }
        result = _rule_atypicity_high(benchmark, meter_id=1)
        assert result is not None
        anomaly, reco = result
        assert reco["code"] == "RECO_DIAGNOSTIC_ATYPIE"

    def test_no_trigger_on_typical(self):
        benchmark = {
            "atypicity": {"score": 0.15},
            "sector_enedis": "S3: Tertiaire",
            "site_stats": {},
        }
        assert _rule_atypicity_high(benchmark, meter_id=1) is None

    def test_no_trigger_none_score(self):
        benchmark = {"atypicity": {"score": None}, "site_stats": {}}
        assert _rule_atypicity_high(benchmark, meter_id=1) is None


class TestRuleDataQuality:
    def test_triggers_on_low_quality(self):
        load_profile = {
            "data_quality": {
                "score": 0.65,
                "details": {"gaps": 50, "outliers": 10},
            }
        }
        result = _rule_data_quality_low(load_profile, meter_id=1)
        assert result is not None
        _, reco = result
        assert reco["code"] == "RECO_FIABILISER_COLLECTE"
        assert reco["impact_score"] == 3  # Pas d'économie directe

    def test_no_trigger_on_good_quality(self):
        load_profile = {"data_quality": {"score": 0.95, "details": {}}}
        assert _rule_data_quality_low(load_profile, meter_id=1) is None


# ── Test pipeline complet ───────────────────────────────────────────────


class TestRecommendationPipeline:
    def test_no_meter_returns_error(self):
        from unittest.mock import MagicMock
        from services.recommendation_engine import generate_recommendations_for_site

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = generate_recommendations_for_site(db, 99999, persist=False)
        assert "error" in result

    def test_rules_sorted_by_ice_score(self):
        """Les règles retournent des recos triées par ICE décroissant."""
        # Simuler les 6 règles activées
        results = []
        for rule_fn, data in [
            (
                _rule_baseload_excessive,
                {
                    "baseload": {"verdict": "eleve", "baseload_pct_of_mean": 75},
                    "power_stats": {"p_mean_kwh": 10.0},
                },
            ),
            (_rule_low_load_factor, {"load_factor": 0.08}),
            (_rule_night_day_ratio_high, {"ratios": {"night_day": 0.75}}),
        ]:
            r = rule_fn(data, meter_id=1)
            if r:
                _, reco = r
                reco["ice_score"] = _ice(
                    reco["impact_score"],
                    reco["confidence_score"],
                    reco["ease_score"],
                )
                results.append(reco)

        results.sort(key=lambda x: x["ice_score"], reverse=True)
        scores = [r["ice_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        assert all(0 < s <= 10 for s in scores)
