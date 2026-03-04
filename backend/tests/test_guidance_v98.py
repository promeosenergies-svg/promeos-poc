"""
test_guidance_v98.py — V98 Grand Public Guidance Layer tests
Tests: translation dicts, NBA determinism, evidence summary, endpoint.
"""

import pytest
import inspect
from services.reconciliation_service import (
    reconcile_site,
    reconcile_portfolio,
    get_evidence_pack,
    get_evidence_summary,
    CHECK_TRANSLATION,
    ACTION_TRANSLATION,
    _CHECK_PRIORITY,
    _SCORE_GAIN_PER_CHECK,
    _compute_next_best_action,
)


class TestCheckTranslation:
    """V98 A: CHECK_TRANSLATION covers all 6 checks."""

    EXPECTED_CHECKS = [
        "has_delivery_points",
        "has_active_contract",
        "has_recent_invoices",
        "period_coherence",
        "energy_type_match",
        "has_payment_rule",
    ]

    def test_all_checks_translated(self):
        for check_id in self.EXPECTED_CHECKS:
            assert check_id in CHECK_TRANSLATION, f"{check_id} missing from CHECK_TRANSLATION"

    def test_each_has_title_simple(self):
        for check_id, tr in CHECK_TRANSLATION.items():
            assert "title_simple" in tr, f"{check_id} missing title_simple"
            assert isinstance(tr["title_simple"], str) and len(tr["title_simple"]) > 0

    def test_each_has_why_it_matters(self):
        for check_id, tr in CHECK_TRANSLATION.items():
            assert "why_it_matters" in tr, f"{check_id} missing why_it_matters"
            assert isinstance(tr["why_it_matters"], str) and len(tr["why_it_matters"]) > 0

    def test_each_has_impact_label(self):
        for check_id, tr in CHECK_TRANSLATION.items():
            assert "impact_label" in tr, f"{check_id} missing impact_label"
            assert tr["impact_label"] in ("Conso", "Achats", "Facture")


class TestActionTranslation:
    """V98 A: ACTION_TRANSLATION covers all fix actions."""

    EXPECTED_ACTIONS = [
        "create_delivery_point",
        "extend_contract",
        "create_contract",
        "adjust_contract_dates",
        "align_energy_type",
        "create_payment_rule",
        "navigate_import",
    ]

    def test_all_actions_translated(self):
        for action_id in self.EXPECTED_ACTIONS:
            assert action_id in ACTION_TRANSLATION, f"{action_id} missing from ACTION_TRANSLATION"

    def test_each_has_label_simple(self):
        for action_id, tr in ACTION_TRANSLATION.items():
            assert "label_simple" in tr, f"{action_id} missing label_simple"
            assert isinstance(tr["label_simple"], str) and len(tr["label_simple"]) > 0

    def test_each_has_confirmation(self):
        for action_id, tr in ACTION_TRANSLATION.items():
            assert "confirmation" in tr, f"{action_id} missing confirmation"
            assert isinstance(tr["confirmation"], str) and len(tr["confirmation"]) > 0


class TestCheckPriority:
    """V98 C: _CHECK_PRIORITY order and completeness."""

    def test_priority_has_6_entries(self):
        assert len(_CHECK_PRIORITY) == 6

    def test_has_active_contract_is_highest_priority(self):
        assert _CHECK_PRIORITY[0] == "has_active_contract"

    def test_all_checks_in_priority(self):
        for check_id in CHECK_TRANSLATION.keys():
            assert check_id in _CHECK_PRIORITY

    def test_score_gain_per_check_is_17(self):
        assert _SCORE_GAIN_PER_CHECK == 17


class TestComputeNextBestAction:
    """V98 C: NBA determinism and correctness."""

    def _make_check(self, check_id, status, fix_actions=None):
        return {
            "id": check_id,
            "label_fr": f"Check {check_id}",
            "status": status,
            "reason_fr": "reason",
            "title_simple": CHECK_TRANSLATION.get(check_id, {}).get("title_simple", ""),
            "why_it_matters": CHECK_TRANSLATION.get(check_id, {}).get("why_it_matters", ""),
            "fix_actions": fix_actions or [],
        }

    def test_all_ok_returns_none(self):
        checks = [self._make_check(c, "ok") for c in _CHECK_PRIORITY]
        assert _compute_next_best_action(checks, 100) is None

    def test_single_fail_selected(self):
        checks = [
            self._make_check(
                "has_active_contract",
                "fail",
                [
                    {"action": "create_contract", "label_fr": "Créer", "label_simple": "Créer un contrat"},
                ],
            ),
            self._make_check("has_delivery_points", "ok"),
        ]
        nba = _compute_next_best_action(checks, 50)
        assert nba is not None
        assert nba["check_id"] == "has_active_contract"
        assert nba["action"] == "create_contract"
        assert nba["expected_score_gain"] == _SCORE_GAIN_PER_CHECK

    def test_fail_beats_warn(self):
        checks = [
            self._make_check(
                "has_payment_rule",
                "warn",
                [
                    {"action": "create_payment_rule", "label_fr": "Créer règle"},
                ],
            ),
            self._make_check(
                "has_delivery_points",
                "fail",
                [
                    {"action": "create_delivery_point", "label_fr": "Créer PdL"},
                ],
            ),
        ]
        nba = _compute_next_best_action(checks, 33)
        assert nba["check_id"] == "has_delivery_points"

    def test_priority_order_within_same_severity(self):
        """Two fails: has_active_contract (priority 0) beats has_recent_invoices (priority 2)."""
        checks = [
            self._make_check(
                "has_recent_invoices",
                "fail",
                [
                    {"action": "navigate_import", "label_fr": "Importer"},
                ],
            ),
            self._make_check(
                "has_active_contract",
                "fail",
                [
                    {"action": "create_contract", "label_fr": "Créer contrat"},
                ],
            ),
        ]
        nba = _compute_next_best_action(checks, 0)
        assert nba["check_id"] == "has_active_contract"

    def test_no_fix_actions_skip(self):
        """Check with no fix_actions should be skipped."""
        checks = [
            self._make_check("has_active_contract", "fail", []),  # no fix
            self._make_check(
                "has_delivery_points",
                "fail",
                [
                    {"action": "create_delivery_point", "label_fr": "Créer PdL"},
                ],
            ),
        ]
        nba = _compute_next_best_action(checks, 0)
        assert nba["check_id"] == "has_delivery_points"

    def test_nba_has_required_keys(self):
        checks = [
            self._make_check(
                "has_active_contract",
                "fail",
                [
                    {
                        "action": "create_contract",
                        "label_fr": "Créer",
                        "label_simple": "Créer un contrat",
                        "confirmation": "Un contrat sera créé.",
                    },
                ],
            ),
        ]
        nba = _compute_next_best_action(checks, 0)
        required_keys = {
            "check_id",
            "label",
            "reason",
            "action",
            "action_label",
            "expected_score_gain",
            "endpoint",
            "payload",
        }
        assert required_keys.issubset(nba.keys())

    def test_nba_deterministic_same_input(self):
        """Same input must yield same output every time."""
        checks = [
            self._make_check(
                "has_recent_invoices",
                "warn",
                [
                    {"action": "navigate_import", "label_fr": "Importer"},
                ],
            ),
            self._make_check(
                "has_payment_rule",
                "warn",
                [
                    {"action": "create_payment_rule", "label_fr": "Créer règle"},
                ],
            ),
        ]
        results = [_compute_next_best_action(checks, 66) for _ in range(10)]
        assert all(r["check_id"] == results[0]["check_id"] for r in results)


class TestReconcileSiteV98Enrichment:
    """V98: reconcile_site output enriched with translations and NBA."""

    def test_source_has_title_simple_enrichment(self):
        source = inspect.getsource(reconcile_site)
        assert "title_simple" in source

    def test_source_has_why_it_matters_enrichment(self):
        source = inspect.getsource(reconcile_site)
        assert "why_it_matters" in source

    def test_source_has_impact_label_enrichment(self):
        source = inspect.getsource(reconcile_site)
        assert "impact_label" in source

    def test_source_has_next_best_action(self):
        source = inspect.getsource(reconcile_site)
        assert "next_best_action" in source

    def test_source_calls_compute_nba(self):
        source = inspect.getsource(reconcile_site)
        assert "_compute_next_best_action" in source

    def test_source_enriches_fix_actions_with_label_simple(self):
        source = inspect.getsource(reconcile_site)
        assert "label_simple" in source

    def test_source_enriches_fix_actions_with_confirmation(self):
        source = inspect.getsource(reconcile_site)
        assert "confirmation" in source


class TestGetEvidenceSummary:
    """V98 D: Evidence summary function."""

    def test_get_evidence_summary_callable(self):
        assert callable(get_evidence_summary)

    def test_source_has_key_checks(self):
        source = inspect.getsource(get_evidence_summary)
        assert "key_checks" in source

    def test_source_has_recent_fixes(self):
        source = inspect.getsource(get_evidence_summary)
        assert "recent_fixes" in source

    def test_source_has_remaining_actions(self):
        source = inspect.getsource(get_evidence_summary)
        assert "remaining_actions" in source

    def test_source_has_next_best_action(self):
        source = inspect.getsource(get_evidence_summary)
        assert "next_best_action" in source

    def test_source_has_generated_at(self):
        source = inspect.getsource(get_evidence_summary)
        assert "generated_at" in source


class TestEvidenceSummaryEndpoint:
    """V98 D: Evidence summary endpoint exists in routes."""

    def test_endpoint_exists(self):
        from routes.patrimoine import get_reconciliation_evidence_summary

        assert callable(get_reconciliation_evidence_summary)

    def test_routes_import_get_evidence_summary(self):
        source = open(inspect.getfile(__import__("routes.patrimoine", fromlist=["patrimoine"]))).read()
        assert "get_evidence_summary" in source

    def test_routes_has_evidence_summary_path(self):
        source = open(inspect.getfile(__import__("routes.patrimoine", fromlist=["patrimoine"]))).read()
        assert "evidence/summary" in source
