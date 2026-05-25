"""
PROMEOS — Bill Intelligence P1 C3 (2026-05-24) :
`POST /api/billing/audit-all` ne doit jamais retourner 500 pour absence de contexte org.

Doctrine alignée sur conformité P1 (`POST /api/conformite/sync-remediation-actions`) :
- 401 HTTP
- code `NO_ORG_CONTEXT`
- message FR clair
- hint FR
- correlation_id
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import Base, EntiteJuridique, Organisation, Portefeuille, Site, TypeSite  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_minimal_org(db):
    org = Organisation(nom="Org C3", siren="999999999", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="999999999")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site C3",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        actif=True,
    )
    db.add(site)
    db.commit()
    return org


def test_audit_all_without_org_context_returns_401_fr(client, db, monkeypatch):
    """Sans JWT ni X-Org-Id et sans fallback DEMO_MODE → 401 NO_ORG_CONTEXT FR.

    On simule DEMO_MODE=False pour forcer le chemin d'erreur.
    """
    # Empêche le fallback DEMO_MODE en patchant la variable d'env scope_utils
    import services.scope_utils as scope_utils

    monkeypatch.setattr(scope_utils, "DEMO_MODE", False, raising=True)

    response = client.post("/api/billing/audit-all")
    assert response.status_code == 401, response.text
    detail = response.json().get("detail") or {}
    assert detail.get("code") == "NO_ORG_CONTEXT"
    assert "organisation" in (detail.get("message") or "").lower()
    assert "JWT" in (detail.get("hint") or "")
    assert detail.get("correlation_id"), "correlation_id obligatoire pour debug"


def test_audit_all_with_x_org_id_demo_mode_returns_200(client, db):
    """Avec X-Org-Id valide en DEMO_MODE → 200 OK."""
    org = _seed_minimal_org(db)
    response = client.post(
        "/api/billing/audit-all",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert "audited" in body


def test_audit_all_never_returns_500_under_normal_path(client, db):
    """Vérifie qu'aucun chemin nominal ne tombe en 500 (parapluie)."""
    org = _seed_minimal_org(db)
    response = client.post(
        "/api/billing/audit-all",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code < 500, response.text
