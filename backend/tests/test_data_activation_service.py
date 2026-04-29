"""
Source-guard Phase 1.4.e — service data_activation (migration JS → Python).

Sprint refonte cockpit dual sol2 (29/04/2026) — étape 1.4.e : verrouille
le contrat du service Python qui remplace
`frontend/src/models/dataActivationModel.js` (JS conservé temporairement).

Tests adaptés des cas du JS V37 (dataActivationV37.test.js) + ajout
des cas migration Python (camelCase legacy, dataclass to_dict, edge cases).

CLAUDE.md règle d'or #1 : zero business logic frontend.
"""

import pytest
from services.data_activation_service import (
    ACTIVATION_DIMENSIONS,
    ACTIVATION_THRESHOLD,
    ActivationDimension,
    ActivationResult,
    build_activation_checklist,
    compute_activated_count,
)


def make_kpis(**overrides):
    base = {
        "total": 10,
        "conformes": 7,
        "nonConformes": 2,
        "aRisque": 1,
        "risqueTotal": 30000,
        "couvertureDonnees": 80,
    }
    base.update(overrides)
    return base


def make_billing(**overrides):
    base = {"total_invoices": 50, "total_eur": 500_000, "total_loss_eur": 8000}
    base.update(overrides)
    return base


def make_purchase(**overrides):
    base = {
        "totalContracts": 8,
        "totalSites": 10,
        "coverageContractsPct": 80,
    }
    base.update(overrides)
    return base


# ── ACTIVATION_DIMENSIONS canonique ──────────────────────────────────


class TestActivationDimensions:
    def test_5_dimensions_in_canonical_order(self):
        assert ACTIVATION_DIMENSIONS == [
            "patrimoine",
            "conformite",
            "consommation",
            "facturation",
            "achat",
        ]

    def test_threshold_canonical_value(self):
        """ACTIVATION_THRESHOLD = 3 (cohérence avec lever_engine_service)."""
        assert ACTIVATION_THRESHOLD == 3


# ── build_activation_checklist ──────────────────────────────────────


class TestBuildActivationChecklist:
    def test_returns_5_dimensions_in_order(self):
        result = build_activation_checklist(make_kpis(), make_billing(), make_purchase())
        assert len(result.dimensions) == 5
        assert [d.key for d in result.dimensions] == ACTIVATION_DIMENSIONS

    def test_all_5_active_when_full_data(self):
        result = build_activation_checklist(make_kpis(), make_billing(), make_purchase())
        assert result.activated_count == 5
        assert result.total_dimensions == 5
        assert all(d.available for d in result.dimensions)

    def test_zero_active_when_empty_input(self):
        result = build_activation_checklist({}, {}, None)
        assert result.activated_count == 0
        assert result.total_dimensions == 5

    def test_overall_coverage_calculation(self):
        """patrimoine=100, conformite=100 (10/10), consommation=80, facturation=100, achat=80"""
        result = build_activation_checklist(make_kpis(), make_billing(), make_purchase())
        # (100 + 100 + 80 + 100 + 80) / 5 = 92
        assert result.overall_coverage == 92

    def test_next_action_is_first_missing_dimension(self):
        result = build_activation_checklist(make_kpis(couvertureDonnees=0), make_billing(), make_purchase())
        assert result.next_action is not None
        assert result.next_action.key == "consommation"
        assert result.next_action.cta_path == "/consommations/import"

    def test_next_action_null_when_all_active(self):
        result = build_activation_checklist(make_kpis(), make_billing(), make_purchase())
        assert result.next_action is None

    def test_patrimoine_coverage_100_when_total_positive(self):
        result = build_activation_checklist(make_kpis(), {}, None)
        dim = next(d for d in result.dimensions if d.key == "patrimoine")
        assert dim.available is True
        assert dim.coverage == 100

    def test_conformite_coverage_proportional(self):
        result = build_activation_checklist(make_kpis(total=10, conformes=3, nonConformes=2, aRisque=1), {}, None)
        dim = next(d for d in result.dimensions if d.key == "conformite")
        assert dim.available is True
        # (3+2+1)/10 * 100 = 60
        assert dim.coverage == 60

    def test_consommation_uses_couverture_donnees(self):
        result = build_activation_checklist(make_kpis(couvertureDonnees=45), {}, None)
        dim = next(d for d in result.dimensions if d.key == "consommation")
        assert dim.coverage == 45

    def test_achat_uses_coverage_contracts_pct(self):
        result = build_activation_checklist(make_kpis(), {}, make_purchase(coverageContractsPct=60))
        dim = next(d for d in result.dimensions if d.key == "achat")
        assert dim.available is True
        assert dim.coverage == 60

    def test_each_dimension_has_label_cta(self):
        result = build_activation_checklist(make_kpis(), make_billing(), make_purchase())
        for dim in result.dimensions:
            assert dim.label
            assert dim.cta_path
            assert dim.cta_label
            assert dim.description


# ── camelCase legacy compatibility ──────────────────────────────────


class TestCamelCaseLegacyCompatibility:
    def test_accepts_camelcase_kpis(self):
        """Tolère payload JS legacy (nonConformes, aRisque, couvertureDonnees)."""
        kpis = {
            "total": 5,
            "conformes": 3,
            "nonConformes": 1,
            "aRisque": 1,
            "couvertureDonnees": 60,
        }
        result = build_activation_checklist(kpis, {}, None)
        assert result.activated_count == 3  # patrimoine + conformite + consommation

    def test_accepts_snakecase_kpis(self):
        """Accepte aussi payload Python natif (non_conformes, a_risque, couverture_donnees)."""
        kpis = {
            "total": 5,
            "conformes": 3,
            "non_conformes": 1,
            "a_risque": 1,
            "couverture_donnees": 60,
        }
        result = build_activation_checklist(kpis, {}, None)
        assert result.activated_count == 3


# ── compute_activated_count ─────────────────────────────────────────


class TestComputeActivatedCount:
    def test_5_when_full(self):
        assert compute_activated_count(make_kpis(), make_billing(), make_purchase()) == 5

    def test_0_when_empty(self):
        assert compute_activated_count({}, {}, None) == 0
        assert compute_activated_count() == 0

    def test_4_when_couverture_missing(self):
        result = compute_activated_count(make_kpis(couvertureDonnees=0), make_billing(), make_purchase())
        assert result == 4

    def test_3_when_billing_and_purchase_missing(self):
        result = compute_activated_count(make_kpis(), {}, None)
        assert result == 3  # patrimoine + conformite + consommation

    def test_no_crash_on_null(self):
        assert compute_activated_count(None, None, None) == 0

    def test_purchase_signals_absent_treated_as_unavailable(self):
        result = compute_activated_count(make_kpis(), make_billing(), None)
        # 4 actives (patrimoine + conformite + consommation + facturation), achat manquant
        assert result == 4


# ── Dataclass to_dict() ─────────────────────────────────────────────


class TestDataclassContracts:
    def test_activation_dimension_to_dict_complete(self):
        result = build_activation_checklist(make_kpis(), make_billing(), make_purchase())
        d = result.dimensions[0].to_dict()
        assert set(d.keys()) == {
            "key",
            "label",
            "description",
            "available",
            "coverage",
            "detail",
            "cta_path",
            "cta_label",
        }

    def test_activation_result_to_dict_complete(self):
        result = build_activation_checklist(make_kpis(), make_billing(), make_purchase())
        d = result.to_dict()
        assert set(d.keys()) == {
            "dimensions",
            "activated_count",
            "total_dimensions",
            "overall_coverage",
            "next_action",
        }
        assert isinstance(d["dimensions"], list)
        assert len(d["dimensions"]) == 5
