"""
PROMEOS - Tests Sprint 2: Dashboard 2min, POST sites, POST compteurs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Compteur, Organisation
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


def _seed(client):
    """Helper: create org via demo seed."""
    return client.post("/api/demo/seed").json()


# ========================================
# Dashboard 2min — GET /api/dashboard/2min
# ========================================

class TestDashboard2Min:
    """Tests pour GET /api/dashboard/2min."""

    def test_no_data_returns_has_data_false(self, client):
        r = client.get("/api/dashboard/2min")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is False
        assert data["conformite_status"] is None
        assert data["pertes_estimees_eur"] is None
        assert data["action_1"] is None

    def test_empty_completude(self, client):
        data = client.get("/api/dashboard/2min").json()
        assert data["completude"]["pct"] == 0
        assert data["completude"]["checks"]["organisation"] is False

    def test_with_data_returns_has_data_true(self, client):
        _seed(client)
        r = client.get("/api/dashboard/2min")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is True

    def test_organisation_present(self, client):
        _seed(client)
        data = client.get("/api/dashboard/2min").json()
        assert data["organisation"]["nom"] == "Demo PROMEOS"
        assert data["organisation"]["type_client"] is not None

    def test_conformite_status_present(self, client):
        _seed(client)
        data = client.get("/api/dashboard/2min").json()
        conf = data["conformite_status"]
        assert "label" in conf
        assert "color" in conf
        assert "obligations_total" in conf
        assert conf["obligations_total"] > 0

    def test_pertes_estimees_is_number(self, client):
        _seed(client)
        data = client.get("/api/dashboard/2min").json()
        assert isinstance(data["pertes_estimees_eur"], (int, float))

    def test_action_1_present(self, client):
        _seed(client)
        data = client.get("/api/dashboard/2min").json()
        a1 = data["action_1"]
        assert "texte" in a1
        assert "priorite" in a1
        assert a1["texte"]  # non-empty

    def test_completude_with_data(self, client):
        _seed(client)
        data = client.get("/api/dashboard/2min").json()
        comp = data["completude"]
        assert comp["pct"] == 100  # org + sites + compteurs from seed
        assert comp["checks"]["organisation"] is True
        assert comp["checks"]["sites"] is True
        assert comp["checks"]["compteurs"] is True

    def test_stats_present(self, client):
        _seed(client)
        data = client.get("/api/dashboard/2min").json()
        stats = data["stats"]
        assert stats["total_sites"] == 3
        assert stats["total_compteurs"] == 6


# ========================================
# POST /api/sites — Create single site
# ========================================

class TestCreateSite:
    """Tests pour POST /api/sites."""

    def test_create_site_requires_org(self, client):
        # V57: resolve_org_id returns 403 when no org resolvable
        r = client.post("/api/sites", json={"nom": "Test Site"})
        assert r.status_code in (400, 403)

    def test_create_site_ok(self, client, db_session):
        _seed(client)
        r = client.post("/api/sites", json={
            "nom": "Nouveau Bureau",
            "type": "bureau",
            "ville": "Lyon",
            "surface_m2": 2000,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["nom"] == "Nouveau Bureau"
        assert data["type"] == "bureau"
        assert data["batiment_id"] is not None
        assert data["obligations"] > 0  # 2000m2 bureau -> decret tertiaire

    def test_create_site_naf_auto(self, client):
        _seed(client)
        r = client.post("/api/sites", json={
            "nom": "Hotel Marseille",
            "naf_code": "55.10Z",
        })
        data = r.json()
        assert data["type"] == "hotel"

    def test_create_site_increments_count(self, client, db_session):
        _seed(client)
        before = db_session.query(Site).count()
        client.post("/api/sites", json={"nom": "Extra Site"})
        after = db_session.query(Site).count()
        assert after == before + 1


# ========================================
# POST /api/compteurs — Create single compteur
# ========================================

class TestCreateCompteur:
    """Tests pour POST /api/compteurs."""

    def test_create_compteur_site_not_found(self, client):
        r = client.post("/api/compteurs", json={
            "site_id": 9999,
            "type": "electricite",
        })
        assert r.status_code == 404

    def test_create_compteur_invalid_type(self, client):
        _seed(client)
        r = client.post("/api/compteurs", json={
            "site_id": 1,
            "type": "invalid_type",
        })
        assert r.status_code == 400
        assert "Type invalide" in r.json()["detail"]

    def test_create_compteur_elec(self, client, db_session):
        seed = _seed(client)
        site_id = seed["sites"][0]["id"]
        r = client.post("/api/compteurs", json={
            "site_id": site_id,
            "type": "electricite",
            "puissance_souscrite_kw": 150,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "electricite"
        assert data["site_id"] == site_id
        assert data["puissance_souscrite_kw"] == 150

    def test_create_compteur_gaz(self, client, db_session):
        seed = _seed(client)
        site_id = seed["sites"][0]["id"]
        r = client.post("/api/compteurs", json={
            "site_id": site_id,
            "type": "gaz",
        })
        assert r.status_code == 200
        assert r.json()["type"] == "gaz"

    def test_create_compteur_auto_serie(self, client, db_session):
        seed = _seed(client)
        site_id = seed["sites"][0]["id"]
        r = client.post("/api/compteurs", json={
            "site_id": site_id,
            "type": "eau",
        })
        data = r.json()
        assert data["numero_serie"]  # auto-generated

    def test_create_compteur_custom_serie(self, client, db_session):
        seed = _seed(client)
        site_id = seed["sites"][0]["id"]
        r = client.post("/api/compteurs", json={
            "site_id": site_id,
            "type": "electricite",
            "numero_serie": "PRM-123456",
        })
        data = r.json()
        assert data["numero_serie"] == "PRM-123456"
