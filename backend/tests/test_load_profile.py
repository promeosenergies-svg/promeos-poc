"""Tests pour load_profile_service et energy_signature_service avancé."""

import math
from datetime import datetime

from services.load_profile_service import _compute_quality_score


# ── Tests score qualité ──────────────────────────────────────────────────


class TestQualityScore:
    """Score Q = 1 - (trous + aberrants + incoherents) / total."""

    def test_perfect_data(self):
        """Données complètes sans anomalies → score excellent."""
        start = datetime(2025, 1, 1).date()
        end = datetime(2025, 1, 31).date()
        readings = [
            {"ts": datetime(2025, 1, d, h), "kwh": 10.0 + d * 0.1, "quality": 1.0}
            for d in range(1, 31)
            for h in range(24)
        ]
        result = _compute_quality_score(readings, start, end)
        assert result["score"] > 0.90
        assert result["label"] in ("excellent", "bon")
        assert result["details"]["gaps"] == 0
        assert result["details"]["outliers"] == 0

    def test_many_gaps(self):
        """Beaucoup de jours manquants → score insuffisant."""
        start = datetime(2025, 1, 1).date()
        end = datetime(2025, 3, 31).date()  # 90 jours
        readings = [
            {"ts": datetime(2025, 1, d, 12), "kwh": 10.0, "quality": 1.0}
            for d in range(1, 11)  # seulement 10 jours
        ]
        result = _compute_quality_score(readings, start, end)
        assert result["score"] < 0.80
        assert result["label"] == "insuffisant"
        assert result["details"]["gaps"] >= 70

    def test_negative_outliers(self):
        """Valeurs négatives détectées comme aberrantes."""
        start = datetime(2025, 1, 1).date()
        end = datetime(2025, 1, 10).date()
        readings = [
            {"ts": datetime(2025, 1, d, h), "kwh": 10.0, "quality": 1.0} for d in range(1, 10) for h in range(24)
        ]
        # Injecter des négatifs
        for i in range(5):
            readings[i]["kwh"] = -5.0
        result = _compute_quality_score(readings, start, end)
        assert result["details"]["outliers"] >= 5

    def test_empty_readings(self):
        """Aucune donnée → score 0."""
        result = _compute_quality_score([], datetime(2025, 1, 1).date(), datetime(2025, 1, 31).date())
        assert result["score"] == 0
        assert result["label"] == "insuffisant"


# ── Tests indicateurs de profil ──────────────────────────────────────────


class TestLoadProfileIndicators:
    """Tests unitaires sur les formules des indicateurs."""

    def test_load_factor_flat_curve(self):
        """Courbe plate → LF = 1.0."""
        powers = [10.0] * 100
        p_moy = sum(powers) / len(powers)
        p_max = max(powers)
        lf = p_moy / p_max
        assert abs(lf - 1.0) < 0.01

    def test_load_factor_spiky_curve(self):
        """Courbe avec un pic → LF faible."""
        powers = [1.0] * 99 + [100.0]
        p_moy = sum(powers) / len(powers)
        p_max = max(powers)
        lf = p_moy / p_max
        assert lf < 0.1

    def test_night_day_ratio(self):
        """Consommation concentrée de jour → ratio faible."""
        e_night = 100  # 22h-6h (8h)
        e_day = 900  # 6h-22h (16h)
        ratio = e_night / e_day
        assert ratio < 0.15

    def test_weekend_weekday_ratio_offices(self):
        """Bureaux fermés le WE → ratio WE/semaine faible."""
        e_weekday_per_day = 500
        e_weekend_per_day = 50
        ratio = e_weekend_per_day / e_weekday_per_day
        assert ratio < 0.15

    def test_base_peak_ratio(self):
        """Ratio base/pointe."""
        p5 = 2.0
        p95 = 20.0
        ratio = p5 / p95
        assert abs(ratio - 0.1) < 0.01

    def test_variability_flat(self):
        """Courbe constante → CV = 0."""
        values = [10.0] * 24
        mu = sum(values) / len(values)
        sigma = math.sqrt(sum((x - mu) ** 2 for x in values) / len(values))
        cv = sigma / mu if mu > 0 else 0
        assert cv == 0


# ── Tests signature avancée ──────────────────────────────────────────────


class TestAdvancedSignature:
    """Tests pour le moteur piecewise (via ems/signature_service)."""

    def test_heating_only(self):
        """Site avec chauffage uniquement → modèle heating_dominant."""
        from services.ems.signature_service import run_signature

        # Simuler E = 100 + 5 * max(0, 15 - T) + bruit
        import random

        random.seed(42)
        temps = [t / 2 for t in range(-10, 50)]  # -5 à 25°C
        kwh = [100 + 5 * max(0, 15 - t) + random.gauss(0, 3) for t in temps]

        result = run_signature(kwh, temps)
        assert "error" not in result
        assert result["label"] in ("heating_dominant", "mixed")
        assert result["a_heating"] > 2.0
        assert result["r_squared"] > 0.7

    def test_flat_site(self):
        """Site constant (data center) → pentes quasi-nulles."""
        from services.ems.signature_service import run_signature

        import random

        random.seed(42)
        temps = [t / 2 for t in range(-10, 50)]
        kwh = [500 + random.gauss(0, 10) for _ in temps]

        result = run_signature(kwh, temps)
        assert "error" not in result
        # Pentes très faibles même si BIC choisit un modèle avec slope
        assert result["a_heating"] < 3.0
        assert result["b_cooling"] < 3.0
        assert result["base_kwh"] > 450

    def test_insufficient_data(self):
        """Moins de 10 points → erreur."""
        from services.ems.signature_service import run_signature

        result = run_signature([1, 2, 3], [10, 11, 12])
        assert "error" in result
        assert result["error"] == "insufficient_data"

    def test_mixed_model(self):
        """Site avec chauffage + climatisation → modèle mixed."""
        from services.ems.signature_service import run_signature

        import random

        random.seed(42)
        temps = [t / 2 for t in range(-10, 70)]  # -5 à 35°C
        kwh = [200 + 8 * max(0, 15 - t) + 4 * max(0, t - 24) + random.gauss(0, 5) for t in temps]

        result = run_signature(kwh, temps)
        assert "error" not in result
        assert result["a_heating"] > 2.0
        assert result["b_cooling"] > 1.0
        assert result["r_squared"] > 0.7
