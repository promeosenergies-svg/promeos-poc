"""
PROMEOS — Tests clamp_score_0_100 (Sprint Énergie P0.S1a).

Cible : services/electric_monitoring/score_utils.py
Garantit qu'aucun score métier exposé au FE ne dépasse [0, 100],
même en cas de bug formule cumulative (cas réel pré-#315 : data_quality
remontait 108/100, anti-confiance DAF).
"""

import math

import pytest

from services.electric_monitoring.score_utils import clamp_score_0_100


class TestClampScore0100:
    """clamp_score_0_100 garantit [0, 100] sur tous types d'entrée."""

    def test_score_above_100_is_clamped_to_100(self):
        """Cas bug 108/100 — un score > 100 doit retomber à 100."""
        assert clamp_score_0_100(108) == 100

    def test_score_well_above_100_is_clamped_to_100(self):
        """Robustesse : 9999 → 100, pas d'overflow."""
        assert clamp_score_0_100(9999) == 100

    def test_score_below_0_is_clamped_to_0(self):
        """Un score négatif (bug) doit retomber à 0."""
        assert clamp_score_0_100(-5) == 0

    def test_score_well_below_0_is_clamped_to_0(self):
        assert clamp_score_0_100(-9999) == 0

    def test_score_in_range_unchanged(self):
        """Un score dans [0, 100] doit passer inchangé (arrondi entier)."""
        assert clamp_score_0_100(72.4) == 72
        assert clamp_score_0_100(72.6) == 73
        assert clamp_score_0_100(0) == 0
        assert clamp_score_0_100(100) == 100
        assert clamp_score_0_100(50) == 50

    def test_none_preserves_none_by_default(self):
        """preserve_none=True (défaut) : None reste None."""
        assert clamp_score_0_100(None) is None

    def test_none_becomes_zero_if_preserve_disabled(self):
        """Compat orchestrator legacy : preserve_none=False → None devient 0."""
        assert clamp_score_0_100(None, preserve_none=False) == 0

    def test_string_castable_is_clamped(self):
        """Un score en str numérique doit être casté + clampé."""
        assert clamp_score_0_100("85") == 85
        assert clamp_score_0_100("108") == 100
        assert clamp_score_0_100("72.4") == 72

    def test_string_non_castable_returns_zero(self):
        """Un score corrompu (str non numérique) retombe à 0 sans planter."""
        assert clamp_score_0_100("abc") == 0
        assert clamp_score_0_100("") == 0

    def test_nan_returns_zero(self):
        """NaN (résultat division 0/0) → 0 et non NaN."""
        assert clamp_score_0_100(float("nan")) == 0

    def test_infinity_returns_zero(self):
        """Inf (résultat overflow) → 0 et non Inf."""
        assert clamp_score_0_100(float("inf")) == 0
        assert clamp_score_0_100(float("-inf")) == 0

    def test_returns_int(self):
        """Résultat toujours int (pour JSON serialisation FE)."""
        assert isinstance(clamp_score_0_100(72.4), int)
        assert isinstance(clamp_score_0_100(108), int)
        assert isinstance(clamp_score_0_100(0), int)
        assert isinstance(clamp_score_0_100("85"), int)


class TestClampScoreCoverageMonitoringFlow:
    """Scénarios métier réels Monitoring (cf. brief P0 #1)."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            (108, 100),  # cas observé capture v3 2026-05-29
            (105, 100),  # quality_score pénalisation cumulative
            (101.5, 100),  # marge arrondi
            (100, 100),  # limite haute
            (99.5, 100),  # arrondi vers 100
            (99.4, 99),
            (75, 75),
            (50.5, 50),  # banker's rounding Python : 50.5 → 50
            (0, 0),
            (-0.1, 0),  # marge arrondi négatif
            (-10, 0),
        ],
    )
    def test_realistic_quality_scores_clamped_to_valid_range(self, raw, expected):
        assert clamp_score_0_100(raw) == expected

    def test_risk_power_score_above_100_is_clamped(self):
        """`risk_power_score` exposé via /api/monitoring/kpis."""
        assert clamp_score_0_100(115) == 100

    def test_data_quality_score_above_100_is_clamped(self):
        """`data_quality_score` exposé via /api/monitoring/kpis."""
        assert clamp_score_0_100(108) == 100
