"""
Tests de l'endpoint GET /api/config/price-references.
Queue 2 audit QA Guardian 2026-04-15 — source unique pour le fallback EUR_FACTOR.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.config_price_references import router


def _build_client() -> TestClient:
    """Isolated app pour éviter les migrations DB du main.py."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_price_references_endpoint_returns_200():
    client = _build_client()
    resp = client.get("/api/config/price-references")
    assert resp.status_code == 200


def test_price_references_has_elec_and_gaz():
    client = _build_client()
    data = client.get("/api/config/price-references").json()
    assert "elec_eur_kwh" in data
    assert "gaz_eur_kwh" in data


def test_price_references_is_not_regulatory():
    """Doctrine : ce fallback N'EST PAS une source réglementaire."""
    client = _build_client()
    data = client.get("/api/config/price-references").json()
    assert data.get("is_regulatory") is False


def test_price_references_has_source_and_valid_from():
    client = _build_client()
    data = client.get("/api/config/price-references").json()
    assert data.get("source") is not None
    assert data.get("valid_from") is not None


def test_price_references_values_match_yaml():
    """Smoke : valeurs cohérentes avec tarifs_reglementaires.yaml (prix_reference)."""
    client = _build_client()
    data = client.get("/api/config/price-references").json()
    assert data["elec_eur_kwh"] == 0.068
    assert data["gaz_eur_kwh"] == 0.045


def test_price_references_doctrine_field_present():
    """Réponse inclut un champ `doctrine` pour expliquer l'usage au frontend."""
    client = _build_client()
    data = client.get("/api/config/price-references").json()
    assert "doctrine" in data
    assert len(data["doctrine"]) > 20
