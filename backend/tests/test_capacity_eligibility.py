"""Tests unitaires module capacité — éligibilité + revenus."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.capacity import (  # noqa: E402
    EnchereType,
    FlexAssetType,
    FlexibleAsset,
    compute_asset_eligibility,
    compute_portfolio_eligibility,
    estimate_capacity_revenue,
)


def _effacement(puissance_kw=500, disponibilite=85.0, **overrides):
    defaults = dict(
        asset_id="A1",
        site_id=1,
        asset_type=FlexAssetType.EFFACEMENT,
        puissance_kw=puissance_kw,
        duree_disponibilite_h=3.0,
        disponibilite_annuelle_pct=disponibilite,
        delai_mobilisation_min=30,
        has_teleometrie=True,
        has_car=True,
    )
    defaults.update(overrides)
    return FlexibleAsset(**defaults)


class TestAssetEligibilityBlockers:
    def test_puissance_trop_faible_bloque(self):
        score = compute_asset_eligibility(_effacement(puissance_kw=50))
        assert not score.eligible
        assert any("seuil minimal" in b for b in score.blockers)

    def test_pas_de_car_bloque(self):
        score = compute_asset_eligibility(_effacement(has_car=False))
        assert not score.eligible
        assert any("CAR" in b for b in score.blockers)

    def test_pas_de_telemetrie_bloque(self):
        score = compute_asset_eligibility(_effacement(has_teleometrie=False))
        assert not score.eligible
        assert any("télémétrie" in b for b in score.blockers)

    def test_obligation_achat_exclut(self):
        score = compute_asset_eligibility(_effacement(sous_obligation_achat=True))
        assert not score.eligible
        assert any("obligation d'achat" in b for b in score.blockers)

    def test_pac_sans_flex_ready_bloque(self):
        asset = FlexibleAsset(
            asset_id="PAC1",
            site_id=1,
            asset_type=FlexAssetType.PAC_PILOTABLE,
            puissance_kw=200,
            duree_disponibilite_h=2.0,
            disponibilite_annuelle_pct=85,
            delai_mobilisation_min=30,
            has_teleometrie=True,
            has_car=True,
            has_flex_ready_gtb=False,
        )
        score = compute_asset_eligibility(asset)
        assert not score.eligible
        assert any("Flex Ready" in b for b in score.blockers)


class TestAssetEligibilityScoring:
    def test_actif_excellent_scored_high(self):
        score = compute_asset_eligibility(_effacement(puissance_kw=1500, disponibilite=95, delai_mobilisation_min=15))
        assert score.eligible
        assert score.score >= 90

    def test_actif_limite_warnings(self):
        score = compute_asset_eligibility(_effacement(puissance_kw=150, disponibilite=65))
        assert score.eligible
        assert len(score.warnings) > 0

    def test_puissance_certifiable_tient_compte_disponibilite(self):
        score = compute_asset_eligibility(_effacement(puissance_kw=1000, disponibilite=80))
        assert score.puissance_certifiable_kw == 800.0

    def test_kb_item_ids_presents(self):
        score = compute_asset_eligibility(_effacement())
        assert "CAPACITE-ELIGIBILITE-ACTIFS" in score.kb_item_ids


class TestPortfolioEligibility:
    def test_agregation_atteint_seuil_1mw(self):
        assets = [_effacement(puissance_kw=400, disponibilite=90) for _ in range(3)]
        score = compute_portfolio_eligibility(assets)
        assert score.eligible
        assert score.puissance_certifiable_kw == 1080.0

    def test_actifs_faibles_ne_suffisent_pas(self):
        assets = [_effacement(puissance_kw=200, disponibilite=90) for _ in range(2)]
        score = compute_portfolio_eligibility(assets)
        assert not score.eligible
        assert any("seuil minimal" in b for b in score.blockers)

    def test_actifs_bloques_skipped(self):
        assets = [_effacement(puissance_kw=1500, disponibilite=90), _effacement(puissance_kw=50)]
        score = compute_portfolio_eligibility(assets)
        assert score.eligible
        assert score.puissance_certifiable_kw == 1350.0

    def test_portfolio_vide_non_eligible(self):
        assert not compute_portfolio_eligibility([]).eligible


class TestRevenueEstimation:
    def test_revenu_pl1_1mw(self):
        est = estimate_capacity_revenue(1000, EnchereType.PL1, retention_agregateur_pct=15)
        assert est.puissance_certifiable_mw == 1.0
        assert est.revenu_min_eur == 17_000
        assert est.revenu_moyen_eur == 25_500
        assert est.revenu_max_eur == 42_500

    def test_revenu_pl4_conservateur(self):
        est_pl4 = estimate_capacity_revenue(1000, EnchereType.PL4)
        est_pl1 = estimate_capacity_revenue(1000, EnchereType.PL1)
        assert est_pl4.revenu_max_eur < est_pl1.revenu_max_eur

    def test_commission_nulle_conserve_brut(self):
        est = estimate_capacity_revenue(1000, EnchereType.PL1, retention_agregateur_pct=0)
        assert est.revenu_moyen_eur == 30_000

    def test_kb_item_ids_presents(self):
        est = estimate_capacity_revenue(1000)
        assert "CAPACITE-MECANISME-RTE-2026" in est.kb_item_ids
        assert "CAPACITE-ELIGIBILITE-ACTIFS" in est.kb_item_ids

    def test_confidence_medium_pl1(self):
        assert estimate_capacity_revenue(1000, EnchereType.PL1).confidence == "medium"

    def test_confidence_low_pl4(self):
        assert estimate_capacity_revenue(1000, EnchereType.PL4).confidence == "low"


class TestEndToEndScenario:
    def test_eti_multisite_scenario(self):
        portfolio = [
            FlexibleAsset(
                asset_id="S1-PAC",
                site_id=1,
                asset_type=FlexAssetType.PAC_PILOTABLE,
                puissance_kw=300,
                duree_disponibilite_h=2.5,
                disponibilite_annuelle_pct=85,
                delai_mobilisation_min=20,
                has_teleometrie=True,
                has_car=True,
                has_flex_ready_gtb=True,
            ),
            FlexibleAsset(
                asset_id="S2-BESS",
                site_id=2,
                asset_type=FlexAssetType.BESS,
                puissance_kw=800,
                duree_disponibilite_h=3.0,
                disponibilite_annuelle_pct=95,
                delai_mobilisation_min=5,
                has_teleometrie=True,
                has_car=True,
            ),
            FlexibleAsset(
                asset_id="S3-EFF",
                site_id=3,
                asset_type=FlexAssetType.EFFACEMENT,
                puissance_kw=500,
                duree_disponibilite_h=4.0,
                disponibilite_annuelle_pct=88,
                delai_mobilisation_min=45,
                has_teleometrie=True,
                has_car=True,
            ),
            FlexibleAsset(
                asset_id="S4-SMALL",
                site_id=4,
                asset_type=FlexAssetType.EFFACEMENT,
                puissance_kw=80,
                duree_disponibilite_h=2.0,
                disponibilite_annuelle_pct=80,
                delai_mobilisation_min=30,
                has_teleometrie=True,
                has_car=True,
            ),
        ]
        elig = compute_portfolio_eligibility(portfolio)
        assert elig.eligible
        assert elig.puissance_certifiable_kw == 1455.0

        est = estimate_capacity_revenue(elig.puissance_certifiable_kw)
        assert est.puissance_certifiable_mw == 1.46
        assert 35_000 <= est.revenu_moyen_eur <= 40_000
