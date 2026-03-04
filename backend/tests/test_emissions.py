"""
PROMEOS - Tests Sprint V9: Emission Factors + Emissions Service + Endpoints
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    EmissionFactor,
    MonitoringSnapshot,
    TypeSite,
)
from database import get_db
from main import app


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


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org_site(db):
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
    db.commit()
    db.refresh(org)
    db.refresh(site)
    return org, site


def _create_snapshot(db, site_id, kpis_json=None):
    snapshot = MonitoringSnapshot(
        site_id=site_id,
        period_start=datetime(2025, 1, 1),
        period_end=datetime(2025, 3, 31),
        kpis_json=kpis_json
        or {"total_kwh": 50000, "off_hours_kwh": 12000, "readings_count": 2160, "interval_minutes": 60},
        data_quality_score=85.0,
        risk_power_score=30.0,
        engine_version="monitoring_v1.0",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


# --- EmissionFactor model tests ---


class TestEmissionFactorModel:
    def test_create_emission_factor(self, db):
        ef = EmissionFactor(
            energy_type="electricity",
            region="FR",
            kgco2e_per_kwh=0.052,
            source_label="ADEME 2024",
            quality="official",
        )
        db.add(ef)
        db.commit()
        db.refresh(ef)
        assert ef.id is not None
        assert ef.kgco2e_per_kwh == 0.052
        assert ef.region == "FR"

    def test_create_gas_factor(self, db):
        ef = EmissionFactor(
            energy_type="gas",
            region="FR",
            kgco2e_per_kwh=0.227,
            source_label="ADEME Base Carbone",
            quality="official",
        )
        db.add(ef)
        db.commit()
        assert ef.energy_type == "gas"
        assert ef.kgco2e_per_kwh == 0.227

    def test_validity_dates(self, db):
        ef = EmissionFactor(
            energy_type="electricity",
            region="DE",
            kgco2e_per_kwh=0.380,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            quality="estimated",
        )
        db.add(ef)
        db.commit()
        assert ef.valid_from == date(2024, 1, 1)
        assert ef.valid_to == date(2024, 12, 31)

    def test_repr(self, db):
        ef = EmissionFactor(
            energy_type="electricity",
            region="FR",
            kgco2e_per_kwh=0.052,
        )
        r = repr(ef)
        assert "electricity" in r
        assert "FR" in r


# --- Emissions service tests ---


class TestEmissionsService:
    def test_compute_with_factor(self, db):
        ef = EmissionFactor(
            energy_type="electricity",
            region="FR",
            kgco2e_per_kwh=0.052,
            quality="demo",
            source_label="Test factor",
        )
        db.add(ef)
        db.commit()

        from services.emissions_service import compute_emissions_summary

        kpis = {"total_kwh": 50000, "off_hours_kwh": 12000, "readings_count": 2160, "interval_minutes": 60}
        result = compute_emissions_summary(db, 1, kpis)

        assert result["total_co2e_kg"] == round(50000 * 0.052, 2)
        assert result["off_hours_co2e_kg"] == round(12000 * 0.052, 2)
        assert result["factor"]["kgco2e_per_kwh"] == 0.052
        assert result["annualized_co2e_tonnes"] > 0

    def test_compute_fallback_no_factor(self, db):
        from services.emissions_service import compute_emissions_summary, DEFAULT_FACTOR_KGCO2E

        kpis = {"total_kwh": 10000, "off_hours_kwh": 2000, "readings_count": 720, "interval_minutes": 60}
        result = compute_emissions_summary(db, 1, kpis)

        assert result["factor"]["quality"] == "fallback"
        assert result["factor"]["kgco2e_per_kwh"] == DEFAULT_FACTOR_KGCO2E
        assert result["total_co2e_kg"] == round(10000 * DEFAULT_FACTOR_KGCO2E, 2)

    def test_compute_empty_kpis(self, db):
        from services.emissions_service import compute_emissions_summary

        result = compute_emissions_summary(db, 1, {})
        assert result["total_co2e_kg"] == 0
        assert result["off_hours_co2e_kg"] == 0
        assert result["annualized_co2e_kg"] == 0

    def test_get_emission_factor_by_date(self, db):
        ef_old = EmissionFactor(
            energy_type="electricity",
            region="FR",
            kgco2e_per_kwh=0.060,
            valid_from=date(2023, 1, 1),
            valid_to=date(2023, 12, 31),
            quality="official",
            source_label="2023",
        )
        ef_new = EmissionFactor(
            energy_type="electricity",
            region="FR",
            kgco2e_per_kwh=0.052,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            quality="official",
            source_label="2024",
        )
        db.add_all([ef_old, ef_new])
        db.commit()

        from services.emissions_service import get_emission_factor

        result = get_emission_factor(db, ref_date=date(2024, 6, 15))
        assert result["kgco2e_per_kwh"] == 0.052

    def test_annualization_correct(self, db):
        ef = EmissionFactor(
            energy_type="electricity",
            region="FR",
            kgco2e_per_kwh=0.1,
            quality="demo",
        )
        db.add(ef)
        db.commit()

        from services.emissions_service import compute_emissions_summary

        # 720 readings * 1h = 30 days of data
        kpis = {"total_kwh": 3000, "off_hours_kwh": 0, "readings_count": 720, "interval_minutes": 60}
        result = compute_emissions_summary(db, 1, kpis)
        # 3000 kWh * 0.1 = 300 kgCO2e over 30 days
        # annualized: 300 * (365/30) = 3650
        assert result["total_co2e_kg"] == 300.0
        assert result["days_covered"] == 30.0
        assert result["annualized_co2e_kg"] == 3650.0


# --- Endpoint tests ---


class TestEmissionsEndpoints:
    def test_seed_emission_factors(self, client, db):
        resp = client.post("/api/monitoring/emission-factors/seed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["kgco2e_per_kwh"] == 0.052

    def test_seed_idempotent(self, client, db):
        client.post("/api/monitoring/emission-factors/seed")
        resp = client.post("/api/monitoring/emission-factors/seed")
        assert resp.status_code == 200
        assert resp.json()["status"] == "already_exists"

    def test_list_emission_factors(self, client, db):
        client.post("/api/monitoring/emission-factors/seed")
        resp = client.get("/api/monitoring/emission-factors")
        assert resp.status_code == 200
        factors = resp.json()
        assert len(factors) >= 1
        assert factors[0]["energy_type"] == "electricity"
        assert factors[0]["region"] == "FR"

    def test_list_emission_factors_filter(self, client, db):
        ef = EmissionFactor(
            energy_type="gas",
            region="FR",
            kgco2e_per_kwh=0.227,
            quality="demo",
        )
        db.add(ef)
        db.commit()

        resp = client.get("/api/monitoring/emission-factors?energy_type=gas")
        assert resp.status_code == 200
        factors = resp.json()
        assert all(f["energy_type"] == "gas" for f in factors)

    def test_get_emissions_with_snapshot(self, client, db):
        _, site = _create_org_site(db)
        client.post("/api/monitoring/emission-factors/seed")
        _create_snapshot(db, site.id)

        resp = client.get(f"/api/monitoring/emissions?site_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_co2e_kg"] > 0
        assert data["factor"]["kgco2e_per_kwh"] == 0.052
        assert "annualized_co2e_tonnes" in data

    def test_get_emissions_no_snapshot(self, client, db):
        _, site = _create_org_site(db)
        resp = client.get(f"/api/monitoring/emissions?site_id={site.id}")
        assert resp.status_code == 404

    def test_kpis_endpoint_includes_emissions(self, client, db):
        _, site = _create_org_site(db)
        client.post("/api/monitoring/emission-factors/seed")
        _create_snapshot(db, site.id)

        resp = client.get(f"/api/monitoring/kpis?site_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "emissions" in data
        assert data["emissions"]["total_co2e_kg"] > 0

    def test_emissions_off_hours_co2e(self, client, db):
        _, site = _create_org_site(db)
        ef = EmissionFactor(
            energy_type="electricity",
            region="FR",
            kgco2e_per_kwh=0.052,
            quality="demo",
        )
        db.add(ef)
        db.commit()
        _create_snapshot(
            db,
            site.id,
            kpis_json={
                "total_kwh": 100000,
                "off_hours_kwh": 30000,
                "readings_count": 2160,
                "interval_minutes": 60,
            },
        )

        resp = client.get(f"/api/monitoring/emissions?site_id={site.id}")
        data = resp.json()
        assert data["off_hours_co2e_kg"] == round(30000 * 0.052, 2)
        assert data["total_co2e_kg"] == round(100000 * 0.052, 2)


# --- Action CO2e field tests ---


class TestActionCO2e:
    def test_create_action_with_co2e(self, client, db):
        org, site = _create_org_site(db)
        resp = client.post(
            "/api/actions",
            json={
                "org_id": org.id,
                "site_id": site.id,
                "source_type": "manual",
                "title": "Reduire conso hors horaires",
                "estimated_gain_eur": 5000,
                "co2e_savings_est_kg": 1733,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["co2e_savings_est_kg"] == 1733

    def test_patch_action_co2e(self, client, db):
        from models import ActionItem, ActionSourceType, ActionStatus

        org, site = _create_org_site(db)
        action = ActionItem(
            org_id=org.id,
            site_id=site.id,
            source_type=ActionSourceType.MANUAL,
            source_id="test-co2e",
            source_key="k1",
            title="Test CO2e patch",
            priority=3,
            status=ActionStatus.OPEN,
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        resp = client.patch(
            f"/api/actions/{action.id}",
            json={
                "co2e_savings_est_kg": 500.5,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["co2e_savings_est_kg"] == 500.5

    def test_action_serialize_includes_co2e(self, client, db):
        from models import ActionItem, ActionSourceType, ActionStatus

        org, site = _create_org_site(db)
        action = ActionItem(
            org_id=org.id,
            site_id=site.id,
            source_type=ActionSourceType.MANUAL,
            source_id="test-co2e-ser",
            source_key="k2",
            title="Test serialize co2e",
            priority=3,
            status=ActionStatus.OPEN,
            co2e_savings_est_kg=250,
        )
        db.add(action)
        db.commit()

        resp = client.get(f"/api/actions/{action.id}")
        assert resp.status_code == 200
        assert resp.json()["co2e_savings_est_kg"] == 250
