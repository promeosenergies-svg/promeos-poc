"""
Tests des 3 nouveaux modules "Usage fil conducteur" :
- archetype_resolver (refactor depuis routes/flex_score.py)
- billing usage_ventilation (shadow bill par usage)
- purchase strategy_recommender (matching profil CDC -> contrat)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestArchetypeResolverService:
    """Le service archetype_resolver est bien expose depuis services/flex/."""

    def test_imports_exposes(self):
        from services.flex.archetype_resolver import (
            resolve_archetype,
            normalize_archetype,
            batch_resolve_archetypes,
            KB_TO_FLEX_ARCHETYPE,
            NAF_PREFIX_TO_FLEX_ARCHETYPE,
        )

        assert callable(resolve_archetype)
        assert callable(normalize_archetype)
        assert callable(batch_resolve_archetypes)
        assert len(KB_TO_FLEX_ARCHETYPE) >= 20
        assert len(NAF_PREFIX_TO_FLEX_ARCHETYPE) >= 20

    def test_normalize_canonical_passthrough(self):
        from services.flex.archetype_resolver import normalize_archetype

        assert normalize_archetype("BUREAU_STANDARD") == "BUREAU_STANDARD"
        assert normalize_archetype("SANTE") == "SANTE"

    def test_normalize_kb_to_flex(self):
        from services.flex.archetype_resolver import normalize_archetype

        assert normalize_archetype("SANTE_HOPITAL") == "SANTE"
        assert normalize_archetype("DATACENTER") == "DATA_CENTER"
        assert normalize_archetype("HOTEL_STANDARD") == "HOTEL_HEBERGEMENT"

    def test_batch_resolve_archetypes_empty(self, app_client):
        _, SessionLocal = app_client
        from services.flex.archetype_resolver import batch_resolve_archetypes

        db = SessionLocal()
        try:
            result = batch_resolve_archetypes(db, [])
            assert result == {}
        finally:
            db.close()

    def test_batch_resolve_archetypes_naf_prefix(self, app_client):
        _, SessionLocal = app_client
        from models.site import Site
        from models.enums import TypeSite
        from services.flex.archetype_resolver import batch_resolve_archetypes

        db = SessionLocal()
        try:
            sites = [
                Site(nom="S1", type=TypeSite.BUREAU, naf_code="6820A", actif=True),
                Site(nom="S2", type=TypeSite.BUREAU, naf_code="5210B", actif=True),
                Site(nom="S3", type=TypeSite.BUREAU, naf_code="8610Z", actif=True),
            ]
            for s in sites:
                db.add(s)
            db.commit()
            for s in sites:
                db.refresh(s)

            result = batch_resolve_archetypes(db, sites)
            assert result[sites[0].id] == "BUREAU_STANDARD"
            assert result[sites[1].id] == "LOGISTIQUE_SEC"
            assert result[sites[2].id] == "SANTE"
        finally:
            db.close()


class TestUsageVentilation:
    """Ventilation shadow bill par usage (fonction pure)."""

    @pytest.fixture
    def sample_shadow_bill(self):
        return {
            "kwh": 10000.0,
            "expected_fourniture_ht": 800.0,
            "expected_reseau_ht": 400.0,
            "expected_taxes_ht": 200.0,
            "expected_abo_ht": 100.0,
            "expected_tva": 300.0,
            "expected_ttc": 1800.0,
        }

    def test_ventilation_bureau_standard(self, sample_shadow_bill):
        from services.billing.usage_ventilation import ventile_shadow_bill_by_usage

        result = ventile_shadow_bill_by_usage(sample_shadow_bill, "BUREAU_STANDARD")
        assert result["archetype_code"] == "BUREAU_STANDARD"
        assert result["total_kwh"] == 10000.0
        assert "CVC_HVAC" in result["by_usage"]
        assert "ECLAIRAGE" in result["by_usage"]
        # Les totaux HT+TVA doivent etre proches du shadow TTC (residual < 10 EUR)
        assert abs(result["totals_check"]["residual_ttc"]) < 10.0

    def test_ventilation_respecte_repartition_kwh(self, sample_shadow_bill):
        from services.billing.usage_ventilation import ventile_shadow_bill_by_usage

        result = ventile_shadow_bill_by_usage(sample_shadow_bill, "BUREAU_STANDARD")
        total_kwh_ventile = sum(u["kwh_total"] for u in result["by_usage"].values())
        assert abs(total_kwh_ventile - 10000.0) < 10.0  # arrondi

    def test_ventilation_hp_hc_coherence(self, sample_shadow_bill):
        """Pour chaque usage : kwh_hp + kwh_hc ~= kwh_total."""
        from services.billing.usage_ventilation import ventile_shadow_bill_by_usage

        result = ventile_shadow_bill_by_usage(sample_shadow_bill, "BUREAU_STANDARD")
        for usage, data in result["by_usage"].items():
            assert abs((data["kwh_hp"] + data["kwh_hc"]) - data["kwh_total"]) < 1.0, usage

    def test_ventilation_data_center_majoritaire_data_center(self, sample_shadow_bill):
        """Un DATA_CENTER doit avoir DATA_CENTER comme usage majoritaire."""
        from services.billing.usage_ventilation import ventile_shadow_bill_by_usage

        result = ventile_shadow_bill_by_usage(sample_shadow_bill, "DATA_CENTER")
        dc_share = result["by_usage"]["DATA_CENTER"]["share_total_pct"]
        assert dc_share >= 70  # 55% HP + 30% HC -> normalise ~85%

    def test_ventilation_archetype_inconnu_fallback(self, sample_shadow_bill):
        from services.billing.usage_ventilation import ventile_shadow_bill_by_usage

        result = ventile_shadow_bill_by_usage(sample_shadow_bill, "ARCHETYPE_FANTAISISTE")
        # Doit retomber sur DEFAULT (pas crasher)
        assert result["archetype_code"] == "ARCHETYPE_FANTAISISTE"
        assert len(result["by_usage"]) > 0

    def test_ventilation_endpoint_site_inexistant(self, app_client):
        client, _ = app_client
        resp = client.get("/api/billing/usage-ventilation/sites/99999")
        assert resp.status_code == 404


class TestPurchaseStrategyRecommender:
    """Matching profil CDC -> strategie d'achat."""

    def test_bureau_standard_fixe(self):
        from services.purchase.strategy_recommender import recommend_purchase_strategy

        reco = recommend_purchase_strategy("BUREAU_STANDARD", P_max_kw=150.0, facteur_forme=0.45)
        assert reco.archetype_code == "BUREAU_STANDARD"
        assert reco.strategy == "fixe"
        assert reco.composition["fixe"] >= 60
        assert sum(reco.composition.values()) == 100

    def test_data_center_ppa(self):
        from services.purchase.strategy_recommender import recommend_purchase_strategy

        reco = recommend_purchase_strategy("DATA_CENTER", P_max_kw=2000.0, facteur_forme=0.85, annual_kwh=15_000_000)
        assert reco.strategy == "ppa"
        assert reco.composition["ppa"] > 0
        assert reco.ppa_eligible is True

    def test_small_site_pas_spot(self):
        """P_max < 250 kW : spot reallouE a indexe."""
        from services.purchase.strategy_recommender import recommend_purchase_strategy

        reco = recommend_purchase_strategy("LOGISTIQUE_SEC", P_max_kw=100.0, facteur_forme=0.5)
        assert reco.composition["spot"] == 0
        assert any("spot" in adj.lower() for adj in reco.adjustments)

    def test_small_site_pas_ppa(self):
        """annual_kwh < 500 MWh : PPA reallouE a fixe."""
        from services.purchase.strategy_recommender import recommend_purchase_strategy

        reco = recommend_purchase_strategy("DATA_CENTER", P_max_kw=300.0, annual_kwh=200_000)
        assert reco.composition["ppa"] == 0
        assert reco.ppa_eligible is False

    def test_facteur_forme_pointu_reduit_spot(self):
        """FF < 0.30 : profil pointu -> spot reduit."""
        from services.purchase.strategy_recommender import recommend_purchase_strategy

        reco_lisse = recommend_purchase_strategy("LOGISTIQUE_SEC", P_max_kw=500.0, facteur_forme=0.7)
        reco_pointu = recommend_purchase_strategy("LOGISTIQUE_SEC", P_max_kw=500.0, facteur_forme=0.2)
        # Pointu doit avoir moins de spot que lisse (ou plus de fixe)
        assert reco_pointu.composition["fixe"] >= reco_lisse.composition["fixe"] - 5

    def test_composition_sum_100(self):
        """Tous les archetypes doivent avoir une composition qui somme a 100."""
        from services.purchase.strategy_recommender import recommend_purchase_strategy, ARCHETYPE_PURCHASE_PROFILES

        for code in ARCHETYPE_PURCHASE_PROFILES:
            reco = recommend_purchase_strategy(code, P_max_kw=500.0, facteur_forme=0.5, annual_kwh=1_000_000)
            assert sum(reco.composition.values()) == 100, f"{code}: {reco.composition}"

    def test_endpoint_site_inexistant(self, app_client):
        client, _ = app_client
        resp = client.get("/api/purchase/strategy/sites/99999")
        assert resp.status_code == 404

    def test_endpoint_site_valide(self, app_client):
        """Site cree via SQL direct : endpoint retourne 200 avec archetype + strategy."""
        client, SessionLocal = app_client
        from models.site import Site
        from models.enums import TypeSite

        db = SessionLocal()
        try:
            site = Site(nom="Hopital Test", type=TypeSite.SANTE, naf_code="8610Z", actif=True)
            db.add(site)
            db.commit()
            db.refresh(site)
            site_id = site.id
        finally:
            db.close()

        resp = client.get(f"/api/purchase/strategy/sites/{site_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["archetype_code"] == "SANTE"
        assert data["strategy"] == "fixe"
        assert "composition" in data
        assert "cdc_profile_snapshot" in data
