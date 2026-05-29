"""
PROMEOS — Tests payload `climate.outlier_bounds` (Sprint Énergie P0.S1c).

Cible : enrichissement payload `GET /api/monitoring/kpis` avec champ
`climate.outlier_bounds` calculé via `compute_quantiles` SoT, pour
remplacer le calcul Math.floor frontend `_filterOutliers`.

Stratégie : tests unitaires de la logique d'enrichissement (sans serveur
FastAPI) — on simule un scatter et vérifie que outlier_bounds + quantiles
+ provenance sont bien construits selon contrat.
"""

from __future__ import annotations

import math

import pytest

from services.consumption_granularity_service import compute_quantiles


pytestmark = pytest.mark.fast


def _build_outlier_bounds_from_scatter(scatter: list[dict]) -> dict:
    """Replique la logique d'enrichissement payload (routes/monitoring.py).

    Permet de tester la cohérence du contrat sans démarrer FastAPI.
    """
    if not scatter or len(scatter) < 5:
        return {}
    kwh_values = [p.get("kwh") for p in scatter if p.get("kwh") is not None]
    qs = compute_quantiles(kwh_values, qs=[0.25, 0.5, 0.75])
    q1 = qs.get("p25")
    q3 = qs.get("p75")
    iqr = qs.get("iqr") or 0.0
    out = {
        "quantiles": {
            "q1": q1,
            "median": qs.get("p50"),
            "q3": q3,
            "iqr": iqr,
            "n": qs.get("n"),
        }
    }
    if q1 is not None and q3 is not None:
        out["outlier_bounds"] = {
            "lower": round(q1 - 3 * iqr, 6),
            "upper": round(q3 + 3 * iqr, 6),
            "method": "tukey_3xIQR",
        }
        out["provenance"] = {
            "source": "MeterReading via ClimateEngine",
            "formula": "linear interpolation percentile (Tukey 3·IQR)",
            "service": "consumption_granularity_service.compute_quantiles",
            "n_points": len(kwh_values),
        }
    return out


class TestClimateOutlierBoundsPayloadShape:
    """Contrat du payload climate enrichi côté API."""

    def test_payload_has_quantiles_and_bounds_when_enough_points(self):
        scatter = [{"T": i, "kwh": float(i)} for i in range(20)]
        out = _build_outlier_bounds_from_scatter(scatter)
        assert "quantiles" in out
        assert "outlier_bounds" in out
        assert "provenance" in out

    def test_quantiles_block_keys(self):
        scatter = [{"T": i, "kwh": float(i)} for i in range(10)]
        out = _build_outlier_bounds_from_scatter(scatter)
        q = out["quantiles"]
        assert {"q1", "median", "q3", "iqr", "n"} <= set(q.keys())

    def test_outlier_bounds_keys(self):
        scatter = [{"T": i, "kwh": float(i)} for i in range(10)]
        out = _build_outlier_bounds_from_scatter(scatter)
        b = out["outlier_bounds"]
        assert {"lower", "upper", "method"} <= set(b.keys())
        assert b["method"] == "tukey_3xIQR"

    def test_provenance_includes_service_reference(self):
        scatter = [{"T": i, "kwh": float(i)} for i in range(10)]
        out = _build_outlier_bounds_from_scatter(scatter)
        prov = out["provenance"]
        assert "compute_quantiles" in prov["service"]
        assert "Tukey" in prov["formula"]
        assert prov["n_points"] == 10


class TestClimateOutlierBoundsBehavior:
    """Comportement métier des bornes outliers (Tukey 3·IQR)."""

    def test_bounds_q1_minus_3iqr_and_q3_plus_3iqr(self):
        # [1..9] (n=9, interpolation linéaire) :
        #   Q1 = 1 + 0.25 × 8 = 3.0
        #   Q3 = 1 + 0.75 × 8 = 7.0
        #   IQR = 4 → lower = 3 - 12 = -9, upper = 7 + 12 = 19
        scatter = [{"T": i, "kwh": float(i)} for i in range(1, 10)]
        out = _build_outlier_bounds_from_scatter(scatter)
        b = out["outlier_bounds"]
        assert math.isclose(b["lower"], -9.0, abs_tol=1e-6)
        assert math.isclose(b["upper"], 19.0, abs_tol=1e-6)

    def test_q1_leq_median_leq_q3(self):
        scatter = [{"T": i, "kwh": float(v)} for i, v in enumerate([3, 1, 4, 1, 5, 9, 2, 6, 5, 3])]
        out = _build_outlier_bounds_from_scatter(scatter)
        q = out["quantiles"]
        assert q["q1"] <= q["median"] <= q["q3"]

    def test_empty_scatter_returns_empty(self):
        out = _build_outlier_bounds_from_scatter([])
        assert out == {}

    def test_too_few_points_returns_empty(self):
        scatter = [{"T": 1, "kwh": 1.0}, {"T": 2, "kwh": 2.0}]
        out = _build_outlier_bounds_from_scatter(scatter)
        assert out == {}

    def test_ignores_none_kwh_values(self):
        scatter = [
            {"T": 1, "kwh": 10.0},
            {"T": 2, "kwh": None},
            {"T": 3, "kwh": 20.0},
            {"T": 4, "kwh": 30.0},
            {"T": 5, "kwh": 40.0},
            {"T": 6, "kwh": 50.0},
        ]
        out = _build_outlier_bounds_from_scatter(scatter)
        # 6 entrées au total, 5 valides → quantiles construits.
        assert out["quantiles"]["n"] == 5


class TestClimateOutlierBoundsFiltering:
    """Validation : un FE qui consomme les bornes filtre correctement."""

    def _filter_with_bounds(self, points: list[dict], bounds: dict) -> list[dict]:
        """Replique le filtre FE pur (pas de calcul métier)."""
        if not points or len(points) < 5:
            return points
        if not bounds or bounds.get("lower") is None or bounds.get("upper") is None:
            return points
        lo, hi = bounds["lower"], bounds["upper"]
        return [p for p in points if lo <= p["kwh"] <= hi]

    def test_filter_keeps_normal_points(self):
        scatter = [{"T": i, "kwh": float(i)} for i in range(1, 11)]
        out = _build_outlier_bounds_from_scatter(scatter)
        filtered = self._filter_with_bounds(scatter, out["outlier_bounds"])
        # Aucun point au-delà Tukey 3·IQR sur série uniforme → tous conservés.
        assert len(filtered) == 10

    def test_filter_removes_extreme_outliers(self):
        scatter = [{"T": i, "kwh": float(i)} for i in range(1, 11)]
        scatter.append({"T": 99, "kwh": 9999.0})  # Outlier extrême
        out = _build_outlier_bounds_from_scatter(scatter)
        filtered = self._filter_with_bounds(scatter, out["outlier_bounds"])
        # L'outlier 9999 est filtré.
        assert all(p["kwh"] < 100 for p in filtered)
