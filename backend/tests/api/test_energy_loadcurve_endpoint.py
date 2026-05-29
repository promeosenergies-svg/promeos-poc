"""
PROMEOS — Tests GET /api/energy/loadcurve (Sprint Énergie P1.S2a).

Couvre :
- granularité hour OK ;
- 15min période > 7 j refusée ;
- empty series propre (200 + empty_state explicite, pas crash) ;
- provenance obligatoire ;
- timezone Europe/Paris ;
- erreurs portent hint actionnable.
"""

from __future__ import annotations

from datetime import datetime, timedelta
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


class TestLoadCurveGranularityHour:
    """Brief : granularité hour OK sur période valide."""

    def test_hour_granularity_returns_200_shape(self, db_empty):
        from services.energy_orchestration.loadcurve import build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        resp = build_loadcurve(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            from_dt=now - timedelta(days=7),
            to_dt=now,
            granularity="hour",
        )
        assert resp.granularity == "hour"
        assert resp.period.timezone == "Europe/Paris"

    def test_provenance_root_present(self, db_empty):
        from services.energy_orchestration.loadcurve import build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        resp = build_loadcurve(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            from_dt=now - timedelta(days=7),
            to_dt=now,
            granularity="hour",
        )
        assert resp.provenance.source
        assert resp.provenance.service.startswith("energy_orchestration.loadcurve")
        assert "Europe/Paris" in " ".join(resp.provenance.assumptions)


class TestLoadCurveGranularityLimits:
    """Brief : 15min ≤ 7 j ; 30min ≤ 30 j ; sinon HTTP 400 hint."""

    def test_15min_8_days_refused(self, db_empty):
        from services.energy_orchestration.loadcurve import LoadCurveError, build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        with pytest.raises(LoadCurveError) as exc_info:
            build_loadcurve(
                db_empty,
                scope_kind="site",
                scope_id=1,
                org_id=1,
                from_dt=now - timedelta(days=8),
                to_dt=now,
                granularity="15min",
            )
        assert "15min" in str(exc_info.value)
        assert exc_info.value.hint is not None

    def test_30min_31_days_refused(self, db_empty):
        from services.energy_orchestration.loadcurve import LoadCurveError, build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        with pytest.raises(LoadCurveError) as exc_info:
            build_loadcurve(
                db_empty,
                scope_kind="site",
                scope_id=1,
                org_id=1,
                from_dt=now - timedelta(days=31),
                to_dt=now,
                granularity="30min",
            )
        assert exc_info.value.hint is not None

    def test_15min_7_days_accepted(self, db_empty):
        from services.energy_orchestration.loadcurve import build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        # Ne doit pas lever
        resp = build_loadcurve(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            from_dt=now - timedelta(days=7),
            to_dt=now,
            granularity="15min",
        )
        assert resp is not None


class TestLoadCurveEmptyState:
    """Brief : aucune donnée → 200 avec series=[] + empty_state explicite."""

    def test_empty_db_returns_empty_state(self, db_empty):
        from services.energy_orchestration.loadcurve import build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        resp = build_loadcurve(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            from_dt=now - timedelta(days=7),
            to_dt=now,
            granularity="hour",
        )
        # MVP : sur DB vide, série vide + empty_state texte explicite
        assert resp.series == []
        assert resp.empty_state is not None
        assert "élargir" in resp.empty_state.lower() or "vérifier" in resp.empty_state.lower()


class TestLoadCurveInvalidRange:
    """Brief : to ≤ from → erreur explicite avec hint."""

    def test_to_before_from_raises(self, db_empty):
        from services.energy_orchestration.loadcurve import LoadCurveError, build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        with pytest.raises(LoadCurveError) as exc_info:
            build_loadcurve(
                db_empty,
                scope_kind="site",
                scope_id=1,
                org_id=1,
                from_dt=now,
                to_dt=now - timedelta(days=1),
                granularity="hour",
            )
        assert exc_info.value.hint is not None


class TestLoadCurveTimezoneNaive:
    """Robustesse : timezone naïf est normalisé Europe/Paris."""

    def test_naive_datetime_normalized(self, db_empty):
        from services.energy_orchestration.loadcurve import build_loadcurve

        now_naive = datetime(2026, 5, 29, 12, 0)  # pas de tzinfo
        resp = build_loadcurve(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            from_dt=now_naive - timedelta(days=1),
            to_dt=now_naive,
            granularity="hour",
        )
        # Le service ajoute TZ_PARIS automatiquement
        assert resp.period.timezone == "Europe/Paris"


class TestLoadCurveResponseFields:
    """Contrat payload réponse."""

    def test_response_has_kpis_field(self, db_empty):
        from services.energy_orchestration.loadcurve import build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        resp = build_loadcurve(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            from_dt=now - timedelta(days=7),
            to_dt=now,
            granularity="hour",
        )
        assert resp.kpis is not None
        # Les 4 KPI agrégés sont toujours présents (peut-être à state=inactif)
        assert resp.kpis.total_kwh is not None
        assert resp.kpis.peak_kw is not None
        assert resp.kpis.baseload_kw is not None
        assert resp.kpis.average_kw is not None

    def test_response_warnings_is_list(self, db_empty):
        from services.energy_orchestration.loadcurve import build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        resp = build_loadcurve(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            from_dt=now - timedelta(days=7),
            to_dt=now,
            granularity="hour",
        )
        assert isinstance(resp.warnings, list)
