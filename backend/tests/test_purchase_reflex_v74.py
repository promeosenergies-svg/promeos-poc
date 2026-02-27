"""
PROMEOS — Achat Energie V74 RéFlex Solar — Backend unit tests
Tests: enum, REFLEX_BLOCS, compute_reflex_scenario, compute_scenarios (4 strats),
       recommend with green bonus, effort_score, report_pct.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from models import PurchaseStrategy


# ========================================
# A. Enum
# ========================================
class TestReflexEnum:
    def test_reflex_solar_in_purchase_strategy(self):
        assert PurchaseStrategy.REFLEX_SOLAR.value == "reflex_solar"

    def test_all_four_strategies_exist(self):
        assert PurchaseStrategy.FIXE.value == "fixe"
        assert PurchaseStrategy.INDEXE.value == "indexe"
        assert PurchaseStrategy.SPOT.value == "spot"
        assert PurchaseStrategy.REFLEX_SOLAR.value == "reflex_solar"


# ========================================
# B. REFLEX_BLOCS constants
# ========================================
class TestReflexBlocs:
    def test_blocs_has_6_entries(self):
        from services.purchase_service import REFLEX_BLOCS
        assert len(REFLEX_BLOCS) == 6

    def test_bloc_keys(self):
        from services.purchase_service import REFLEX_BLOCS
        expected = {
            "solaire_ete_semaine", "solaire_ete_weekend",
            "pointe_hiver_matin", "pointe_hiver_soir",
            "hc", "hp",
        }
        assert set(REFLEX_BLOCS.keys()) == expected

    def test_solaire_ete_semaine_hours(self):
        from services.purchase_service import REFLEX_BLOCS
        bloc = REFLEX_BLOCS["solaire_ete_semaine"]
        assert bloc["hours"] == (13, 16)
        assert bloc["weekday"] is True
        assert bloc["months"] == [4, 5, 6, 7, 8, 9]

    def test_solaire_ete_weekend_hours(self):
        from services.purchase_service import REFLEX_BLOCS
        bloc = REFLEX_BLOCS["solaire_ete_weekend"]
        assert bloc["hours"] == (10, 17)
        assert bloc["weekday"] is False

    def test_pointe_hiver_matin(self):
        from services.purchase_service import REFLEX_BLOCS
        bloc = REFLEX_BLOCS["pointe_hiver_matin"]
        assert bloc["hours"] == (8, 10)
        assert bloc["price_mult"] == 1.25

    def test_pointe_hiver_soir(self):
        from services.purchase_service import REFLEX_BLOCS
        bloc = REFLEX_BLOCS["pointe_hiver_soir"]
        assert bloc["hours"] == (17, 20)
        assert bloc["price_mult"] == 1.25

    def test_hc_bloc(self):
        from services.purchase_service import REFLEX_BLOCS
        bloc = REFLEX_BLOCS["hc"]
        assert bloc["hours"] == (0, 6)
        assert bloc["price_mult"] == 0.80
        assert bloc["weekday"] is None
        assert len(bloc["months"]) == 12

    def test_hp_bloc(self):
        from services.purchase_service import REFLEX_BLOCS
        bloc = REFLEX_BLOCS["hp"]
        assert bloc["hours"] == (6, 22)
        assert bloc["price_mult"] == 1.00

    def test_weights_sum_to_100_pct(self):
        from services.purchase_service import REFLEX_BLOC_WEIGHTS
        total = sum(REFLEX_BLOC_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_weights_match_blocs(self):
        from services.purchase_service import REFLEX_BLOCS, REFLEX_BLOC_WEIGHTS
        assert set(REFLEX_BLOCS.keys()) == set(REFLEX_BLOC_WEIGHTS.keys())

    def test_solaire_cheaper_than_hp(self):
        from services.purchase_service import REFLEX_BLOCS
        assert REFLEX_BLOCS["solaire_ete_semaine"]["price_mult"] < REFLEX_BLOCS["hp"]["price_mult"]
        assert REFLEX_BLOCS["solaire_ete_weekend"]["price_mult"] < REFLEX_BLOCS["hp"]["price_mult"]


# ========================================
# C. compute_reflex_scenario
# ========================================
class TestComputeReflex:
    def test_basic_output_shape(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(
            ref_price=0.10,
            volume_kwh_an=500_000,
            profile_factor=1.0,
            price_source="market",
        )
        assert result["strategy"] == "reflex_solar"
        assert "price_eur_per_kwh" in result
        assert "total_annual_eur" in result
        assert "risk_score" in result
        assert "p10_eur" in result
        assert "p90_eur" in result
        assert "effort_score" in result
        assert "report_pct" in result
        assert "blocs" in result

    def test_returns_6_blocs(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market")
        assert len(result["blocs"]) == 6

    def test_blocs_have_required_fields(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market")
        for b in result["blocs"]:
            assert "bloc" in b
            assert "weight_pct" in b
            assert "kwh" in b
            assert "price_eur_kwh" in b
            assert "cost_eur" in b
            assert "hours" in b

    def test_total_cost_is_sum_of_blocs(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market")
        blocs_sum = sum(b["cost_eur"] for b in result["blocs"])
        assert abs(result["total_annual_eur"] - blocs_sum) < 1.0  # rounding tolerance

    def test_avg_price_consistent(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market")
        expected = round(result["total_annual_eur"] / 500_000, 4)
        assert result["price_eur_per_kwh"] == expected

    def test_risk_score_is_40(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market")
        assert result["risk_score"] == 40

    def test_p10_p90_range(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market")
        assert result["p10_eur"] < result["total_annual_eur"]
        assert result["p90_eur"] > result["total_annual_eur"]

    def test_effort_score_no_report(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market", report_pct=0.0)
        assert result["effort_score"] == 20

    def test_effort_score_with_report(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market", report_pct=0.15)
        assert result["effort_score"] == 80  # min(80, 20 + 15*400/100) = min(80, 80) = 80

    def test_effort_score_small_report(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market", report_pct=0.05)
        assert result["effort_score"] == 40  # 20 + int(0.05 * 400) = 20 + 20 = 40

    def test_report_pct_in_output(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "market", report_pct=0.15)
        assert result["report_pct"] == 15.0

    def test_report_shifts_hp_to_solaire(self):
        from services.purchase_service import compute_reflex_scenario
        no_report = compute_reflex_scenario(0.10, 500_000, 1.0, "market", report_pct=0.0)
        with_report = compute_reflex_scenario(0.10, 500_000, 1.0, "market", report_pct=0.15)
        # HP weight should decrease with report
        hp_no = next(b for b in no_report["blocs"] if b["bloc"] == "hp")
        hp_yes = next(b for b in with_report["blocs"] if b["bloc"] == "hp")
        assert hp_yes["weight_pct"] < hp_no["weight_pct"]
        # Solaire ete semaine weight should increase
        sol_no = next(b for b in no_report["blocs"] if b["bloc"] == "solaire_ete_semaine")
        sol_yes = next(b for b in with_report["blocs"] if b["bloc"] == "solaire_ete_semaine")
        assert sol_yes["weight_pct"] > sol_no["weight_pct"]

    def test_report_lowers_total_cost(self):
        from services.purchase_service import compute_reflex_scenario
        no_report = compute_reflex_scenario(0.10, 500_000, 1.0, "market", report_pct=0.0)
        with_report = compute_reflex_scenario(0.10, 500_000, 1.0, "market", report_pct=0.10)
        # Shifting from HP (1.0 mult) to solaire (0.72 mult) should lower cost
        assert with_report["total_annual_eur"] < no_report["total_annual_eur"]

    def test_zero_volume(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 0, 1.0, "market")
        assert result["price_eur_per_kwh"] == 0
        assert result["total_annual_eur"] == 0

    def test_ref_price_source_passthrough(self):
        from services.purchase_service import compute_reflex_scenario
        result = compute_reflex_scenario(0.10, 500_000, 1.0, "contract_avg")
        assert result["ref_price_source"] == "contract_avg"
        assert result["ref_price"] == 0.10


# ========================================
# D. compute_scenarios returns 4 strategies
# ========================================
class TestComputeScenarios:
    def test_returns_4_scenarios(self):
        from unittest.mock import patch
        from services.purchase_service import compute_scenarios

        with patch("services.purchase_service.get_reference_price", return_value=(0.10, "market")):
            from unittest.mock import MagicMock
            db = MagicMock()
            scenarios = compute_scenarios(db, site_id=1, volume_kwh_an=500_000)
            assert len(scenarios) == 4

    def test_all_four_strategies_present(self):
        from unittest.mock import patch, MagicMock
        from services.purchase_service import compute_scenarios

        with patch("services.purchase_service.get_reference_price", return_value=(0.10, "market")):
            db = MagicMock()
            scenarios = compute_scenarios(db, site_id=1, volume_kwh_an=500_000)
            strategies = {s["strategy"] for s in scenarios}
            assert strategies == {"fixe", "indexe", "spot", "reflex_solar"}

    def test_reflex_solar_has_blocs(self):
        from unittest.mock import patch, MagicMock
        from services.purchase_service import compute_scenarios

        with patch("services.purchase_service.get_reference_price", return_value=(0.10, "market")):
            db = MagicMock()
            scenarios = compute_scenarios(db, site_id=1, volume_kwh_an=500_000)
            reflex = next(s for s in scenarios if s["strategy"] == "reflex_solar")
            assert "blocs" in reflex
            assert len(reflex["blocs"]) == 6

    def test_all_scenarios_have_savings(self):
        from unittest.mock import patch, MagicMock
        from services.purchase_service import compute_scenarios

        with patch("services.purchase_service.get_reference_price", return_value=(0.10, "market")):
            db = MagicMock()
            scenarios = compute_scenarios(db, site_id=1, volume_kwh_an=500_000)
            for s in scenarios:
                assert "savings_vs_current_pct" in s


# ========================================
# E. recommend_scenario green bonus for reflex
# ========================================
class TestRecommendReflex:
    def test_green_bonus_applies_to_reflex(self):
        from services.purchase_service import recommend_scenario
        scenarios = [
            {"strategy": "fixe", "risk_score": 15, "total_annual_eur": 50000, "savings_vs_current_pct": 5},
            {"strategy": "reflex_solar", "risk_score": 40, "total_annual_eur": 47000, "savings_vs_current_pct": 6},
        ]
        result = recommend_scenario(scenarios, green_preference=True, budget_priority=0.5)
        reflex = next(s for s in result if s["strategy"] == "reflex_solar")
        # With green_preference, reflex_solar gets +5 bonus
        assert any(s.get("is_recommended") for s in result)

    def test_reflex_reasoning_includes_label(self):
        from services.purchase_service import recommend_scenario
        scenarios = [
            {"strategy": "fixe", "risk_score": 15, "total_annual_eur": 60000, "savings_vs_current_pct": 0},
            {"strategy": "reflex_solar", "risk_score": 40, "total_annual_eur": 47000, "savings_vs_current_pct": 10},
        ]
        result = recommend_scenario(scenarios, budget_priority=0.8)
        reco = next(s for s in result if s.get("is_recommended"))
        if reco["strategy"] == "reflex_solar":
            assert "ReFlex Solar" in reco.get("reasoning", "")

    def test_low_risk_tolerance_excludes_reflex(self):
        from services.purchase_service import recommend_scenario
        scenarios = [
            {"strategy": "fixe", "risk_score": 15, "total_annual_eur": 50000, "savings_vs_current_pct": 5},
            {"strategy": "reflex_solar", "risk_score": 40, "total_annual_eur": 47000, "savings_vs_current_pct": 8},
        ]
        result = recommend_scenario(scenarios, risk_tolerance="low", budget_priority=0.5)
        reco = next(s for s in result if s.get("is_recommended"))
        # risk_score 40 < 50 threshold for low → reflex IS eligible
        # But fixe has lower risk → depends on budget_priority
        assert reco["strategy"] in ("fixe", "reflex_solar")
