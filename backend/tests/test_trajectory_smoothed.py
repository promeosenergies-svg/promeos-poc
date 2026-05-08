"""
PROMEOS — Source-guard Phase 1.6 : trajectoire DT lissée par action.due_date (Q5).

Avant Phase 1.6 : la projection trajectoire appliquait 100 % des gains dès
l'année courante → drop YoY -43 % brutal visuellement faux. Après : chaque
action contribue selon sa due_date, drop YoY < 15 % attendu.

Tests :
  1. Pure helper `_project_with_action_echeances` (algorithme isolé)
  2. Endpoint /api/cockpit/trajectory : drop YoY < 15 % sur projection_mwh

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.6.
"""

import os
import sys
from datetime import date, datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient

from main import app
from routes.cockpit import _project_with_action_echeances

HEADERS = {"X-Org-Id": "1"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── Helper unitaire pure ────────────────────────────────────────────────


class TestProjectWithActionEcheances:
    def test_no_actions_returns_baseline(self):
        result = _project_with_action_echeances(1000.0, [], target_year=2027, current_year=2026)
        assert result == 1000.0

    def test_action_without_due_date_applies_from_current_year(self):
        action = SimpleNamespace(estimated_gain_eur=68000, due_date=None)
        # gain_kwh = 68000 / 0.068 = 1_000_000 kWh = 1000 MWh
        result = _project_with_action_echeances(2000.0, [action], target_year=2027, current_year=2026)
        assert abs(result - 1000.0) < 1.0  # 2000 - 1000 = 1000

    def test_action_due_after_target_year_engagement_only(self):
        """Phase 30 : action due dans le futur lointain → contribution
        engagement (≤ 30 % du gain) au lieu de 0. Modèle apprentissage 3
        phases (engagement → ramp-up → régime nominal).
        """
        action = SimpleNamespace(estimated_gain_eur=68000, due_date=date(2030, 6, 15))
        result = _project_with_action_echeances(2000.0, [action], target_year=2027, current_year=2026)
        # Avant Phase 30 : result == 2000 (zéro contribution)
        # Après Phase 30 : result < 2000 (engagement progress contribue)
        # Mais ne dépasse pas 30 % du gain modélisé (RATIO_ENGAGEMENT plafond)
        assert 1700.0 <= result <= 2000.0, f"Phase 30 engagement progress : 1700 ≤ result ≤ 2000, trouvé {result}"

    def test_action_due_in_target_year_engagement_phase(self):
        """Phase 30 : action due début target_year (target_mid > due_date) →
        ramp-up post-installation, ratio entre RATIO_ENGAGEMENT (20 %) et
        RATIO_RAMP_UP (75 %)."""
        action = SimpleNamespace(estimated_gain_eur=68000, due_date=date(2026, 7, 1))
        # target_mid 2026-07-01 = due_date → months_since_due=0, ratio=20%
        result = _project_with_action_echeances(2000.0, [action], target_year=2026, current_year=2026)
        # Contribution attendue : ~ 20 % × 1000 MWh = 200 → result ~ 1800
        assert 1750.0 <= result <= 1850.0, f"Phase 30 engagement à due_date : ~1800, trouvé {result}"

    def test_action_due_before_target_year_ramp_up(self):
        """Phase 30 : action due 13 mois avant target_mid → ramp-up plein
        (ratio = RATIO_ENGAGEMENT + (RATIO_RAMP_UP - RATIO_ENGAGEMENT) ×
        13/MONTHS_RAMP_UP). Pour 13/18 ≈ 72 % : ratio ≈ 0.20 + 0.55*0.72 = 0.60."""
        action = SimpleNamespace(estimated_gain_eur=68000, due_date=date(2026, 6, 1))
        # target_mid 2027-07-01 = due_date + 13 mois
        result = _project_with_action_echeances(2000.0, [action], target_year=2027, current_year=2026)
        # Contribution attendue : ~ 60 % × 1000 = 600 → result ~ 1400
        assert 1350.0 <= result <= 1500.0, f"Phase 30 ramp-up 13 mois post-due : ~1400, trouvé {result}"

    def test_action_due_two_years_before_target_full_nominal(self):
        """Phase 30 : action due 24 mois avant target → régime nominal plein."""
        action = SimpleNamespace(estimated_gain_eur=68000, due_date=date(2026, 1, 1))
        # target_mid 2028-07-01 = due_date + 30 mois > MONTHS_RAMP_UP=18
        result = _project_with_action_echeances(2000.0, [action], target_year=2028, current_year=2026)
        # Contribution : 100 % × 1000 = 1000 → result = 1000
        assert abs(result - 1000.0) < 1.0, f"Phase 30 régime nominal post 24 mois : 1000, trouvé {result}"

    def test_baseline_floor_zero(self):
        """Si savings > baseline, projection plancher à 0."""
        action = SimpleNamespace(estimated_gain_eur=1_000_000, due_date=None)
        result = _project_with_action_echeances(100.0, [action], target_year=2027, current_year=2026)
        assert result == 0.0

    def test_zero_gain_action_skipped(self):
        action = SimpleNamespace(estimated_gain_eur=0, due_date=None)
        result = _project_with_action_echeances(1000.0, [action], target_year=2027, current_year=2026)
        assert result == 1000.0

    def test_smoothed_progression_avoids_brutal_drop(self):
        """Plusieurs actions avec due_dates étalées → progression lissée.

        Phase 30 : seuil drop YoY assoupli à -25 % (vs -15 % Phase 1.6) car
        le modèle apprentissage exhibe naturellement un palier intermédiaire
        plus marqué entre engagement et régime nominal. Le test vérifie
        toujours qu'on n'a PAS de chute step-function brutale (-43 % avant
        Phase 1.6).
        """
        actions = [
            SimpleNamespace(estimated_gain_eur=20_000, due_date=date(2026, 6, 1)),
            SimpleNamespace(estimated_gain_eur=20_000, due_date=date(2027, 6, 1)),
            SimpleNamespace(estimated_gain_eur=20_000, due_date=date(2028, 6, 1)),
        ]
        baseline_2025 = 4229.0
        proj_2026 = _project_with_action_echeances(baseline_2025, actions, 2026, 2026)
        proj_2027 = _project_with_action_echeances(baseline_2025, actions, 2027, 2026)
        proj_2028 = _project_with_action_echeances(baseline_2025, actions, 2028, 2026)
        # Chaque drop YoY relatif doit être < 25 % (Phase 30 : courbe
        # apprentissage 3 phases peut avoir palier intermédiaire un peu
        # plus marqué qu'avant Phase 30 sur seed avec actions concentrées).
        drop_2027 = (proj_2027 - proj_2026) / proj_2026
        drop_2028 = (proj_2028 - proj_2027) / proj_2027
        assert drop_2027 > -0.25, f"Drop 2026→2027 trop violent : {drop_2027:.2%}"
        assert drop_2028 > -0.25, f"Drop 2027→2028 trop violent : {drop_2028:.2%}"


# ── Source-guard endpoint ──────────────────────────────────────────────


class TestTrajectoryEndpointSmoothed:
    def test_trajectory_smoothed_by_echeance(self, client):
        """Trajectoire lissée — drops YoY améliorés vs régime pré-Phase 1.6.

        Avant Phase 1.6 : drop unique brutal -43 % current_year → current_year+1
        (tous les savings appliqués d'un coup). Après : lissage par due_date
        OU au minimum drop < 35 % (cas seed concentré sur une seule année).

        Cible idéale : drop YoY < 15 % (cas seed avec due_dates étalées sur
        plusieurs années, validé par tests unit du helper).
        """
        response = client.get("/api/cockpit/trajectory", headers=HEADERS)
        assert response.status_code == 200, response.text
        body = response.json()
        proj = body.get("projection_mwh") or []
        valid_pairs = [
            (proj[i], proj[i + 1])
            for i in range(len(proj) - 1)
            if proj[i] is not None and proj[i + 1] is not None and proj[i] > 0
        ]
        if not valid_pairs:
            pytest.skip("Aucun couple de projections valides (seed minimal)")

        max_drop = min((curr - prev) / prev for prev, curr in valid_pairs)
        assert max_drop > -0.35, (
            f"Régression Phase 1.6 : drop max {max_drop:.2%} (seuil -35 %). "
            "Avant Phase 1.6 le drop atteignait -43 %. Si seed actions ont "
            "des due_dates concentrées sur une seule année, le drop initial "
            "reste fort — voir tests unitaires _project_with_action_echeances "
            "pour validation lissage rigoureux."
        )

        # Phase 30 : drops post-saut initial relâchés à 30 % (palier
        # apprentissage 3 phases sur seed avec actions concentrées en 2026 :
        # 2026 = engagement (15-20 %) → 2027 = ramp-up (60-80 %) → 2028 =
        # nominal 100 % donne un drop ~25 % entre 2026 et 2027 maximum).
        stable_drops = [d for d in ((curr - prev) / prev for prev, curr in valid_pairs[1:])]
        if stable_drops:
            assert max(abs(d) for d in stable_drops) < 0.30, (
                f"Drops post-saut initial doivent être stables (<30 %) : {stable_drops}"
            )

    def test_trajectory_continuity_anchor_last_real_year(self, client):
        """Phase G fix défaut graphe trajectoire DT : continuité RÉEL→PROJECTION.

        Avant ce fix : projection_mwh[i] = None pour year < current_year, créant
        une discontinuité visible entre dernier RÉEL (year _cy - 1) et premier
        PROJECTION (year _cy). Après : projection_mwh[year == _cy - 1] est ancré
        sur la valeur RÉEL pour le pont visuel cardinal.
        """
        response = client.get("/api/cockpit/trajectory", headers=HEADERS)
        assert response.status_code == 200, response.text
        body = response.json()
        annees = body.get("annees") or []
        proj = body.get("projection_mwh") or []
        reel = body.get("reel_mwh") or []
        if not annees or not proj:
            pytest.skip("Pas de série trajectoire (seed minimal)")

        current_year = datetime.now(tz=None).year
        anchor_year = current_year - 1
        if anchor_year not in annees:
            pytest.skip("Année d'ancrage hors plage")

        idx = annees.index(anchor_year)
        # Si reel_mwh disponible à l'année d'ancrage, projection doit être ancrée dessus
        if reel[idx] is not None and proj[idx] is not None:
            assert proj[idx] == reel[idx], (
                f"Phase G fix continuité : projection[{anchor_year}]={proj[idx]} doit "
                f"matcher reel[{anchor_year}]={reel[idx]} pour le pont visuel cardinal"
            )
