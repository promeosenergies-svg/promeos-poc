"""
PROMEOS — Tests data_freshness_service (Sprint Énergie P0.S1b, brief P4).

Cible : `services.data_freshness_service.compute_meter_freshness`

Garantit :
- Score borné [0, 100]
- Statuts discrets (fresh / warning / stale / missing)
- Timezone Europe/Paris (cf. source-guard cdc_timezone_paris)
- Provenance présente
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.energy_models import (
    FrequencyType,
    Meter,
    MeterReading,
)
from models.enums import EnergyVector
from models.site import Site
from services.data_freshness_service import (
    TZ_PARIS,
    compute_meter_freshness,
)


pytestmark = pytest.mark.fast


@pytest.fixture
def db_session():
    """SQLite in-memory pour tests isolés rapides."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def site_with_meter(db_session):
    """Site + Meter électrique 30 min (segment C5 Linky)."""
    site = Site(nom="Test Site", type="bureau", surface_m2=1000)
    db_session.add(site)
    db_session.flush()

    meter = Meter(
        site_id=site.id,
        meter_id="PRM-TEST-001",
        name="Linky principal",
        energy_vector=EnergyVector.ELECTRICITY,
        is_active=True,
        subscribed_power_kva=36,
    )
    db_session.add(meter)
    db_session.commit()
    return meter


def _add_readings(
    db,
    meter_id: int,
    *,
    n: int,
    freq: FrequencyType,
    last_ts: datetime,
    quality_score: float | None = 1.0,
):
    """Génère n relevés en arrière depuis last_ts, espacés selon freq."""
    step_minutes = {
        FrequencyType.MIN_15: 15,
        FrequencyType.MIN_30: 30,
        FrequencyType.HOURLY: 60,
        FrequencyType.DAILY: 60 * 24,
    }[freq]
    for i in range(n):
        ts = last_ts - timedelta(minutes=i * step_minutes)
        db.add(
            MeterReading(
                meter_id=meter_id,
                timestamp=ts.replace(tzinfo=None),
                frequency=freq,
                value_kwh=10.0,
                is_estimated=False,
                quality_score=quality_score,
            )
        )
    db.commit()


class TestComputeMeterFreshnessMissing:
    """Cas brief #1 : données manquantes → status=missing, score=None."""

    def test_no_reading_returns_missing(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert result.status == "missing"
        assert result.freshness_score is None
        assert result.readings_count == 0
        assert result.last_read_at is None

    def test_provenance_includes_reason(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert result.provenance["reason"] == "no_reading_in_window"


class TestComputeMeterFreshnessFresh:
    """Cas brief #2 : données fraîches → status=fresh, score élevé."""

    def test_recent_full_coverage_high_quality_is_fresh(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        # 7 jours × 48 relevés/j = 336 (couverture parfaite 30 min)
        last_ts = now - timedelta(hours=1)  # dernier relevé il y a 1h
        _add_readings(
            db_session,
            site_with_meter.id,
            n=336,
            freq=FrequencyType.MIN_30,
            last_ts=last_ts,
            quality_score=1.0,
        )

        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert result.status == "fresh"
        assert result.freshness_score >= 80
        assert result.delay_hours <= 6
        # 336 attendus sur la fenêtre 7j ; tolérance ±2 selon dernier_ts
        assert 330 <= result.readings_count <= 336

    def test_score_bounded_max_100(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        last_ts = now - timedelta(minutes=10)
        _add_readings(
            db_session,
            site_with_meter.id,
            n=336,
            freq=FrequencyType.MIN_30,
            last_ts=last_ts,
            quality_score=1.0,
        )
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert 0 <= result.freshness_score <= 100


class TestComputeMeterFreshnessStale:
    """Cas brief #3 : données anciennes → status=stale ou missing."""

    def test_old_reading_is_stale(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        # Dernier relevé il y a 48h (au-delà du seuil 12h pour MIN_30)
        last_ts = now - timedelta(hours=48)
        _add_readings(
            db_session,
            site_with_meter.id,
            n=100,
            freq=FrequencyType.MIN_30,
            last_ts=last_ts,
            quality_score=1.0,
        )
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert result.status in ("stale", "warning", "missing")
        assert result.delay_hours >= 47.0


class TestComputeMeterFreshnessBounds:
    """Garde-fou : score TOUJOURS borné [0, 100]."""

    @pytest.mark.parametrize(
        "n,delay_hours,quality",
        [
            (1, 0, 1.0),  # mini
            (336, 0, 1.0),  # max
            (336, 0, 0.0),  # qualité nulle
            (1, 1000, 0.5),  # très vieux
        ],
    )
    def test_score_always_in_0_100(self, db_session, site_with_meter, n, delay_hours, quality):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        last_ts = now - timedelta(hours=delay_hours)
        _add_readings(
            db_session,
            site_with_meter.id,
            n=n,
            freq=FrequencyType.MIN_30,
            last_ts=last_ts,
            quality_score=quality,
        )
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        if result.freshness_score is not None:
            assert 0 <= result.freshness_score <= 100


class TestComputeMeterFreshnessTimezone:
    """Cas brief #5 : timezone Europe/Paris cohérente."""

    def test_provenance_declares_europe_paris(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert result.provenance["timezone"] == "Europe/Paris"

    def test_last_read_at_is_paris_iso(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        last_ts = now - timedelta(hours=2)
        _add_readings(
            db_session,
            site_with_meter.id,
            n=5,
            freq=FrequencyType.MIN_30,
            last_ts=last_ts,
            quality_score=1.0,
        )
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert "+02:00" in result.last_read_at or "+01:00" in result.last_read_at


class TestComputeMeterFreshnessProvenance:
    """Provenance obligatoire dans toutes réponses (doctrine traçabilité)."""

    def test_provenance_has_source(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert result.provenance["source"] == "PROMEOS data_freshness_service"

    def test_provenance_has_formula(self, db_session, site_with_meter):
        now = datetime(2026, 5, 29, 12, 0, tzinfo=TZ_PARIS)
        last_ts = now - timedelta(hours=2)
        _add_readings(
            db_session,
            site_with_meter.id,
            n=10,
            freq=FrequencyType.MIN_30,
            last_ts=last_ts,
        )
        result = compute_meter_freshness(db_session, site_with_meter.id, now=now)
        assert "delay_subscore" in result.provenance["formula"]
