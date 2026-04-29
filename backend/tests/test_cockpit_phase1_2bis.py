"""
PROMEOS — Tests Phase 1.2bis : 6 endpoints backend cockpit/action/purchase
Endpoints créés : _facts.scope, _facts.alerts, cdc, priorities,
                  actions/summary (top_urgences), purchase portfolio.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient
from main import app

HEADERS = {"X-Org-Id": "1"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── Endpoint #1 : GET /api/cockpit/_facts.scope ───────────────────────────


class TestCockpitFactsScope:
    def test_200_happy_path(self, client):
        r = client.get("/api/cockpit/_facts.scope", headers=HEADERS)
        assert r.status_code == 200, r.text

    def test_response_contract(self, client):
        data = client.get("/api/cockpit/_facts.scope", headers=HEADERS).json()
        assert "org_id" in data
        assert "org_name" in data
        assert "site_count" in data
        assert "portefeuille_count" in data

    def test_org_id_is_int(self, client):
        data = client.get("/api/cockpit/_facts.scope", headers=HEADERS).json()
        assert isinstance(data["org_id"], int)

    def test_counts_are_non_negative(self, client):
        data = client.get("/api/cockpit/_facts.scope", headers=HEADERS).json()
        assert data["site_count"] >= 0
        assert data["portefeuille_count"] >= 0


# ── Endpoint #2 : GET /api/cockpit/_facts.alerts ─────────────────────────


class TestCockpitFactsAlerts:
    def test_200_happy_path(self, client):
        r = client.get("/api/cockpit/_facts.alerts", headers=HEADERS)
        assert r.status_code == 200, r.text

    def test_response_contract(self, client):
        data = client.get("/api/cockpit/_facts.alerts", headers=HEADERS).json()
        assert "count" in data
        assert "top" in data
        assert isinstance(data["top"], list)

    def test_top_max_5_items(self, client):
        data = client.get("/api/cockpit/_facts.alerts", headers=HEADERS).json()
        assert len(data["top"]) <= 5

    def test_top_item_contract(self, client):
        data = client.get("/api/cockpit/_facts.alerts", headers=HEADERS).json()
        for item in data["top"]:
            assert "id" in item
            assert "title" in item
            assert "priority" in item
            assert "domain" in item


# ── Endpoint #3 : GET /api/action-center/actions/summary étendu ──────────


class TestActionsSummaryExtended:
    def test_200_happy_path(self, client):
        r = client.get("/api/action-center/actions/summary", headers=HEADERS)
        assert r.status_code == 200, r.text

    def test_top_urgences_present(self, client):
        data = client.get("/api/action-center/actions/summary", headers=HEADERS).json()
        assert "top_urgences" in data

    def test_top_urgences_is_list(self, client):
        data = client.get("/api/action-center/actions/summary", headers=HEADERS).json()
        assert isinstance(data["top_urgences"], list)

    def test_top_urgences_max_5(self, client):
        data = client.get("/api/action-center/actions/summary", headers=HEADERS).json()
        assert len(data["top_urgences"]) <= 5

    def test_existing_fields_preserved(self, client):
        data = client.get("/api/action-center/actions/summary", headers=HEADERS).json()
        # Champs existants ne doivent pas régresser
        assert "total" in data
        assert "by_status" in data
        assert "by_priority" in data
        assert "overdue_count" in data

    def test_top_urgences_item_contract(self, client):
        data = client.get("/api/action-center/actions/summary", headers=HEADERS).json()
        for item in data["top_urgences"]:
            assert "id" in item
            assert "title" in item
            assert "priority" in item
            assert "domain" in item


# ── Endpoint #4 : GET /api/cockpit/cdc ───────────────────────────────────


class TestCockpitCdc:
    def test_200_happy_path(self, client):
        r = client.get("/api/cockpit/cdc", headers=HEADERS, params={"period": "j_minus_1"})
        assert r.status_code == 200, r.text

    def test_response_contract(self, client):
        data = client.get("/api/cockpit/cdc", headers=HEADERS, params={"period": "j_minus_1"}).json()
        assert "period" in data
        assert "hp_kwh" in data
        assert "hc_kwh" in data

    def test_hp_hc_are_lists(self, client):
        data = client.get("/api/cockpit/cdc", headers=HEADERS, params={"period": "j_minus_1"}).json()
        assert isinstance(data["hp_kwh"], list)
        assert isinstance(data["hc_kwh"], list)

    def test_period_echoed(self, client):
        data = client.get("/api/cockpit/cdc", headers=HEADERS, params={"period": "j_minus_1"}).json()
        assert data["period"] == "j_minus_1"

    def test_no_meter_returns_error_key(self, client):
        """Si aucun compteur, l'endpoint retourne 200 avec error=no_meter ou no_sites."""
        data = client.get("/api/cockpit/cdc", headers=HEADERS, params={"period": "j_minus_1"}).json()
        # Soit les données existent, soit un error key est présent
        assert "hp_kwh" in data or "error" in data


# ── Endpoint #5 : GET /api/cockpit/priorities ────────────────────────────


class TestCockpitPriorities:
    def test_200_happy_path(self, client):
        r = client.get("/api/cockpit/priorities", headers=HEADERS)
        assert r.status_code == 200, r.text

    def test_response_contract(self, client):
        data = client.get("/api/cockpit/priorities", headers=HEADERS).json()
        assert "priorities" in data
        assert "total" in data
        assert isinstance(data["priorities"], list)

    def test_max_5_priorities(self, client):
        data = client.get("/api/cockpit/priorities", headers=HEADERS).json()
        assert len(data["priorities"]) <= 5

    def test_priority_item_contract(self, client):
        data = client.get("/api/cockpit/priorities", headers=HEADERS).json()
        for p in data["priorities"]:
            assert "rank" in p
            assert "title" in p
            assert "urgency" in p
            assert "domain" in p
            assert "action_url" in p

    def test_rank_sequential(self, client):
        data = client.get("/api/cockpit/priorities", headers=HEADERS).json()
        for i, p in enumerate(data["priorities"], start=1):
            assert p["rank"] == i


# ── Endpoint #6 : GET /api/purchase/cost-simulation/portfolio/{org_id} ───


class TestPurchaseCostSimulationPortfolio:
    def test_200_happy_path(self, client):
        r = client.get("/api/purchase/cost-simulation/portfolio/1", headers=HEADERS)
        assert r.status_code == 200, r.text

    def test_response_contract(self, client):
        data = client.get("/api/purchase/cost-simulation/portfolio/1", headers=HEADERS).json()
        assert "org_id" in data
        assert "sites" in data
        assert "total_portfolio_eur" in data
        assert "composantes_inactives" in data

    def test_sites_is_list(self, client):
        data = client.get("/api/purchase/cost-simulation/portfolio/1", headers=HEADERS).json()
        assert isinstance(data["sites"], list)

    def test_org_id_echoed(self, client):
        data = client.get("/api/purchase/cost-simulation/portfolio/1", headers=HEADERS).json()
        assert data["org_id"] == 1

    def test_total_is_sum_of_sites(self, client):
        data = client.get("/api/purchase/cost-simulation/portfolio/1", headers=HEADERS).json()
        computed = sum(s["total_eur"] for s in data["sites"])
        assert abs(data["total_portfolio_eur"] - computed) < 1.0  # tolérance arrondi

    def test_composantes_inactives_keys(self, client):
        data = client.get("/api/purchase/cost-simulation/portfolio/1", headers=HEADERS).json()
        ci = data["composantes_inactives"]
        assert "vnu_eur" in ci
        assert "cbam_eur" in ci

    def test_org_scope_mismatch_forbidden(self, client):
        """org_id=999 avec scope X-Org-Id=1 doit retourner 403."""
        r = client.get("/api/purchase/cost-simulation/portfolio/999", headers=HEADERS)
        assert r.status_code == 403
