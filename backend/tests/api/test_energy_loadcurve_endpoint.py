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


# ── Sprint Énergie P3.1 — top_peaks + weekday_overlay ────────────────


class _FakeSeriesMaker:
    """Helper pour fabriquer une série loadcurve cohérente (DB vide)."""

    @staticmethod
    def make(
        n_days: int = 14,
        start: datetime = datetime(2026, 5, 1, 0, 0, tzinfo=TZ_PARIS),
        kwh_for_hour=lambda dow, h: 10 + (h * 0.5) + (5 if dow < 5 else 0),
    ) -> list:
        """Fabrique une série horaire artificielle pour tester les helpers
        P3.1 sans DB. Format aligné avec EnergyLoadCurvePoint."""
        from schemas.energy_orchestration import EnergyLoadCurvePoint

        series = []
        for day_idx in range(n_days):
            base = start + timedelta(days=day_idx)
            for hour in range(24):
                ts = base.replace(hour=hour)
                kwh = kwh_for_hour(ts.weekday(), hour)
                series.append(
                    EnergyLoadCurvePoint(
                        timestamp=ts,
                        kwh=kwh,
                        kw_avg=kwh,  # granularité hour → kw_avg = kwh/1h
                        quality_status="measured",
                    )
                )
        return series


class TestLoadCurveP3_1TopPeaks:
    """Critère 1-3 : top_peaks présent, trié, provenance."""

    def test_top_peaks_present_when_series(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_top_peaks
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        series = _FakeSeriesMaker.make(n_days=14)
        peaks = _compute_top_peaks(series, period)
        assert len(peaks) == 5  # _MAX_TOP_PEAKS
        for p in peaks:
            assert p.rank >= 1
            assert p.timestamp is not None
            assert p.kw_avg is not None
            assert p.period_label
            assert p.recommended_action

    def test_top_peaks_sorted_desc_by_kw_avg(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_top_peaks
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        series = _FakeSeriesMaker.make()
        peaks = _compute_top_peaks(series, period)
        values = [p.kw_avg for p in peaks]
        assert values == sorted(values, reverse=True), "Top peaks doivent être triés desc"
        # rangs canoniques 1..5
        assert [p.rank for p in peaks] == list(range(1, len(peaks) + 1))

    def test_top_peaks_each_has_provenance(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_top_peaks
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        series = _FakeSeriesMaker.make()
        peaks = _compute_top_peaks(series, period)
        for p in peaks:
            assert p.provenance.source
            assert p.provenance.service == ("energy_orchestration.loadcurve._compute_top_peaks")
            assert p.provenance.formula
            assert "Europe/Paris" in " ".join(p.provenance.assumptions)

    def test_top_peaks_empty_when_no_series(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_top_peaks
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 8, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        assert _compute_top_peaks([], period) == []


class TestLoadCurveP3_1WeekdayOverlay:
    """Critère 4-5 : 7 jours, 24 points si données suffisantes."""

    def test_weekday_overlay_contains_7_days(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_weekday_overlay
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        series = _FakeSeriesMaker.make(n_days=14)
        curves = _compute_weekday_overlay(series, period)
        assert len(curves) == 7
        labels = [c.label for c in curves]
        assert labels == ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        assert [c.day_of_week for c in curves] == [0, 1, 2, 3, 4, 5, 6]

    def test_weekday_overlay_24_points_per_day_when_sufficient(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_weekday_overlay
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        series = _FakeSeriesMaker.make(n_days=14)
        curves = _compute_weekday_overlay(series, period)
        for curve in curves:
            assert len(curve.points) == 24
            for point in curve.points:
                assert 0 <= point.hour <= 23
                assert point.avg_kwh is not None
                assert point.n_points > 0

    def test_weekday_overlay_provenance(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_weekday_overlay
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        curves = _compute_weekday_overlay(_FakeSeriesMaker.make(), period)
        for c in curves:
            assert c.provenance.service == ("energy_orchestration.loadcurve._compute_weekday_overlay")

    def test_weekday_overlay_empty_when_no_series(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_weekday_overlay
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 8, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        assert _compute_weekday_overlay([], period) == []


class TestLoadCurveP3_1WeekdayDecomposition:
    """Critère 6-7 : 7 lignes décomposition + weekend_share_pct backend."""

    def test_decomposition_contains_7_rows(self, db_empty):
        from services.energy_orchestration.loadcurve import _compute_weekday_decomposition
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        decomposition = _compute_weekday_decomposition(_FakeSeriesMaker.make(), period)
        assert len(decomposition) == 7
        assert [d.day_of_week for d in decomposition] == [0, 1, 2, 3, 4, 5, 6]
        # share_pct doit sommer à ~100 (sauf nan/None)
        shares = [d.share_pct for d in decomposition if d.share_pct is not None]
        assert abs(sum(shares) - 100.0) < 0.1

    def test_weekend_share_pct_computed_backend(self, db_empty):
        from services.energy_orchestration.loadcurve import (
            _compute_weekday_weekend_comparison,
        )
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        comparison = _compute_weekday_weekend_comparison(_FakeSeriesMaker.make(), period)
        assert comparison is not None
        assert comparison.weekday_kwh is not None
        assert comparison.weekend_kwh is not None
        assert comparison.weekend_share_pct is not None
        assert 0.0 <= comparison.weekend_share_pct <= 100.0
        assert comparison.provenance.service == ("energy_orchestration.loadcurve._compute_weekday_weekend_comparison")

    def test_decomposition_state_classified_backend(self, db_empty):
        """Le `state` est fourni par le backend (sain/vigilance/critique/inactif)."""
        from services.energy_orchestration.loadcurve import _compute_weekday_decomposition
        from schemas.energy_orchestration import EnergyPeriod

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 15, tzinfo=TZ_PARIS),
            days=14,
            timezone="Europe/Paris",
        )
        decomposition = _compute_weekday_decomposition(_FakeSeriesMaker.make(), period)
        valid_states = {"sain", "vigilance", "critique", "inactif"}
        for d in decomposition:
            assert d.state in valid_states


class TestLoadCurveP3_1BuildIntegration:
    """Critère 8-10 : intégration build_loadcurve + empty + tz + non-régression."""

    def test_build_loadcurve_exposes_new_fields_when_empty_db(self, db_empty):
        from services.energy_orchestration.loadcurve import build_loadcurve

        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        resp = build_loadcurve(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            from_dt=now - timedelta(days=14),
            to_dt=now,
            granularity="hour",
        )
        # Nouveaux champs P3.1 présents (même si vides sur DB vide)
        assert hasattr(resp, "top_peaks")
        assert hasattr(resp, "weekday_overlay")
        assert hasattr(resp, "weekday_decomposition")
        assert hasattr(resp, "weekday_weekend_comparison")
        assert isinstance(resp.top_peaks, list)
        assert isinstance(resp.weekday_overlay, list)
        assert isinstance(resp.weekday_decomposition, list)

    def test_build_loadcurve_non_regression_existing_fields(self, db_empty):
        """Les anciens champs restent intacts."""
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
        assert resp.provenance.source
        assert resp.kpis is not None
        # Les 4 KPI legacy
        assert resp.kpis.total_kwh is not None
        assert resp.kpis.peak_kw is not None
