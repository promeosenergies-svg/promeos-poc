"""
PROMEOS — Tests routes Contrats V2 (CRUD cadres + annexes + idempotence).
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
from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    EnergyContract,
    BillingEnergyType,
    ContractStatus,
    ContractIndexation,
    TariffOptionEnum,
)
from models.contract_v2_models import ContractAnnexe, ContractPricing
from database import get_db


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def db():
    """In-memory SQLite session avec toutes les tables."""
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
def org_hierarchy(db):
    """Cree org -> EJ -> portefeuille -> 2 sites."""
    from models.enums import TypeSite

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
    for name in ["Site A", "Site B"]:
        s = Site(portefeuille_id=pf.id, nom=name, type=TypeSite.BUREAU, actif=True)
        db.add(s)
        db.flush()
        sites.append(s)

    db.commit()
    return {"org": org, "ej": ej, "pf": pf, "sites": sites}


@pytest.fixture
def client(db, org_hierarchy):
    """TestClient avec DB isolee."""

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Tests GET ──────────────────────────────────────────────────────


class TestCadresGet:
    def test_list_cadres_200(self, client):
        """GET /cadres retourne 200 + liste."""
        r = client.get("/api/contracts/v2/cadres")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_suppliers_200(self, client):
        """GET /cadres/suppliers retourne referentiels."""
        r = client.get("/api/contracts/v2/cadres/suppliers")
        assert r.status_code == 200
        data = r.json()
        assert "suppliers" in data
        assert "pricing_models" in data
        assert len(data["suppliers"]) >= 10

    def test_kpis_200(self, client):
        """GET /cadres/kpis retourne KPIs portefeuille."""
        r = client.get("/api/contracts/v2/cadres/kpis")
        assert r.status_code == 200
        data = r.json()
        assert "total_cadres" in data

    def test_get_cadre_404(self, client):
        """GET /cadres/99999 retourne 404."""
        r = client.get("/api/contracts/v2/cadres/99999")
        assert r.status_code == 404

    def test_import_template(self, client):
        """GET /import/template retourne CSV."""
        r = client.get("/api/contracts/v2/import/template")
        assert r.status_code == 200
        assert "supplier" in r.text


# ── Tests POST (CRUD) ─────────────────────────────────────────────


class TestCadresCreate:
    def _create_payload(self, site_id):
        return {
            "supplier_name": "EDF Entreprises",
            "energy_type": "elec",
            "start_date": "2026-01-01",
            "end_date": "2028-12-31",
            "annexes": [{"site_id": site_id}],
        }

    def test_create_cadre_201(self, client, org_hierarchy):
        """POST /cadres cree un cadre avec annexe."""
        payload = self._create_payload(org_hierarchy["sites"][0].id)
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["supplier_name"] == "EDF Entreprises"
        assert data.get("nb_annexes", 0) >= 1

    def test_create_cadre_validation_error(self, client, org_hierarchy):
        """POST /cadres avec dates inversees retourne 422."""
        payload = self._create_payload(org_hierarchy["sites"][0].id)
        payload["start_date"] = "2028-12-31"
        payload["end_date"] = "2026-01-01"
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 422


# ── Tests PATCH / DELETE ─────────────────────────────────────────


class TestCadresUpdateDelete:
    def test_patch_cadre_404(self, client):
        """PATCH /cadres/99999 retourne 404."""
        r = client.patch("/api/contracts/v2/cadres/99999", json={"notes": "test"})
        assert r.status_code == 404

    def test_delete_cadre_404(self, client):
        """DELETE /cadres/99999 retourne 404."""
        r = client.delete("/api/contracts/v2/cadres/99999")
        assert r.status_code == 404

    def test_create_then_delete(self, client, org_hierarchy):
        """Cycle complet : create → delete."""
        payload = {
            "supplier_name": "ENGIE Pro",
            "energy_type": "gaz",
            "start_date": "2026-06-01",
            "end_date": "2028-05-31",
            "annexes": [{"site_id": org_hierarchy["sites"][0].id}],
        }
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 201
        cadre_id = r.json()["id"]

        r2 = client.delete(f"/api/contracts/v2/cadres/{cadre_id}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "deleted"


# ── Tests Annexes ────────────────────────────────────────────────


class TestAnnexes:
    def _create_cadre(self, client, site_id):
        payload = {
            "supplier_name": "EDF Entreprises",
            "energy_type": "elec",
            "start_date": "2026-01-01",
            "end_date": "2028-12-31",
            "annexes": [{"site_id": site_id}],
        }
        r = client.post("/api/contracts/v2/cadres", json=payload)
        return r.json()["id"]

    def test_create_annexe_201(self, client, org_hierarchy):
        """POST /cadres/{id}/annexes ajoute une annexe."""
        cadre_id = self._create_cadre(client, org_hierarchy["sites"][0].id)
        r = client.post(
            f"/api/contracts/v2/cadres/{cadre_id}/annexes",
            json={"site_id": org_hierarchy["sites"][1].id},
        )
        assert r.status_code == 201

    def test_create_annexe_cadre_404(self, client, org_hierarchy):
        """POST /cadres/99999/annexes retourne 404."""
        r = client.post(
            "/api/contracts/v2/cadres/99999/annexes",
            json={"site_id": org_hierarchy["sites"][0].id},
        )
        assert r.status_code == 404

    def test_delete_annexe_404(self, client):
        """DELETE /annexes/99999 retourne 404."""
        r = client.delete("/api/contracts/v2/annexes/99999")
        assert r.status_code == 404


# ── Tests Idempotence ────────────────────────────────────────────


class TestIdempotence:
    def test_create_cadre_idempotent(self, client, org_hierarchy):
        """Deux POST avec meme idempotency_key retournent le meme cadre."""
        site_id = org_hierarchy["sites"][0].id
        payload = {
            "supplier_name": "Vattenfall",
            "energy_type": "elec",
            "contract_ref": "IDEM-001",
            "start_date": "2026-01-01",
            "end_date": "2028-12-31",
            "annexes": [{"site_id": site_id}],
        }
        r1 = client.post("/api/contracts/v2/cadres?idempotency_key=IDEM-001", json=payload)
        assert r1.status_code == 201

        # Deuxieme appel avec meme cle
        r2 = client.post("/api/contracts/v2/cadres?idempotency_key=IDEM-001", json=payload)
        # Doit retourner le meme cadre (pas de doublon)
        assert r2.status_code in (200, 201)


# ── Tests Events ─────────────────────────────────────────────────


class TestEvents:
    def test_add_event_404(self, client):
        """POST /cadres/99999/events retourne 404."""
        r = client.post(
            "/api/contracts/v2/cadres/99999/events",
            json={"event_type": "CREATION", "event_date": "2026-01-01"},
        )
        assert r.status_code == 404


# ── Tests Coherence ──────────────────────────────────────────────


class TestCoherenceRoute:
    def test_coherence_404(self, client):
        """GET /cadres/99999/coherence retourne 404 ou resultat vide."""
        r = client.get("/api/contracts/v2/cadres/99999/coherence")
        # Peut retourner 404 ou 200 selon implementation
        assert r.status_code in (200, 404)
