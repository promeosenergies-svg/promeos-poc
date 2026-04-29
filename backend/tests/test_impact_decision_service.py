"""
Source-guard Phase 1.4.b — service impact_decision (migration JS → Python).

Sprint refonte cockpit dual sol2 (29/04/2026) — étape 1.4.b : verrouille
le contrat du service Python qui remplace `frontend/src/models/impactDecisionModel.js`
(supprimé en parallèle).

Tests adaptés des cas couverts par les tests JS historiques V30 + ajout
des cas pour la migration Python (fallback dict, cas limites).

CLAUDE.md règle d'or #1 : zero business logic frontend. Ce service
porte désormais la logique de priorisation Impact & Décision côté backend.
"""

import pytest
from services.impact_decision_service import (
    OPTIM_RATE_V1,
    ImpactKpis,
    Recommendation,
    compute_impact_kpis,
    compute_recommendation,
)


# ── compute_impact_kpis ──────────────────────────────────────────────


class TestComputeImpactKpis:
    """Tests des 3 KPIs Impact & Décision."""

    def test_default_values_when_no_input(self):
        result = compute_impact_kpis()
        assert result.risque_conformite_eur == 0
        assert result.surcout_facture_eur == 0
        assert result.opportunite_optim_eur == 0
        assert result.risque_available is False
        assert result.surcout_available is False
        assert result.optim_available is False

    def test_risque_from_kpis_total(self):
        result = compute_impact_kpis(kpis={"risque_total_eur": 26200, "total": 5}, billing_summary={})
        assert result.risque_conformite_eur == 26200
        assert result.risque_available is True

    def test_risque_legacy_camelcase_compatibility(self):
        """Tolère le payload JS legacy `risqueTotal` (camelCase)."""
        result = compute_impact_kpis(kpis={"risqueTotal": 7500, "total": 1})
        assert result.risque_conformite_eur == 7500

    def test_surcout_clamp_negative(self):
        """Surcoût négatif clampé à 0 (anti pertes-négatives)."""
        result = compute_impact_kpis(billing_summary={"total_loss_eur": -500, "total_invoices": 5})
        assert result.surcout_facture_eur == 0
        assert result.surcout_available is True  # invoices présentes

    def test_surcout_available_when_invoices_present(self):
        """surcout_available True si au moins une facture, même sans loss."""
        result = compute_impact_kpis(billing_summary={"total_loss_eur": 0, "total_invoices": 12})
        assert result.surcout_available is True

    def test_opportunite_uses_optim_rate_v1(self):
        """Opportunité = 1 % du facturé (heuristique V1)."""
        result = compute_impact_kpis(billing_summary={"total_eur": 100_000})
        assert result.opportunite_optim_eur == round(100_000 * OPTIM_RATE_V1)
        assert result.opportunite_optim_eur == 1000
        assert result.optim_available is True

    def test_optim_available_only_if_total_eur_positive(self):
        result = compute_impact_kpis(billing_summary={"total_eur": 0})
        assert result.optim_available is False

    def test_to_dict_contract(self):
        impact = compute_impact_kpis(
            kpis={"risque_total_eur": 100, "total": 1},
            billing_summary={"total_eur": 5000, "total_loss_eur": 50, "total_invoices": 3},
        )
        d = impact.to_dict()
        assert set(d.keys()) == {
            "risque_conformite_eur",
            "surcout_facture_eur",
            "opportunite_optim_eur",
            "risque_available",
            "surcout_available",
            "optim_available",
        }


# ── compute_recommendation ───────────────────────────────────────────


class TestComputeRecommendation:
    """Tests de la recommandation prioritaire rule-based V1."""

    def test_no_data_when_all_zero(self):
        impact = ImpactKpis(0, 0, 0, False, False, False)
        reco = compute_recommendation(impact, {})
        assert reco.key == "no_data"
        assert "compléter les données" in reco.titre.lower()
        assert reco.cta_path == "/patrimoine"
        assert len(reco.bullets) == 3

    def test_priorite_conformite_when_risque_max(self):
        impact = ImpactKpis(26200, 1000, 500, True, True, True)
        reco = compute_recommendation(impact, {"non_conformes": 1, "a_risque": 4})
        assert reco.key == "conformite"
        assert reco.cta_path == "/conformite"
        # Mention sites_count = 1 + 4 = 5
        assert "5 site" in reco.bullets[0]
        # Risque mentionné
        assert "26" in reco.bullets[1]

    def test_priorite_conformite_legacy_camelcase_kpis(self):
        """Tolère payload JS legacy nonConformes/aRisque (camelCase)."""
        impact = ImpactKpis(15000, 100, 100, True, True, True)
        reco = compute_recommendation(impact, {"nonConformes": 2, "aRisque": 1})
        assert "3 site" in reco.bullets[0]

    def test_priorite_facture_when_surcout_max(self):
        impact = ImpactKpis(100, 5000, 100, True, True, True)
        reco = compute_recommendation(impact, {})
        assert reco.key == "facture"
        assert reco.cta_path == "/bill-intel"
        assert "5" in reco.bullets[0]  # 5 000 €

    def test_priorite_optimisation_when_opportunite_max(self):
        impact = ImpactKpis(100, 100, 8500, True, True, True)
        reco = compute_recommendation(impact, {})
        assert reco.key == "optimisation"
        assert reco.cta_path == "/diagnostic-conso"

    def test_singular_when_one_site(self):
        """Pas de pluralisation quand 1 seul site."""
        impact = ImpactKpis(7500, 100, 100, True, True, True)
        reco = compute_recommendation(impact, {"non_conformes": 1, "a_risque": 0})
        # "1 site non conforme" — pas "1 sites non conformes"
        assert "1 site non conforme" in reco.bullets[0]
        assert "1 sites" not in reco.bullets[0]

    def test_accepts_dict_impact_input(self):
        """compute_recommendation accepte aussi dict (pas seulement ImpactKpis)."""
        impact_dict = {
            "risque_conformite_eur": 26200,
            "surcout_facture_eur": 1000,
            "opportunite_optim_eur": 500,
        }
        reco = compute_recommendation(impact_dict, {"non_conformes": 1, "a_risque": 4})
        assert reco.key == "conformite"

    def test_to_dict_contract(self):
        impact = ImpactKpis(0, 0, 0, False, False, False)
        reco = compute_recommendation(impact, {})
        d = reco.to_dict()
        assert set(d.keys()) == {"key", "titre", "bullets", "cta", "cta_path"}
        assert isinstance(d["bullets"], list)


# ── Cohérence migration JS V30 ───────────────────────────────────────


class TestMigrationCompatibility:
    """Vérifie que la migration Python respecte les contrats du JS V30."""

    def test_optim_rate_v1_unchanged(self):
        """V30 fixait OPTIM_RATE_V1 = 0.01 — ne pas changer sans incrémenter version."""
        assert OPTIM_RATE_V1 == 0.01

    def test_4_recommendation_keys_canonical(self):
        """Les 4 keys canoniques V30 doivent être préservées."""
        # no_data
        r = compute_recommendation(ImpactKpis(0, 0, 0, False, False, False), {})
        assert r.key == "no_data"
        # conformite
        r = compute_recommendation(ImpactKpis(1000, 100, 100, True, True, True), {})
        assert r.key == "conformite"
        # facture
        r = compute_recommendation(ImpactKpis(100, 1000, 100, True, True, True), {})
        assert r.key == "facture"
        # optimisation
        r = compute_recommendation(ImpactKpis(100, 100, 1000, True, True, True), {})
        assert r.key == "optimisation"

    def test_3_kpis_canonical_names(self):
        """Les 3 KPIs canoniques V30 doivent avoir les noms attendus."""
        impact = compute_impact_kpis()
        d = impact.to_dict()
        assert "risque_conformite_eur" in d
        assert "surcout_facture_eur" in d
        assert "opportunite_optim_eur" in d
