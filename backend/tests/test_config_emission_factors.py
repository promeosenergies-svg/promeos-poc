"""
Tests de l'endpoint GET /api/config/emission-factors.
Fix P0 #1-5 audit QA Guardian 2026-04-15 — source unique ADEME pour le frontend.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_emission_factors_endpoint_returns_200():
    resp = client.get("/api/config/emission-factors")
    assert resp.status_code == 200


def test_emission_factors_has_elec_and_gaz():
    resp = client.get("/api/config/emission-factors")
    data = resp.json()
    assert "factors" in data
    assert "elec" in data["factors"]
    assert "gaz" in data["factors"]


def test_elec_factor_is_ademe_052():
    """CO₂ élec = 0.052 kgCO₂e/kWh (ADEME Base Empreinte V23.6)."""
    resp = client.get("/api/config/emission-factors")
    data = resp.json()
    assert data["factors"]["elec"]["kgco2e_per_kwh"] == 0.052


def test_gaz_factor_is_ademe_0227():
    """CO₂ gaz = 0.227 kgCO₂e/kWh (ADEME Base Empreinte V23.6)."""
    resp = client.get("/api/config/emission-factors")
    data = resp.json()
    assert data["factors"]["gaz"]["kgco2e_per_kwh"] == 0.227


def test_emission_factors_sources_cited():
    """Chaque facteur doit citer sa source (doctrine PROMEOS)."""
    resp = client.get("/api/config/emission-factors")
    data = resp.json()
    for vector, entry in data["factors"].items():
        assert "source" in entry, f"Vector {vector} sans champ source"
        assert "ADEME" in entry["source"], f"Vector {vector} source ne mentionne pas ADEME"


def test_source_version_present():
    resp = client.get("/api/config/emission-factors")
    data = resp.json()
    assert "source_version" in data
    assert "ADEME" in data["source_version"]


def test_no_0_0569_regression():
    """Garde-fou : 0.0569 est un tarif TURPE HPH, PAS un facteur CO₂."""
    resp = client.get("/api/config/emission-factors")
    data = resp.json()
    for vector, entry in data["factors"].items():
        assert entry["kgco2e_per_kwh"] != 0.0569, (
            f"Vector {vector} a le tarif TURPE 0.0569 au lieu du facteur CO₂ ADEME"
        )
