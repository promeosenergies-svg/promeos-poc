"""
PROMEOS — Tests Export CSV + Pagination (PR3 Phase 3)
Tests for: GET /api/patrimoine/sites/export.csv, enhanced list_sites pagination.
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
    org = Organisation(nom="Export Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ Export", siren="222333444")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Export")
    db.add(pf)
    db.flush()
    return org, ej, pf


def _seed_sites(db, pf, count=10):
    """Create `count` sites in the given portfolio."""
    sites = []
    for i in range(count):
        site = Site(
            nom=f"Site {i + 1}",
            type=TypeSite.BUREAU,
            adresse=f"{i + 1} rue Test",
            code_postal="75001",
            ville="Paris" if i % 2 == 0 else "Lyon",
            surface_m2=1000 + i * 100,
            portefeuille_id=pf.id,
            actif=True,
            statut_decret_tertiaire=StatutConformite.CONFORME,
            risque_financier_euro=i * 500.0,
            anomalie_facture=(i % 3 == 0),
        )
        db.add(site)
        sites.append(site)
    db.flush()
    return sites


# ========================================
# CSV Export Tests
# ========================================


class TestExportCSV:
    def test_export_csv_200(self, client, db):
        """CSV export returns 200 with correct content-type."""
        org, _, pf = _create_org(db)
        _seed_sites(db, pf, count=5)
        db.commit()

        resp = client.get("/api/patrimoine/sites/export.csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        assert "patrimoine_sites_" in resp.headers["content-disposition"]

    def test_export_csv_bom(self, client, db):
        """CSV starts with UTF-8 BOM for French Excel."""
        org, _, pf = _create_org(db)
        _seed_sites(db, pf, count=3)
        db.commit()

        resp = client.get("/api/patrimoine/sites/export.csv")
        assert resp.content[:3] == b"\xef\xbb\xbf"  # UTF-8 BOM

    def test_export_csv_columns(self, client, db):
        """CSV header row contains expected columns."""
        org, _, pf = _create_org(db)
        _seed_sites(db, pf, count=2)
        db.commit()

        resp = client.get("/api/patrimoine/sites/export.csv")
        text = resp.text.lstrip("\ufeff")
        first_line = text.split("\n")[0]
        assert "nom" in first_line
        assert "ville" in first_line
        assert "surface_m2" in first_line
        assert "risque_financier_euro" in first_line
        assert "statut_conformite" in first_line


# ========================================
# Pagination Tests
# ========================================


class TestPagination:
    def test_page_param(self, client, db):
        """GET /api/patrimoine/sites?page=1&page_size=5 returns paginated results."""
        org, _, pf = _create_org(db)
        _seed_sites(db, pf, count=10)
        db.commit()

        resp = client.get("/api/patrimoine/sites?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10
        assert len(data["sites"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_page_boundary(self, client, db):
        """Page 3 of 10 items with page_size=5 returns empty."""
        org, _, pf = _create_org(db)
        _seed_sites(db, pf, count=10)
        db.commit()

        resp = client.get("/api/patrimoine/sites?page=3&page_size=5")
        data = resp.json()
        assert len(data["sites"]) == 0
        assert data["total"] == 10


# ========================================
# Database Config Tests
# ========================================


class TestDatabaseConfig:
    def test_sqlite_url_default(self):
        """Default DATABASE_URL uses SQLite."""
        from database.connection import DATABASE_URL

        assert "sqlite" in DATABASE_URL
