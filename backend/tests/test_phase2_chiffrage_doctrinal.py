"""
PROMEOS — Source-guards Phase 2 : chiffrage doctrinal MWh/an (Q1 + 2.2).

Verrouille les exigences DoD §3.C Phase 2 :
  - Phase 2.1 : KPI Leviers exposé en MWh/an (jamais value_eur)
  - Phase 2.2 : KPI Exposition décomposé art. par art. dans tooltip
  - Phase 2.2 : narrative_generator utilise les constantes doctrine
                DT_PENALTY_EUR / BACS_PENALTY_EUR / OPERAT_PENALTY_EUR
                (zéro littéral 7500.0 / 1500 / 3750 dans le code)

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §3.B Phase 2.1/2.2/2.4.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient

from main import app

HEADERS = {"X-Org-Id": "1"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── Phase 2.1 : KPI Leviers en MWh/an (Q1) ──────────────────────────


class TestLeversKpiInMwhNotEur:
    def test_levers_kpi_value_in_mwh_not_eur(self, client):
        """Le KPI Leviers/Potentiel ne doit JAMAIS exposer un value_eur."""
        response = client.get("/api/pages/cockpit_comex/briefing", headers=HEADERS)
        assert response.status_code == 200, response.text
        body = response.json().get("data", {})
        kpis = body.get("kpis", [])

        # Trouver le KPI "Potentiel énergétique récupérable"
        levers_kpi = next(
            (k for k in kpis if "potentiel" in (k.get("label") or "").lower()),
            None,
        )
        assert levers_kpi is not None, (
            f"KPI 'Potentiel énergétique récupérable' absent. KPIs trouvés : {[k.get('label') for k in kpis]}"
        )
        # Value DOIT être en MWh/an, pas en €
        value = levers_kpi.get("value", "")
        assert "MWh" in value or value == "—", (
            f"KPI Leviers value='{value}' — attendu 'X MWh/an' ou '—'. "
            "Phase 2.1 (Q1) : suppression heuristique 8500 €/site."
        )
        assert "€" not in value, f"KPI Leviers value='{value}' contient '€' — interdit Phase 2.1."

    def test_no_value_eur_field_in_levers(self, client):
        """Le payload KPI Leviers ne contient pas de champ value_eur séparé."""
        response = client.get("/api/pages/cockpit_comex/briefing", headers=HEADERS)
        body = response.json().get("data", {})
        kpis = body.get("kpis", [])
        levers_kpi = next(
            (k for k in kpis if "potentiel" in (k.get("label") or "").lower()),
            None,
        )
        if levers_kpi:
            assert "value_eur" not in levers_kpi, "Champ value_eur interdit Phase 2.1"


# ── Phase 2.2 : Exposition décomposé loi à la main ──────────────────


class TestExpositionKpiDecomposed:
    def test_exposure_kpi_tooltip_decomposes_art_par_art(self, client):
        """Le tooltip du KPI Exposition cite les 4 articles canoniques."""
        response = client.get("/api/pages/cockpit_comex/briefing", headers=HEADERS)
        body = response.json().get("data", {})
        kpis = body.get("kpis", [])
        exp_kpi = next(
            (k for k in kpis if "exposition" in (k.get("label") or "").lower()),
            None,
        )
        assert exp_kpi is not None, "KPI 'Exposition financière' absent"
        tooltip = exp_kpi.get("tooltip", "")
        # 4 références réglementaires canoniques attendues
        assert "Décret 2019-771 art. 9" in tooltip, f"Tooltip Exposition manque ref Décret 2019-771 : {tooltip}"
        assert "Décret 2020-887" in tooltip or "BACS" in tooltip, "Tooltip Exposition manque ref BACS"
        assert "Circulaire DGEC" in tooltip or "OPERAT" in tooltip, "Tooltip Exposition manque ref OPERAT"


# ── Phase 2.2 : Constantes doctrine (zéro littéral) ─────────────────


class TestNarrativeGeneratorUsesDoctrineConstants:
    NARRATIVE_PATH = Path(__file__).resolve().parent.parent / "services" / "narrative" / "narrative_generator.py"

    def test_imports_doctrine_penalty_constants(self):
        """narrative_generator importe DT/BACS/OPERAT_PENALTY_EUR depuis doctrine."""
        src = self.NARRATIVE_PATH.read_text()
        assert "DT_PENALTY_EUR" in src, "Import DT_PENALTY_EUR absent"
        assert "DT_PENALTY_AT_RISK_EUR" in src, "Import DT_PENALTY_AT_RISK_EUR absent"
        assert "BACS_PENALTY_EUR" in src, "Import BACS_PENALTY_EUR absent"
        assert "OPERAT_PENALTY_EUR" in src, "Import OPERAT_PENALTY_EUR absent"
        assert "from doctrine.constants import" in src, "Import depuis doctrine.constants absent"

    def test_no_literal_7500_in_narrative_generator(self):
        """Aucun littéral 7500/3750/1500 hors commentaires (zéro hardcoding)."""
        src = self.NARRATIVE_PATH.read_text()
        # Strip docstrings et commentaires Python
        code_only = re.sub(r"#.*$", "", src, flags=re.MULTILINE)
        code_only = re.sub(r'""".*?"""', "", code_only, flags=re.DOTALL)
        code_only = re.sub(r"'''.*?'''", "", code_only, flags=re.DOTALL)

        # 7500.0 ou 7500 isolés (anciens hardcodes)
        forbidden_literals = ["7500.0", "7_500.0", "3750.0", "3_750.0"]
        for lit in forbidden_literals:
            # Tolérer si dans une string `"7500 €"` (tooltip) — pas dans expression numérique
            occurrences = re.findall(rf"\b{re.escape(lit)}\b", code_only)
            assert not occurrences, (
                f"Littéral {lit} encore présent dans narrative_generator.py — "
                f"utiliser DT_PENALTY_EUR / DT_PENALTY_AT_RISK_EUR (Phase 2.2)."
            )

    def test_no_legacy_levier_estime_constant(self):
        """L'heuristique LEVIER_ESTIME_PAR_SITE_EUR doit être supprimée (Q1)."""
        src = self.NARRATIVE_PATH.read_text()
        assert "LEVIER_ESTIME_PAR_SITE_EUR" not in src, (
            "Heuristique LEVIER_ESTIME_PAR_SITE_EUR encore présente — Phase 2.1 (Q1) suppression incomplète."
        )


# ── Phase 2.4 : Footer file actions en MWh/an ───────────────────────


class TestFooterFileActionsMwh:
    def test_week_cards_footer_potentiel_in_mwh(self, client):
        """Les week_cards CFO mentionnent MWh/an et plus € pour les leviers."""
        response = client.get("/api/pages/cockpit_comex/briefing", headers=HEADERS)
        body = response.json().get("data", {})
        week_cards = body.get("week_cards", [])
        watch_cards = [w for w in week_cards if w.get("type") == "watch"]
        if not watch_cards:
            pytest.skip("Aucune week-card watch (seed minimal)")
        # Au moins une card "Potentiel" / "récupérable" en MWh
        recovery_cards = [
            w
            for w in watch_cards
            if "potentiel" in (w.get("title") or "").lower() or "récupérable" in (w.get("title") or "").lower()
        ]
        if recovery_cards:
            for card in recovery_cards:
                title = card.get("title", "")
                assert "MWh" in title, f"Week-card Potentiel '{title}' doit être en MWh/an"
                assert card.get("impact_eur") is None, (
                    "Week-card Potentiel ne doit pas exposer impact_eur (doctrine §0.D)"
                )
