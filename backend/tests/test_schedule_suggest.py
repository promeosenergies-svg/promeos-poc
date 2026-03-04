"""
PROMEOS - Tests Sprint V4.9: Schedule Suggest Service
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, EntiteJuridique, Portefeuille, TypeSite
from models.energy_models import Meter, MeterReading, EnergyVector, FrequencyType
from services.ems.schedule_suggest_service import suggest_schedule_from_consumption


@pytest.fixture
def db():
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


def _create_site_with_meter(db):
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="P1")
    db.add(pf)
    db.flush()
    site = Site(portefeuille_id=pf.id, nom="Site Test", type=TypeSite.BUREAU, surface_m2=1000, actif=True)
    db.add(site)
    db.flush()
    meter = Meter(
        meter_id="PDL_TEST",
        name="Compteur principal",
        energy_vector=EnergyVector.ELECTRICITY,
        site_id=site.id,
        is_active=True,
    )
    db.add(meter)
    db.flush()
    return site, meter


def _inject_office_readings(db, meter, days=90):
    """Inject office-pattern readings: high 8-18 weekdays, low nights/weekends."""
    now = datetime.now(timezone.utc)
    for d in range(days):
        ts_base = now - timedelta(days=days - d)
        dow = ts_base.weekday()
        for h in range(24):
            ts = ts_base.replace(hour=h, minute=0, second=0, microsecond=0)
            if dow < 5 and 8 <= h < 18:
                value = 50 + (h % 5) * 2  # 50-58 kWh during office hours
            else:
                value = 5  # talon at night/weekend
            reading = MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=value,
            )
            db.add(reading)
    db.flush()


def _inject_flat_readings(db, meter, days=90):
    """Inject flat curve (24/7 constant)."""
    now = datetime.now(timezone.utc)
    for d in range(days):
        ts_base = now - timedelta(days=days - d)
        for h in range(24):
            ts = ts_base.replace(hour=h, minute=0, second=0, microsecond=0)
            reading = MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=30,
            )
            db.add(reading)
    db.flush()


class TestScheduleSuggest:
    def test_office_pattern_detection(self, db):
        """Office pattern: detect Mon-Fri 8h-18h."""
        site, meter = _create_site_with_meter(db)
        _inject_office_readings(db, meter, days=90)
        db.commit()

        result = suggest_schedule_from_consumption(db, site.id)
        assert result["schedule_suggested"] is not None
        sched = result["schedule_suggested"]
        assert sched["is_24_7"] is False
        # Should detect weekdays (0-4)
        open_days = [int(d) for d in sched["open_days"].split(",")]
        assert 0 in open_days  # Monday
        assert 4 in open_days  # Friday
        assert 5 not in open_days  # Saturday excluded
        assert result["active_days"] == 5
        assert result["confidence"] in ("high", "medium")

    def test_insufficient_data(self, db):
        """Fewer than 168 readings -> error."""
        site, meter = _create_site_with_meter(db)
        # Only inject 100 readings (less than 168)
        now = datetime.now(timezone.utc)
        for i in range(100):
            ts = now - timedelta(hours=100 - i)
            db.add(
                MeterReading(
                    meter_id=meter.id,
                    timestamp=ts,
                    frequency=FrequencyType.HOURLY,
                    value_kwh=30,
                )
            )
        db.commit()

        result = suggest_schedule_from_consumption(db, site.id)
        assert result["error"] == "insufficient_data"
        assert result["schedule_suggested"] is None

    def test_24_7_detection(self, db):
        """Flat curve -> 24/7 schedule."""
        site, meter = _create_site_with_meter(db)
        _inject_flat_readings(db, meter, days=30)
        db.commit()

        result = suggest_schedule_from_consumption(db, site.id)
        assert result["schedule_suggested"] is not None
        assert result["schedule_suggested"]["is_24_7"] is True

    def test_confidence_levels(self, db):
        """More readings -> higher confidence."""
        site, meter = _create_site_with_meter(db)
        _inject_office_readings(db, meter, days=120)  # >2000 readings
        db.commit()

        result = suggest_schedule_from_consumption(db, site.id)
        assert result["confidence"] == "high"
        assert result["n_readings"] >= 2000
