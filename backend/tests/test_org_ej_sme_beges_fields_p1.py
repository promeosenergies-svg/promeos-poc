"""
PROMEOS — Conformité P1 2026-05-23 : champs Org/EJ pour gates SMÉ/BEGES.

`PATCH /api/patrimoine/crud/organisations/{id}` accepte désormais :
- `effectif_total` (gate BEGES + SMÉ)
- `chiffre_affaires_eur` (gate SMÉ)
- `bilan_eur` (gate SMÉ)

`PATCH /api/patrimoine/crud/entites/{id}` accepte désormais :
- `consommation_annuelle_moyenne_3y_gwh` (gate Audit SMÉ)
- `iso_50001_actif` + `iso_50001_date_validite` (exemption SMÉ)

Avant ces tests : ces champs étaient mutés silencieusement (pas dans schema) ou
inaccessibles depuis le frontend. Gap P0 audit Conformité.
"""

from __future__ import annotations

import os
import sys
from datetime import date

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import Base, EntiteJuridique, Organisation  # noqa: E402


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


def _seed_org_with_ej(db):
    org = Organisation(nom="Org P1 SME", siren="111111111", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ P1", siren="111111111")
    db.add(ej)
    db.commit()
    return org, ej


# ─── PATCH Organisation : SMÉ/BEGES ──────────────────────────────────────


def test_patch_organisation_accepts_effectif_total(client, db):
    """`effectif_total` (gate BEGES) accepté en PATCH."""
    org, _ = _seed_org_with_ej(db)
    response = client.patch(
        f"/api/patrimoine/crud/organisations/{org.id}",
        json={"effectif_total": 750},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["effectif_total"] == 750
    db.refresh(org)
    assert org.effectif_total == 750


def test_patch_organisation_accepts_chiffre_affaires_and_bilan(client, db):
    """`chiffre_affaires_eur` + `bilan_eur` (gate SMÉ) acceptés."""
    org, _ = _seed_org_with_ej(db)
    response = client.patch(
        f"/api/patrimoine/crud/organisations/{org.id}",
        json={"chiffre_affaires_eur": 50_000_000.0, "bilan_eur": 43_000_000.0},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["chiffre_affaires_eur"] == 50_000_000.0
    assert body["bilan_eur"] == 43_000_000.0


def test_patch_organisation_rejects_negative_effectif(client, db):
    """`effectif_total < 0` → 422 (Pydantic validation)."""
    org, _ = _seed_org_with_ej(db)
    response = client.patch(
        f"/api/patrimoine/crud/organisations/{org.id}",
        json={"effectif_total": -10},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 422


def test_get_organisation_returns_sme_beges_fields(client, db):
    """`GET /organisations/{id}` expose les 3 champs SMÉ/BEGES."""
    org, _ = _seed_org_with_ej(db)
    org.effectif_total = 600
    org.chiffre_affaires_eur = 40_000_000.0
    org.bilan_eur = 30_000_000.0
    db.commit()

    response = client.get(
        f"/api/patrimoine/crud/organisations/{org.id}",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["effectif_total"] == 600
    assert body["chiffre_affaires_eur"] == 40_000_000.0
    assert body["bilan_eur"] == 30_000_000.0


# ─── PATCH EJ : SMÉ ──────────────────────────────────────────────────────


def test_patch_ej_accepts_consommation_3y(client, db):
    """`consommation_annuelle_moyenne_3y_gwh` (gate Audit SMÉ) accepté."""
    org, ej = _seed_org_with_ej(db)
    response = client.patch(
        f"/api/patrimoine/crud/entites/{ej.id}",
        json={"consommation_annuelle_moyenne_3y_gwh": 5.3},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["consommation_annuelle_moyenne_3y_gwh"] == 5.3


def test_patch_ej_accepts_iso_50001_certification(client, db):
    """`iso_50001_actif` + date_validite (exemption SMÉ) acceptés."""
    org, ej = _seed_org_with_ej(db)
    response = client.patch(
        f"/api/patrimoine/crud/entites/{ej.id}",
        json={"iso_50001_actif": True, "iso_50001_date_validite": "2029-06-30"},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["iso_50001_actif"] is True
    assert body["iso_50001_date_validite"] == "2029-06-30"


def test_patch_ej_rejects_negative_consommation(client, db):
    """`consommation_annuelle_moyenne_3y_gwh < 0` → 422."""
    org, ej = _seed_org_with_ej(db)
    response = client.patch(
        f"/api/patrimoine/crud/entites/{ej.id}",
        json={"consommation_annuelle_moyenne_3y_gwh": -1.0},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 422


def test_get_ej_returns_sme_fields(client, db):
    """`GET /entites/{id}` expose les 3 champs SMÉ."""
    org, ej = _seed_org_with_ej(db)
    ej.consommation_annuelle_moyenne_3y_gwh = 4.2
    ej.iso_50001_actif = True
    ej.iso_50001_date_validite = date(2028, 12, 31)
    db.commit()

    response = client.get(
        f"/api/patrimoine/crud/entites?organisation_id={org.id}",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    target_ej = next(e for e in body["entites"] if e["id"] == ej.id)
    assert target_ej["consommation_annuelle_moyenne_3y_gwh"] == 4.2
    assert target_ej["iso_50001_actif"] is True
    assert target_ej["iso_50001_date_validite"] == "2028-12-31"
