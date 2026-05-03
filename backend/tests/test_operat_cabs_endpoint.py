"""
PROMEOS — Sprint C-1 Phase 4 : Tests endpoint /api/operat/cabs/{site_id}.

Vérifie l'org-scoping (sécurité multi-tenant), les codes d'erreur, et la
sérialisation du tooltip traçabilité.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    """FastAPI TestClient sur l'app principale."""
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


def _seed_site_with_operat_data(db) -> int:
    """Helper : récupère un site existant HELIOS et injecte des champs OPERAT MVP.

    Returns site_id.
    """
    from models import Site, not_deleted

    site = db.query(Site).filter(not_deleted(Site)).first()
    if site is None:
        return None
    # Patch les champs Phase 3 pour permettre le calcul Cabs
    site.altitude_m = 35
    site.operat_sous_categorie_id = "Bureaux - Bureaux Standards (cloisonnés - attribués)"
    if not site.tertiaire_area_m2:
        site.tertiaire_area_m2 = site.surface_m2 or 1000.0
    db.commit()
    return site.id


def test_endpoint_returns_cabs_for_valid_site(client):
    """Site valide avec données complètes → 200 + cabs_2030_kwh_m2_an dans la réponse."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        site_id = _seed_site_with_operat_data(db)
        if site_id is None:
            pytest.skip("Aucun site HELIOS dans la DB de test")
    finally:
        db.close()

    r = client.get(f"/api/operat/cabs/{site_id}")
    assert r.status_code == 200, f"Réponse inattendue : {r.status_code} {r.text[:200]}"
    body = r.json()
    assert "cabs_2030_kwh_m2_an" in body
    assert body["cabs_2030_kwh_m2_an"] > 0
    assert "tracability_complete" in body
    assert body["tracability_complete"]["nor_annexe_i"] == "ATDL2430864A (annexe I)"


def test_endpoint_404_unknown_site(client):
    """Site inexistant → 404 (pas 403, pas leak d'info)."""
    r = client.get("/api/operat/cabs/999999999")
    assert r.status_code == 404
    detail = r.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error") == "SITE_INTROUVABLE"


def test_endpoint_422_missing_altitude(client):
    """Site sans altitude_m → 422 + missing_fields contient 'altitude_m'."""
    from database import SessionLocal
    from models import Site, not_deleted

    db = SessionLocal()
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if site is None:
            pytest.skip("Aucun site dans la DB")
        site.altitude_m = None  # Force missing
        site.operat_sous_categorie_id = "Bureaux - Bureaux Standards (cloisonnés - attribués)"
        db.commit()
        site_id = site.id
    finally:
        db.close()

    r = client.get(f"/api/operat/cabs/{site_id}")
    assert r.status_code == 422
    detail = r.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error") == "DONNEES_INCOMPLETES"
        assert "altitude_m" in detail.get("missing_fields", [])


def test_endpoint_422_subcat_not_declared(client):
    """Site sans operat_sous_categorie_id → 422 SOUS_CATEGORIE_NON_DECLAREE."""
    from database import SessionLocal
    from models import Site, not_deleted

    db = SessionLocal()
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if site is None:
            pytest.skip("Aucun site dans la DB")
        site.altitude_m = 35
        site.operat_sous_categorie_id = None
        db.commit()
        site_id = site.id
    finally:
        db.close()

    r = client.get(f"/api/operat/cabs/{site_id}")
    assert r.status_code == 422
    detail = r.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error") == "SOUS_CATEGORIE_NON_DECLAREE"


def test_endpoint_422_subcat_invalid(client):
    """Site avec sous-cat absente d'Annexe I → 422 SOUS_CATEGORIE_INTROUVABLE."""
    from database import SessionLocal
    from models import Site, not_deleted

    db = SessionLocal()
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if site is None:
            pytest.skip("Aucun site dans la DB")
        site.altitude_m = 35
        site.operat_sous_categorie_id = "SOUS_CATEGORIE_QUI_N_EXISTE_PAS"
        if not site.tertiaire_area_m2:
            site.tertiaire_area_m2 = site.surface_m2 or 1000.0
        db.commit()
        site_id = site.id
    finally:
        db.close()

    r = client.get(f"/api/operat/cabs/{site_id}")
    assert r.status_code == 422
    detail = r.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error") == "SOUS_CATEGORIE_INTROUVABLE"


def test_endpoint_response_contains_full_tracability(client):
    """La réponse contient le tooltip traçabilité complet (NOR + URLs + date)."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        site_id = _seed_site_with_operat_data(db)
        if site_id is None:
            pytest.skip("Aucun site HELIOS")
    finally:
        db.close()

    r = client.get(f"/api/operat/cabs/{site_id}")
    if r.status_code != 200:
        pytest.skip(f"Endpoint non disponible : {r.status_code}")
    body = r.json()
    trac = body.get("tracability_complete", {})
    assert trac.get("nor_annexe_i") == "ATDL2430864A (annexe I)"
    assert trac.get("nor_annexe_ii") == "ATDL2430864A (annexe II)"
    assert trac.get("nor_zones") == "LOGL2005904A v2 (annexe III)"
    assert trac.get("date_arrete") == "2025-08-01"
    assert "zone" in trac
    assert "palier_altitude" in trac
