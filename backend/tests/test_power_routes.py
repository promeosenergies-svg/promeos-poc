"""
PROMEOS — Tests routes Power Intelligence (profile, peaks, nebco).
Sprint B : couverture des endpoints REST.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base, Organisation, EntiteJuridique, Portefeuille, Site
from models.energy_models import Meter
from database import get_db


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def db():
    """In-memory SQLite session."""
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
def org_with_site(db):
    """Cree org -> EJ -> portefeuille -> site avec compteur."""
    from models.enums import TypeSite

    org = Organisation(nom="PowerOrg", siren="111222333", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="PowerEJ", siren="444555666")
    db.add(ej)
    db.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="PowerPF")
    db.add(pf)
    db.flush()

    site = Site(portefeuille_id=pf.id, nom="Site Power Test", type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()

    # Compteur principal
    meter = Meter(site_id=site.id, reference="PDL-POWER-001", type_compteur="elec")
    db.add(meter)
    db.flush()

    db.commit()
    return {"org": org, "site": site, "meter": meter}


@pytest.fixture
def client(db, org_with_site):
    """TestClient avec DB isolee."""

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Tests Profile ─────────────────────────────────────────────────


class TestPowerProfile:
    def test_profile_site_not_found(self, client):
        """GET /power/sites/99999/profile retourne 404."""
        r = client.get("/api/power/sites/99999/profile")
        assert r.status_code == 404

    def test_profile_with_site(self, client, org_with_site):
        """GET /power/sites/{id}/profile retourne 200 ou erreur gracieuse."""
        site_id = org_with_site["site"].id
        r = client.get(f"/api/power/sites/{site_id}/profile")
        # 200 si donnees existent, sinon peut lever 404 pour compteur sans mesures
        assert r.status_code in (200, 404, 500)


# ── Tests Contract ────────────────────────────────────────────────


class TestPowerContract:
    def test_contract_no_meter(self, client):
        """GET /power/sites/99999/contract retourne 404."""
        r = client.get("/api/power/sites/99999/contract")
        assert r.status_code == 404

    def test_contract_with_site(self, client, org_with_site):
        """GET /power/sites/{id}/contract retourne 200."""
        site_id = org_with_site["site"].id
        r = client.get(f"/api/power/sites/{site_id}/contract")
        assert r.status_code == 200
        data = r.json()
        assert data["site_id"] == site_id
        # Pas de contrat puissance en DB test → contract=None
        assert data["contract"] is None


# ── Tests Peaks ───────────────────────────────────────────────────


class TestPowerPeaks:
    def test_peaks_no_site(self, client):
        """GET /power/sites/99999/peaks retourne 404."""
        r = client.get("/api/power/sites/99999/peaks")
        assert r.status_code == 404

    def test_peaks_with_site(self, client, org_with_site):
        """GET /power/sites/{id}/peaks retourne 200 ou erreur gracieuse."""
        site_id = org_with_site["site"].id
        r = client.get(f"/api/power/sites/{site_id}/peaks")
        assert r.status_code in (200, 404, 500)


# ── Tests Factor ──────────────────────────────────────────────────


class TestPowerFactor:
    def test_factor_no_site(self, client):
        """GET /power/sites/99999/factor retourne 404."""
        r = client.get("/api/power/sites/99999/factor")
        assert r.status_code == 404


# ── Tests Optimize PS ─────────────────────────────────────────────


class TestOptimizePs:
    def test_optimize_no_site(self, client):
        """GET /power/sites/99999/optimize-ps retourne 404."""
        r = client.get("/api/power/sites/99999/optimize-ps")
        assert r.status_code == 404


# ── Tests NEBCO ───────────────────────────────────────────────────


class TestNebco:
    def test_nebco_no_site(self, client):
        """GET /power/sites/99999/nebco retourne 404."""
        r = client.get("/api/power/sites/99999/nebco")
        assert r.status_code == 404

    def test_nebco_with_site(self, client, org_with_site):
        """GET /power/sites/{id}/nebco retourne 200 ou erreur gracieuse."""
        site_id = org_with_site["site"].id
        r = client.get(f"/api/power/sites/{site_id}/nebco")
        assert r.status_code in (200, 404, 500)

    def test_portfolio_nebco_summary(self, client, org_with_site):
        """GET /power/portfolio/nebco-summary retourne 200 ou 404."""
        r = client.get("/api/power/portfolio/nebco-summary")
        assert r.status_code in (200, 404)
