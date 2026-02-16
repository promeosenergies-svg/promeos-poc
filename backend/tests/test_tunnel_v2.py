"""
PROMEOS — Tests V11 C3: Tunnel V2 (energy + power mode)
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
from models.energy_models import EnergyVector, FrequencyType
from database import get_db
from main import app


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def seeded_db(db):
    """DB with a site, meter, and 100 readings."""
    site = Site(nom="Test Site", type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()
    meter = Meter(
        site_id=site.id, meter_id="PDL-TUNNEL-V2", name="Compteur Test",
        energy_vector=EnergyVector.ELECTRICITY,
        is_active=True,
    )
    db.add(meter)
    db.flush()

    # Generate 100 hourly readings over ~4 days
    now = datetime.utcnow()
    for i in range(100):
        db.add(MeterReading(
            meter_id=meter.id,
            timestamp=now - timedelta(hours=100 - i),
            value_kwh=10.0 + (i % 24) * 0.5,  # pattern by hour
        ))
    db.commit()
    return db, site.id


@pytest.fixture
def client(seeded_db):
    db, _ = seeded_db
    def _override():
        try: yield db
        finally: pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestTunnelV2:
    def test_energy_mode(self, client, seeded_db):
        _, site_id = seeded_db
        r = client.get(f"/api/consumption/tunnel_v2?site_id={site_id}&days=30&mode=energy")
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "energy"
        assert data["unit"] == "kWh"
        assert "envelope" in data

    def test_power_mode(self, client, seeded_db):
        _, site_id = seeded_db
        r = client.get(f"/api/consumption/tunnel_v2?site_id={site_id}&days=30&mode=power")
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "power"
        assert data["unit"] == "kW"

    def test_metadata_present(self, client, seeded_db):
        _, site_id = seeded_db
        r = client.get(f"/api/consumption/tunnel_v2?site_id={site_id}&days=30")
        data = r.json()
        assert "reference_band_method" in data
        assert "sample_size" in data
        assert data["reference_band_method"] == "percentile_hourly"

    def test_empty_data(self, client):
        """Request for a non-existent site returns empty tunnel."""
        r = client.get("/api/consumption/tunnel_v2?site_id=99999&days=30")
        assert r.status_code == 404

    def test_v1_still_works(self, client, seeded_db):
        """V1 endpoint still available (backward compat)."""
        _, site_id = seeded_db
        r = client.get(f"/api/consumption/tunnel?site_id={site_id}&days=30")
        assert r.status_code == 200
        data = r.json()
        assert "envelope" in data
        # V1 does NOT have "mode" key
        assert "mode" not in data

    def test_invalid_mode(self, client, seeded_db):
        _, site_id = seeded_db
        r = client.get(f"/api/consumption/tunnel_v2?site_id={site_id}&mode=invalid")
        assert r.status_code == 400
