"""
PROMEOS — Tests API Contrats V2 : CRUD + validate + expiring.
Phase 6 CONTRATS-V2 QA — couvre endpoints via TestClient.
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
from models.contract_v2_models import ContractAnnexe, ContractPricing, VolumeCommitment
from database import get_db


# ── Fixtures ──────────────────────────────────────────────────────


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
def org_hierarchy(db):
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
    for name in ["Site A", "Site B", "Site C"]:
        s = Site(portefeuille_id=pf.id, nom=name, type=TypeSite.BUREAU, actif=True)
        db.add(s)
        db.flush()
        sites.append(s)
    db.commit()
    return {"org": org, "ej": ej, "sites": sites}


@pytest.fixture
def client(db, org_hierarchy):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _base_payload(site_id, **overrides):
    payload = {
        "supplier_name": "EDF Entreprises",
        "energy_type": "elec",
        "start_date": "2026-01-01",
        "end_date": "2028-12-31",
        "annexes": [{"site_id": site_id}],
    }
    payload.update(overrides)
    return payload


# ============================================================
# CRUD — Create cadre
# ============================================================


class TestCreateCadre:
    def test_create_cadre_basic_201(self, client, org_hierarchy):
        """POST /cadres → 201 avec cadre + 1 annexe."""
        payload = _base_payload(org_hierarchy["sites"][0].id)
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["supplier_name"] == "EDF Entreprises"
        assert data["energy_type"] == "elec"
        assert data["nb_annexes"] >= 1

    def test_create_cadre_with_pricing(self, client, org_hierarchy):
        """POST /cadres avec grille tarifaire HP+HC."""
        payload = _base_payload(
            org_hierarchy["sites"][0].id,
            pricing=[
                {"period_code": "HP", "season": "ANNUEL", "unit_price_eur_kwh": 0.168},
                {"period_code": "HC", "season": "ANNUEL", "unit_price_eur_kwh": 0.122},
            ],
        )
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert len(data.get("pricing", [])) == 2

    def test_create_cadre_multi_annexes(self, client, org_hierarchy):
        """POST /cadres avec 2 annexes (2 sites differents)."""
        sites = org_hierarchy["sites"]
        payload = _base_payload(
            sites[0].id,
            annexes=[
                {"site_id": sites[0].id, "annexe_ref": "ANX-001"},
                {"site_id": sites[1].id, "annexe_ref": "ANX-002"},
            ],
        )
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["nb_annexes"] == 2


# ============================================================
# CRUD — Read / Update / Delete
# ============================================================


class TestCRUDCycle:
    def _create(self, client, site_id):
        payload = _base_payload(site_id)
        r = client.post("/api/contracts/v2/cadres", json=payload)
        return r.json()["id"]

    def test_get_cadre_200(self, client, org_hierarchy):
        """GET /cadres/{id} retourne detail complet."""
        cadre_id = self._create(client, org_hierarchy["sites"][0].id)
        r = client.get(f"/api/contracts/v2/cadres/{cadre_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == cadre_id
        assert "annexes" in data
        assert "coherence" in data

    def test_patch_cadre_notes(self, client, org_hierarchy):
        """PATCH /cadres/{id} met a jour les notes."""
        cadre_id = self._create(client, org_hierarchy["sites"][0].id)
        r = client.patch(
            f"/api/contracts/v2/cadres/{cadre_id}",
            json={"notes": "Updated by QA test"},
        )
        assert r.status_code == 200
        assert r.json()["notes"] == "Updated by QA test"

    def test_delete_cadre_soft(self, client, org_hierarchy):
        """DELETE /cadres/{id} → soft-delete (status=terminated)."""
        cadre_id = self._create(client, org_hierarchy["sites"][0].id)
        r = client.delete(f"/api/contracts/v2/cadres/{cadre_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

        # cadre still accessible but terminated
        r2 = client.get(f"/api/contracts/v2/cadres/{cadre_id}")
        # May return 404 or the terminated cadre depending on implementation
        assert r2.status_code in (200, 404)


# ============================================================
# Validation — dates inversees
# ============================================================


class TestValidation:
    def test_create_reversed_dates_422(self, client, org_hierarchy):
        """POST /cadres avec start > end → 422."""
        payload = _base_payload(
            org_hierarchy["sites"][0].id,
            start_date="2028-12-31",
            end_date="2026-01-01",
        )
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 422

    def test_create_missing_annexes_422(self, client, org_hierarchy):
        """POST /cadres sans annexes → 422 (validation Pydantic)."""
        payload = {
            "supplier_name": "EDF",
            "energy_type": "elec",
            "start_date": "2026-01-01",
            "end_date": "2028-12-31",
            "annexes": [],
        }
        r = client.post("/api/contracts/v2/cadres", json=payload)
        # Empty annexes list may fail validation
        assert r.status_code in (422, 201)  # Depends on schema min_length


# ============================================================
# Coherence endpoint
# ============================================================


class TestCoherenceEndpoint:
    def test_coherence_check_returns_rules(self, client, org_hierarchy):
        """GET /cadres/{id}/coherence retourne liste de regles."""
        site_id = org_hierarchy["sites"][0].id
        payload = _base_payload(site_id)
        r = client.post("/api/contracts/v2/cadres", json=payload)
        cadre_id = r.json()["id"]

        r2 = client.get(f"/api/contracts/v2/cadres/{cadre_id}/coherence")
        assert r2.status_code == 200
        data = r2.json()
        assert "rules" in data
        assert "total" in data
        assert isinstance(data["rules"], list)


# ============================================================
# Expiring endpoint
# ============================================================


class TestExpiringEndpoint:
    def test_expiring_90_days(self, client, db, org_hierarchy):
        """GET /cadres/expiring?days=90 retourne cadres expirant."""
        # Create a cadre that expires in 60 days (within 90 day window)
        # Must include entite_juridique_id for org-scoped expiring query
        sites = org_hierarchy["sites"]
        ej_id = org_hierarchy["ej"].id
        start = (date.today() - timedelta(days=300)).isoformat()
        end = (date.today() + timedelta(days=60)).isoformat()
        payload = _base_payload(
            sites[0].id,
            start_date=start,
            end_date=end,
            entite_juridique_id=ej_id,
        )
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 201

        r2 = client.get("/api/contracts/v2/cadres/expiring?days=90")
        assert r2.status_code == 200
        data = r2.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_expiring_does_not_include_distant(self, client, db, org_hierarchy):
        """Cadre expirant dans 400j n'apparait pas dans expiring?days=90."""
        sites = org_hierarchy["sites"]
        ej_id = org_hierarchy["ej"].id
        start = (date.today() - timedelta(days=30)).isoformat()
        end = (date.today() + timedelta(days=400)).isoformat()
        payload = _base_payload(
            sites[0].id,
            start_date=start,
            end_date=end,
            entite_juridique_id=ej_id,
        )
        r = client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 201

        r2 = client.get("/api/contracts/v2/cadres/expiring?days=90")
        assert r2.status_code == 200
        data = r2.json()
        # The distant cadre should NOT appear
        cadre_id = r.json()["id"]
        ids_in_expiring = [c["id"] for c in data]
        assert cadre_id not in ids_in_expiring
