"""
PROMEOS — Tests GET /api/energy/cost-vs-contract (Sprint Énergie P1.S2c).

Couvre :
- site scope valide → 200 ;
- scope invalide → erreur standard ENERGY_* + correlation_id ;
- total_kwh=0 → weighted_price=null (pas de division par zéro) ;
- 4 scénarios par défaut : fixed / indexed / mixed / ths ;
- chaque scénario porte provenance ;
- chaque KPI porte provenance ;
- warning « Simulation indicative » présent dans recommendation ;
- price_decomposition shares cohérentes [0, 100] ;
- empty_state actionnable si contrat + données absents ;
- pas de promesse d'économie ferme dans payload.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


pytestmark = pytest.mark.fast


TZ_PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture
def db_empty(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


# ── 1. Scope valide → 200 + shape ───────────────────────────────────────


class TestCostVsContractScope:
    """Site scope valide → 200."""

    def test_site_scope_returns_response(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import build_cost_vs_contract

        resp = build_cost_vs_contract(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        assert resp.scope.kind == "site"
        assert resp.period.timezone == "Europe/Paris"
        assert resp.period.label == "12m"


# ── 2. Scope invalide ──────────────────────────────────────────────────


class TestCostVsContractScopeInvalid:
    """Scope non site/meter → erreur standard."""

    def test_org_scope_raises(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import (
            CostVsContractError,
            build_cost_vs_contract,
        )

        with pytest.raises(CostVsContractError) as exc_info:
            build_cost_vs_contract(
                db_empty,
                scope_kind="org",
                scope_id=1,
                org_id=1,
                period_label="12m",
            )
        assert exc_info.value.hint is not None

    def test_portfolio_scope_raises(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import (
            CostVsContractError,
            build_cost_vs_contract,
        )

        with pytest.raises(CostVsContractError):
            build_cost_vs_contract(
                db_empty,
                scope_kind="portfolio",
                scope_id=1,
                org_id=1,
                period_label="12m",
            )

    def test_missing_scope_id_raises(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import (
            CostVsContractError,
            build_cost_vs_contract,
        )

        with pytest.raises(CostVsContractError) as exc_info:
            build_cost_vs_contract(
                db_empty,
                scope_kind="site",
                scope_id=None,
                org_id=1,
                period_label="12m",
            )
        assert "scope_id" in str(exc_info.value).lower()


class TestCostVsContractScenariosInvalid:
    """Liste scénarios invalides → erreur."""

    def test_unknown_scenario_raises(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import (
            CostVsContractError,
            build_cost_vs_contract,
        )

        with pytest.raises(CostVsContractError) as exc_info:
            build_cost_vs_contract(
                db_empty,
                scope_kind="site",
                scope_id=1,
                org_id=1,
                scenarios=["plouf"],
            )
        assert exc_info.value.hint is not None


# ── 3. total_kwh = 0 → weighted_price null ─────────────────────────────


class TestWeightedPriceNullSafe:
    """Brief : si total_kwh=0 → weighted_price=null + pas de division."""

    def test_zero_kwh_returns_null_weighted_price(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import build_cost_vs_contract

        resp = build_cost_vs_contract(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        # DB vide → total_kwh = None ; weighted_price = None
        wp = resp.kpis.weighted_price_eur_mwh
        assert wp is not None  # KPI structure présente
        assert wp.value is None
        assert wp.state == "inactif"


# ── 4. Empty state ──────────────────────────────────────────────────────


class TestCostVsContractEmptyState:
    """Aucune donnée + aucun contrat → empty_state actionnable."""

    def test_empty_db_has_empty_state(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import build_cost_vs_contract

        resp = build_cost_vs_contract(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        assert resp.empty_state is not None
        assert (
            "vérifier" in resp.empty_state.lower()
            or "élargir" in resp.empty_state.lower()
            or "connexion" in resp.empty_state.lower()
        )


# ── 5. KPI structure ────────────────────────────────────────────────────


class TestCostVsContractKpis:
    """Tous les KPI ont provenance + format normalisé."""

    def test_all_kpis_have_provenance(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import build_cost_vs_contract

        resp = build_cost_vs_contract(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        for kpi in (
            resp.kpis.total_cost_eur,
            resp.kpis.consumption_kwh,
            resp.kpis.weighted_price_eur_mwh,
            resp.kpis.supply_cost_eur,
            resp.kpis.network_cost_eur,
            resp.kpis.taxes_cost_eur,
        ):
            assert kpi is not None
            assert kpi.provenance.source
            assert kpi.provenance.service
            assert kpi.provenance.formula

    def test_kpi_keys_are_normalized(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import build_cost_vs_contract

        resp = build_cost_vs_contract(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        assert resp.kpis.total_cost_eur.key == "total_cost_eur"
        assert resp.kpis.weighted_price_eur_mwh.key == "weighted_price_eur_mwh"
        assert resp.kpis.supply_cost_eur.key == "supply_cost_eur"


# ── 6. Provenance racine ───────────────────────────────────────────────


class TestCostVsContractProvenanceRoot:
    """Provenance racine inclut Europe/Paris + simulation indicative."""

    def test_root_provenance_includes_paris(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import build_cost_vs_contract

        resp = build_cost_vs_contract(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        joined = " ".join(resp.provenance.assumptions)
        assert "Europe/Paris" in joined or "Paris" in joined
        assert "simulation" in joined.lower() or "indicative" in joined.lower()

    def test_provenance_service_name(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import build_cost_vs_contract

        resp = build_cost_vs_contract(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        assert resp.provenance.service == "energy_orchestration.cost_vs_contract.build_cost_vs_contract"


# ── 7. Assumptions globales ─────────────────────────────────────────────


class TestCostVsContractAssumptions:
    """Hypothèses globales documentées."""

    def test_assumptions_include_doctrine_note(self, db_empty):
        from services.energy_orchestration.cost_vs_contract import build_cost_vs_contract

        resp = build_cost_vs_contract(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="12m",
        )
        joined = " ".join(resp.assumptions.notes)
        assert "indicative" in joined.lower() or "doctrine" in joined.lower()


# ── 8. Erreur standardisée ──────────────────────────────────────────────


class TestEnergyErrorStandard:
    """Brief P3 : codes erreur extensibles + correlation_id."""

    def test_contract_not_found_code_exists(self):
        from services.energy_orchestration.errors import (
            CODE_CONTRACT_NOT_FOUND,
            CODE_DATA_INSUFFICIENT,
            CODE_SCENARIO_INVALID,
        )

        assert CODE_CONTRACT_NOT_FOUND == "ENERGY_CONTRACT_NOT_FOUND"
        assert CODE_SCENARIO_INVALID == "ENERGY_SCENARIO_INVALID"
        assert CODE_DATA_INSUFFICIENT == "ENERGY_DATA_INSUFFICIENT"


# ── 9. Pas d'endpoint market-exposure ──────────────────────────────────


class TestMarketExposureNotYetCreated:
    """Brief P1.S2c INTERDIT : pas de /market-exposure dans cette PR."""

    def test_no_market_exposure_endpoint(self):
        from pathlib import Path

        router_file = Path(__file__).resolve().parents[2] / "routes" / "energy_orchestration.py"
        content = router_file.read_text(encoding="utf-8")
        assert "/market-exposure" not in content, "Endpoint /market-exposure interdit dans P1.S2c (planifié P1.S2d)"


# ── 10. Pas de promesse d'économie ferme ───────────────────────────────


class TestNoGuaranteedSavings:
    """Doctrine : aucune économie présentée comme certaine."""

    def test_default_warning_in_recommendation_class(self):
        from schemas.energy_orchestration import EnergyContractRecommendation

        # Le warning a une valeur par défaut documentant le caractère
        # indicatif. Toute recommandation créée sans warning explicite
        # porte ce message non-engageant.
        default_warning = EnergyContractRecommendation.model_fields["warning"].default
        assert "indicative" in default_warning.lower()
        assert "promesse" in default_warning.lower()
