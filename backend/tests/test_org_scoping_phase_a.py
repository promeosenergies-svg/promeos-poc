"""
PROMEOS — Phase A: Org-Scoping Isolation Tests
Covers: power.py, usages.py, flex.py, ems.py, bridge_route.py

Setup: 2 orgs (Alpha, Bravo), each with EJ → Portfolio → Site → Meter.
Tests: accessing Org B data from Org A context → 403/404.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Meter,
    TypeSite,
)
from models.energy_models import EnergyVector
from database import get_db
from main import app


# ========================================
# Fixtures
# ========================================


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


def _create_two_orgs(db):
    """Create 2 complete org hierarchies: Alpha and Bravo with meters."""
    org_a = Organisation(nom="Org Alpha", type_client="bureau", actif=True, siren="111111111")
    db.add(org_a)
    db.flush()
    ej_a = EntiteJuridique(organisation_id=org_a.id, nom="EJ Alpha", siren="111111111")
    db.add(ej_a)
    db.flush()
    pf_a = Portefeuille(entite_juridique_id=ej_a.id, nom="PF Alpha")
    db.add(pf_a)
    db.flush()
    site_a = Site(
        portefeuille_id=pf_a.id,
        nom="Site Alpha",
        type=TypeSite.BUREAU,
        adresse="10 rue Alpha",
        code_postal="75001",
        ville="Paris",
        surface_m2=1000,
        actif=True,
    )
    db.add(site_a)
    db.flush()
    meter_a = Meter(
        meter_id="PRM-ALPHA-001",
        name="Meter Alpha",
        site_id=site_a.id,
        energy_vector=EnergyVector.ELECTRICITY,
    )
    db.add(meter_a)
    db.flush()

    org_b = Organisation(nom="Org Bravo", type_client="industrie", actif=True, siren="222222222")
    db.add(org_b)
    db.flush()
    ej_b = EntiteJuridique(organisation_id=org_b.id, nom="EJ Bravo", siren="222222222")
    db.add(ej_b)
    db.flush()
    pf_b = Portefeuille(entite_juridique_id=ej_b.id, nom="PF Bravo")
    db.add(pf_b)
    db.flush()
    site_b = Site(
        portefeuille_id=pf_b.id,
        nom="Site Bravo",
        type=TypeSite.BUREAU,
        adresse="20 rue Bravo",
        code_postal="69001",
        ville="Lyon",
        surface_m2=800,
        actif=True,
    )
    db.add(site_b)
    db.flush()
    meter_b = Meter(
        meter_id="PRM-BRAVO-001",
        name="Meter Bravo",
        site_id=site_b.id,
        energy_vector=EnergyVector.ELECTRICITY,
    )
    db.add(meter_b)
    db.flush()

    db.commit()
    return {
        "org_a": org_a,
        "ej_a": ej_a,
        "pf_a": pf_a,
        "site_a": site_a,
        "meter_a": meter_a,
        "org_b": org_b,
        "ej_b": ej_b,
        "pf_b": pf_b,
        "site_b": site_b,
        "meter_b": meter_b,
    }


def _h(org_id: int) -> dict:
    """X-Org-Id header for org scoping."""
    return {"X-Org-Id": str(org_id)}


# ════════════════════════════════════════════════════════════
# 1. Power module isolation
# ════════════════════════════════════════════════════════════


class TestPowerIsolation:
    def test_power_profile_own_org(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/power/sites/{d['site_a'].id}/profile", headers=_h(d["org_a"].id))
        assert r.status_code in (200, 404)  # 404 if no meter data

    def test_power_profile_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/power/sites/{d['site_b'].id}/profile", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_power_contract_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/power/sites/{d['site_b'].id}/contract", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_power_peaks_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/power/sites/{d['site_b'].id}/peaks", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_power_factor_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/power/sites/{d['site_b'].id}/factor", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_power_optimize_ps_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/power/sites/{d['site_b'].id}/optimize-ps", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_power_nebco_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/power/sites/{d['site_b'].id}/nebco", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_portfolio_nebco_scoped_to_org(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/power/portfolio/nebco-summary", headers=_h(d["org_a"].id))
        assert r.status_code in (200, 404)


# ════════════════════════════════════════════════════════════
# 2. Usages module isolation
# ════════════════════════════════════════════════════════════


class TestUsagesIsolation:
    def test_usages_dashboard_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/dashboard/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_readiness_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/readiness/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_metering_plan_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/metering-plan/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_top_ues_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/top-ues/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_cost_breakdown_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/cost-breakdown/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_baselines_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/baselines/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_compliance_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/compliance/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_billing_links_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/billing-links/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_list_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/site/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_timeline_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/timeline/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_energy_signature_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/energy-signature/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_power_optimization_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/power-optimization/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_cost_by_period_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/cost-by-period/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_flex_potential_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/flex-potential/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_usages_meter_readings_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/usages/meter-readings/{d['meter_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404  # meter not found in org scope


# ════════════════════════════════════════════════════════════
# 3. Flex module isolation
# ════════════════════════════════════════════════════════════


class TestFlexIsolation:
    def test_flex_mini_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/sites/{d['site_b'].id}/flex/mini", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_flex_assets_scoped_to_org(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/flex/assets", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        data = r.json()
        for asset in data.get("assets", []):
            assert asset["site_id"] == d["site_a"].id

    def test_flex_assessment_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/flex/assessment?site_id={d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_flex_prioritization_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/flex/portfolios/{d['pf_b'].id}/flex-prioritization", headers=_h(d["org_a"].id))
        assert r.status_code == 403


# ════════════════════════════════════════════════════════════
# 4. EMS module isolation
# ════════════════════════════════════════════════════════════


class TestEmsIsolation:
    def test_ems_hierarchy_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/ems/hierarchy", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        data = r.json()
        assert data["org_id"] == d["org_a"].id

    def test_ems_timeseries_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(
            f"/api/ems/timeseries?site_ids={d['site_b'].id}&date_from=2025-01-01&date_to=2025-01-31",
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 403

    def test_ems_timeseries_mixed_orgs_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(
            f"/api/ems/timeseries?site_ids={d['site_a'].id},{d['site_b'].id}&date_from=2025-01-01&date_to=2025-01-31",
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 403

    def test_ems_usage_suggest_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/ems/usage_suggest?site_id={d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_ems_benchmark_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/ems/benchmark?site_id={d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_ems_cdc_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(
            f"/api/ems/cdc/{d['meter_b'].id}?start=2025-01-01&end=2025-01-31",
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404  # meter not found in org scope

    def test_ems_data_quality_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(f"/api/ems/data-quality/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 403

    def test_ems_weather_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(
            f"/api/ems/weather?site_id={d['site_b'].id}&date_from=2025-01-01&date_to=2025-01-31",
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 403

    def test_ems_weather_hourly_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get(
            f"/api/ems/weather_hourly?site_id={d['site_b'].id}&date_from=2025-01-01&date_to=2025-01-31",
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 403


# ════════════════════════════════════════════════════════════
# 5. Bridge module isolation
# ════════════════════════════════════════════════════════════


class TestBridgeIsolation:
    def test_bridge_coverage_scoped(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/bridge/coverage", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        data = r.json()
        prms = [item["prm"] for item in data]
        assert "PRM-BRAVO-001" not in prms

    def test_bridge_gaps_cross_org_blocked(self, client, db):
        d = _create_two_orgs(db)
        r = client.get("/api/bridge/gaps/PRM-BRAVO-001", headers=_h(d["org_a"].id))
        assert r.status_code == 404  # PRM not in org scope
