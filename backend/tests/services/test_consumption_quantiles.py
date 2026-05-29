"""
PROMEOS — Tests `compute_quantiles` (Sprint Énergie P0.S1b, brief P3).

Cible : `services.consumption_granularity_service.compute_quantiles`

Cette fonction est le SoT canonique des quartiles Q1/Q3 et de la
médiane. Elle remplace le calcul `Math.floor(length * 0.25)` qui
vivait dans `frontend/src/pages/MonitoringPage.jsx:_filterOutliers`
(violation doctrine « zéro calcul métier frontend »).

Méthode : interpolation linéaire entre rangs (équivalent
numpy.quantile method='linear'). Plus précise que l'index-floor
utilisée frontend.
"""

import math

import pytest

from services.consumption_granularity_service import compute_quantiles


pytestmark = pytest.mark.fast


class TestComputeQuantilesEmpty:
    """Cas brief #1 : liste vide → toutes valeurs None."""

    def test_empty_list_returns_none_for_all_qs(self):
        out = compute_quantiles([])
        assert out["p25"] is None
        assert out["p50"] is None
        assert out["p75"] is None
        assert out["iqr"] is None
        assert out["n"] == 0

    def test_none_list_returns_none(self):
        out = compute_quantiles(None)
        assert out["n"] == 0

    def test_all_none_values_returns_none(self):
        out = compute_quantiles([None, None, None])
        assert out["p25"] is None
        assert out["n"] == 0


class TestComputeQuantilesSingleValue:
    """Cas brief #2 : 1 valeur → Q1=Q3=médiane=cette valeur."""

    def test_single_value_all_quantiles_equal(self):
        out = compute_quantiles([42])
        assert out["p25"] == 42.0
        assert out["p50"] == 42.0
        assert out["p75"] == 42.0
        assert out["iqr"] == 0.0
        assert out["n"] == 1

    def test_single_negative_value(self):
        out = compute_quantiles([-7.5])
        assert out["p25"] == -7.5
        assert out["p50"] == -7.5


class TestComputeQuantilesOddSize:
    """Cas brief #3a : valeurs impaires (médiane = élément central)."""

    def test_5_values_returns_correct_quantiles(self):
        # [1, 2, 3, 4, 5] — Q1 = 2.0, Q2 = 3.0, Q3 = 4.0 (linear)
        out = compute_quantiles([1, 2, 3, 4, 5])
        assert out["p25"] == 2.0
        assert out["p50"] == 3.0
        assert out["p75"] == 4.0
        assert out["iqr"] == 2.0
        assert out["n"] == 5

    def test_7_values_returns_correct_quantiles(self):
        # [1..7] — Q1 = 2.5, median = 4, Q3 = 5.5
        out = compute_quantiles([1, 2, 3, 4, 5, 6, 7])
        assert out["p25"] == 2.5
        assert out["p50"] == 4.0
        assert out["p75"] == 5.5

    def test_unsorted_input_is_handled(self):
        """L'entrée doit être triée en interne (Sprint robustesse)."""
        out = compute_quantiles([5, 1, 3, 4, 2])
        assert out["p50"] == 3.0


class TestComputeQuantilesEvenSize:
    """Cas brief #3b : valeurs paires (interpolation linéaire)."""

    def test_4_values_returns_interpolated_quantiles(self):
        # [1, 2, 3, 4] — Q1 = 1.75, Q2 = 2.5, Q3 = 3.25 (linear)
        out = compute_quantiles([1, 2, 3, 4])
        assert out["p25"] == 1.75
        assert out["p50"] == 2.5
        assert out["p75"] == 3.25

    def test_6_values_returns_interpolated_quantiles(self):
        out = compute_quantiles([10, 20, 30, 40, 50, 60])
        # Q1 = 22.5, Q2 = 35.0, Q3 = 47.5
        assert out["p25"] == 22.5
        assert out["p50"] == 35.0
        assert out["p75"] == 47.5


class TestComputeQuantilesDecimal:
    """Cas brief #4 : valeurs décimales (précision conservée)."""

    def test_decimal_values_precision_6_digits(self):
        out = compute_quantiles([1.1, 2.2, 3.3, 4.4, 5.5])
        assert out["p50"] == 3.3
        assert math.isclose(out["p25"], 2.2, abs_tol=1e-6)
        assert math.isclose(out["p75"], 4.4, abs_tol=1e-6)

    def test_small_decimals(self):
        out = compute_quantiles([0.001, 0.002, 0.003])
        assert out["p50"] == 0.002


class TestComputeQuantilesOrdering:
    """Cas brief #5 : Q1 <= médiane <= Q3 (cohérence statistique)."""

    @pytest.mark.parametrize(
        "values",
        [
            [1, 2, 3, 4, 5],
            [10, 5, 15, 20, 1],
            [100, 1, 50, 25, 75, 10],
            [1.5, 2.7, 3.1, 4.9, 5.2, 6.8, 7.3],
        ],
    )
    def test_ordering_q1_leq_median_leq_q3(self, values):
        out = compute_quantiles(values)
        assert out["p25"] <= out["p50"] <= out["p75"], f"Ordering violated for {values} → {out}"

    def test_iqr_is_non_negative(self):
        out = compute_quantiles([1, 2, 3, 4, 5, 6, 7, 8, 9])
        assert out["iqr"] >= 0


class TestComputeQuantilesEdgeCases:
    """Cas robustesse — entrées corrompues."""

    def test_filters_nan_and_inf(self):
        out = compute_quantiles([1, float("nan"), 2, float("inf"), 3])
        # NaN et Inf ignorés → effectif [1, 2, 3]
        assert out["n"] == 3
        assert out["p50"] == 2.0

    def test_filters_non_numeric(self):
        out = compute_quantiles([1, "abc", 2, None, 3])
        assert out["n"] == 3
        assert out["p50"] == 2.0

    def test_accepts_string_castable(self):
        out = compute_quantiles(["1", "2", "3"])
        assert out["n"] == 3
        assert out["p50"] == 2.0

    def test_custom_quantiles(self):
        """Brief : `qs` paramétrable (ex P10 / P90)."""
        out = compute_quantiles([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], qs=[0.1, 0.9])
        assert out["p10"] == 1.9
        assert out["p90"] == 9.1
        # iqr seulement si 0.25 ET 0.75 demandés
        assert "iqr" not in out or out.get("iqr") is None

    def test_invalid_quantile_returns_none(self):
        """Quantile hors [0, 1] → None mais ne plante pas."""
        out = compute_quantiles([1, 2, 3], qs=[0.5, 1.5, -0.1])
        assert out["p50"] == 2.0
        assert out["p150"] is None
        assert out["p-10"] is None


class TestComputeQuantilesNumpyCompat:
    """Compatibilité numpy.quantile method='linear' (validation référence)."""

    def test_matches_numpy_method_linear(self):
        """Si numpy disponible, validation cross-référence."""
        try:
            import numpy as np
        except ImportError:
            pytest.skip("numpy non disponible")

        vals = [1.2, 4.5, 7.8, 2.3, 9.1, 3.4, 6.7, 5.6, 8.9, 0.1]
        out = compute_quantiles(vals)

        # numpy.quantile method='linear' (défaut)
        np_q25 = float(np.quantile(vals, 0.25))
        np_q50 = float(np.quantile(vals, 0.50))
        np_q75 = float(np.quantile(vals, 0.75))

        assert math.isclose(out["p25"], np_q25, abs_tol=1e-5)
        assert math.isclose(out["p50"], np_q50, abs_tol=1e-5)
        assert math.isclose(out["p75"], np_q75, abs_tol=1e-5)
