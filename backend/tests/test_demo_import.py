"""
PROMEOS - Tests Sprint 1: Demo Seed + Import CSV standalone
Tests: /api/demo/seed, /api/demo/status, /api/import/sites, /api/import/template
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Compteur, Organisation, Portefeuille, Batiment, Obligation
from database import get_db
from main import app


@pytest.fixture
def db_session():
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
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ========================================
# Demo Seed — POST /api/demo/seed
# ========================================


class TestDemoSeed:
    """Tests pour l'endpoint POST /api/demo/seed."""

    def test_seed_creates_org(self, client, db_session):
        r = client.post("/api/demo/seed")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["organisation_id"] is not None
        org = db_session.query(Organisation).first()
        assert org.nom == "Demo PROMEOS"

    def test_seed_creates_2_entites_juridiques(self, client):
        data = client.post("/api/demo/seed").json()
        assert data["entites_juridiques"] == 2

    def test_seed_creates_1_portefeuille(self, client):
        data = client.post("/api/demo/seed").json()
        assert data["portefeuilles"] == 1

    def test_seed_creates_3_sites(self, client, db_session):
        data = client.post("/api/demo/seed").json()
        assert data["sites_created"] == 3
        sites = db_session.query(Site).all()
        assert len(sites) == 3
        noms = {s.nom for s in sites}
        assert "Hypermarche Montreuil" in noms
        assert "Bureau Haussmann" in noms
        assert "Entrepot Rungis" in noms

    def test_seed_creates_6_compteurs(self, client, db_session):
        data = client.post("/api/demo/seed").json()
        assert data["compteurs_created"] == 6
        compteurs = db_session.query(Compteur).all()
        assert len(compteurs) == 6

    def test_seed_provisions_batiments(self, client, db_session):
        client.post("/api/demo/seed")
        batiments = db_session.query(Batiment).all()
        assert len(batiments) == 3  # 1 par site

    def test_seed_provisions_obligations(self, client, db_session):
        client.post("/api/demo/seed")
        obligations = db_session.query(Obligation).all()
        assert len(obligations) > 0  # Au moins decret tertiaire pour les sites > 1000m2

    def test_seed_returns_site_details(self, client):
        data = client.post("/api/demo/seed").json()
        assert len(data["sites"]) == 3
        for site in data["sites"]:
            assert "id" in site
            assert "nom" in site
            assert "type" in site

    def test_seed_enables_demo_enabled(self, client):
        client.post("/api/demo/seed")
        r = client.get("/api/demo/status")
        data = r.json()
        assert data["demo_enabled"] is True

    def test_seed_409_if_org_exists(self, client):
        # Premier seed: OK
        r1 = client.post("/api/demo/seed")
        assert r1.status_code == 200
        # Deuxieme seed: 409
        r2 = client.post("/api/demo/seed")
        assert r2.status_code == 409
        body = r2.json()
        assert "existe deja" in body.get("detail", body.get("message", ""))


# ========================================
# Demo Status — GET /api/demo/status
# ========================================


class TestDemoStatus:
    """Tests pour enable/disable/status demo."""

    def test_enable_demo(self, client):
        r = client.post("/api/demo/enable")
        assert r.status_code == 200
        assert r.json()["demo_enabled"] is True

    def test_disable_demo(self, client):
        client.post("/api/demo/enable")
        r = client.post("/api/demo/disable")
        assert r.status_code == 200
        assert r.json()["demo_enabled"] is False

    def test_status_returns_demo_enabled(self, client):
        r = client.get("/api/demo/status")
        assert r.status_code == 200
        assert "demo_enabled" in r.json()


# ========================================
# Import Template — GET /api/import/template
# ========================================


class TestImportTemplate:
    """Tests pour GET /api/import/template."""

    def test_template_returns_columns(self, client):
        r = client.get("/api/import/template")
        assert r.status_code == 200
        data = r.json()
        assert "columns" in data
        assert "nom" in data["columns"]
        assert "surface_m2" in data["columns"]
        assert "naf_code" in data["columns"]

    def test_template_has_examples(self, client):
        data = client.get("/api/import/template").json()
        assert "example_rows" in data
        assert len(data["example_rows"]) >= 1

    def test_template_has_notes(self, client):
        data = client.get("/api/import/template").json()
        assert "notes" in data
        assert len(data["notes"]) >= 1


# ========================================
# Import CSV standalone — POST /api/import/sites
# ========================================


class TestImportCSV:
    """Tests pour POST /api/import/sites (standalone)."""

    def _seed_org(self, client):
        """Helper: creer une org via demo seed."""
        client.post("/api/demo/seed")

    def test_import_requires_org(self, client):
        csv = "nom,type\nTest,bureau\n"
        r = client.post(
            "/api/import/sites",
            files={"file": ("sites.csv", io.BytesIO(csv.encode()), "text/csv")},
        )
        # V57: resolve_org_id returns 403 when no org resolvable
        assert r.status_code in (400, 403)

    def test_import_basic_csv(self, client, db_session):
        self._seed_org(client)
        csv_content = (
            "nom,adresse,code_postal,ville,surface_m2,type,naf_code\n"
            "Nouveau Bureau,1 rue Neuve,75001,Paris,900,bureau,\n"
            "Nouveau Hotel,2 av Mer,06000,Nice,600,,55.10Z\n"
        )
        r = client.post(
            "/api/import/sites",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["imported"] == 2
        assert data["errors"] == 0

    def test_import_naf_auto_classification(self, client):
        self._seed_org(client)
        csv_content = "nom,adresse,code_postal,ville,surface_m2,type,naf_code\nMairie Test,,29200,Brest,2000,,84.11Z\n"
        r = client.post(
            "/api/import/sites",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        data = r.json()
        assert data["imported"] == 1
        assert data["sites"][0]["type"] == "collectivite"

    def test_import_semicolon_delimiter(self, client):
        self._seed_org(client)
        csv_content = (
            "nom;adresse;code_postal;ville;surface_m2;type;naf_code\n"
            "Bureau Marseille;La Canebiere;13001;Marseille;1100;bureau;\n"
        )
        r = client.post(
            "/api/import/sites",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        data = r.json()
        assert data["imported"] == 1

    def test_import_with_errors(self, client):
        self._seed_org(client)
        csv_content = (
            "nom,adresse,code_postal,ville,surface_m2,type,naf_code\n"
            ",rue vide,,Paris,1000,bureau,\n"
            "Bon Site,rue OK,75001,Paris,500,bureau,\n"
        )
        r = client.post(
            "/api/import/sites",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        data = r.json()
        assert data["imported"] == 1
        assert data["errors"] == 1
        assert data["error_details"][0]["row"] == 2

    def test_import_provisions_batiments(self, client, db_session):
        self._seed_org(client)
        initial_bat = db_session.query(Batiment).count()
        csv_content = (
            "nom,adresse,code_postal,ville,surface_m2,type,naf_code\nImport Bureau,rue X,75001,Paris,2000,bureau,\n"
        )
        client.post(
            "/api/import/sites",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        new_bat = db_session.query(Batiment).count()
        assert new_bat == initial_bat + 1

    def test_import_sites_added_to_existing_portefeuille(self, client, db_session):
        self._seed_org(client)
        pf = db_session.query(Portefeuille).first()
        initial_count = db_session.query(Site).filter_by(portefeuille_id=pf.id).count()
        csv_content = "nom,type\nExtra Site,bureau\n"
        client.post(
            "/api/import/sites",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        new_count = db_session.query(Site).filter_by(portefeuille_id=pf.id).count()
        assert new_count == initial_count + 1

    def test_import_utf8_bom(self, client):
        self._seed_org(client)
        csv_content = "nom,type\nSite BOM,bureau\n"
        # Encode with BOM (utf-8-sig adds \xef\xbb\xbf prefix)
        r = client.post(
            "/api/import/sites",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode("utf-8-sig")), "text/csv")},
        )
        data = r.json()
        assert data["imported"] == 1
        assert data["sites"][0]["nom"] == "Site BOM"
