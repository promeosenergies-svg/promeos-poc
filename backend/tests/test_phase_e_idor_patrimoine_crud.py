"""
PROMEOS — Phase E IDOR Sprint : tests cardinaux org-scoping patrimoine_crud.

Couvre 22 endpoints CRUD multi-tenant :
- Organisation : list / get / patch / delete (5 endpoints)
- EntiteJuridique : list / create / get / patch / delete (5 endpoints)
- Portefeuille : list / create / get / patch / delete (5 endpoints)
- Site : list / create / get / patch / delete (5 endpoints)
- Batiment : create / patch / delete (3 endpoints)

Setup : 2 orgs (Alpha, Bravo), chacune avec EJ → Pf → Site → Bati.
Chaque test injecte X-Org-Id Alpha pour tenter d'accéder aux données Bravo (et inverse).
Attendu : 404 systématique sur cross-tenant (anti-énumération).

Source : `services/patrimoine_scope_guard.py` (helpers `assert_org_owns_*`).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import (
    Base,
    Batiment,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


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


def _seed_two_orgs(db):
    """Crée 2 hiérarchies complètes Alpha + Bravo."""
    org_a = Organisation(nom="Org Alpha", type_client="bureau", actif=True, siren="111111111")
    org_b = Organisation(nom="Org Bravo", type_client="industrie", actif=True, siren="222222222")
    db.add_all([org_a, org_b])
    db.flush()

    ej_a = EntiteJuridique(organisation_id=org_a.id, nom="EJ Alpha", siren="111111111")
    ej_b = EntiteJuridique(organisation_id=org_b.id, nom="EJ Bravo", siren="222222222")
    db.add_all([ej_a, ej_b])
    db.flush()

    pf_a = Portefeuille(entite_juridique_id=ej_a.id, nom="PF Alpha")
    pf_b = Portefeuille(entite_juridique_id=ej_b.id, nom="PF Bravo")
    db.add_all([pf_a, pf_b])
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
    db.add_all([site_a, site_b])
    db.flush()

    bat_a = Batiment(site_id=site_a.id, nom="Bati Alpha", surface_m2=500.0, cvc_power_kw=40.0)
    bat_b = Batiment(site_id=site_b.id, nom="Bati Bravo", surface_m2=300.0, cvc_power_kw=20.0)
    db.add_all([bat_a, bat_b])
    db.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "ej_a": ej_a,
        "ej_b": ej_b,
        "pf_a": pf_a,
        "pf_b": pf_b,
        "site_a": site_a,
        "site_b": site_b,
        "bat_a": bat_a,
        "bat_b": bat_b,
    }


def _h(org_id: int) -> dict:
    return {"X-Org-Id": str(org_id)}


# ── Organisation IDOR ────────────────────────────────────────────────────────


class TestOrganisationIDOR:
    def test_list_organisations_scoped(self, client, db):
        """LIST orgs ne montre que l'org du scope, pas tout le SaaS."""
        d = _seed_two_orgs(db)
        r = client.get("/api/patrimoine/crud/organisations", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        ids = [o["id"] for o in r.json()["organisations"]]
        assert ids == [d["org_a"].id]
        assert d["org_b"].id not in ids

    def test_get_org_self_ok(self, client, db):
        d = _seed_two_orgs(db)
        r = client.get(f"/api/patrimoine/crud/organisations/{d['org_a'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 200

    def test_get_org_cross_tenant_404(self, client, db):
        """Org A demande org B → 404 anti-énumération."""
        d = _seed_two_orgs(db)
        r = client.get(f"/api/patrimoine/crud/organisations/{d['org_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_patch_org_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.patch(
            f"/api/patrimoine/crud/organisations/{d['org_b'].id}",
            json={"nom": "Hacked"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404

    def test_delete_org_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.delete(f"/api/patrimoine/crud/organisations/{d['org_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404


# ── EntiteJuridique IDOR ─────────────────────────────────────────────────────


class TestEntiteJuridiqueIDOR:
    def test_list_entites_scoped(self, client, db):
        d = _seed_two_orgs(db)
        r = client.get("/api/patrimoine/crud/entites", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        ids = [e["id"] for e in r.json()["entites"]]
        assert ids == [d["ej_a"].id]

    def test_list_entites_query_org_id_ignored(self, client, db):
        """Phase E IDOR : query param org_id ignoré, scope serveur force la valeur."""
        d = _seed_two_orgs(db)
        # Tente cross-tenant via query param
        r = client.get(
            f"/api/patrimoine/crud/entites?org_id={d['org_b'].id}",
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 200
        ids = [e["id"] for e in r.json()["entites"]]
        # Le scope_org_id (Alpha) gagne, query param Bravo ignoré
        assert d["ej_b"].id not in ids
        assert ids == [d["ej_a"].id]

    def test_get_entite_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.get(f"/api/patrimoine/crud/entites/{d['ej_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_patch_entite_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.patch(
            f"/api/patrimoine/crud/entites/{d['ej_b'].id}",
            json={"nom": "Hacked"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404

    def test_delete_entite_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.delete(f"/api/patrimoine/crud/entites/{d['ej_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_create_entite_with_other_org_id_404(self, client, db):
        """Tenter de créer EJ sous org B en étant scopé Alpha → 404."""
        d = _seed_two_orgs(db)
        r = client.post(
            "/api/patrimoine/crud/entites",
            json={
                "organisation_id": d["org_b"].id,
                "nom": "EJ Hacker",
                "siren": "333333333",
            },
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404


# ── Portefeuille IDOR ────────────────────────────────────────────────────────


class TestPortefeuilleIDOR:
    def test_list_portefeuilles_scoped(self, client, db):
        d = _seed_two_orgs(db)
        r = client.get("/api/patrimoine/crud/portefeuilles", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        ids = [pf["id"] for pf in r.json()["portefeuilles"]]
        assert ids == [d["pf_a"].id]

    def test_get_pf_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.get(f"/api/patrimoine/crud/portefeuilles/{d['pf_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_patch_pf_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.patch(
            f"/api/patrimoine/crud/portefeuilles/{d['pf_b'].id}",
            json={"nom": "Hacked"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404

    def test_delete_pf_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.delete(f"/api/patrimoine/crud/portefeuilles/{d['pf_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_create_pf_under_other_org_ej_404(self, client, db):
        """Créer un Pf sous EJ Bravo en étant scopé Alpha → 404."""
        d = _seed_two_orgs(db)
        r = client.post(
            "/api/patrimoine/crud/portefeuilles",
            json={"entite_juridique_id": d["ej_b"].id, "nom": "PF Hacker"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404


# ── Site IDOR ────────────────────────────────────────────────────────────────


class TestSiteIDOR:
    def test_list_sites_scoped(self, client, db):
        d = _seed_two_orgs(db)
        r = client.get("/api/patrimoine/crud/sites", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()["sites"]]
        assert ids == [d["site_a"].id]

    def test_get_site_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.get(f"/api/patrimoine/crud/sites/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_patch_site_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.patch(
            f"/api/patrimoine/crud/sites/{d['site_b'].id}",
            json={"nom": "Hacked"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404

    def test_delete_site_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.delete(f"/api/patrimoine/crud/sites/{d['site_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_create_site_under_other_org_pf_404(self, client, db):
        """Créer un Site sous Pf Bravo en étant scopé Alpha → 404."""
        d = _seed_two_orgs(db)
        r = client.post(
            "/api/patrimoine/crud/sites",
            json={
                "portefeuille_id": d["pf_b"].id,
                "nom": "Site Hacker",
                "type": "bureau",
            },
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404


# ── Batiment IDOR ────────────────────────────────────────────────────────────


class TestBatimentIDOR:
    def test_create_bati_under_other_org_site_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.post(
            "/api/patrimoine/crud/batiments",
            json={"site_id": d["site_b"].id, "nom": "Bati Hacker", "surface_m2": 100.0},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404

    def test_patch_bati_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.patch(
            f"/api/patrimoine/crud/batiments/{d['bat_b'].id}",
            json={"nom": "Hacked"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 404

    def test_delete_bati_cross_tenant_404(self, client, db):
        d = _seed_two_orgs(db)
        r = client.delete(f"/api/patrimoine/crud/batiments/{d['bat_b'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404


# ── Same-tenant golden path (non-régression) ─────────────────────────────────


class TestSameTenantGoldenPath:
    """Vérifie que le scoping ne casse pas les opérations same-tenant légitimes."""

    def test_get_own_site_ok(self, client, db):
        d = _seed_two_orgs(db)
        r = client.get(f"/api/patrimoine/crud/sites/{d['site_a'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 200
        assert r.json()["nom"] == "Site Alpha"

    def test_patch_own_pf_ok(self, client, db):
        d = _seed_two_orgs(db)
        r = client.patch(
            f"/api/patrimoine/crud/portefeuilles/{d['pf_a'].id}",
            json={"nom": "PF Alpha v2"},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 200
        assert r.json()["nom"] == "PF Alpha v2"

    def test_create_site_own_pf_ok(self, client, db):
        d = _seed_two_orgs(db)
        r = client.post(
            "/api/patrimoine/crud/sites",
            json={
                "portefeuille_id": d["pf_a"].id,
                "nom": "Site Alpha 2",
                "type": "bureau",
            },
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 201

    def test_create_bati_own_site_ok(self, client, db):
        d = _seed_two_orgs(db)
        r = client.post(
            "/api/patrimoine/crud/batiments",
            json={"site_id": d["site_a"].id, "nom": "Bati Alpha 2", "surface_m2": 200.0},
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 201

    def test_create_entite_own_org_ok(self, client, db):
        """Golden path création EJ same-tenant (régression schema 422 / scope 404)."""
        d = _seed_two_orgs(db)
        r = client.post(
            "/api/patrimoine/crud/entites",
            json={
                "organisation_id": d["org_a"].id,
                "nom": "EJ Alpha #2",
                "siren": "444444444",
            },
            headers=_h(d["org_a"].id),
        )
        assert r.status_code == 201
        assert r.json()["organisation_id"] == d["org_a"].id


# ── Anti-régression `not_deleted` (soft-delete + IDOR cardinal) ──────────────


class TestSoftDeletedIDOR:
    """Garantit que les guards `assert_org_owns_*` filtrent bien les entités soft-deleted.

    Sans `not_deleted()` dans le helper, un attaquant pourrait recharger une entité
    archivée via l'ID — finding code-reviewer Phase E P1.
    """

    def test_get_soft_deleted_site_returns_404(self, client, db):
        d = _seed_two_orgs(db)
        d["site_a"].soft_delete()
        db.commit()
        r = client.get(f"/api/patrimoine/crud/sites/{d['site_a'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_get_soft_deleted_pf_returns_404(self, client, db):
        d = _seed_two_orgs(db)
        d["pf_a"].soft_delete()
        db.commit()
        r = client.get(f"/api/patrimoine/crud/portefeuilles/{d['pf_a'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404

    def test_get_soft_deleted_entite_returns_404(self, client, db):
        d = _seed_two_orgs(db)
        d["ej_a"].soft_delete()
        db.commit()
        r = client.get(f"/api/patrimoine/crud/entites/{d['ej_a'].id}", headers=_h(d["org_a"].id))
        assert r.status_code == 404
