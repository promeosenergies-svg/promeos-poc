"""
PROMEOS - Tests wiring Site model reel pour Pilotage Flex Ready (R).

Couvre :
    1. Colonnes Site.archetype_code + Site.puissance_pilotable_kw presentes.
    2. Seed pilotage fields : canonique (Carrefour -> COMMERCE_ALIMENTAIRE),
       fallback TypeSite, idempotence.
    3. /roi-flex-ready/{Site.id} : lookup DB avec scope org + 404 hors scope.
    4. /portefeuille-scoring : lit archetype_code + puissance_pilotable_kw
       directement depuis Site.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from middleware.auth import AuthContext, get_optional_auth
from models import (
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
)
from models.enums import TypeSite
from services.demo_seed.gen_pilotage_fields import seed_pilotage_fields


@pytest.fixture
def db_session():
    """Session DB SQLite in-memory, isolation totale."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def org_with_site(db_session):
    """Cree une Org + EntiteJuridique + Portefeuille + Site canonique."""
    org = Organisation(nom="Test Org", siren="123456789")
    db_session.add(org)
    db_session.flush()

    entite = EntiteJuridique(
        nom="Test Entite",
        siren="123456789",
        organisation_id=org.id,
    )
    db_session.add(entite)
    db_session.flush()

    ptf = Portefeuille(
        nom="Test Portefeuille",
        entite_juridique_id=entite.id,
    )
    db_session.add(ptf)
    db_session.flush()

    site = Site(
        nom="Hypermarche Montreuil",
        type=TypeSite.MAGASIN,
        portefeuille_id=ptf.id,
        surface_m2=2500.0,
        actif=True,
    )
    db_session.add(site)
    db_session.flush()
    return {"org": org, "entite": entite, "ptf": ptf, "site": site}


# ---------------------------------------------------------------------------
# Test 1 : colonnes Site presentes (Site model a jour)
# ---------------------------------------------------------------------------
def test_site_model_porte_les_colonnes_pilotage():
    """Le modele Site doit porter `archetype_code` + `puissance_pilotable_kw`."""
    assert hasattr(Site, "archetype_code"), "Site.archetype_code manquant"
    assert hasattr(Site, "puissance_pilotable_kw"), "Site.puissance_pilotable_kw manquant"


# ---------------------------------------------------------------------------
# Test 2 : seed canonique matche sur le nom (Carrefour -> COMMERCE_ALIMENTAIRE)
# ---------------------------------------------------------------------------
def test_seed_canonique_matche_par_nom(db_session, org_with_site):
    """Un site nomme 'Hypermarche Montreuil' doit recevoir COMMERCE_ALIMENTAIRE."""
    site = org_with_site["site"]
    stats = seed_pilotage_fields(db_session, [site])
    db_session.flush()

    assert stats["updated"] == 1
    assert site.archetype_code == "COMMERCE_ALIMENTAIRE"
    assert site.puissance_pilotable_kw == 220.0


# ---------------------------------------------------------------------------
# Test 3 : fallback TypeSite pour un nom inconnu
# ---------------------------------------------------------------------------
def test_seed_fallback_typesite(db_session, org_with_site):
    """Un site inconnu doit retomber sur l'archetype du TypeSite."""
    site = org_with_site["site"]
    site.nom = "Site Inconnu 42"
    db_session.flush()

    stats = seed_pilotage_fields(db_session, [site])
    db_session.flush()

    assert stats["updated"] == 1
    # TypeSite.MAGASIN -> COMMERCE_ALIMENTAIRE (80.0 kW)
    assert site.archetype_code == "COMMERCE_ALIMENTAIRE"
    assert site.puissance_pilotable_kw == 80.0


# ---------------------------------------------------------------------------
# Test 4 : seed idempotent (ne reecrase pas les valeurs existantes)
# ---------------------------------------------------------------------------
def test_seed_idempotent(db_session, org_with_site):
    """Un second run ne doit pas ecraser les valeurs deja renseignees."""
    site = org_with_site["site"]
    site.archetype_code = "SANTE"
    site.puissance_pilotable_kw = 999.0
    db_session.flush()

    stats = seed_pilotage_fields(db_session, [site])

    assert stats["skipped_full"] == 1
    assert site.archetype_code == "SANTE", "valeur existante ecrasee"
    assert site.puissance_pilotable_kw == 999.0


# ---------------------------------------------------------------------------
# Test 5 : /roi-flex-ready/{Site.id} accepte Site.id reel (numerique)
# ---------------------------------------------------------------------------
def test_roi_flex_ready_accepte_site_id_reel(db_session, org_with_site):
    """L'endpoint resout un Site.id numerique en DB et construit le ctx."""
    site = org_with_site["site"]
    # Seed des champs pilotage pour que l'archetype soit deterministe.
    seed_pilotage_fields(db_session, [site])
    db_session.flush()

    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(f"/api/pilotage/roi-flex-ready/{site.id}")
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
        data = r.json()
        assert data["site_id"] == str(site.id)
        assert data["archetype"] == "COMMERCE_ALIMENTAIRE"
        assert data["gain_annuel_total_eur"] > 0
        # CEE = surface_m2 * 3.5
        assert data["composantes"]["cee_bacs_eur"] == pytest.approx(2500.0 * 3.5)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 6 : /roi-flex-ready/{Site.id} 404 si hors scope org (defense-in-depth)
# ---------------------------------------------------------------------------
def test_roi_flex_ready_404_hors_scope_org(db_session, org_with_site):
    """Un Site.id qui n'appartient pas a l'org de l'utilisateur -> 404."""
    site = org_with_site["site"]

    def _override_db():
        yield db_session

    # Auth avec org_id DIFFERENT de celui du site
    fake_auth = AuthContext(
        user=None,
        user_org_role=None,
        org_id=999,  # pas l'org du site
        role=None,
        site_ids=[site.id],
    )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_optional_auth] = lambda: fake_auth
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(f"/api/pilotage/roi-flex-ready/{site.id}")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 7 : /portefeuille-scoring lit archetype + puissance depuis Site
# ---------------------------------------------------------------------------
def test_portefeuille_scoring_lit_archetype_depuis_site(db_session, org_with_site):
    """Le scoring portefeuille en prod lit les vrais champs Site, pas DEMO."""
    site = org_with_site["site"]
    seed_pilotage_fields(db_session, [site])
    db_session.flush()

    def _override_db():
        yield db_session

    fake_auth = AuthContext(
        user=None,
        user_org_role=None,
        org_id=org_with_site["org"].id,
        role=None,
        site_ids=[site.id],
    )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_optional_auth] = lambda: fake_auth
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/pilotage/portefeuille-scoring")
        assert r.status_code == 200
        data = r.json()
        assert data["nb_sites_total"] == 1
        top = data["top_10"]
        assert len(top) == 1
        # site_id format : str(Site.id) (cf. _org_sites_as_portfolio)
        assert top[0]["site_id"] == str(site.id)
        assert top[0]["archetype"] == "COMMERCE_ALIMENTAIRE"
        assert top[0]["gain_annuel_eur"] > 0
    finally:
        app.dependency_overrides.clear()
