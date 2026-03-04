"""
PROMEOS — Tests KPIs Patrimoine (PR1 Phase 3)
Tests for: GET /api/patrimoine/kpis server-side aggregation.
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
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    TypeSite,
    StatutConformite,
)
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


def _create_org(db):
    org = Organisation(nom="KPI Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ KPI", siren="111222333")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF KPI")
    db.add(pf)
    db.flush()
    return org, ej, pf


def _create_site(db, pf, nom="Site KPI", statut=StatutConformite.CONFORME, risque=0.0, anomalie=False, surface=1500.0):
    site = Site(
        nom=nom,
        type=TypeSite.BUREAU,
        adresse="1 rue Test",
        code_postal="75001",
        ville="Paris",
        surface_m2=surface,
        portefeuille_id=pf.id,
        actif=True,
        statut_decret_tertiaire=statut,
        risque_financier_euro=risque,
        anomalie_facture=anomalie,
    )
    db.add(site)
    db.flush()
    return site


# ========================================
# Tests
# ========================================


class TestPatrimoineKpis:
    def test_kpis_empty_org(self, client, db):
        """KPIs for an org with zero sites returns all zeros."""
        _create_org(db)
        db.commit()

        resp = client.get("/api/patrimoine/kpis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["conformes"] == 0
        assert data["aRisque"] == 0
        assert data["nonConformes"] == 0
        assert data["totalRisque"] == 0
        assert data["totalSurface"] == 0
        assert data["totalAnomalies"] == 0

    def test_kpis_with_sites(self, client, db):
        """KPIs correctly aggregate conformite, risque, anomalies."""
        org, _, pf = _create_org(db)

        _create_site(db, pf, "Conforme 1", StatutConformite.CONFORME, 0, False, 1000)
        _create_site(db, pf, "Conforme 2", StatutConformite.CONFORME, 500, False, 2000)
        _create_site(db, pf, "A Risque 1", StatutConformite.A_RISQUE, 3000, True, 1500)
        _create_site(db, pf, "Non Conf 1", StatutConformite.NON_CONFORME, 10000, True, 1500)
        db.commit()

        resp = client.get("/api/patrimoine/kpis")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 4
        assert data["conformes"] == 2
        assert data["aRisque"] == 1
        assert data["nonConformes"] == 1
        assert data["totalRisque"] == 13500.0
        assert data["totalAnomalies"] == 2
        assert data["totalSurface"] == 6000.0

    def test_kpis_site_id_filter(self, client, db):
        """site_id query param filters KPIs to a single site."""
        org, _, pf = _create_org(db)

        _create_site(db, pf, "Site A", StatutConformite.CONFORME, 1000, False, 1000)
        site_b = _create_site(db, pf, "Site B", StatutConformite.A_RISQUE, 5000, True, 2000)
        db.commit()

        resp = client.get(f"/api/patrimoine/kpis?site_id={site_b.id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 1
        assert data["conformes"] == 0
        assert data["aRisque"] == 1
        assert data["totalRisque"] == 5000.0
        assert data["totalAnomalies"] == 1
        assert data["totalSurface"] == 2000.0

    def test_kpis_excludes_inactive_sites(self, client, db):
        """Archived (actif=False) sites are excluded from KPIs."""
        org, _, pf = _create_org(db)

        _create_site(db, pf, "Active", StatutConformite.CONFORME, 1000, False, 1000)
        inactive = _create_site(db, pf, "Inactive", StatutConformite.A_RISQUE, 9000, True, 2000)
        inactive.actif = False
        db.commit()

        resp = client.get("/api/patrimoine/kpis")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 1
        assert data["conformes"] == 1
        assert data["aRisque"] == 0
        assert data["totalRisque"] == 1000.0
