"""
PROMEOS — P0-B 2026-05-23 : audit log sur tous les POST création patrimoine_crud.

P0-A a wiré PATCH/DELETE. P0-B complète avec les POST :
- organisation.create
- entite_juridique.create
- portefeuille.create
- batiment.create
(site.create / site.quick_create déjà couverts par P0-A.)
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
from models import (  # noqa: E402
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    TypeSite,
)
from models.iam import AuditLog  # noqa: E402


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


def _audit_logs(db, *, action: str):
    return db.query(AuditLog).filter(AuditLog.action == action).all()


def test_post_organisation_writes_create_audit_log(client, db):
    """POST /organisations → AuditLog action=organisation.create."""
    response = client.post(
        "/api/patrimoine/crud/organisations",
        json={"nom": "Org P0B", "siren": "111000111", "type_client": "bureau"},
        headers={"X-Correlation-ID": "test-p0b-org-001"},
    )
    assert response.status_code == 201, response.text
    org_id = response.json()["id"]
    logs = _audit_logs(db, action="organisation.create")
    assert len(logs) == 1
    log = logs[0]
    assert log.resource_type == "organisation"
    assert log.resource_id == str(org_id)
    assert log.correlation_id == "test-p0b-org-001"
    assert "Org P0B" in (log.new_value or "")


def test_post_entite_writes_create_audit_log(client, db):
    """POST /entites → AuditLog action=entite_juridique.create."""
    # Pré-créer une org pour l'EJ
    org = Organisation(nom="Org parent", siren="222000222", type_client="bureau", actif=True)
    db.add(org)
    db.commit()

    response = client.post(
        "/api/patrimoine/crud/entites",
        json={"organisation_id": org.id, "nom": "EJ P0B", "siren": "222000222"},
        headers={"X-Org-Id": str(org.id), "X-Correlation-ID": "test-p0b-ej-001"},
    )
    assert response.status_code == 201, response.text
    ej_id = response.json()["id"]
    logs = _audit_logs(db, action="entite_juridique.create")
    assert len(logs) == 1
    assert logs[0].resource_id == str(ej_id)
    assert logs[0].org_id == org.id
    assert logs[0].correlation_id == "test-p0b-ej-001"


def test_post_portefeuille_writes_create_audit_log(client, db):
    """POST /portefeuilles → AuditLog action=portefeuille.create."""
    org = Organisation(nom="Org parent", siren="333000333", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="333000333")
    db.add(ej)
    db.commit()

    response = client.post(
        "/api/patrimoine/crud/portefeuilles",
        json={"entite_juridique_id": ej.id, "nom": "PF P0B", "description": "Test"},
        headers={"X-Org-Id": str(org.id), "X-Correlation-ID": "test-p0b-pf-001"},
    )
    assert response.status_code == 201, response.text
    pf_id = response.json()["id"]
    logs = _audit_logs(db, action="portefeuille.create")
    assert len(logs) == 1
    assert logs[0].resource_id == str(pf_id)


def test_post_batiment_writes_create_audit_log(client, db):
    """POST /batiments → AuditLog action=batiment.create."""
    org = Organisation(nom="Org B", siren="444000444", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="444000444")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id, nom="Site", type=TypeSite.BUREAU,
        adresse="x", code_postal="75001", ville="Paris", surface_m2=1000, actif=True,
    )
    db.add(site)
    db.commit()

    response = client.post(
        "/api/patrimoine/crud/batiments",
        json={"site_id": site.id, "nom": "Bât A", "surface_m2": 600.0, "cvc_power_kw": 50.0},
        headers={"X-Org-Id": str(org.id), "X-Correlation-ID": "test-p0b-bat-001"},
    )
    assert response.status_code == 201, response.text
    bat_id = response.json()["id"]
    logs = _audit_logs(db, action="batiment.create")
    assert len(logs) == 1
    assert logs[0].resource_id == str(bat_id)
    assert logs[0].org_id == org.id


def test_get_endpoints_do_not_write_audit_log(client, db):
    """GET ne doit jamais écrire d'audit log (read-only)."""
    org = Organisation(nom="Org GET", siren="555000555", type_client="bureau", actif=True)
    db.add(org)
    db.commit()
    initial = db.query(AuditLog).count()

    client.get("/api/patrimoine/crud/organisations", headers={"X-Org-Id": str(org.id)})
    client.get(f"/api/patrimoine/crud/organisations/{org.id}", headers={"X-Org-Id": str(org.id)})
    client.get("/api/patrimoine/crud/entites", headers={"X-Org-Id": str(org.id)})
    client.get("/api/patrimoine/crud/portefeuilles", headers={"X-Org-Id": str(org.id)})
    client.get("/api/patrimoine/crud/sites", headers={"X-Org-Id": str(org.id)})

    final = db.query(AuditLog).count()
    assert final == initial, "Aucun GET ne doit créer d'audit log"
