"""
PROMEOS — Tests V11 C6: Gas Weather-Normalized DJU Model + Alerts
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Meter, MeterReading
from models.enums import TypeSite
from models.energy_models import EnergyVector
from database import get_db
from main import app
from services.gas_weather_service import _mock_dju, _linear_regression, compute_weather_normalized


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def seeded_gas_db(db):
    """DB with a site, gas meter, and 90 days of readings."""
    site = Site(nom="Usine Gaz Test", type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()
    meter = Meter(
        site_id=site.id, meter_id="GAZ-DJU-001", name="Compteur Gaz",
        energy_vector=EnergyVector.GAS, is_active=True,
    )
    db.add(meter)
    db.flush()

    # Generate 90 days of hourly gas readings (seasonal pattern)
    now = datetime.utcnow()
    for day_offset in range(90):
        dt_base = now - timedelta(days=90 - day_offset)
        doy = dt_base.timetuple().tm_yday
        dju = _mock_dju(doy)
        # Simulate: base 20 kWh/day + 5 * DJU kWh/day, split into 24 hourly readings
        daily_kwh = 20 + 5 * dju
        hourly_kwh = daily_kwh / 24
        for h in range(24):
            db.add(MeterReading(
                meter_id=meter.id,
                timestamp=dt_base.replace(hour=h, minute=0, second=0),
                value_kwh=round(hourly_kwh, 2),
            ))
    db.commit()
    return db, site.id


@pytest.fixture
def client(seeded_gas_db):
    db, _ = seeded_gas_db
    def _override():
        try: yield db
        finally: pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestDJUModel:
    def test_mock_dju_winter(self):
        """Winter days should have high DJU."""
        dju = _mock_dju(15)  # January
        assert dju > 0

    def test_mock_dju_summer(self):
        """Summer days should have low or zero DJU."""
        dju = _mock_dju(200)  # mid-July
        assert dju >= 0  # can be 0

    def test_mock_dju_deterministic(self):
        """Same doy should give same DJU."""
        assert _mock_dju(100) == _mock_dju(100)

    def test_linear_regression_basic(self):
        """Simple linear regression."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        a, b, r2 = _linear_regression(x, y)
        assert abs(a - 2.0) < 0.01
        assert abs(b - 0.0) < 0.01
        assert r2 > 0.99

    def test_linear_regression_insufficient(self):
        """Too few points should return zeros."""
        a, b, r2 = _linear_regression([1, 2], [3, 4])
        assert a == 0 and r2 == 0


class TestGasWeatherService:
    def test_weather_normalized_returns_model(self, seeded_gas_db):
        db, site_id = seeded_gas_db
        result = compute_weather_normalized(db, site_id, days=90)
        assert "model" in result
        assert result["model"]["r_squared"] > 0
        assert result["model"]["base_kwh_day"] > 0
        assert result["model"]["heating_sensitivity"] >= 0

    def test_dju_data_populated(self, seeded_gas_db):
        db, site_id = seeded_gas_db
        result = compute_weather_normalized(db, site_id, days=90)
        assert len(result["dju_data"]) > 0
        sample = result["dju_data"][0]
        assert "date" in sample
        assert "dju" in sample
        assert "kwh" in sample
        assert "normalized_kwh" in sample

    def test_decomposition(self, seeded_gas_db):
        db, site_id = seeded_gas_db
        result = compute_weather_normalized(db, site_id, days=90)
        decomp = result["decomposition"]
        assert decomp["base_pct"] >= 0
        assert decomp["heating_pct"] >= 0
        assert abs(decomp["base_pct"] + decomp["heating_pct"] - 100) < 0.5

    def test_no_gas_meters(self, db):
        """Site with no gas meters should return empty result."""
        site = Site(nom="No Gas", type=TypeSite.BUREAU, actif=True)
        db.add(site)
        db.flush()
        result = compute_weather_normalized(db, site.id, days=90)
        assert result["reason"] == "no_gas_meters"
        assert result["dju_data"] == []

    def test_insufficient_data(self, db):
        """Site with very few readings returns insufficient_data."""
        site = Site(nom="Few Data", type=TypeSite.BUREAU, actif=True)
        db.add(site)
        db.flush()
        meter = Meter(
            site_id=site.id, meter_id="GAZ-FEW", name="Compteur Peu",
            energy_vector=EnergyVector.GAS, is_active=True,
        )
        db.add(meter)
        db.flush()
        # Only 10 readings (< 48 threshold)
        now = datetime.utcnow()
        for i in range(10):
            db.add(MeterReading(
                meter_id=meter.id,
                timestamp=now - timedelta(hours=i),
                value_kwh=5.0,
            ))
        db.commit()
        result = compute_weather_normalized(db, site.id, days=90)
        assert result["reason"] == "insufficient_data"

    def test_confidence_level(self, seeded_gas_db):
        db, site_id = seeded_gas_db
        result = compute_weather_normalized(db, site_id, days=90)
        assert result["confidence"] in ("high", "medium", "low")


class TestGasWeatherEndpoint:
    def test_endpoint_returns_200(self, client, seeded_gas_db):
        _, site_id = seeded_gas_db
        r = client.get(f"/api/consumption/gas/weather_normalized?site_id={site_id}&days=90")
        assert r.status_code == 200
        data = r.json()
        assert "model" in data
        assert "dju_data" in data
        assert "alerts" in data

    def test_endpoint_no_site(self, client):
        r = client.get("/api/consumption/gas/weather_normalized?site_id=99999&days=90")
        assert r.status_code in (200, 404)
