"""
PROMEOS — Source-guard Phase 2.3 : Top 3 actions Décision impact MWh/an.

Verrouille que chaque action retournée par /api/cockpit/decisions/top3
expose soit `estimated_gain_mwh_year` (MWh/an), soit une pénalité légale
typée via EurAmount avec `regulatory_article` non-null. Jamais d'€ sans
traçabilité (doctrine §0.D décision A).

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §3.B Phase 2.3.
"""

import os
import sys
from datetime import date
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient

from main import app
from services.cockpit_decisions_service import (
    _extract_cee_reference,
    _infer_regulatory_article,
    serialize_action_for_decision,
)

HEADERS = {"X-Org-Id": "1"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── Helpers unitaires ───────────────────────────────────────────────────


class TestExtractCeeReference:
    def test_extracts_bat_th_pattern(self):
        assert _extract_cee_reference("Installer pilotage CVC (BAT-TH-116)") == "BAT-TH-116"

    def test_returns_none_if_no_pattern(self):
        assert _extract_cee_reference("Audit énergétique site") is None
        assert _extract_cee_reference(None) is None
        assert _extract_cee_reference("") is None

    def test_case_insensitive(self):
        assert _extract_cee_reference("Référence bat-th-104") == "BAT-TH-104"


class TestInferRegulatoryArticle:
    def test_compliance_critical_returns_dt_article(self):
        action = SimpleNamespace(source_type="compliance", severity="critical")
        assert _infer_regulatory_article(action) == "Décret 2019-771 art. 9"

    def test_non_compliance_returns_none(self):
        action = SimpleNamespace(source_type="billing", severity="critical")
        assert _infer_regulatory_article(action) is None

    def test_non_critical_returns_none(self):
        action = SimpleNamespace(source_type="compliance", severity="medium")
        assert _infer_regulatory_article(action) is None


# ── serialize_action_for_decision ───────────────────────────────────────


class TestSerializeActionForDecision:
    def test_action_with_gain_exposes_mwh_year(self):
        """Une action avec gain >0 expose estimated_gain_mwh_year, pas _eur."""
        action = SimpleNamespace(
            id=42,
            title="Installer pilotage CVC (BAT-TH-116)",
            rationale="Système GTB classe A/B",
            description=None,
            site_id=1,
            due_date=date(2026, 12, 1),
            estimated_gain_eur=68000,  # → 1000 MWh @ 0.068 €/kWh
            severity="high",
            priority="P1",
            source_type="compliance",
        )
        result = serialize_action_for_decision(action, site_name="Siège HELIOS Paris")
        assert result["estimated_gain_mwh_year"] == 1000
        assert "estimated_gain_eur" not in result, "Phase 2.3 interdit estimated_gain_eur"

    def test_critical_compliance_action_has_traced_penalty(self):
        action = SimpleNamespace(
            id=1,
            title="Mettre en conformité Décret BACS",
            rationale="Pilotage CVC obligatoire",
            description=None,
            site_id=1,
            due_date=date(2026, 12, 31),
            estimated_gain_eur=0,
            severity="critical",
            priority="P1",
            source_type="compliance",
        )
        result = serialize_action_for_decision(action, site_name="Test")
        assert result["regulatory_penalty_eur"] is not None
        penalty = result["regulatory_penalty_eur"]
        assert penalty["regulatory_article"] == "Décret 2019-771 art. 9"
        assert penalty["category"] == "calculated_regulatory"
        assert penalty["value_eur"] > 0

    def test_non_critical_action_no_penalty(self):
        action = SimpleNamespace(
            id=2,
            title="Audit énergétique site",
            rationale="",
            description=None,
            site_id=1,
            due_date=None,
            estimated_gain_eur=15000,
            severity="medium",
            priority="P3",
            source_type="audit",
        )
        result = serialize_action_for_decision(action, site_name="Test")
        assert result["regulatory_penalty_eur"] is None

    def test_title_acronym_transformed(self):
        """Phase 1.8 + 2.3 : le title est passé à transform_acronym."""
        action = SimpleNamespace(
            id=1,
            title="Action DT urgent",
            rationale="",
            description=None,
            site_id=1,
            due_date=None,
            estimated_gain_eur=0,
            severity="high",
            priority="P2",
            source_type="compliance",
        )
        result = serialize_action_for_decision(action, site_name="Test")
        # "DT" → "Décret Tertiaire"
        assert "Décret Tertiaire" in result["title"]


# ── Source-guard endpoint /api/cockpit/decisions/top3 ──────────────────


class TestActionsDecisionShowMwhOrTracedEur:
    def test_endpoint_200(self, client):
        response = client.get("/api/cockpit/decisions/top3", headers=HEADERS)
        assert response.status_code == 200, response.text

    def test_each_action_has_mwh_or_traced_eur(self, client):
        """Chaque action expose soit MWh/an, soit € avec regulatory_article tracé."""
        response = client.get("/api/cockpit/decisions/top3", headers=HEADERS)
        body = response.json()
        decisions = body.get("decisions", [])
        if not decisions:
            pytest.skip("Aucune action ouverte (seed minimal)")

        for action in decisions:
            has_mwh = "estimated_gain_mwh_year" in action and action["estimated_gain_mwh_year"] is not None
            penalty = action.get("regulatory_penalty_eur")
            eur_traced = (
                penalty is not None
                and penalty.get("regulatory_article") is not None
                and penalty.get("regulatory_article") != ""
            )
            assert has_mwh or eur_traced, (
                f"Action id={action.get('id')} viole §0.D : ni MWh exposé ni € tracé. Payload : {action}"
            )

    def test_no_estimated_gain_eur_field_exposed(self, client):
        """Phase 2.3 : aucune action ne doit exposer estimated_gain_eur (anti-régression)."""
        response = client.get("/api/cockpit/decisions/top3", headers=HEADERS)
        decisions = response.json().get("decisions", [])
        for action in decisions:
            assert "estimated_gain_eur" not in action, (
                f"Action id={action.get('id')} expose estimated_gain_eur — interdit Phase 2.3"
            )

    def test_max_3_actions(self, client):
        response = client.get("/api/cockpit/decisions/top3", headers=HEADERS)
        decisions = response.json().get("decisions", [])
        assert len(decisions) <= 3, f"Endpoint retourne {len(decisions)} actions, max 3"
