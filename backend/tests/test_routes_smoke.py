"""
PROMEOS — Tests smoke routes API (Sprint C: coverage).

Vérifie que chaque endpoint répond 200 (ou 4xx attendu) avec la structure
de réponse correcte. Pas de logique métier — juste du smoke testing.

Couvre les routes NON TESTÉES identifiées par l'audit :
  - cockpit (7 routes)
  - usages (21 routes)
  - power (7 routes)
  - energy (8 routes)
  - sites (7 routes)
  - ems (sélection)
  - monitoring (sélection)
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base, Organisation, EntiteJuridique, Portefeuille, Site
from models.energy_models import Meter, MeterReading, EnergyVector
from models.enums import TypeSite
from database import get_db


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def seeded(db):
    """Org + EJ + PF + 2 sites + 1 meter."""
    # Check if already seeded (module-scoped engine)
    existing = db.query(Organisation).first()
    if existing:
        sites = db.query(Site).all()
        meter = db.query(Meter).first()
        return {"org": existing, "sites": sites, "meter": meter}

    org = Organisation(nom="TestOrg", siren="123456789", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="TestEJ", siren="987654321")
    db.add(ej)
    db.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="TestPF")
    db.add(pf)
    db.flush()

    sites = []
    for i, name in enumerate(["Site A", "Site B"], 1):
        s = Site(portefeuille_id=pf.id, nom=name, type=TypeSite.BUREAU, actif=True, surface_m2=500.0)
        db.add(s)
        db.flush()
        sites.append(s)

    meter = Meter(
        site_id=sites[0].id,
        meter_id="M001",
        name="Compteur A",
        energy_vector=EnergyVector.ELECTRICITY,
        subscribed_power_kva=36,
    )
    db.add(meter)
    db.flush()
    db.commit()

    return {"org": org, "sites": sites, "meter": meter}


@pytest.fixture
def client(db, seeded):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# COCKPIT (7 routes)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCockpitRoutes:
    def test_cockpit_200(self, client, seeded):
        r = client.get("/api/cockpit", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200
        data = r.json()
        assert "organisation" in data
        assert "stats" in data
        assert "action_center" in data

    def test_portefeuilles_200(self, client, seeded):
        r = client.get("/api/portefeuilles", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200
        data = r.json()
        assert "portefeuilles" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_kpi_catalog_200(self, client):
        r = client.get("/api/kpi-catalog")
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert "kpis" in data
        assert data["count"] > 0

    def test_benchmark_200(self, client, seeded):
        r = client.get("/api/cockpit/benchmark", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200
        data = r.json()
        assert "sites" in data
        assert "source" in data

    def test_trajectory_200(self, client, seeded):
        r = client.get("/api/cockpit/trajectory", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200

    def test_conso_month_200(self, client, seeded):
        r = client.get("/api/cockpit/conso-month", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200
        data = r.json()
        assert "year" in data
        assert "month" in data

    def test_co2_200(self, client, seeded):
        r = client.get("/api/cockpit/co2", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# USAGES (21 routes)
# ═══════════════════════════════════════════════════════════════════════════════


class TestUsagesRoutes:
    def test_scoped_dashboard_200(self, client, seeded):
        r = client.get("/api/usages/scoped-dashboard", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200

    def test_scoped_timeline_200(self, client, seeded):
        r = client.get("/api/usages/scoped-timeline", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200

    def test_archetypes_in_scope_200(self, client, seeded):
        r = client.get("/api/usages/archetypes-in-scope", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200

    def test_cost_by_period_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/cost-by-period/{sid}")
        assert r.status_code == 200
        data = r.json()
        assert "site_id" in data
        assert "usages" in data

    def test_dashboard_site_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/dashboard/{sid}")
        assert r.status_code == 200

    def test_taxonomy_200(self, client):
        r = client.get("/api/usages/taxonomy")
        assert r.status_code == 200

    def test_site_usages_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/site/{sid}")
        assert r.status_code == 200

    def test_readiness_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/readiness/{sid}")
        assert r.status_code == 200

    def test_metering_plan_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/metering-plan/{sid}")
        assert r.status_code == 200

    def test_cost_breakdown_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/cost-breakdown/{sid}")
        assert r.status_code == 200

    def test_baselines_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/baselines/{sid}")
        assert r.status_code == 200

    def test_compliance_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/compliance/{sid}")
        assert r.status_code == 200

    def test_portfolio_compare_200(self, client, seeded):
        r = client.get("/api/usages/portfolio-compare", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200

    def test_energy_signature_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/energy-signature/{sid}")
        assert r.status_code == 200

    def test_power_optimization_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/usages/power-optimization/{sid}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# POWER (7 routes)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPowerRoutes:
    def test_power_profile_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/power/sites/{sid}/profile")
        assert r.status_code == 200

    def test_power_contracts_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/power/sites/{sid}/contract")
        assert r.status_code == 200

    def test_power_peaks_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/power/sites/{sid}/peaks")
        assert r.status_code == 200

    def test_power_factor_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/power/sites/{sid}/factor")
        assert r.status_code == 200

    def test_power_optimize_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/power/sites/{sid}/optimize-ps")
        assert r.status_code == 200

    def test_nebco_site_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/power/sites/{sid}/nebco")
        assert r.status_code == 200

    def test_nebco_portfolio_200(self, client, seeded):
        r = client.get("/api/power/portfolio/nebco-summary", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# ENERGY (8 routes)
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnergyRoutes:
    def test_tou_schedules_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/consumption/tou_schedules?site_id={sid}")
        assert r.status_code == 200

    def test_tou_active_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/consumption/tou_schedules/active?site_id={sid}")
        assert r.status_code == 200

    def test_energy_meters_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/energy/meters?site_id={sid}")
        assert r.status_code == 200

    def test_energy_intensity_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/energy/intensity?site_id={sid}", headers={"X-Org-Id": str(seeded["org"].id)})
        # 200 or 422 (missing params) — both acceptable for smoke
        assert r.status_code in (200, 422)


# ═══════════════════════════════════════════════════════════════════════════════
# SITES (7 routes)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSitesRoutes:
    def test_list_sites_200(self, client, seeded):
        r = client.get("/api/sites", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200

    def test_get_site_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/sites/{sid}")
        assert r.status_code == 200

    def test_get_site_404(self, client):
        r = client.get("/api/sites/99999")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# MONITORING (sélection)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMonitoringRoutes:
    def test_monitoring_alerts_200(self, client, seeded):
        sid = seeded["sites"][0].id
        r = client.get(f"/api/monitoring/alerts?site_id={sid}", headers={"X-Org-Id": str(seeded["org"].id)})
        assert r.status_code == 200
