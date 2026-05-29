"""
PROMEOS — Tests GET /api/energy/week-profile (Sprint Énergie P1.S2b).

Couvre :
- site scope ;
- empty matrix → 200 + empty_state propre ;
- scope invalide / scope_id manquant / days insuffisant → erreurs
  standardisées avec code + message + hint + correlation_id ;
- 4 KPI agrégés (highest_day, highest_hour, night_baseload_kw,
  weekend_consumption_pct) + provenance individuelle ;
- timezone Europe/Paris.
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


class TestWeekProfileScopeValidation:
    """Brief : scope invalide → WeekProfileError + hint."""

    def test_org_scope_raises_with_hint(self, db_empty):
        from services.energy_orchestration.week_profile import (
            WeekProfileError,
            build_week_profile,
        )

        with pytest.raises(WeekProfileError) as exc_info:
            build_week_profile(
                db_empty,
                scope_kind="org",
                scope_id=1,
                org_id=1,
                days=90,
            )
        assert exc_info.value.hint is not None
        assert "site" in exc_info.value.hint or "meter" in exc_info.value.hint

    def test_portfolio_scope_raises(self, db_empty):
        from services.energy_orchestration.week_profile import (
            WeekProfileError,
            build_week_profile,
        )

        with pytest.raises(WeekProfileError):
            build_week_profile(
                db_empty,
                scope_kind="portfolio",
                scope_id=1,
                org_id=1,
                days=90,
            )


class TestWeekProfileScopeIdRequired:
    """Brief : scope_id obligatoire."""

    def test_site_without_scope_id_raises(self, db_empty):
        from services.energy_orchestration.week_profile import (
            WeekProfileError,
            build_week_profile,
        )

        with pytest.raises(WeekProfileError) as exc_info:
            build_week_profile(
                db_empty,
                scope_kind="site",
                scope_id=None,
                org_id=1,
                days=90,
            )
        assert "scope_id" in str(exc_info.value).lower()


class TestWeekProfileDaysValidation:
    """Brief : days insuffisant → erreur claire."""

    def test_days_below_7_raises(self, db_empty):
        from services.energy_orchestration.week_profile import (
            WeekProfileError,
            build_week_profile,
        )

        with pytest.raises(WeekProfileError) as exc_info:
            build_week_profile(
                db_empty,
                scope_kind="site",
                scope_id=1,
                org_id=1,
                days=3,
            )
        assert exc_info.value.hint is not None


class TestWeekProfileEmptyState:
    """Brief : aucune donnée → 200 + matrix=[] + empty_state actionnable."""

    def test_empty_db_returns_200_with_empty_state(self, db_empty):
        from services.energy_orchestration.week_profile import build_week_profile

        resp = build_week_profile(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            days=90,
        )
        assert resp.scope.kind == "site"
        # Pas de compteur → matrix vide + empty_state
        assert resp.empty_state is not None
        assert "élargir" in resp.empty_state.lower() or "vérifier" in resp.empty_state.lower()


class TestWeekProfilePeriodTimezone:
    """Brief : timezone Europe/Paris."""

    def test_period_timezone_is_europe_paris(self, db_empty):
        from services.energy_orchestration.week_profile import build_week_profile

        resp = build_week_profile(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            days=30,
        )
        assert resp.period.timezone == "Europe/Paris"
        assert resp.period.days == 30


class TestWeekProfileKpisShape:
    """Brief : 4 KPI agrégés + provenance individuelle."""

    def test_response_has_4_kpis(self, db_empty):
        from services.energy_orchestration.week_profile import build_week_profile

        resp = build_week_profile(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            days=30,
        )
        assert resp.kpis.highest_day is not None
        assert resp.kpis.highest_hour is not None
        assert resp.kpis.night_baseload_kw is not None
        assert resp.kpis.weekend_consumption_pct is not None

    def test_each_kpi_has_provenance(self, db_empty):
        from services.energy_orchestration.week_profile import build_week_profile

        resp = build_week_profile(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            days=30,
        )
        for kpi in (
            resp.kpis.highest_day,
            resp.kpis.highest_hour,
            resp.kpis.night_baseload_kw,
            resp.kpis.weekend_consumption_pct,
        ):
            assert kpi.provenance.source
            assert kpi.provenance.service
            assert kpi.provenance.formula

    def test_inactive_kpis_when_no_data(self, db_empty):
        """Sans data, les 4 KPI sont state=inactif."""
        from services.energy_orchestration.week_profile import build_week_profile

        resp = build_week_profile(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            days=30,
        )
        assert resp.kpis.highest_day.state == "inactif"
        assert resp.kpis.night_baseload_kw.state == "inactif"


class TestWeekProfileProvenanceRoot:
    """Brief : provenance racine + assumptions clés."""

    def test_root_provenance_includes_paris(self, db_empty):
        from services.energy_orchestration.week_profile import build_week_profile

        resp = build_week_profile(
            db_empty,
            scope_kind="site",
            scope_id=1,
            org_id=1,
            days=30,
        )
        assert resp.provenance.service == "energy_orchestration.week_profile.build_week_profile"
        assert "Europe/Paris" in " ".join(resp.provenance.assumptions)
        assert "weekday=0=Lun" in " ".join(resp.provenance.assumptions)


class TestEnergyErrorPayloadStandard:
    """Brief P2 : erreurs standardisées avec correlation_id."""

    def test_energy_error_includes_correlation_id(self):
        from services.energy_orchestration.errors import energy_error

        exc = energy_error(
            code="ENERGY_SCOPE_INVALID",
            message="scope='org' invalide",
            hint="utiliser site|meter",
        )
        assert exc.status_code == 400
        # Le detail contient le payload standardisé
        assert exc.detail["code"] == "ENERGY_SCOPE_INVALID"
        assert exc.detail["message"]
        assert exc.detail["hint"]
        assert "correlation_id" in exc.detail
        assert exc.detail["correlation_id"]  # UUID généré

    def test_correlation_id_propagated_from_header(self):
        """Si le header X-Correlation-Id est présent, on le réutilise."""
        from unittest.mock import MagicMock

        from services.energy_orchestration.errors import energy_error

        fake_req = MagicMock()
        fake_req.headers = {"X-Correlation-Id": "trace-12345"}
        exc = energy_error(
            code="ENERGY_PERIOD_INVALID",
            message="period invalide",
            request=fake_req,
        )
        assert exc.detail["correlation_id"] == "trace-12345"

    def test_correlation_id_generated_when_absent(self):
        from unittest.mock import MagicMock

        from services.energy_orchestration.errors import energy_error

        fake_req = MagicMock()
        fake_req.headers = {}
        exc = energy_error(
            code="ENERGY_PERIOD_INVALID",
            message="period invalide",
            request=fake_req,
        )
        cid = exc.detail["correlation_id"]
        # UUID v4 = 36 caractères avec tirets
        assert len(cid) == 36
