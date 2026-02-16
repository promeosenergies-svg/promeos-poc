"""
PROMEOS — Tests V11 C4: Targets V2 (variance decomposition + run-rate)
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
from models.consumption_target import ConsumptionTarget
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
    """DB with site, meter, readings, and monthly targets."""
    site = Site(nom="Bureau Lyon", type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()

    meter = Meter(
        site_id=site.id, meter_id="PRM-TARGETS-V2", name="Compteur Principal",
        energy_vector=EnergyVector.ELECTRICITY, is_active=True,
    )
    db.add(meter)
    db.flush()

    # Seed readings (100 hourly) + monthly targets for current year
    now = datetime.utcnow()
    year = now.year
    for i in range(100):
        db.add(MeterReading(
            meter_id=meter.id,
            timestamp=now - timedelta(hours=100 - i),
            value_kwh=8.0 + (i % 24) * 0.3,
        ))

    for m in range(1, 13):
        db.add(ConsumptionTarget(
            site_id=site.id, energy_type="electricity",
            period="monthly", year=year, month=m,
            target_kwh=5000.0,
        ))

    db.commit()
    return db, site.id, year


@pytest.fixture
def client(seeded_db):
    db, _, _ = seeded_db
    def _override():
        try: yield db
        finally: pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestTargetsV2:
    def test_variance_decomposition_key(self, client, seeded_db):
        _, site_id, year = seeded_db
        r = client.get(f"/api/consumption/targets/progress_v2?site_id={site_id}&year={year}")
        assert r.status_code == 200
        data = r.json()
        assert "variance_decomposition" in data
        assert isinstance(data["variance_decomposition"], list)

    def test_run_rate_key(self, client, seeded_db):
        _, site_id, year = seeded_db
        r = client.get(f"/api/consumption/targets/progress_v2?site_id={site_id}&year={year}")
        data = r.json()
        assert "run_rate_kwh" in data
        assert data["run_rate_kwh"] >= 0

    def test_top_3_causes(self, client, seeded_db):
        _, site_id, year = seeded_db
        r = client.get(f"/api/consumption/targets/progress_v2?site_id={site_id}&year={year}")
        data = r.json()
        assert len(data["variance_decomposition"]) <= 3

    def test_no_data(self, client):
        """Non-existent site should still return valid V2 structure."""
        r = client.get("/api/consumption/targets/progress_v2?site_id=99999")
        assert r.status_code == 200
        data = r.json()
        assert "run_rate_kwh" in data
        assert "variance_decomposition" in data

    def test_v1_still_works(self, client, seeded_db):
        """V1 progression endpoint still works (backward compat)."""
        _, site_id, year = seeded_db
        r = client.get(f"/api/consumption/targets/progression?site_id={site_id}&year={year}")
        assert r.status_code == 200
        data = r.json()
        assert "alert" in data
        # V1 does NOT have variance_decomposition
        assert "variance_decomposition" not in data
