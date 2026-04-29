"""
PROMEOS — Source-guard Phase 3.3 : push événementiel "+X vs S-1" (4 métriques).

Verrouille que /api/cockpit/_facts expose une section `weekly_deltas` avec
les 4 métriques canoniques selon doctrine §11.3 push hebdo Vue Exécutive :

  - exposure_eur          : exposition réglementaire (« +3,8 k€ vs S-1 »)
  - potential_mwh_year    : potentiel récupérable (« +18 MWh/an vs S-1 »)
  - sites_in_drift        : sites en dérive (« +1 site vs S-1 »)
  - compliance_score      : score conformité (« stable / -2 pts vs S-1 »)

MVP : previous_value=None tant que l'historique semaine n'est pas seedé en DB
(direction='unknown'). Phase 3.3.bis ajoutera la calibration historique.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §4.B Phase 3.3.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient

from main import app
from services.cockpit_facts_service import _weekly_delta_struct

HEADERS = {"X-Org-Id": "1"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── Helper unitaire _weekly_delta_struct ────────────────────────────


class TestWeeklyDeltaStruct:
    def test_current_none_returns_unknown(self):
        result = _weekly_delta_struct(current_value=None, previous_value=None, unit="€")
        assert result["direction"] == "unknown"
        assert result["delta_absolute"] is None
        assert result["unit"] == "€"

    def test_previous_none_returns_unknown_with_current(self):
        result = _weekly_delta_struct(current_value=26200, previous_value=None, unit="€")
        assert result["current"] == 26200
        assert result["previous"] is None
        assert result["direction"] == "unknown"

    def test_positive_delta_direction_up(self):
        result = _weekly_delta_struct(current_value=30000, previous_value=26200, unit="€")
        assert result["direction"] == "up"
        assert result["delta_absolute"] == 3800
        assert result["delta_pct"] is not None and result["delta_pct"] > 0

    def test_negative_delta_direction_down(self):
        result = _weekly_delta_struct(current_value=20000, previous_value=26200, unit="€")
        assert result["direction"] == "down"
        assert result["delta_absolute"] == -6200
        assert result["delta_pct"] is not None and result["delta_pct"] < 0

    def test_zero_delta_direction_stable(self):
        result = _weekly_delta_struct(current_value=37, previous_value=37, unit="pts")
        assert result["direction"] == "stable"
        assert result["delta_absolute"] == 0


# ── Source-guard endpoint Phase 3.3 ─────────────────────────────────


class TestVueExecutivePushesWeeklyEvolution:
    """L'endpoint /api/cockpit/_facts expose les 4 métriques weekly_deltas."""

    def test_endpoint_exposes_weekly_deltas_section(self, client):
        response = client.get("/api/cockpit/_facts", headers=HEADERS)
        assert response.status_code == 200, response.text
        body = response.json()
        assert "weekly_deltas" in body, "Section weekly_deltas absente du payload _facts"

    def test_4_canonical_metrics_present(self, client):
        response = client.get("/api/cockpit/_facts", headers=HEADERS)
        body = response.json()
        deltas = body.get("weekly_deltas", {})
        canonical = {"exposure_eur", "potential_mwh_year", "sites_in_drift", "compliance_score"}
        assert set(deltas.keys()) >= canonical, f"Metrics manquantes : {canonical - set(deltas.keys())}"

    def test_each_metric_has_canonical_struct(self, client):
        response = client.get("/api/cockpit/_facts", headers=HEADERS)
        deltas = response.json().get("weekly_deltas", {})
        for metric_name, payload in deltas.items():
            for field in ("current", "previous", "delta_absolute", "delta_pct", "direction", "unit"):
                assert field in payload, f"Metric '{metric_name}' manque champ '{field}'. Payload : {payload}"

    def test_direction_canonical_values(self, client):
        response = client.get("/api/cockpit/_facts", headers=HEADERS)
        deltas = response.json().get("weekly_deltas", {})
        valid_directions = {"up", "down", "stable", "unknown"}
        for metric_name, payload in deltas.items():
            assert payload["direction"] in valid_directions, (
                f"Metric '{metric_name}' direction='{payload['direction']}' hors enum canonique"
            )

    def test_units_canonical(self, client):
        """Chaque métrique a une unité humaine cohérente avec son label."""
        response = client.get("/api/cockpit/_facts", headers=HEADERS)
        deltas = response.json().get("weekly_deltas", {})
        # Exposure → € ; potential → MWh/an ; sites → sites ; score → pts
        assert deltas.get("exposure_eur", {}).get("unit") == "€"
        assert deltas.get("potential_mwh_year", {}).get("unit") == "MWh/an"
        assert deltas.get("sites_in_drift", {}).get("unit") == "sites"
        assert deltas.get("compliance_score", {}).get("unit") == "pts"
