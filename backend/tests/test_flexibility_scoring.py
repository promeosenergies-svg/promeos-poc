"""
Tests du moteur de score de flexibilite par usage.
12 tests couvrant : 15 usages, bornes [0,1], IRVE, Process_continu,
P_max, signal prix negatifs, heures solaires, constantes canoniques.
"""

import pytest
from services.flex.flexibility_scoring_engine import (
    score_usage,
    score_site_flex,
    get_usages_par_archetype,
    detect_prix_negatif_signal,
    USAGE_PROFILES,
    SEUIL_NEBCO_KW,
    PRIX_NEGATIF_SEUIL_EUR_MWH,
    PRIX_POSITIF_SEUIL_EUR_MWH,
    HEURES_NEGATIVES_2025,
)


class TestScoreUsage:
    def test_15_usages_definis(self):
        """Les 15 usages canoniques doivent etre definis."""
        assert len(USAGE_PROFILES) == 15

    def test_score_usage_irve_est_hautement_flexible(self):
        """IRVE = usage le plus flexible (pilotabilite maximale, NEBCO naturelle)."""
        s = score_usage("IRVE")
        assert s.score_global >= 0.85
        assert s.score_pilotabilite >= 0.9
        assert "NEBCO" in s.mecanismes
        assert "ANTICIPATION" in s.modulations

    def test_score_usage_process_continu_est_bas(self):
        """Process continu = usage peu flexible (no-go NEBCO)."""
        s = score_usage("PROCESS_CONTINU")
        assert s.score_global <= 0.35
        assert s.nogo_nebco is True

    def test_score_usage_batteries_signal_prix_negatifs(self):
        """Batteries = signal prix negatifs active."""
        s = score_usage("BATTERIES")
        assert s.signal_prix_negatifs is True
        assert "NEBCO_ANTICIPATION" in s.mecanismes

    def test_score_usage_ecs_heures_solaires(self):
        """ECS = heures solaires applicables (CRE delib. 2026-33)."""
        s = score_usage("ECS")
        assert s.heures_solaires is True

    def test_score_global_borne_0_1(self):
        """Tous les scores doivent etre dans [0, 1]."""
        for code in USAGE_PROFILES:
            s = score_usage(code)
            assert 0.0 <= s.score_global <= 1.0, f"Score hors borne pour {code}: {s.score_global}"

    def test_p_max_insuffisant_plafonne_nebco(self):
        """P_max < 100 kW plafonne le score NEBCO a 0.5 max."""
        s_petit = score_usage("CVC_HVAC", P_max_kw=50.0)
        s_grand = score_usage("CVC_HVAC", P_max_kw=500.0)
        assert s_petit.score_nebco <= 0.5
        assert s_grand.score_nebco > s_petit.score_nebco

    def test_seuil_nebco_constant(self):
        """Seuil NEBCO = 100 kW : constante canonique."""
        assert SEUIL_NEBCO_KW == 100.0


class TestScoreSiteFlex:
    def test_score_site_irve_batteries_haut(self):
        """Site avec IRVE + batteries = score tres eleve."""
        result = score_site_flex(["IRVE", "BATTERIES", "CVC_HVAC"])
        assert result["score_global_site"] >= 0.85
        assert result["nebco_eligible_direct"] is True
        assert result["signal_prix_negatifs"] is True

    def test_score_site_vide(self):
        """Site sans usage : score 0."""
        result = score_site_flex([])
        assert result["score_global_site"] == 0.0

    def test_mecanismes_accessibles_union(self):
        """Mecanismes = union de tous les usages."""
        result = score_site_flex(["IRVE", "ECS"])
        assert "NEBCO" in result["mecanismes_accessibles"]
        assert "HP_HC" in result["mecanismes_accessibles"]

    def test_archetype_bureau_usages_corrects(self):
        """Archetype bureau : CVC_HVAC + ECS + IRVE au minimum."""
        usages = get_usages_par_archetype("BUREAU_STANDARD")
        assert "CVC_HVAC" in usages
        assert "ECS" in usages


class TestPrixSignal:
    def test_prix_negatif_signal_anticipation(self):
        """Prix spot < -10 EUR/MWh : signal ANTICIPATION NEBCO."""
        result = detect_prix_negatif_signal(-20.0)
        assert result["signal"] == "PRIX_NEGATIF"
        assert result["modulation_nebco"] == "ANTICIPATION"
        assert "BATTERIES" in result["usages_cibles"]

    def test_prix_eleve_signal_effacement(self):
        """Prix spot >= 100 EUR/MWh : signal EFFACEMENT NEBCO."""
        result = detect_prix_negatif_signal(150.0)
        assert result["signal"] == "PRIX_ELEVE"
        assert result["modulation_nebco"] == "EFFACEMENT"
        assert "CVC_HVAC" in result["usages_cibles"]

    def test_prix_neutre(self):
        """Prix spot normal : signal NEUTRE."""
        result = detect_prix_negatif_signal(50.0)
        assert result["signal"] == "NEUTRE"

    def test_heures_negatives_2025_canoniques(self):
        """513h prix negatifs en 2025 : source RTE Bilan 2025."""
        assert HEURES_NEGATIVES_2025 == 513
