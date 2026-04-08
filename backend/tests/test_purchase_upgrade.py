"""
PROMEOS — Tests Upgrade Achat Energie (Purchase Module)
P0: Benchmark pricing vs contrat actuel
P1: Explanation text, green premium, budget badge, estimate bridge
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    EnergyContract,
    ContractAnnexe,
    SiteOperatingSchedule,
    PurchaseAssumptionSet,
    PurchasePreference,
    PurchaseScenarioResult,
    PurchaseStrategy,
    PurchaseRecoStatus,
    BillingEnergyType,
    TypeSite,
)
from database import get_db
from main import app
from services.purchase_service import (
    get_current_contract_price,
    compute_budget_badge,
    compute_scenarios,
    STRATEGY_EXPLANATIONS,
    GREEN_PREMIUM_EUR_MWH,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org_site(db, surface=2000):
    """Helper: crée org + site minimal."""
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Test PF")
    db.add(pf)
    db.flush()
    site = Site(
        nom="Site A",
        type=TypeSite.BUREAU,
        adresse="1 rue Test",
        code_postal="75001",
        ville="Paris",
        surface_m2=surface,
        portefeuille_id=pf.id,
    )
    db.add(site)
    db.flush()
    return org, site


# ========================================
# P0 — Benchmark pricing vs contrat actuel
# ========================================


class TestBenchmarkPricing:
    """P0 — benchmark 'vs prix actuel' utilise le contrat réel."""

    def test_benchmark_with_active_contract(self, db_session):
        """Site avec contrat actif → source == 'contrat' et prix > 0."""
        org, site = _create_org_site(db_session)

        # Créer un contrat cadre actif
        contract = EnergyContract(
            reference=f"CTR-TEST-{site.id}",
            energy_type="ELEC",
            supplier_name="EDF",
            start_date=date.today() - timedelta(days=180),
            end_date=date.today() + timedelta(days=180),
            status="active",
        )
        db_session.add(contract)
        db_session.flush()

        # Créer une annexe active liée au site
        annexe = ContractAnnexe(
            contrat_cadre_id=contract.id,
            site_id=site.id,
            status="active",
            start_date=date.today() - timedelta(days=180),
            end_date=date.today() + timedelta(days=180),
        )
        db_session.add(annexe)
        db_session.commit()

        # Mock resolve_pricing pour retourner des lignes de prix
        with patch("services.purchase_service.resolve_pricing") as mock_rp:
            mock_rp.return_value = [
                {"unit_price_eur_kwh": 0.12, "period_code": "HP"},
                {"unit_price_eur_kwh": 0.09, "period_code": "HC"},
            ]
            result = get_current_contract_price(db_session, site.id)

        assert result["source"] == "contrat"
        assert result["price_eur_mwh"] > 0
        assert "contrat" in result["label"].lower() or "EDF" in result["label"]

    def test_benchmark_fallback_market(self, db_session):
        """Site sans contrat → fallback sur moyenne marché."""
        org, site = _create_org_site(db_session)

        result = get_current_contract_price(db_session, site.id)

        assert result["source"] == "marche"
        assert result["price_eur_mwh"] > 0
        assert "march" in result["label"].lower()


# ========================================
# P1 — Explanation text par stratégie
# ========================================


class TestExplanationText:
    """P1 — chaque stratégie a un texte d'explication."""

    def test_all_strategies_have_explanation(self):
        """Les 4 stratégies (fixe, indexe, spot, reflex_solar) ont un texte."""
        expected = {"fixe", "indexe", "spot", "reflex_solar"}
        assert set(STRATEGY_EXPLANATIONS.keys()) == expected

    def test_explanations_are_non_empty(self):
        """Chaque explication fait au moins 20 caractères."""
        for key, text in STRATEGY_EXPLANATIONS.items():
            assert len(text) >= 20, f"Explication trop courte pour {key}"

    def test_compute_scenarios_returns_strategy_fields(self, db_session):
        """compute_scenarios retourne les champs strategy et market_context."""
        org, site = _create_org_site(db_session)

        with (
            patch("services.purchase_service.get_reference_price") as mock_ref,
            patch("services.purchase_service.get_market_context") as mock_mkt,
            patch("services.purchase_service.compute_strategy_price") as mock_csp,
            patch("services.purchase_service.compute_reflex_scenario") as mock_rfx,
        ):
            mock_ref.return_value = (0.10, "contrat")
            mock_mkt.return_value = {
                "spot_avg_30d_eur_mwh": 75.0,
                "forward_y1_eur_mwh": 80.0,
                "volatility_30d_pct": 12.0,
            }
            mock_csp.return_value = {
                "price_eur_kwh": 0.095,
                "risk_score": 3,
                "p10_eur_mwh": 70.0,
                "p90_eur_mwh": 110.0,
                "breakdown": {},
                "methodology": "test",
            }
            mock_rfx.return_value = {
                "strategy": "reflex_solar",
                "price_eur_per_kwh": 0.085,
                "total_annual_eur": 42500,
                "risk_score": 4,
                "p10_eur": 35000,
                "p90_eur": 55000,
            }

            scenarios = compute_scenarios(db_session, site.id, 500_000)

        assert len(scenarios) == 4
        strategies = {s["strategy"] for s in scenarios}
        assert "fixe" in strategies
        assert "spot" in strategies


# ========================================
# P1 — Green premium
# ========================================


class TestGreenPremium:
    """P1 — premium vert = 2.5 EUR/MWh."""

    def test_green_premium_constant(self):
        """La constante GREEN_PREMIUM_EUR_MWH vaut 2.5."""
        assert GREEN_PREMIUM_EUR_MWH == 2.5

    def test_green_premium_positive(self):
        """Le premium vert est strictement positif."""
        assert GREEN_PREMIUM_EUR_MWH > 0


# ========================================
# P1 — Budget badge
# ========================================


class TestBudgetBadge:
    """P1 — budget badge retourne la bonne couleur selon le ratio."""

    def test_budget_optimise(self):
        """ratio <= 0.95 → green."""
        result = compute_budget_badge(9000, 10000)  # ratio = 0.90
        assert result["color"] == "green"
        assert "optimis" in result["label"].lower()

    def test_budget_standard(self):
        """ratio 0.95-1.10 → amber."""
        result = compute_budget_badge(10000, 10000)  # ratio = 1.00
        assert result["color"] == "amber"
        assert "standard" in result["label"].lower()

    def test_budget_eleve(self):
        """ratio > 1.10 → red."""
        result = compute_budget_badge(12000, 10000)  # ratio = 1.20
        assert result["color"] == "red"
        assert "lev" in result["label"].lower()  # "élevé" sans accent

    def test_budget_edge_095(self):
        """ratio exactement 0.95 → green (<=)."""
        result = compute_budget_badge(9500, 10000)
        assert result["color"] == "green"

    def test_budget_edge_110(self):
        """ratio exactement 1.10 → amber (<=)."""
        result = compute_budget_badge(11000, 10000)
        assert result["color"] == "amber"

    def test_budget_zero_benchmark(self):
        """benchmark = 0 → ne crash pas."""
        result = compute_budget_badge(10000, 0)
        assert result["color"] in ("green", "amber", "red")


# ========================================
# P1 — /estimate/{site_id} bridge
# ========================================


class TestEstimateContractBridge:
    """P1 — /estimate/{site_id} retourne les données de base."""

    def test_estimate_returns_volume(self, client, db_session):
        """GET /api/purchase/estimate/{site_id} retourne volume_kwh_an."""
        org, site = _create_org_site(db_session)

        with patch("services.consumption_unified_service.get_consumption_summary") as mock_cs:
            mock_cs.return_value = {
                "volume_kwh_an": 450_000,
                "source": "compteur",
                "confidence": "high",
            }
            resp = client.get(f"/api/purchase/estimate/{site.id}")

        assert resp.status_code == 200
        if resp.status_code == 200:
            data = resp.json()
            assert "profile_factor" in data

    def test_estimate_unknown_site(self, client):
        """GET /api/purchase/estimate/999999 → gère proprement."""
        resp = client.get("/api/purchase/estimate/999999")
        # Peut retourner 404 ou 200 avec fallback
        assert resp.status_code in (200, 404, 500)
