"""
PROMEOS - Tests V10.1: Availability endpoint + energy_type normalization
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Meter, MeterReading,
    Organisation, EntiteJuridique, Portefeuille, TypeSite,
)
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
def client(db):
    def _override():
        try: yield db
        finally: pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org_site(db):
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org); db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db.add(ej); db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Default")
    db.add(pf); db.flush()
    site = Site(nom="Bureau Lyon", portefeuille_id=pf.id, type=TypeSite.BUREAU,
                adresse="10 rue", code_postal="69003", ville="Lyon", surface_m2=2000, actif=True)
    db.add(site); db.commit()
    return org, site


def _create_meter(db, site, ev=EnergyVector.ELECTRICITY, mid="PRM-001"):
    m = Meter(meter_id=mid, name=f"Compteur {mid}", energy_vector=ev,
              site_id=site.id, subscribed_power_kva=60, is_active=True)
    db.add(m); db.commit()
    return m


def _seed_readings(db, meter, count=100):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    readings = []
    for i in range(count):
        ts = now - timedelta(hours=count - i)
        readings.append(MeterReading(meter_id=meter.id, timestamp=ts,
                                     frequency=FrequencyType.HOURLY, value_kwh=10.0))
    db.add_all(readings); db.commit()


# =============================================
# TestAvailability
# =============================================

class TestAvailability:
    def test_has_data(self, client, db):
        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, count=200)
        r = client.get(f"/api/consumption/availability?site_id={site.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is True
        assert data["readings_count"] == 200
        assert data["first_ts"] is not None
        assert data["last_ts"] is not None
        assert "electricity" in data["energy_types"]

    def test_no_meter(self, client, db):
        _, site = _create_org_site(db)
        r = client.get(f"/api/consumption/availability?site_id={site.id}")
        data = r.json()
        assert data["has_data"] is False
        assert "no_meter" in data["reasons"]

    def test_no_readings(self, client, db):
        _, site = _create_org_site(db)
        _create_meter(db, site)
        r = client.get(f"/api/consumption/availability?site_id={site.id}")
        data = r.json()
        assert data["has_data"] is False
        assert "no_readings" in data["reasons"]

    def test_wrong_energy_type(self, client, db):
        _, site = _create_org_site(db)
        _create_meter(db, site, ev=EnergyVector.GAS, mid="PCE-001")
        _seed_readings(db, _create_meter(db, site, ev=EnergyVector.GAS, mid="PCE-002"), count=200)
        r = client.get(f"/api/consumption/availability?site_id={site.id}&energy_type=electricity")
        data = r.json()
        assert data["has_data"] is False
        assert "wrong_energy_type" in data["reasons"]
        assert "gas" in data["energy_types"]

    def test_insufficient_readings(self, client, db):
        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, count=20)
        r = client.get(f"/api/consumption/availability?site_id={site.id}")
        data = r.json()
        assert data["has_data"] is False
        assert "insufficient_readings" in data["reasons"]

    def test_no_site(self, client, db):
        r = client.get("/api/consumption/availability?site_id=9999")
        data = r.json()
        assert data["has_data"] is False
        assert "no_site" in data["reasons"]


# =============================================
# TestEnergyTypeNormalization
# =============================================

class TestEnergyTypeNormalization:
    def test_tunnel_accepts_elec(self, client, db):
        """'elec' should be normalized to 'electricity'."""
        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, count=200)
        r = client.get(f"/api/consumption/tunnel?site_id={site.id}&energy_type=elec")
        assert r.status_code == 200
        assert r.json()["readings_count"] > 0

    def test_tunnel_accepts_electricite(self, client, db):
        """'electricite' should be normalized to 'electricity'."""
        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, count=200)
        r = client.get(f"/api/consumption/tunnel?site_id={site.id}&energy_type=electricite")
        assert r.status_code == 200
        assert r.json()["readings_count"] > 0

    def test_tunnel_gaz_alias(self, client, db):
        """'gaz' should be normalized to 'gas'."""
        _, site = _create_org_site(db)
        meter = _create_meter(db, site, ev=EnergyVector.GAS, mid="PCE-001")
        _seed_readings(db, meter, count=200)
        r = client.get(f"/api/consumption/tunnel?site_id={site.id}&energy_type=gaz")
        assert r.status_code == 200
        assert r.json()["readings_count"] > 0

    def test_availability_accepts_gaz(self, client, db):
        _, site = _create_org_site(db)
        meter = _create_meter(db, site, ev=EnergyVector.GAS, mid="PCE-001")
        _seed_readings(db, meter, count=200)
        r = client.get(f"/api/consumption/availability?site_id={site.id}&energy_type=gaz")
        data = r.json()
        assert data["has_data"] is True
