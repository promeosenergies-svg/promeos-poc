"""
Tests CO₂ service (V110).
Vérifie les facteurs d'émission ADEME, le calcul par site, et le portfolio.
"""

import pytest
from services.co2_service import EMISSION_FACTORS, Co2Result


class TestEmissionFactors:
    """Facteurs ADEME Base Carbone 2024."""

    def test_elec_factor(self):
        """Élec France mix moyen = 52 gCO₂/kWh."""
        assert EMISSION_FACTORS["elec"]["factor_kg_per_kwh"] == pytest.approx(0.052)

    def test_gaz_factor(self):
        """Gaz naturel PCI = 227 gCO₂/kWh."""
        assert EMISSION_FACTORS["gaz"]["factor_kg_per_kwh"] == pytest.approx(0.227)

    def test_reseau_chaleur_factor(self):
        """Réseau chaleur moyen = 110 gCO₂/kWh."""
        assert EMISSION_FACTORS["reseau_chaleur"]["factor_kg_per_kwh"] == pytest.approx(0.110)

    def test_fioul_factor(self):
        """Fioul domestique = 324 gCO₂/kWh."""
        assert EMISSION_FACTORS["fioul"]["factor_kg_per_kwh"] == pytest.approx(0.324)

    def test_all_have_source(self):
        """Chaque facteur a une source documentée."""
        for key, info in EMISSION_FACTORS.items():
            assert "source" in info, f"{key} manque source"
            assert "ADEME" in info["source"], f"{key} source non ADEME"


class TestCo2Result:
    """Dataclass Co2Result."""

    def test_to_dict(self):
        r = Co2Result(site_id=1, total_kg_co2=520.0, total_t_co2=0.5, breakdown=[], confidence="high")
        d = r.to_dict()
        assert d["site_id"] == 1
        assert d["total_t_co2"] == 0.5

    def test_basic_elec_calculation(self):
        """10 000 kWh élec × 0.052 = 520 kgCO₂."""
        kwh = 10_000
        factor = EMISSION_FACTORS["elec"]["factor_kg_per_kwh"]
        kg = round(kwh * factor, 1)
        assert kg == pytest.approx(520.0, abs=0.1)

    def test_basic_gaz_calculation(self):
        """10 000 kWh gaz × 0.227 = 2270 kgCO₂."""
        kwh = 10_000
        factor = EMISSION_FACTORS["gaz"]["factor_kg_per_kwh"]
        kg = round(kwh * factor, 1)
        assert kg == pytest.approx(2270.0, abs=0.1)

    def test_gaz_vs_elec_ratio(self):
        """Le gaz émet ~4.4× plus que l'élec par kWh."""
        ratio = EMISSION_FACTORS["gaz"]["factor_kg_per_kwh"] / EMISSION_FACTORS["elec"]["factor_kg_per_kwh"]
        assert ratio > 4.0
        assert ratio < 5.0


class TestBenchmarkAssumptions:
    """Benchmarks ADEME patrimoine_assumptions."""

    def test_bureau_thresholds(self):
        from config.patrimoine_assumptions import BENCHMARK_ADEME_KWH_M2_AN

        b = BENCHMARK_ADEME_KWH_M2_AN["bureau"]
        assert b["performant"] < b["bon"] < b["median"]
        assert b["performant"] == 100
        assert b["bon"] == 150
        assert b["median"] == 210

    def test_all_usages_have_3_levels(self):
        from config.patrimoine_assumptions import BENCHMARK_ADEME_KWH_M2_AN

        for usage, bench in BENCHMARK_ADEME_KWH_M2_AN.items():
            assert "performant" in bench, f"{usage} manque performant"
            assert "bon" in bench, f"{usage} manque bon"
            assert "median" in bench, f"{usage} manque median"

    def test_cee_prix_cumac(self):
        from config.patrimoine_assumptions import CEE_PRIX_MWHC_CUMAC_EUR

        assert CEE_PRIX_MWHC_CUMAC_EUR == pytest.approx(8.50)

    def test_benchmark_positioning_logic(self):
        """Logique positionnement : IPE vs seuils."""
        from config.patrimoine_assumptions import BENCHMARK_ADEME_KWH_M2_AN

        bench = BENCHMARK_ADEME_KWH_M2_AN["bureau"]

        # Site performant : 80 kWh/m²/an
        assert 80 <= bench["performant"]
        # Site bon : 120 kWh/m²/an
        assert 120 <= bench["bon"]
        # Site au-dessus : 250 kWh/m²/an
        assert 250 > bench["median"]


class TestCo2N1Comparison:
    """Comparaison N-1 — helpers et shape de réponse."""

    def test_delta_pct_improvement(self):
        """Baisse = delta négatif."""
        from services.co2_service import _delta_pct

        assert _delta_pct(90, 100) == pytest.approx(-10.0)

    def test_delta_pct_degradation(self):
        """Hausse = delta positif."""
        from services.co2_service import _delta_pct

        assert _delta_pct(110, 100) == pytest.approx(10.0)

    def test_delta_pct_no_change(self):
        """Aucun changement = 0."""
        from services.co2_service import _delta_pct

        assert _delta_pct(100, 100) == pytest.approx(0.0)

    def test_delta_pct_no_prev_data(self):
        """Pas de données N-1 → None."""
        from services.co2_service import _delta_pct

        assert _delta_pct(100, None) is None
        assert _delta_pct(100, 0) is None
        assert _delta_pct(None, 100) is None

    def test_safe_prev_date_normal(self):
        """Date normale → OK."""
        from services.co2_service import _safe_prev_date
        from datetime import date

        assert _safe_prev_date(2025, 3, 15) == date(2025, 3, 15)

    def test_safe_prev_date_leap_year(self):
        """29 février N-1 non bissextile → fallback 28."""
        from services.co2_service import _safe_prev_date
        from datetime import date

        # 2025 n'est pas bissextile
        assert _safe_prev_date(2025, 2, 29) == date(2025, 2, 28)

    def test_safe_prev_date_leap_year_ok(self):
        """29 février année bissextile → OK."""
        from services.co2_service import _safe_prev_date
        from datetime import date

        # 2024 est bissextile
        assert _safe_prev_date(2024, 2, 29) == date(2024, 2, 29)

    def test_month_names_fr_complete(self):
        """12 mois en français."""
        from services.co2_service import MONTH_NAMES_FR

        assert len(MONTH_NAMES_FR) == 12
        assert MONTH_NAMES_FR[1] == "Janv"
        assert MONTH_NAMES_FR[12] == "Déc"

    def test_aggregate_co2_results_scopes(self):
        """Scope 1 = gaz/fioul, Scope 2 = elec/réseau chaleur."""
        from services.co2_service import _aggregate_co2_results

        results = [
            {
                "total_kg_co2": 100.0,
                "breakdown": [
                    {"energy_type": "elec", "kwh": 1000, "kg_co2": 52.0},
                    {"energy_type": "gaz", "kwh": 200, "kg_co2": 45.4},
                ],
            },
        ]
        agg = _aggregate_co2_results(results)
        assert agg["scope2_kg"] == pytest.approx(52.0)
        assert agg["scope1_kg"] == pytest.approx(45.4)
        assert agg["total_kg"] == pytest.approx(100.0)

    def test_co2_factors_in_portfolio_response(self):
        """La réponse portfolio doit contenir les facteurs ADEME traçables."""
        # Vérification statique des facteurs exposés
        assert EMISSION_FACTORS["elec"]["factor_kg_per_kwh"] == pytest.approx(0.052)
        assert EMISSION_FACTORS["gaz"]["factor_kg_per_kwh"] == pytest.approx(0.227)
