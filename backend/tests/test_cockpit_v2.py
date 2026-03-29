"""
PROMEOS - Tests Cockpit Executive V2
Vérifie : shape réponse, cohérence impact, tri actions, anti-doublon.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Client with demo DB (read-only tests)."""
    return TestClient(app)


def test_executive_v2_response_shape(client):
    """La réponse a la bonne structure."""
    resp = client.get("/api/cockpit/executive-v2")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) >= {"org", "impact", "sante", "actions"}
    assert set(data["impact"].keys()) >= {"total_eur", "conformite_eur", "factures_eur", "optimisation_eur"}
    assert set(data["sante"].keys()) >= {"conformite", "qualite_donnees", "contrats", "consommation"}


def test_total_equals_sum_of_parts(client):
    """total_eur = conformite + factures + optimisation."""
    data = client.get("/api/cockpit/executive-v2").json()
    i = data["impact"]
    expected = round(i["conformite_eur"] + i["factures_eur"] + i["optimisation_eur"], 2)
    assert i["total_eur"] == expected


def test_actions_sorted_by_impact_desc_nulls_last(client):
    """Actions triées par impact_eur DESC, nulls last."""
    data = client.get("/api/cockpit/executive-v2").json()
    actions = data["actions"]
    for idx in range(len(actions) - 1):
        curr = actions[idx]["impact_eur"]
        nxt = actions[idx + 1]["impact_eur"]
        if curr is not None and nxt is not None:
            assert curr >= nxt
        if curr is None:
            assert nxt is None  # nulls stay together at end


def test_qualite_donnees_single_score(client):
    """Un seul score, pas 3 métriques legacy."""
    data = client.get("/api/cockpit/executive-v2").json()
    qd = data["sante"]["qualite_donnees"]
    assert "score" in qd
    assert "completude" not in qd
    assert "couverture_operationnelle" not in qd


def test_kwh_m2_calculated_backend(client):
    """kWh/m²/an calculé backend."""
    data = client.get("/api/cockpit/executive-v2").json()
    c = data["sante"]["consommation"]
    surface = data["org"]["surface_totale_m2"]
    if surface > 0 and c["total_mwh"] > 0:
        expected = round(c["total_mwh"] * 1000 / surface)
        assert c["kwh_m2_an"] == expected


def test_no_risque_in_sante(client):
    """Le risque financier est dans impact, pas dans sante (anti-doublon)."""
    data = client.get("/api/cockpit/executive-v2").json()
    sante_str = str(data["sante"])
    assert "risque_financier" not in sante_str
