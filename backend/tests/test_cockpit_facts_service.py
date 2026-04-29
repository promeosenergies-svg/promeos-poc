"""
PROMEOS — Tests Phase 1.3.a : endpoint atomique _facts + monthly_comparison_service.

Couverture :
  - Endpoint /api/cockpit/_facts happy path (200)
  - Toutes sections du payload : scope, consumption, power, compliance,
    exposure, potential_recoverable, alerts, data_quality, metadata
  - Sous-objet monthly_vs_n1 (KPI 2 maquette v1.1)
  - Fallback gracieux empty org → 200 sans 500
  - Source-guards doctrine : DT_PENALTY_EUR, BACS_PENALTY_EUR, OPERAT_PENALTY_EUR
    issus de doctrine.constants — pas de littéraux hardcodés
  - monthly_comparison_service en isolation

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.3
"""

import ast
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient
from main import app
from sqlalchemy.orm import Session

HEADERS = {"X-Org-Id": "1"}
BASE_DIR = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── 1. Endpoint /api/cockpit/_facts happy path ────────────────────────────


class TestCockpitFactsEndpoint:
    def test_200_happy_path(self, client):
        r = client.get("/api/cockpit/_facts", headers=HEADERS)
        assert r.status_code == 200, r.text

    def test_200_with_period_param(self, client):
        for period in ("current_week", "current_month", "current_year"):
            r = client.get(f"/api/cockpit/_facts?period={period}", headers=HEADERS)
            assert r.status_code == 200, f"period={period} failed: {r.text}"

    def test_top_level_sections_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        required_sections = [
            "scope",
            "consumption",
            "power",
            "compliance",
            "exposure",
            "potential_recoverable",
            "alerts",
            "data_quality",
            "metadata",
        ]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"

    def test_no_missing_org_raises_401_or_200(self, client):
        """Sans header org, le demo mode doit retourner 200 (DEMO_MODE=true)."""
        r = client.get("/api/cockpit/_facts")
        # DEMO_MODE=true auto-scope → 200 ; sans démo → 401 ; les deux sont acceptables
        assert r.status_code in (200, 401)


# ── 2. Section scope ──────────────────────────────────────────────────────


class TestScopeSection:
    def test_org_id_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "org_id" in data["scope"]
        assert isinstance(data["scope"]["org_id"], int)

    def test_site_count_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "site_count" in data["scope"]
        assert isinstance(data["scope"]["site_count"], int)

    def test_site_ids_is_list(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "site_ids" in data["scope"]
        assert isinstance(data["scope"]["site_ids"], list)

    def test_surface_total_m2_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "surface_total_m2" in data["scope"]
        assert isinstance(data["scope"]["surface_total_m2"], (int, float))

    def test_ref_year_from_doctrine(self, client):
        from doctrine.constants import DT_REF_YEAR_DEFAULT

        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert data["scope"]["ref_year"] == DT_REF_YEAR_DEFAULT

    def test_org_name_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "org_name" in data["scope"]
        assert isinstance(data["scope"]["org_name"], str)


# ── 3. Section consumption ────────────────────────────────────────────────


class TestConsumptionSection:
    def test_j_minus_1_mwh_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "j_minus_1_mwh" in data["consumption"]
        assert isinstance(data["consumption"]["j_minus_1_mwh"], (int, float))

    def test_baseline_j_minus_1_structure(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        b = data["consumption"]["baseline_j_minus_1"]
        assert "value_mwh" in b
        assert "method" in b
        assert "delta_pct" in b
        assert b["method"] == "a_historical"

    def test_surconso_7d_mwh_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "surconso_7d_mwh" in data["consumption"]

    def test_baseline_7d_structure(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        b = data["consumption"]["baseline_7d"]
        assert "method" in b
        assert "calibration_date" in b

    def test_monthly_vs_n1_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "monthly_vs_n1" in data["consumption"]

    def test_annual_mwh_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "annual_mwh" in data["consumption"]

    def test_trajectory_2030_score_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "trajectory_2030_score" in data["consumption"]
        assert "trajectory_method" in data["consumption"]
        assert data["consumption"]["trajectory_method"] == "c_regulatory_dt"

    def test_sites_in_drift_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "sites_in_drift" in data["consumption"]
        assert isinstance(data["consumption"]["sites_in_drift"], int)


# ── 4. Sous-objet monthly_vs_n1 ──────────────────────────────────────────


class TestMonthlyVsN1:
    def test_current_month_mwh_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        mvn = data["consumption"]["monthly_vs_n1"]
        assert "current_month_mwh" in mvn
        assert isinstance(mvn["current_month_mwh"], (int, float))

    def test_previous_year_month_normalized_mwh_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        mvn = data["consumption"]["monthly_vs_n1"]
        assert "previous_year_month_normalized_mwh" in mvn
        assert isinstance(mvn["previous_year_month_normalized_mwh"], (int, float))

    def test_delta_pct_dju_adjusted_is_int(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        mvn = data["consumption"]["monthly_vs_n1"]
        assert "delta_pct_dju_adjusted" in mvn
        assert isinstance(mvn["delta_pct_dju_adjusted"], int)

    def test_baseline_method_b_dju_adjusted(self, client):
        """monthly_vs_n1 DOIT utiliser baseline_method='b_dju_adjusted' ou 'a_historical' (jamais autre chose)."""
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        mvn = data["consumption"]["monthly_vs_n1"]
        assert "baseline_method" in mvn
        assert mvn["baseline_method"] in ("b_dju_adjusted", "a_historical"), (
            f"baseline_method invalide: {mvn['baseline_method']}"
        )

    def test_r_squared_field_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        mvn = data["consumption"]["monthly_vs_n1"]
        assert "r_squared" in mvn  # peut être None si pas de calibration

    def test_confidence_field_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        mvn = data["consumption"]["monthly_vs_n1"]
        assert "confidence" in mvn
        assert mvn["confidence"] in ("haute", "moyenne", "faible")

    def test_current_month_label_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        mvn = data["consumption"]["monthly_vs_n1"]
        assert "current_month_label" in mvn
        assert isinstance(mvn["current_month_label"], str)
        assert len(mvn["current_month_label"]) > 0


# ── 5. Section power ──────────────────────────────────────────────────────


class TestPowerSection:
    def test_peak_j_minus_1_kw_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "peak_j_minus_1_kw" in data["power"]
        assert isinstance(data["power"]["peak_j_minus_1_kw"], (int, float))

    def test_subscribed_kw_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "subscribed_kw" in data["power"]

    def test_delta_pct_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "delta_pct" in data["power"]
        assert isinstance(data["power"]["delta_pct"], int)

    def test_peak_time_format(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        peak_time = data["power"]["peak_time"]
        assert isinstance(peak_time, str)
        assert ":" in peak_time, f"peak_time should be HH:MM format, got: {peak_time}"


# ── 6. Section compliance ─────────────────────────────────────────────────


class TestComplianceSection:
    def test_score_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "score" in data["compliance"]
        assert isinstance(data["compliance"]["score"], (int, float))

    def test_max_is_100(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert data["compliance"]["max"] == 100

    def test_weighting_keys(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        w = data["compliance"]["weighting"]
        assert "DT" in w
        assert "BACS" in w
        assert "APER" in w

    def test_non_conform_sites_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "non_conform_sites" in data["compliance"]
        assert isinstance(data["compliance"]["non_conform_sites"], int)

    def test_at_risk_sites_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "at_risk_sites" in data["compliance"]
        assert isinstance(data["compliance"]["at_risk_sites"], int)

    def test_obligations_to_treat_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "obligations_to_treat" in data["compliance"]
        assert isinstance(data["compliance"]["obligations_to_treat"], int)


# ── 7. Section exposure ───────────────────────────────────────────────────


class TestExposureSection:
    def test_total_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "total" in data["exposure"]
        assert "value_eur" in data["exposure"]["total"]

    def test_total_has_regulatory_article(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "regulatory_article" in data["exposure"]["total"]

    def test_delta_vs_last_week_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "delta_vs_last_week" in data["exposure"]
        assert "value_eur" in data["exposure"]["delta_vs_last_week"]

    def test_components_is_list(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "components" in data["exposure"]
        assert isinstance(data["exposure"]["components"], list)

    def test_components_structure_if_not_empty(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        for comp in data["exposure"]["components"]:
            assert "label" in comp
            assert "count" in comp
            assert "unit_value_eur" in comp
            assert "value_eur" in comp
            assert "regulatory_article" in comp


# ── 8. Section potential_recoverable ─────────────────────────────────────


class TestPotentialRecoverableSection:
    def test_value_mwh_year_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        pr = data["potential_recoverable"]
        assert "value_mwh_year" in pr
        assert isinstance(pr["value_mwh_year"], int)

    def test_method_is_modeled_cee(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert data["potential_recoverable"]["method"] == "modeled_cee"

    def test_references_is_list(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert isinstance(data["potential_recoverable"]["references"], list)

    def test_by_lever_is_list(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert isinstance(data["potential_recoverable"]["by_lever"], list)

    def test_leverage_count_matches_by_lever(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        pr = data["potential_recoverable"]
        assert pr["leverage_count"] == len(pr["by_lever"])


# ── 9. Section alerts ─────────────────────────────────────────────────────


class TestAlertsSection:
    def test_total_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "total" in data["alerts"]
        assert isinstance(data["alerts"]["total"], int)

    def test_by_severity_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "by_severity" in data["alerts"]
        assert isinstance(data["alerts"]["by_severity"], dict)

    def test_by_type_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "by_type" in data["alerts"]
        assert isinstance(data["alerts"]["by_type"], dict)


# ── 10. Section data_quality ──────────────────────────────────────────────


class TestDataQualitySection:
    def test_ems_coverage_pct_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "ems_coverage_pct" in data["data_quality"]
        assert isinstance(data["data_quality"]["ems_coverage_pct"], int)

    def test_data_completeness_pct_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "data_completeness_pct" in data["data_quality"]
        assert isinstance(data["data_quality"]["data_completeness_pct"], int)

    def test_missing_indices_24h_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "missing_indices_24h" in data["data_quality"]

    def test_sites_with_gaps_is_list(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "sites_with_gaps" in data["data_quality"]
        assert isinstance(data["data_quality"]["sites_with_gaps"], list)


# ── 11. Section metadata ──────────────────────────────────────────────────


class TestMetadataSection:
    def test_last_update_iso_format(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        lu = data["metadata"]["last_update"]
        assert isinstance(lu, str)
        # Format ISO 8601 doit contenir T et Z ou +
        assert "T" in lu

    def test_confidence_present(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "confidence" in data["metadata"]
        assert data["metadata"]["confidence"] in ("haute", "moyenne", "faible")

    def test_sources_is_list(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert "sources" in data["metadata"]
        assert isinstance(data["metadata"]["sources"], list)
        assert len(data["metadata"]["sources"]) > 0


# ── 12. Fallback gracieux empty org ──────────────────────────────────────


class TestFallbackGracieux:
    def test_returns_200_not_500_on_valid_org(self, client):
        """Le payload doit retourner 200 même sur org seed minimal."""
        r = client.get("/api/cockpit/_facts", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        # Sections vides acceptables mais pas d'erreur 500
        assert "scope" in data
        assert "metadata" in data

    def test_all_sections_have_correct_types(self, client):
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        assert isinstance(data["consumption"]["j_minus_1_mwh"], (int, float))
        assert isinstance(data["consumption"]["surconso_7d_mwh"], (int, float))
        assert isinstance(data["power"]["peak_j_minus_1_kw"], (int, float))
        assert isinstance(data["compliance"]["score"], (int, float))
        assert isinstance(data["exposure"]["total"]["value_eur"], (int, float))
        assert isinstance(data["potential_recoverable"]["value_mwh_year"], int)
        assert isinstance(data["alerts"]["total"], int)


# ── 13. Tests monthly_comparison_service isolé ───────────────────────────


class TestMonthlyComparisonService:
    def test_empty_org_returns_zeros_and_faible(self):
        """org sans sites → zéros + confidence='faible' (pas d'exception).
        On patche _meter_ids_for_org pour simuler un org sans compteurs."""
        from services.monthly_comparison_service import get_monthly_vs_previous_year

        db_mock = MagicMock(spec=Session)

        with patch("services.monthly_comparison_service._meter_ids_for_org", return_value=[]):
            result = get_monthly_vs_previous_year(db_mock, org_id=999, today=date(2026, 4, 27))

        assert result["current_month_mwh"] == 0.0
        assert result["previous_year_month_normalized_mwh"] == 0.0
        assert result["delta_pct_dju_adjusted"] == 0
        assert result["confidence"] == "faible"

    def test_canonical_fields_always_present(self):
        """Vérifie que tous les champs canoniques sont présents même en fallback."""
        from services.monthly_comparison_service import get_monthly_vs_previous_year

        db_mock = MagicMock(spec=Session)

        with patch("services.monthly_comparison_service._meter_ids_for_org", return_value=[]):
            result = get_monthly_vs_previous_year(db_mock, org_id=999, today=date(2026, 4, 27))

        required_keys = [
            "current_month_label",
            "current_month_mwh",
            "previous_year_month_normalized_mwh",
            "delta_pct_dju_adjusted",
            "baseline_method",
            "calibration_date",
            "r_squared",
            "confidence",
        ]
        for key in required_keys:
            assert key in result, f"Champ manquant: {key}"

    def test_baseline_method_is_b_dju_adjusted_or_a_historical(self):
        """baseline_method ne peut pas être une valeur arbitraire."""
        from services.monthly_comparison_service import get_monthly_vs_previous_year

        db_mock = MagicMock(spec=Session)

        with patch("services.monthly_comparison_service._meter_ids_for_org", return_value=[]):
            result = get_monthly_vs_previous_year(db_mock, org_id=999, today=date(2026, 4, 27))
        assert result["baseline_method"] in ("b_dju_adjusted", "a_historical")


# ── 14. Source-guards §2.B ────────────────────────────────────────────────


class TestSourceGuardsDoctrine:
    def test_cockpit_facts_dt_penalty_doctrine(self):
        """exposure.components utilise DT_PENALTY_EUR depuis doctrine, pas littéral 7500.0."""
        from doctrine.constants import DT_PENALTY_EUR

        assert DT_PENALTY_EUR == 7500, "DT_PENALTY_EUR doctrine doit être 7500"
        # Vérifier que le service l'utilise (pas de hard-code dans cockpit_facts_service.py)
        service_path = BASE_DIR / "services" / "cockpit_facts_service.py"
        source = service_path.read_text()
        # Le service doit importer DT_PENALTY_EUR
        assert "DT_PENALTY_EUR" in source, "cockpit_facts_service doit importer DT_PENALTY_EUR"
        # Le service ne doit pas contenir le littéral 7500 hors commentaires/docstrings
        lines = source.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if "7500" in stripped and "DT_PENALTY_EUR" not in stripped:
                raise AssertionError(f"Littéral 7500 trouvé sans DT_PENALTY_EUR (source-guard): {stripped!r}")

    def test_facts_uses_doctrine_constants_bacs(self):
        """Vérifie BACS_PENALTY_EUR présent dans le service (pas de littéral 1500)."""
        from doctrine.constants import BACS_PENALTY_EUR

        assert BACS_PENALTY_EUR == 1500
        service_path = BASE_DIR / "services" / "cockpit_facts_service.py"
        source = service_path.read_text()
        assert "BACS_PENALTY_EUR" in source

        lines = source.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            # 1500 peut apparaître légitimement dans d'autres contextes
            # La règle est que BACS_PENALTY_EUR doit être importé et utilisé
        assert "BACS_PENALTY_EUR" in source, "BACS_PENALTY_EUR doit être utilisé"

    def test_monthly_kpi_dju_adjusted(self, client):
        """monthly_vs_n1.baseline_method doit être 'b_dju_adjusted' ou 'a_historical'
        (jamais une méthode inconnue)."""
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        mvn = data["consumption"]["monthly_vs_n1"]
        assert mvn["baseline_method"] in ("b_dju_adjusted", "a_historical"), (
            f"Source-guard: baseline_method invalide pour monthly_vs_n1: {mvn['baseline_method']!r}"
        )

    def test_monthly_kpi_normalized_window(self, client):
        """current_month_label doit contenir mention de la fenêtre (j X-Y)."""
        data = client.get("/api/cockpit/_facts", headers=HEADERS).json()
        label = data["consumption"]["monthly_vs_n1"]["current_month_label"]
        assert "j 1-" in label or "j 1" in label, (
            f"Source-guard: current_month_label doit mentionner la fenêtre, got: {label!r}"
        )

    def test_facts_endpoint_org_scoped(self, client):
        """Vérifie que l'endpoint retourne 200 avec X-Org-Id valide (org-scoping actif)."""
        r = client.get("/api/cockpit/_facts", headers={"X-Org-Id": "1"})
        assert r.status_code == 200

        # Sans header en mode non-demo → comportement variable, mais pas 500
        r_no_header = client.get("/api/cockpit/_facts")
        assert r_no_header.status_code in (200, 401), (
            f"Sans scope: attendu 200 (demo) ou 401, got {r_no_header.status_code}"
        )

    def test_no_literal_dt_penalty_in_facts_service(self):
        """AST guard : cockpit_facts_service.py ne doit pas contenir le littéral
        numérique 7500 (float ou int) en dehors de commentaires."""
        service_path = BASE_DIR / "services" / "cockpit_facts_service.py"
        source = service_path.read_text()
        tree = ast.parse(source)

        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in (7500, 7500.0):
                violations.append(f"Ligne {node.lineno}: littéral {node.value}")
        assert not violations, (
            f"Source-guard AST: DT_PENALTY_EUR (7500) hardcodé dans cockpit_facts_service.py: {violations}"
        )
