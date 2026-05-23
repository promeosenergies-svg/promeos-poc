"""
PROMEOS — P0-A 2026-05-23 : audit log wiring sur PATCH/DELETE patrimoine_crud.

Avant ce fix : 5 endpoints CRUD (Org/EJ/PF/Site/Batiment) mutaient sans tracer.
Maintenant chaque PATCH écrit un AuditLog `*.update` et chaque DELETE écrit
un AuditLog `*.archive`/`.delete` via `audit_log_service.log_patrimoine_change`.

Source-guard structurel : voir tests/source_guards/test_patrimoine_crud_audit_log_wiring_source_guards.py
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
    Batiment,
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


@pytest.fixture
def seeded(db):
    """Crée une hiérarchie complète Org→EJ→PF→Site→Batiment."""
    org = Organisation(nom="Org P0A", type_client="bureau", actif=True, siren="111111111")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ P0A", siren="111111111")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF P0A")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site P0A",
        type=TypeSite.BUREAU,
        adresse="1 rue Test",
        code_postal="75001",
        ville="Paris",
        surface_m2=1000,
        actif=True,
    )
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="Bâtiment A", surface_m2=600.0)
    db.add(bat)
    db.commit()
    return {"org": org, "ej": ej, "pf": pf, "site": site, "bat": bat}


def _audit_logs(db, *, resource_type: str, resource_id: int, action: str):
    return (
        db.query(AuditLog)
        .filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == str(resource_id),
            AuditLog.action == action,
        )
        .all()
    )


def _headers(org_id):
    return {"X-Org-Id": str(org_id), "X-Correlation-ID": "test-p0a-001"}


def test_patch_organisation_writes_audit_log(client, db, seeded):
    org = seeded["org"]
    response = client.patch(
        f"/api/patrimoine/crud/organisations/{org.id}",
        json={"nom": "Org P0A v2"},
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="organisation", resource_id=org.id, action="organisation.update")
    assert len(logs) >= 1
    log = logs[-1]
    assert log.org_id == org.id
    assert log.correlation_id == "test-p0a-001"
    assert log.field_modified == "nom"


def test_delete_organisation_writes_audit_log(client, db, seeded):
    org = seeded["org"]
    response = client.delete(
        f"/api/patrimoine/crud/organisations/{org.id}",
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="organisation", resource_id=org.id, action="organisation.archive")
    assert len(logs) == 1


def test_patch_entite_writes_audit_log(client, db, seeded):
    org, ej = seeded["org"], seeded["ej"]
    response = client.patch(
        f"/api/patrimoine/crud/entites/{ej.id}",
        json={"nom": "EJ P0A v2"},
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="entite_juridique", resource_id=ej.id, action="entite_juridique.update")
    assert len(logs) == 1
    assert logs[0].correlation_id == "test-p0a-001"


def test_delete_entite_writes_audit_log(client, db, seeded):
    org, ej = seeded["org"], seeded["ej"]
    response = client.delete(
        f"/api/patrimoine/crud/entites/{ej.id}",
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="entite_juridique", resource_id=ej.id, action="entite_juridique.archive")
    assert len(logs) == 1


def test_patch_portefeuille_writes_audit_log(client, db, seeded):
    org, pf = seeded["org"], seeded["pf"]
    response = client.patch(
        f"/api/patrimoine/crud/portefeuilles/{pf.id}",
        json={"nom": "PF P0A v2"},
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="portefeuille", resource_id=pf.id, action="portefeuille.update")
    assert len(logs) == 1


def test_delete_portefeuille_writes_audit_log(client, db, seeded):
    org, pf = seeded["org"], seeded["pf"]
    response = client.delete(
        f"/api/patrimoine/crud/portefeuilles/{pf.id}",
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="portefeuille", resource_id=pf.id, action="portefeuille.archive")
    assert len(logs) == 1


def test_patch_site_writes_audit_log(client, db, seeded):
    org, site = seeded["org"], seeded["site"]
    response = client.patch(
        f"/api/patrimoine/crud/sites/{site.id}",
        json={"ville": "Marseille"},
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="site", resource_id=site.id, action="site.update")
    assert len(logs) == 1
    assert logs[0].field_modified == "ville"
    assert "Marseille" in (logs[0].new_value or "")


def test_delete_site_writes_audit_log(client, db, seeded):
    org, site = seeded["org"], seeded["site"]
    response = client.delete(
        f"/api/patrimoine/crud/sites/{site.id}",
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="site", resource_id=site.id, action="site.archive")
    assert len(logs) == 1


def test_patch_batiment_writes_audit_log(client, db, seeded):
    org, bat = seeded["org"], seeded["bat"]
    response = client.patch(
        f"/api/patrimoine/crud/batiments/{bat.id}",
        json={"surface_m2": 750.0},
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="batiment", resource_id=bat.id, action="batiment.update")
    assert len(logs) == 1


def test_delete_batiment_writes_audit_log(client, db, seeded):
    org, bat = seeded["org"], seeded["bat"]
    response = client.delete(
        f"/api/patrimoine/crud/batiments/{bat.id}",
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    logs = _audit_logs(db, resource_type="batiment", resource_id=bat.id, action="batiment.delete")
    assert len(logs) == 1


def test_patch_with_no_change_writes_no_audit(client, db, seeded):
    """PATCH avec un payload identique aux valeurs courantes ne doit pas créer d'audit log."""
    org, ej = seeded["org"], seeded["ej"]
    # Premier PATCH avec une modif
    client.patch(
        f"/api/patrimoine/crud/entites/{ej.id}",
        json={"nom": "EJ same"},
        headers=_headers(org.id),
    )
    initial_count = len(
        _audit_logs(db, resource_type="entite_juridique", resource_id=ej.id, action="entite_juridique.update")
    )
    # Deuxième PATCH avec même valeur → no diff
    client.patch(
        f"/api/patrimoine/crud/entites/{ej.id}",
        json={"nom": "EJ same"},
        headers=_headers(org.id),
    )
    final_count = len(
        _audit_logs(db, resource_type="entite_juridique", resource_id=ej.id, action="entite_juridique.update")
    )
    assert final_count == initial_count, "PATCH no-op ne doit pas écrire d'audit log"
