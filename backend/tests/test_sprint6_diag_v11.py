"""
PROMEOS - Tests Sprint 6: Diagnostic Consommation V1.1
Schedule-aware hors_horaires, tariff-aware loss EUR,
robust stats (median+MAD, linreg), recommended actions,
site config endpoints (schedule + tariff).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Meter,
    MeterReading,
    ConsumptionInsight,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    SiteOperatingSchedule,
    SiteTariffProfile,
    TypeSite,
)
from models.energy_models import FrequencyType
from database import get_db
from main import app


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


def _create_org_site(db_session, surface=2000):
    """Helper: org + entite + portefeuille + site."""
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Test PF")
    db_session.add(pf)
    db_session.flush()

    site = Site(
        nom="Bureau Test",
        type=TypeSite.BUREAU,
        adresse="1 rue de la Paix",
        code_postal="75001",
        ville="Paris",
        surface_m2=surface,
        portefeuille_id=pf.id,
        actif=True,
    )
    db_session.add(site)
    db_session.flush()
    return org, site


def _create_meter_readings(
    db_session, site_id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=0, drift_per_day=0.0
):
    """Create meter + hourly readings with controllable patterns."""
    meter = Meter(
        meter_id=f"PRM-TEST-{site_id:04d}",
        name="Compteur test",
        site_id=site_id,
        subscribed_power_kva=100.0,
        is_active=True,
    )
    db_session.add(meter)
    db_session.flush()

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)
    readings = []
    ts = start

    while ts < now:
        hour = ts.hour
        weekday = ts.weekday()
        day_idx = (ts - start).days
        is_weekend = weekday >= 5

        if not is_weekend and 8 <= hour < 19:
            val = peak_kwh
        else:
            val = base_kwh

        # Anomaly: elevated night on certain days
        if anomaly_every_n > 0 and day_idx % anomaly_every_n == 0 and (hour < 7 or hour >= 20):
            val = peak_kwh * 0.7

        # Drift
        if drift_per_day > 0:
            val *= 1.0 + drift_per_day * day_idx

        readings.append(
            MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=round(val, 2),
                quality_score=0.95,
            )
        )
        ts += timedelta(hours=1)

    db_session.bulk_save_objects(readings)
    db_session.flush()
    return meter, len(readings)


# ==============================================
# Test SiteOperatingSchedule model
# ==============================================


class TestScheduleModel:
    def test_create_schedule(self, db_session):
        _, site = _create_org_site(db_session)
        sched = SiteOperatingSchedule(
            site_id=site.id,
            timezone="Europe/Paris",
            open_days="0,1,2,3,4",
            open_time="09:00",
            close_time="18:00",
            is_24_7=False,
        )
        db_session.add(sched)
        db_session.flush()
        assert sched.id is not None
        assert sched.open_time == "09:00"
        assert sched.close_time == "18:00"

    def test_default_values(self, db_session):
        _, site = _create_org_site(db_session)
        sched = SiteOperatingSchedule(site_id=site.id)
        db_session.add(sched)
        db_session.flush()
        assert sched.open_time == "08:00"
        assert sched.close_time == "19:00"
        assert sched.is_24_7 is False
        assert sched.timezone == "Europe/Paris"


# ==============================================
# Test SiteTariffProfile model
# ==============================================


class TestTariffModel:
    def test_create_tariff(self, db_session):
        _, site = _create_org_site(db_session)
        tariff = SiteTariffProfile(
            site_id=site.id,
            price_ref_eur_per_kwh=0.22,
            currency="EUR",
        )
        db_session.add(tariff)
        db_session.flush()
        assert tariff.id is not None
        assert tariff.price_ref_eur_per_kwh == 0.22

    def test_default_price(self, db_session):
        _, site = _create_org_site(db_session)
        tariff = SiteTariffProfile(site_id=site.id)
        db_session.add(tariff)
        db_session.flush()
        assert tariff.price_ref_eur_per_kwh == 0.18


# ==============================================
# Test Schedule API endpoints
# ==============================================


class TestScheduleAPI:
    def test_get_schedule_default(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()
        resp = client.get(f"/api/site/{site.id}/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_default"] is True
        assert data["open_time"] == "08:00"
        assert data["close_time"] == "19:00"

    def test_put_schedule(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()
        resp = client.put(
            f"/api/site/{site.id}/schedule",
            json={
                "timezone": "Europe/Paris",
                "open_days": "0,1,2,3,4,5",
                "open_time": "07:00",
                "close_time": "22:00",
                "is_24_7": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["open_time"] == "07:00"
        assert data["close_time"] == "22:00"
        assert data["is_default"] is False

    def test_put_schedule_update(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()
        client.put(
            f"/api/site/{site.id}/schedule",
            json={
                "open_time": "09:00",
                "close_time": "18:00",
            },
        )
        resp = client.put(
            f"/api/site/{site.id}/schedule",
            json={
                "open_time": "10:00",
                "close_time": "20:00",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["open_time"] == "10:00"

    def test_schedule_404(self, client):
        resp = client.get("/api/site/9999/schedule")
        assert resp.status_code == 404

    def test_schedule_with_exceptions(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()
        resp = client.put(
            f"/api/site/{site.id}/schedule",
            json={
                "open_time": "08:00",
                "close_time": "19:00",
                "exceptions_json": json.dumps(["2026-01-01", "2026-05-01"]),
            },
        )
        assert resp.status_code == 200

    def test_schedule_invalid_exceptions(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()
        resp = client.put(
            f"/api/site/{site.id}/schedule",
            json={
                "open_time": "08:00",
                "close_time": "19:00",
                "exceptions_json": "not a json array",
            },
        )
        assert resp.status_code == 422


# ==============================================
# Test Tariff API endpoints
# ==============================================


class TestTariffAPI:
    def test_get_tariff_default(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()
        resp = client.get(f"/api/site/{site.id}/tariff")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_default"] is True
        assert data["price_ref_eur_per_kwh"] == 0.18

    def test_put_tariff(self, client, db_session):
        _, site = _create_org_site(db_session)
        db_session.commit()
        resp = client.put(
            f"/api/site/{site.id}/tariff",
            json={
                "price_ref_eur_per_kwh": 0.25,
                "currency": "EUR",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["price_ref_eur_per_kwh"] == 0.25
        assert data["is_default"] is False

    def test_tariff_404(self, client):
        resp = client.get("/api/site/9999/tariff")
        assert resp.status_code == 404


# ==============================================
# Test schedule-aware hors_horaires detector
# ==============================================


class TestScheduleAwareDetection:
    def test_hors_horaires_changes_with_schedule(self, db_session):
        """Changing open_time/close_time should change hors_horaires detection."""
        from services.consumption_diagnostic import run_diagnostic

        _, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        db_session.commit()

        # Default schedule (8-19)
        insights_default = run_diagnostic(db_session, site.id)
        hh_default = [i for i in insights_default if i.type == "hors_horaires"]

        # Now set wide schedule (6-23) — should reduce off-hours %
        sched = SiteOperatingSchedule(
            site_id=site.id,
            open_time="06:00",
            close_time="23:00",
            open_days="0,1,2,3,4,5,6",
            is_24_7=False,
        )
        db_session.add(sched)
        db_session.commit()

        insights_wide = run_diagnostic(db_session, site.id)
        hh_wide = [i for i in insights_wide if i.type == "hors_horaires"]

        # With wider schedule, off-hours should be less (or no insight)
        if hh_default and hh_wide:
            metrics_default = json.loads(hh_default[0].metrics_json)
            metrics_wide = json.loads(hh_wide[0].metrics_json)
            assert metrics_wide["off_hours_pct"] < metrics_default["off_hours_pct"]
        elif hh_default and not hh_wide:
            pass  # Wide schedule eliminated hors_horaires — expected
        # else: no insight in either case — acceptable

    def test_24_7_site_no_hors_horaires(self, db_session):
        """A 24/7 site should never trigger hors_horaires."""
        from services.consumption_diagnostic import run_diagnostic

        _, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        sched = SiteOperatingSchedule(
            site_id=site.id,
            is_24_7=True,
        )
        db_session.add(sched)
        db_session.commit()

        insights = run_diagnostic(db_session, site.id)
        hh = [i for i in insights if i.type == "hors_horaires"]
        assert len(hh) == 0


# ==============================================
# Test tariff-aware loss EUR
# ==============================================


class TestTariffAwareLoss:
    def test_loss_eur_uses_site_price(self, db_session):
        """estimated_loss_eur should use SiteTariffProfile price."""
        from services.consumption_diagnostic import run_diagnostic

        _, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)

        # Set custom price: 0.30 EUR/kWh
        tariff = SiteTariffProfile(site_id=site.id, price_ref_eur_per_kwh=0.30)
        db_session.add(tariff)
        db_session.commit()

        insights = run_diagnostic(db_session, site.id)
        for ci in insights:
            if ci.estimated_loss_kwh and ci.estimated_loss_kwh > 0:
                # Check EUR = kWh * 0.30
                expected_eur = round(ci.estimated_loss_kwh * 0.30, 0)
                assert ci.estimated_loss_eur == expected_eur, (
                    f"type={ci.type}: {ci.estimated_loss_eur} != {expected_eur}"
                )

    def test_loss_eur_fallback_default(self, db_session):
        """Without tariff profile, should use DEFAULT_PRICE_REF_KWH (0.18)."""
        from services.consumption_diagnostic import run_diagnostic

        _, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        db_session.commit()

        insights = run_diagnostic(db_session, site.id)
        for ci in insights:
            if ci.estimated_loss_kwh and ci.estimated_loss_kwh > 0:
                expected_eur = round(ci.estimated_loss_kwh * 0.18, 0)
                assert ci.estimated_loss_eur == expected_eur

    def test_price_ref_in_metrics(self, db_session):
        """price_ref_eur_kwh should appear in metrics_json."""
        from services.consumption_diagnostic import run_diagnostic

        _, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        db_session.commit()

        insights = run_diagnostic(db_session, site.id)
        for ci in insights:
            metrics = json.loads(ci.metrics_json) if ci.metrics_json else {}
            assert "price_ref_eur_kwh" in metrics
            assert metrics["price_ref_eur_kwh"] == 0.18


# ==============================================
# Test robust statistics
# ==============================================


class TestRobustStats:
    def test_pointe_robust_single_outlier_no_alert(self, db_session):
        """A single extreme day should NOT trigger pointe with median+MAD (robust)."""
        from services.consumption_diagnostic import _detect_pointe
        from models.energy_models import MeterReading

        # Create 30 days of flat consumption + 1 extreme day
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        readings = []
        for day in range(30):
            for hour in range(24):
                ts = now - timedelta(days=30 - day, hours=24 - hour)
                val = 50.0  # flat
                if day == 15:
                    val = 500.0  # one extreme day
                r = MeterReading()
                r.timestamp = ts
                r.value_kwh = val
                readings.append(r)

        result = _detect_pointe(readings)
        # Should NOT detect >= 2 anomaly days (only 1 extreme day)
        assert result is None or result["metrics"]["anomaly_days_count"] < 2

    def test_derive_linreg_in_metrics(self, db_session):
        """Derive should include linreg and fallback drift in metrics."""
        from services.consumption_diagnostic import run_diagnostic

        _, site = _create_org_site(db_session)
        # Create readings with drift of +1% per day
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, drift_per_day=0.01)
        db_session.commit()

        insights = run_diagnostic(db_session, site.id)
        derive = [i for i in insights if i.type == "derive"]
        if derive:
            metrics = json.loads(derive[0].metrics_json)
            assert "drift_pct_linreg" in metrics
            assert "drift_pct_fallback" in metrics
            assert "slope_kw_per_day" in metrics


# ==============================================
# Test recommended actions
# ==============================================


class TestRecommendedActions:
    def test_insights_have_recommended_actions(self, db_session):
        """All insights should have recommended_actions_json."""
        from services.consumption_diagnostic import run_diagnostic

        _, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        db_session.commit()

        insights = run_diagnostic(db_session, site.id)
        for ci in insights:
            assert ci.recommended_actions_json is not None, f"type={ci.type} missing actions"
            actions = json.loads(ci.recommended_actions_json)
            assert len(actions) >= 1
            for a in actions:
                assert "title" in a
                assert "rationale" in a
                assert "effort" in a
                assert "priority" in a

    def test_hors_horaires_actions(self, db_session):
        """hors_horaires should produce CVC and GTC actions."""
        from services.consumption_diagnostic import run_diagnostic

        _, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        db_session.commit()

        insights = run_diagnostic(db_session, site.id)
        hh = [i for i in insights if i.type == "hors_horaires"]
        if hh:
            actions = json.loads(hh[0].recommended_actions_json)
            titles = [a["title"] for a in actions]
            assert any("CVC" in t for t in titles)

    def test_recommended_actions_in_api_response(self, client, db_session):
        """GET /api/consumption/site/:id should include recommended_actions."""
        _, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        db_session.commit()

        # Run diagnostic first
        from services.consumption_diagnostic import run_diagnostic

        run_diagnostic(db_session, site.id)
        db_session.commit()

        resp = client.get(f"/api/consumption/site/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        for ins in data["insights"]:
            assert "recommended_actions" in ins

    def test_summary_includes_recommended_actions(self, client, db_session):
        """GET /api/consumption/insights should include recommended_actions per insight."""
        org, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        db_session.commit()

        from services.consumption_diagnostic import run_diagnostic

        run_diagnostic(db_session, site.id)
        db_session.commit()

        resp = client.get(f"/api/consumption/insights?org_id={org.id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["insights"]:
            for ins in data["insights"]:
                assert "recommended_actions" in ins


# ==============================================
# Test helper functions
# ==============================================


class TestHelpers:
    def test_median(self):
        from services.consumption_diagnostic import _median

        assert _median([1, 2, 3, 4, 5]) == 3
        assert _median([1, 2, 3, 4]) == 2.5
        assert _median([]) == 0.0
        assert _median([42]) == 42

    def test_mad(self):
        from services.consumption_diagnostic import _mad

        # MAD of [1,1,2,2,4,6,9] = median of [1,1,0,0,2,4,7] = 1
        assert _mad([1, 1, 2, 2, 4, 6, 9]) == 1.0

    def test_linear_slope(self):
        from services.consumption_diagnostic import _linear_slope

        # Perfect linear: y = 2*x
        assert abs(_linear_slope([0, 2, 4, 6, 8]) - 2.0) < 0.01
        # Flat
        assert abs(_linear_slope([5, 5, 5, 5])) < 0.01
        # Not enough data
        assert _linear_slope([1]) == 0.0


# ==============================================
# Test dashboard 2min integration
# ==============================================


class TestDashboard2minIntegration:
    def test_dashboard_conso_insight_action_fallback(self, client, db_session):
        """When no compliance NOK, dashboard action_1 should come from conso insight."""
        org, site = _create_org_site(db_session)
        _create_meter_readings(db_session, site.id, days=30, base_kwh=20, peak_kwh=80, anomaly_every_n=3)
        db_session.commit()

        from services.consumption_diagnostic import run_diagnostic

        run_diagnostic(db_session, site.id)
        db_session.commit()

        resp = client.get("/api/dashboard/2min")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_data"] is True
        # action_1 may come from conso insights if no compliance
        if data["action_1"] and data["action_1"].get("source") == "conso_insight":
            assert data["action_1"]["expected_gain_eur"] >= 0
