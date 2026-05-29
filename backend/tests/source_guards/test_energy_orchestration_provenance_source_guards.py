"""
PROMEOS — Source-guard provenance KPI /api/energy/* (Sprint P1.S2a).

Doctrine traçabilité : tout payload exposé par les endpoints
d'orchestration énergie DOIT porter une `provenance` complète sur :
1. Le payload racine (source, service, formula, period, confidence).
2. Chaque KPI individuel (clé `kpis[*].provenance`).
3. Chaque recommendation (clé `recommendations[*].provenance`).

Ce guard vérifie le contrat statique des schémas Pydantic
(EnergyKpi, EnergyRecommendation, EnergySynthesisResponse,
EnergyLoadCurveResponse). Il valide aussi que `estimated_impact_eur`
est calculé backend dans `build_synthesis` (retire la dette whitelist
frontend reduce post-filtre scope FE).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


REPO_ROOT = Path(__file__).resolve().parents[3]


class TestSchemaContracts:
    """Le schéma Pydantic impose `provenance` obligatoire sur les KPI."""

    def test_energy_kpi_has_required_provenance(self):
        from schemas.energy_orchestration import EnergyKpi

        fields = EnergyKpi.model_fields
        assert "provenance" in fields, "EnergyKpi.provenance manquant"
        assert fields["provenance"].is_required(), "EnergyKpi.provenance doit être obligatoire (pas Optional)"

    def test_energy_provenance_has_required_keys(self):
        from schemas.energy_orchestration import EnergyProvenance

        fields = EnergyProvenance.model_fields
        for key in ("source", "service", "formula", "period"):
            assert key in fields, f"EnergyProvenance.{key} manquant"
            assert fields[key].is_required(), f"EnergyProvenance.{key} doit être obligatoire"

    def test_energy_synthesis_response_has_root_provenance(self):
        from schemas.energy_orchestration import EnergySynthesisResponse

        fields = EnergySynthesisResponse.model_fields
        assert "provenance" in fields
        assert "kpis" in fields
        assert fields["provenance"].is_required()
        assert fields["kpis"].is_required()

    def test_energy_loadcurve_response_has_provenance(self):
        from schemas.energy_orchestration import EnergyLoadCurveResponse

        fields = EnergyLoadCurveResponse.model_fields
        assert "provenance" in fields
        assert "series" in fields
        assert "warnings" in fields

    def test_energy_recommendation_has_provenance(self):
        from schemas.energy_orchestration import EnergyRecommendation

        fields = EnergyRecommendation.model_fields
        assert "provenance" in fields
        assert fields["provenance"].is_required()


class TestSynthesisServiceContract:
    """Le service `build_synthesis` fournit `estimated_impact_eur` backend."""

    def test_kpi_keys_include_estimated_impact_eur(self):
        """Brief P1.S2a phase 5 : estimated_impact_eur agrégé backend (retire
        whitelist FE)."""
        from services.energy_orchestration import synthesis

        source = inspect.getsource(synthesis)
        assert "estimated_impact_eur" in source, (
            "build_synthesis doit exposer estimated_impact_eur (retrait whitelist FE reduce post-filtre scope)"
        )

    def test_kpi_keys_include_all_minimum_keys(self):
        """Brief minimum 10 KPI : consumption_kwh / cost_eur / co2_kg / peak_kw
        / weighted_price_eur_mwh / data_quality_score / sites_coverage_pct
        / alerts_open / actions_open / estimated_impact_eur."""
        from services.energy_orchestration import synthesis

        source = inspect.getsource(synthesis)
        for required_key in (
            "consumption_kwh",
            "cost_eur",
            "co2_kg",
            "peak_kw",
            "weighted_price_eur_mwh",
            "data_quality_score",
            "sites_coverage_pct",
            "alerts_open",
            "actions_open",
            "estimated_impact_eur",
        ):
            assert required_key in source, f"KPI '{required_key}' manquant dans build_synthesis"

    def test_provenance_helper_documents_doctrine_ref(self):
        from services.energy_orchestration.synthesis import _build_provenance

        # Smoke : la signature inclut bien les args attendus.
        sig = inspect.signature(_build_provenance)
        for arg in ("service", "formula", "period"):
            assert arg in sig.parameters


class TestLoadCurveServiceContract:
    """Le service `build_loadcurve` respecte les limites volumétriques."""

    def test_15min_max_7_days(self):
        from services.energy_orchestration.loadcurve import (
            LoadCurveError,
            validate_granularity_for_period,
        )

        validate_granularity_for_period("15min", 7)  # OK
        with pytest.raises(LoadCurveError):
            validate_granularity_for_period("15min", 8)

    def test_30min_max_30_days(self):
        from services.energy_orchestration.loadcurve import (
            LoadCurveError,
            validate_granularity_for_period,
        )

        validate_granularity_for_period("30min", 30)
        with pytest.raises(LoadCurveError):
            validate_granularity_for_period("30min", 31)

    def test_hour_max_90_days(self):
        from services.energy_orchestration.loadcurve import (
            LoadCurveError,
            validate_granularity_for_period,
        )

        validate_granularity_for_period("hour", 90)
        with pytest.raises(LoadCurveError):
            validate_granularity_for_period("hour", 91)

    def test_unknown_granularity_raises(self):
        from services.energy_orchestration.loadcurve import (
            LoadCurveError,
            validate_granularity_for_period,
        )

        with pytest.raises(LoadCurveError):
            validate_granularity_for_period("plouf", 7)


class TestEndpointsLivrés:
    """Brief P1.S2d — les 5 endpoints d'orchestration sont tous livrés."""

    def test_synthesis_endpoint_present(self):
        router_file = REPO_ROOT / "backend" / "routes" / "energy_orchestration.py"
        content = router_file.read_text(encoding="utf-8")
        assert "/synthesis" in content and "build_synthesis" in content

    def test_loadcurve_endpoint_present(self):
        router_file = REPO_ROOT / "backend" / "routes" / "energy_orchestration.py"
        content = router_file.read_text(encoding="utf-8")
        assert "/loadcurve" in content and "build_loadcurve" in content

    def test_week_profile_endpoint_present(self):
        router_file = REPO_ROOT / "backend" / "routes" / "energy_orchestration.py"
        content = router_file.read_text(encoding="utf-8")
        assert "/week-profile" in content and "build_week_profile" in content

    def test_cost_vs_contract_endpoint_present(self):
        router_file = REPO_ROOT / "backend" / "routes" / "energy_orchestration.py"
        content = router_file.read_text(encoding="utf-8")
        assert "/cost-vs-contract" in content and "build_cost_vs_contract" in content

    def test_market_exposure_endpoint_present(self):
        """P1.S2d — /market-exposure est livré (dernier endpoint d'orchestration)."""
        router_file = REPO_ROOT / "backend" / "routes" / "energy_orchestration.py"
        content = router_file.read_text(encoding="utf-8")
        assert "/market-exposure" in content and "build_market_exposure" in content


class TestMarketExposureInvariants:
    """Le service market_exposure respecte les invariants doctrine."""

    def test_uses_canonical_mkt_price_model(self):
        """Doctrine source-guard market_price_canonical — MktPrice only."""
        svc_file = REPO_ROOT / "backend" / "services" / "energy_orchestration" / "market_exposure.py"
        content = svc_file.read_text(encoding="utf-8")
        assert "from models.market_models import MktPrice" in content
        assert "from models.market_price" not in content

    def test_simulation_warning_immutable_default(self):
        """Doctrine : warning par défaut « Simulation indicative »."""
        from schemas.energy_orchestration import EnergyDisplacementSimulation

        default = EnergyDisplacementSimulation.model_fields["warning"].default
        assert default.lower().startswith("simulation indicative")
        assert "promesse" in default.lower()

    def test_exposure_score_uses_canonical_clamp(self):
        """Score exposition borné via helper canonique."""
        svc_file = REPO_ROOT / "backend" / "services" / "energy_orchestration" / "market_exposure.py"
        content = svc_file.read_text(encoding="utf-8")
        assert "clamp_score_0_100" in content


class TestCostVsContractContract:
    """Le service cost_vs_contract respecte les invariants doctrine."""

    def test_default_scenarios_are_4(self):
        from services.energy_orchestration.cost_vs_contract import DEFAULT_SCENARIOS

        assert set(DEFAULT_SCENARIOS) == {"fixed", "indexed", "mixed", "ths"}

    def test_recommendation_warning_immutable_default(self):
        """Doctrine : warning par défaut « Simulation indicative »."""
        from schemas.energy_orchestration import EnergyContractRecommendation

        default = EnergyContractRecommendation.model_fields["warning"].default
        assert default.lower().startswith("simulation indicative")
        assert "promesse" in default.lower()


class TestRouterRegistration:
    """Le router energy_orchestration est branché dans main.py."""

    def test_main_imports_energy_orchestration_router(self):
        main_file = REPO_ROOT / "backend" / "main.py"
        content = main_file.read_text(encoding="utf-8")
        assert "energy_orchestration_router" in content
        assert "app.include_router(energy_orchestration_router)" in content
