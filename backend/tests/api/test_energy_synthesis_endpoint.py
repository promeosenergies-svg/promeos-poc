"""
PROMEOS — Tests GET /api/energy/synthesis (Sprint Énergie P1.S2a).

Couvre :
- org scope / site scope ;
- période vide → state=inactif propre, pas de crash ;
- score borné [0, 100] ;
- provenance obligatoire ;
- 10 KPI minimum ;
- estimated_impact_eur agrégé backend.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


pytestmark = pytest.mark.fast


TZ_PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture
def db_empty(tmp_path):
    """SQLite in-memory propre pour test isolés."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


class TestBuildSynthesisOrgScope:
    """Brief : org scope, période vide → tout 'inactif' + provenance."""

    def test_org_scope_empty_period_returns_inactive_kpis(self, db_empty):
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="org",
            scope_id=None,
            org_id=1,
            period_label="30d",
        )

        assert resp.scope.kind == "org"
        assert resp.period.label == "30d"
        assert resp.period.days == 30
        # 10 KPI minimum
        assert len(resp.kpis) >= 10
        # Tous les KPI ont provenance complète
        for key, kpi in resp.kpis.items():
            assert kpi.provenance.source
            assert kpi.provenance.service
            assert kpi.provenance.formula

    def test_period_is_europe_paris_timezone(self, db_empty):
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="org",
            scope_id=None,
            org_id=1,
            period_label="30d",
        )
        assert resp.period.timezone == "Europe/Paris"

    def test_invalid_period_raises(self, db_empty):
        from services.energy_orchestration.synthesis import build_synthesis

        with pytest.raises(ValueError):
            build_synthesis(
                db_empty,
                scope_kind="org",
                scope_id=None,
                org_id=1,
                period_label="999z",
            )


class TestBuildSynthesisKpiMinimum:
    """Brief : 10 KPI minimum + clés normalisées."""

    def test_required_kpi_keys_present(self, db_empty):
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="org",
            scope_id=None,
            org_id=1,
            period_label="30d",
        )

        required = [
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
        ]
        for key in required:
            assert key in resp.kpis, f"KPI '{key}' manquant"

    def test_estimated_impact_eur_is_backend_aggregated(self, db_empty):
        """Cas brief P1.S2a : `estimated_impact_eur` calculé backend pour
        retirer la dette whitelist FE reduce post-filtre scope."""
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="org",
            scope_id=None,
            org_id=1,
            period_label="30d",
        )
        impact = resp.kpis["estimated_impact_eur"]
        assert impact.unit == "€"
        # Valeur calculée backend (peut être 0 sur DB vide)
        assert impact.value is not None
        assert isinstance(impact.value, (int, float))
        # Provenance documente l'agrégation backend explicitement
        assert any(
            "agrégation pré-calculée backend" in a or "post-filtre scope" in a for a in impact.provenance.assumptions
        )


class TestBuildSynthesisScoreBounded:
    """Tout score numérique exposé est borné [0, 100]."""

    def test_data_quality_score_in_0_100(self, db_empty):
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            period_label="7d",
        )
        q = resp.kpis.get("data_quality_score")
        assert q is not None
        if q.value is not None and isinstance(q.value, (int, float)):
            assert 0 <= q.value <= 100


class TestBuildSynthesisStateInactive:
    """Pas de donnée → state='inactif' avec assumptions explicites."""

    def test_inactive_kpis_have_reason_assumption(self, db_empty):
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="site",
            scope_id=999,
            org_id=1,
            period_label="30d",
        )
        # Sur DB vide, la consommation est inactive
        cons = resp.kpis["consumption_kwh"]
        assert cons.state == "inactif"
        assert cons.value is None
        # Provenance documente la raison
        assert any("reason=" in a for a in cons.provenance.assumptions)


class TestBuildSynthesisNarrative:
    """Le briefing narrative est généré + non-vide."""

    def test_narrative_present_for_clean_state(self, db_empty):
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="org",
            scope_id=None,
            org_id=1,
            period_label="30d",
        )
        assert resp.narrative is not None
        assert len(resp.narrative) > 20


class TestBuildSynthesisProvenanceRoot:
    """Le payload racine porte provenance + assumptions clés."""

    def test_root_provenance_present(self, db_empty):
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="org",
            scope_id=None,
            org_id=1,
            period_label="30d",
        )
        assert resp.provenance.source
        assert resp.provenance.service == "energy_orchestration.synthesis.build_synthesis"
        assert "tous les scores bornés" in " ".join(resp.provenance.assumptions)
        assert "timezone Europe/Paris" in " ".join(resp.provenance.assumptions)


class TestBuildSynthesisCompareMode:
    """Le param compare est propagé dans le payload."""

    @pytest.mark.parametrize("compare", ["none", "n-1", "baseline", "contract"])
    def test_compare_propagated(self, db_empty, compare):
        from services.energy_orchestration.synthesis import build_synthesis

        resp = build_synthesis(
            db_empty,
            scope_kind="org",
            scope_id=None,
            org_id=1,
            period_label="30d",
            compare=compare,
        )
        assert resp.compare == compare
