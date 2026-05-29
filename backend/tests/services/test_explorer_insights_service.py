"""
PROMEOS — Tests build_explorer_insights (Sprint Énergie P0.S1c, brief P3).

Cible : `services.explorer_insights_service.build_explorer_insights`

Couvre les 6 règles + tri par sévérité + provenance obligatoire.
"""

import pytest

from services.explorer_insights_service import build_explorer_insights


pytestmark = pytest.mark.fast


class TestEmptyOrInvalidInput:
    """Cas vide / payload incomplet → empty state propre."""

    def test_empty_dict_returns_no_insights(self):
        assert build_explorer_insights({}) == []

    def test_none_input_does_not_crash(self):
        assert build_explorer_insights(None) == []

    def test_payload_with_only_unknown_keys(self):
        assert build_explorer_insights({"unknown_key": 42}) == []


class TestRuleOutsideBandHigh:
    """Règle 1 : outside_pct > 15 → warn ; > 30 → crit."""

    def test_below_threshold_returns_no_insight(self):
        out = build_explorer_insights({"primaryTunnel": {"outside_pct": 10}})
        assert out == []

    def test_at_threshold_returns_no_insight(self):
        out = build_explorer_insights({"primaryTunnel": {"outside_pct": 15}})
        assert out == []

    def test_above_warn_threshold_returns_warn(self):
        out = build_explorer_insights({"primaryTunnel": {"outside_pct": 20}})
        assert len(out) == 1
        assert out[0]["id"] == "outside_band_high"
        assert out[0]["severity"] == "warn"

    def test_above_crit_threshold_returns_crit(self):
        out = build_explorer_insights({"primaryTunnel": {"outside_pct": 35}})
        assert out[0]["severity"] == "crit"

    def test_provenance_includes_thresholds(self):
        out = build_explorer_insights({"primaryTunnel": {"outside_pct": 20}})
        prov = out[0]["provenance"]
        assert prov["rule"] == "outside_band_high"
        assert prov["threshold"] == {"warn": 15, "crit": 30}
        assert "explorer_insights_service" in prov["source"]


class TestRuleBaseLoadDrift:
    """Règle 2 : |base_drift_pct| > 10 → warn ; > 20 → crit."""

    def test_below_threshold_returns_no_insight(self):
        out = build_explorer_insights({"primaryWeather": {"drift": {"base_drift_pct": 5}}})
        assert out == []

    def test_above_warn_threshold_returns_warn(self):
        out = build_explorer_insights({"primaryWeather": {"drift": {"base_drift_pct": 15}}})
        assert out[0]["severity"] == "warn"

    def test_negative_drift_above_threshold_returns_warn(self):
        out = build_explorer_insights({"primaryWeather": {"drift": {"base_drift_pct": -25}}})
        assert out[0]["severity"] == "crit"

    def test_label_shows_sign(self):
        out = build_explorer_insights({"primaryWeather": {"drift": {"base_drift_pct": 15}}})
        assert "+15" in out[0]["label"]


class TestRuleHpRatioHigh:
    """Règle 3 : hp_ratio > 0.70 → info ; > 0.85 → warn."""

    def test_below_threshold_returns_no_insight(self):
        out = build_explorer_insights({"primaryHphc": {"hp_ratio": 0.6}})
        assert out == []

    def test_above_info_threshold_returns_info(self):
        out = build_explorer_insights({"primaryHphc": {"hp_ratio": 0.75}})
        assert out[0]["severity"] == "info"

    def test_above_warn_threshold_returns_warn(self):
        out = build_explorer_insights({"primaryHphc": {"hp_ratio": 0.90}})
        assert out[0]["severity"] == "warn"

    def test_label_shows_percentage(self):
        out = build_explorer_insights({"primaryHphc": {"hp_ratio": 0.75}})
        assert "75%" in out[0]["label"]


class TestRuleTargetOverBudget:
    """Règle 4 : progress_pct > 110 → warn ; > 130 → crit."""

    def test_under_budget_returns_no_insight(self):
        out = build_explorer_insights({"primaryProgression": {"progress_pct": 95}})
        assert out == []

    def test_over_warn_returns_warn(self):
        out = build_explorer_insights({"primaryProgression": {"progress_pct": 115}})
        assert out[0]["severity"] == "warn"
        assert "15%" in out[0]["label"]

    def test_over_crit_returns_crit(self):
        out = build_explorer_insights({"primaryProgression": {"progress_pct": 140}})
        assert out[0]["severity"] == "crit"


class TestRuleGasLeakSuspect:
    """Règle 5 : alerte probable_leak → crit."""

    def test_no_alerts_returns_no_insight(self):
        out = build_explorer_insights({"primaryWeather": {}})
        assert out == []

    def test_unrelated_alerts_ignored(self):
        out = build_explorer_insights({"primaryWeather": {"alerts": [{"type": "spike", "message": "test"}]}})
        assert out == []

    def test_probable_leak_returns_crit(self):
        out = build_explorer_insights(
            {"primaryWeather": {"alerts": [{"type": "probable_leak", "message": "Conso été élevée"}]}}
        )
        assert out[0]["id"] == "gas_leak_suspect"
        assert out[0]["severity"] == "crit"
        assert "Conso été élevée" in out[0]["detail"]


class TestRuleLowConfidence:
    """Règle 6 : un panel avec confidence == 'low' → info."""

    def test_no_low_confidence_returns_no_insight(self):
        out = build_explorer_insights({"primaryTunnel": {"confidence": "high"}})
        assert out == []

    def test_low_confidence_returns_info(self):
        out = build_explorer_insights({"primaryTunnel": {"confidence": "low"}})
        assert any(i["id"] == "low_confidence" and i["severity"] == "info" for i in out)


class TestInsightsOrdering:
    """Le tri doit placer crit en tête, info en queue."""

    def test_sort_order_crit_warn_info(self):
        payload = {
            "primaryTunnel": {"outside_pct": 35, "confidence": "low"},  # crit + low
            "primaryHphc": {"hp_ratio": 0.75},  # info
        }
        out = build_explorer_insights(payload)
        severities = [i["severity"] for i in out]
        # crit avant warn avant info
        for i in range(len(severities) - 1):
            assert _order(severities[i]) <= _order(severities[i + 1])


def _order(s: str) -> int:
    return {"crit": 0, "warn": 1, "info": 2}.get(s, 3)


class TestRobustness:
    """Robustesse aux payloads malformés."""

    def test_missing_outside_pct_returns_no_insight(self):
        out = build_explorer_insights({"primaryTunnel": {"foo": "bar"}})
        assert all(i["id"] != "outside_band_high" for i in out)

    def test_none_values_silently_ignored(self):
        out = build_explorer_insights({"primaryTunnel": {"outside_pct": None}, "primaryHphc": {"hp_ratio": None}})
        assert out == []

    def test_provenance_present_on_every_insight(self):
        out = build_explorer_insights(
            {
                "primaryTunnel": {"outside_pct": 35},
                "primaryHphc": {"hp_ratio": 0.90},
                "primaryProgression": {"progress_pct": 140},
            }
        )
        for i in out:
            assert "provenance" in i
            assert i["provenance"]["source"]
            assert i["provenance"]["formula"]
            assert "threshold" in i["provenance"]
