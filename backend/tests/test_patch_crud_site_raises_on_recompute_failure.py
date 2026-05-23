"""
PROMEOS — P0-A 2026-05-23 : PATCH /api/patrimoine/crud/sites/{id} ne masque plus
les échecs de recompute. Avant ce fix, un try/except avalait l'exception et
laissait la mutation persister avec une conformité stale silencieuse.

Comportement attendu maintenant :
- Recompute OK → 200 + audit log + commit
- Recompute fail (champ critique modifié) → 500 PATRIMOINE_RECOMPUTE_FAILED
  + rollback + correlation_id propagé.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch as mock_patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import (  # noqa: E402
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    TypeSite,
)


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
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def site(db):
    org = Organisation(nom="Org R", type_client="bureau", actif=True, siren="333000111")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ R", siren="333000111")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF R")
    db.add(pf)
    db.flush()
    s = Site(
        portefeuille_id=pf.id,
        nom="Site Recompute",
        type=TypeSite.BUREAU,
        adresse="1 rue R",
        code_postal="75001",
        ville="Paris",
        surface_m2=1000,
        actif=True,
    )
    db.add(s)
    db.commit()
    return {"org": org, "site": s}


def test_recompute_failure_returns_500_with_error_envelope(client, db, site):
    """Quand recompute_site_full plante, PATCH doit retourner 500 PATRIMOINE_RECOMPUTE_FAILED."""
    headers = {"X-Org-Id": str(site["org"].id), "X-Correlation-ID": "test-rcfail-001"}
    with mock_patch(
        "services.compliance_coordinator.recompute_site_full",
        side_effect=RuntimeError("boom recompute"),
    ):
        response = client.patch(
            f"/api/patrimoine/crud/sites/{site['site'].id}",
            json={"surface_m2": 2000},
            headers=headers,
        )
    assert response.status_code == 500
    body = response.json()
    detail = body.get("detail") or body
    assert detail["code"] == "PATRIMOINE_RECOMPUTE_FAILED"
    assert "réglementaire" in detail["message"].lower()
    assert detail["blocking"] is True
    assert detail["correlation_id"] == "test-rcfail-001"


def test_recompute_failure_does_not_persist_mutation(client, db, site):
    """En cas d'échec recompute, la mutation surface_m2 doit être rollback."""
    original_surface = site["site"].surface_m2
    with mock_patch(
        "services.compliance_coordinator.recompute_site_full",
        side_effect=RuntimeError("boom"),
    ):
        client.patch(
            f"/api/patrimoine/crud/sites/{site['site'].id}",
            json={"surface_m2": 9999},
            headers={"X-Org-Id": str(site["org"].id)},
        )
    db.expire_all()
    refreshed = db.query(Site).filter(Site.id == site["site"].id).first()
    assert refreshed.surface_m2 == original_surface, (
        f"Mutation devait être rollback : surface={refreshed.surface_m2} (attendu {original_surface})"
    )


def test_non_compliance_field_does_not_trigger_recompute(client, db, site):
    """PATCH d'un champ non-conformité (ex : ville) ne déclenche pas recompute."""
    # Pas de mock : si recompute était appelé sur 'ville', il ferait crasher quand même.
    response = client.patch(
        f"/api/patrimoine/crud/sites/{site['site'].id}",
        json={"ville": "Toulouse"},
        headers={"X-Org-Id": str(site["org"].id)},
    )
    assert response.status_code == 200, response.text
