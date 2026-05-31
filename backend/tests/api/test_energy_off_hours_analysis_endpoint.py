"""
PROMEOS — Tests GET /api/energy/off-hours-analysis (Sprint Énergie P3.2).

Couvre :
- empty_state si SiteOperatingSchedule manquant ;
- consommation hors plage déclarée détectée ;
- jour fermé détecté ;
- plage ouverte non comptée ;
- KPI week-end + talon nuit ;
- provenance complète sur KPI et slots ;
- timezone Europe/Paris ;
- scope invalid standardisé ;
- pas de division par zéro ;
- seed HELIOS retourne analyse exploitable.
"""

from __future__ import annotations

import json
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


def _seed_schedule(
    db, site_id=1, *, open_days="0,1,2,3,4", open_time="08:00", close_time="19:00", is_24_7=False, intervals_json=None
):
    """Crée un SiteOperatingSchedule (Site optionnel, non requis pour le helper)."""
    from models.site_operating_schedule import SiteOperatingSchedule

    sched = SiteOperatingSchedule(
        site_id=site_id,
        timezone="Europe/Paris",
        open_days=open_days,
        open_time=open_time,
        close_time=close_time,
        is_24_7=is_24_7,
        intervals_json=intervals_json,
    )
    db.add(sched)
    db.commit()
    return sched


class _FakeSeries:
    """Génère une série EnergyLoadCurvePoint synthétique sur la période."""

    @staticmethod
    def hourly(*, start: datetime, hours: int, kwh: float = 50.0, kw: float = 50.0):
        from schemas.energy_orchestration import EnergyLoadCurvePoint

        return [
            EnergyLoadCurvePoint(
                timestamp=start + timedelta(hours=h),
                kwh=kwh,
                kw_avg=kw,
                quality_status="measured",
            )
            for h in range(hours)
        ]


class TestOpeningSchedule:
    """Lecture / fallback du modèle SiteOperatingSchedule."""

    def test_missing_schedule_returns_source_missing(self, db_empty):
        from services.energy_orchestration.opening_hours_analysis import (
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 8, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=42, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        assert schedule.source == "missing"
        assert schedule.weekly_schedule == []
        assert schedule.provenance.service.endswith("_missing_schedule")

    def test_declared_schedule_returns_7_days_grid(self, db_empty):
        _seed_schedule(db_empty)
        from services.energy_orchestration.opening_hours_analysis import (
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 8, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        assert schedule.source == "declared"
        assert len(schedule.weekly_schedule) == 7
        # Lundi-Vendredi ouverts
        for d in range(5):
            assert schedule.weekly_schedule[d].is_open is True
            assert schedule.weekly_schedule[d].ranges
            assert schedule.weekly_schedule[d].ranges[0].start_time == "08:00"
            assert schedule.weekly_schedule[d].ranges[0].end_time == "19:00"
        # Samedi-Dimanche fermés (pas dans open_days)
        for d in (5, 6):
            assert schedule.weekly_schedule[d].is_open is False

    def test_24_7_schedule_marks_all_days_open(self, db_empty):
        _seed_schedule(
            db_empty,
            site_id=2,
            open_days="0,1,2,3,4,5,6",
            open_time="00:00",
            close_time="23:59",
            is_24_7=True,
        )
        from services.energy_orchestration.opening_hours_analysis import (
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 8, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=2, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        assert schedule.source == "declared"
        for day in schedule.weekly_schedule:
            assert day.is_open is True
            assert day.ranges[0].start_time == "00:00"


class TestOffHoursDetection:
    """Détection des slots hors horaires."""

    def test_point_within_opening_hours_not_off(self, db_empty):
        from services.energy_orchestration.opening_hours_analysis import (
            _is_within_opening_hours,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        _seed_schedule(db_empty)
        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 11, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)

        # Lundi 10h00 → dans 08:00-19:00 → dans plage
        ts_in = datetime(2026, 5, 4, 10, 0, tzinfo=TZ_PARIS)
        assert _is_within_opening_hours(ts_in, schedule) is True
        # Lundi 22h00 → hors plage
        ts_out = datetime(2026, 5, 4, 22, 0, tzinfo=TZ_PARIS)
        assert _is_within_opening_hours(ts_out, schedule) is False
        # Samedi 10h00 → jour fermé
        ts_sat = datetime(2026, 5, 9, 10, 0, tzinfo=TZ_PARIS)
        assert _is_within_opening_hours(ts_sat, schedule) is False

    def test_compute_slots_detects_off_points_only(self, db_empty):
        _seed_schedule(db_empty)
        from services.energy_orchestration.opening_hours_analysis import (
            _compute_slots,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 11, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        # 2 points : un dans plage (lundi 10h), un hors plage (lundi 22h)
        series = [
            *_FakeSeries.hourly(start=datetime(2026, 5, 4, 10, 0, tzinfo=TZ_PARIS), hours=1),
            *_FakeSeries.hourly(start=datetime(2026, 5, 4, 22, 0, tzinfo=TZ_PARIS), hours=1),
        ]
        slots = _compute_slots(series, schedule, period)
        assert len(slots) == 1
        assert slots[0].hour == 22
        assert slots[0].day_of_week == 0  # Lundi

    def test_noise_threshold_ignored(self, db_empty):
        """Points < 0.1 kWh ignorés (anti-bruit)."""
        _seed_schedule(db_empty)
        from services.energy_orchestration.opening_hours_analysis import (
            _compute_slots,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 5, tzinfo=TZ_PARIS),
            days=1,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        series = _FakeSeries.hourly(
            start=datetime(2026, 5, 4, 22, 0, tzinfo=TZ_PARIS),
            hours=1,
            kwh=0.05,  # sous seuil
        )
        slots = _compute_slots(series, schedule, period)
        assert slots == []

    def test_weekend_off_hours_aggregated(self, db_empty):
        _seed_schedule(db_empty)
        from services.energy_orchestration.opening_hours_analysis import (
            _compute_kpis,
            _compute_slots,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 11, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        # Samedi entier 24h
        sat_series = _FakeSeries.hourly(
            start=datetime(2026, 5, 9, 0, 0, tzinfo=TZ_PARIS),
            hours=24,
            kwh=10.0,
        )
        slots = _compute_slots(sat_series, schedule, period)
        kpis, _ = _compute_kpis(sat_series, slots, schedule, period, scope)
        # week-end_off_hours_kwh = 24 × 10 = 240
        assert kpis.weekend_off_hours_kwh.value == 240.0
        assert kpis.weekend_off_hours_kwh.provenance.service.startswith("energy_orchestration.opening_hours_analysis")


class TestKpiNightBaseload:
    """Talon nuit calculé backend."""

    def test_night_baseload_kw_computed_from_hour_window(self, db_empty):
        _seed_schedule(db_empty, is_24_7=True, site_id=10)
        from services.energy_orchestration.opening_hours_analysis import (
            _compute_kpis,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 5, tzinfo=TZ_PARIS),
            days=1,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=10, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        series = _FakeSeries.hourly(
            start=datetime(2026, 5, 4, 0, 0, tzinfo=TZ_PARIS),
            hours=24,
            kwh=4.0,
            kw=4.0,
        )
        kpis, _ = _compute_kpis(series, [], schedule, period, scope)
        # 6 points heure 0..5 → moyenne kw_avg = 4.0
        assert kpis.night_baseload_kw.value == 4.0


class TestProvenance:
    """Provenance obligatoire sur chaque KPI / slot."""

    def test_kpi_provenance_complete(self, db_empty):
        _seed_schedule(db_empty)
        from services.energy_orchestration.opening_hours_analysis import (
            _compute_kpis,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 11, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        series = _FakeSeries.hourly(start=datetime(2026, 5, 4, 22, 0, tzinfo=TZ_PARIS), hours=4, kwh=50.0)
        from services.energy_orchestration.opening_hours_analysis import _compute_slots

        slots = _compute_slots(series, schedule, period)
        kpis, _ = _compute_kpis(series, slots, schedule, period, scope)
        for kpi in (
            kpis.off_hours_kwh,
            kpis.off_hours_share_pct,
            kpis.weekend_off_hours_kwh,
            kpis.night_baseload_kw,
        ):
            assert kpi is not None
            assert kpi.provenance.service.startswith("energy_orchestration.opening_hours_analysis")
            assert "Europe/Paris" in " ".join(kpi.provenance.assumptions)

    def test_slot_provenance_complete(self, db_empty):
        _seed_schedule(db_empty)
        from services.energy_orchestration.opening_hours_analysis import (
            _compute_slots,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 5, tzinfo=TZ_PARIS),
            days=1,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        series = _FakeSeries.hourly(start=datetime(2026, 5, 4, 22, 0, tzinfo=TZ_PARIS), hours=1, kwh=15.0)
        slots = _compute_slots(series, schedule, period)
        assert slots
        for s in slots:
            assert s.provenance.service.startswith("energy_orchestration.opening_hours_analysis")


class TestBuildResponseFull:
    """Composition complète build_off_hours_analysis."""

    def test_empty_state_when_no_schedule(self, db_empty):
        from services.energy_orchestration.opening_hours_analysis import (
            build_off_hours_analysis,
        )

        resp = build_off_hours_analysis(
            db_empty,
            scope_kind="site",
            scope_id=999,
            org_id=1,
            from_dt=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
            to_dt=datetime(2026, 5, 8, tzinfo=TZ_PARIS),
            granularity="hour",
        )
        assert resp.schedule.source == "missing"
        assert resp.empty_state == "Horaires d'ouverture non renseignés pour ce site."
        assert resp.kpis.off_hours_kwh is None
        assert resp.recommendations == []

    def test_recommendation_severity_scaled_by_share(self, db_empty):
        _seed_schedule(db_empty)
        from services.energy_orchestration.opening_hours_analysis import (
            _compute_recommendations,
            _compute_kpis,
            _compute_slots,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 11, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        # 50 % du temps en plage, 50 % hors → share doit être ≥ 25 = critical
        in_series = _FakeSeries.hourly(start=datetime(2026, 5, 4, 10, 0, tzinfo=TZ_PARIS), hours=5, kwh=10.0)
        off_series = _FakeSeries.hourly(start=datetime(2026, 5, 4, 22, 0, tzinfo=TZ_PARIS), hours=5, kwh=10.0)
        series = in_series + off_series
        slots = _compute_slots(series, schedule, period)
        kpis, total_off = _compute_kpis(series, slots, schedule, period, scope)
        recs = _compute_recommendations(kpis, slots, schedule, period)
        assert any(r.severity == "critical" for r in recs)
        # Recommandations doivent porter une provenance complète
        for r in recs:
            assert r.provenance.service.startswith("energy_orchestration.opening_hours_analysis")

    def test_invalid_range_raises_load_curve_error(self, db_empty):
        from services.energy_orchestration.opening_hours_analysis import (
            build_off_hours_analysis,
        )
        from services.energy_orchestration.loadcurve import LoadCurveError

        with pytest.raises(LoadCurveError):
            build_off_hours_analysis(
                db_empty,
                scope_kind="site",
                scope_id=1,
                org_id=1,
                from_dt=datetime(2026, 5, 8, tzinfo=TZ_PARIS),
                to_dt=datetime(2026, 5, 1, tzinfo=TZ_PARIS),
                granularity="hour",
            )

    def test_aggregate_hourly_multi_day_concatenates_window(self, db_empty, monkeypatch):
        """Hotfix P3.2 — granularity=hour multi-jours charge TOUS les jours.

        Cause racine : `_aggregate_series` du loadcurve (MVP P1.S2a) ne
        lit que le dernier jour ; on bascule sur un helper P3.2-local
        qui boucle sur tous les jours de la fenêtre.
        """
        called_dates: list = []

        def fake_hourly_curve(db, org_id, day, *args, **kwargs):
            called_dates.append(day)
            return [{"hour": h, "kw": 100.0} for h in range(24)]

        import services.consumption_granularity_service as svc

        monkeypatch.setattr(svc, "get_org_hourly_curve_kw", fake_hourly_curve)
        from services.energy_orchestration.opening_hours_analysis import (
            _aggregate_hourly_multi_day,
        )
        from schemas.energy_orchestration import EnergyScope

        scope = EnergyScope(kind="site", id=1, org_id=1)
        from_dt = datetime(2026, 4, 1, tzinfo=TZ_PARIS)
        to_dt = datetime(2026, 4, 8, tzinfo=TZ_PARIS)  # 8 jours
        points, _w = _aggregate_hourly_multi_day(db_empty, scope, from_dt, to_dt)
        # 8 jours × 24 heures = 192 points
        assert len(points) == 8 * 24
        # 8 dates distinctes chargées
        assert len(set(called_dates)) == 8

    def test_zero_total_does_not_divide_by_zero(self, db_empty):
        """Share = None si total = 0, jamais d'exception."""
        _seed_schedule(db_empty)
        from services.energy_orchestration.opening_hours_analysis import (
            _compute_kpis,
            _load_opening_schedule,
        )
        from schemas.energy_orchestration import EnergyPeriod, EnergyScope

        period = EnergyPeriod(
            label="custom",
            start=datetime(2026, 5, 4, tzinfo=TZ_PARIS),
            end=datetime(2026, 5, 11, tzinfo=TZ_PARIS),
            days=7,
            timezone="Europe/Paris",
        )
        scope = EnergyScope(kind="site", id=1, org_id=1)
        schedule = _load_opening_schedule(db_empty, scope, period)
        kpis, _ = _compute_kpis([], [], schedule, period, scope)
        assert kpis.off_hours_kwh.value is None
        assert kpis.off_hours_share_pct.value is None
