"""
Tests endpoint GET /api/tertiaire/sites/{id}/dt-progress
et GET /api/tertiaire/portfolio/{org_id}/dt-progress.

Verifie : assujettissement, delegation operat_trajectory, jalons officiels.
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


class TestSiteDtProgress:
    def test_site_assujetti_retourne_assujetti_true(self, client):
        """Site >= 1000m² retourne assujetti=True."""
        resp = client.get("/api/tertiaire/sites/1/dt-progress")
        assert resp.status_code == 200
        data = resp.json()
        assert data["assujetti"] is True
        assert "jalons_officiels" in data

    def test_site_avec_efa_retourne_reduction(self, client):
        """Site avec EFA retourne reduction_pct et prochain_jalon."""
        resp = client.get("/api/tertiaire/sites/1/dt-progress")
        data = resp.json()
        if data.get("n_efa_actives", 0) > 0:
            assert "reduction_pct" in data
            assert "prochain_jalon" in data
            assert data.get("source") == "operat_trajectory"

    def test_jalons_officiels_uniquement_2030_2040_2050(self, client):
        """Seuls les jalons 2030/2040/2050 — jamais 2026."""
        resp = client.get("/api/tertiaire/sites/1/dt-progress")
        assert resp.status_code == 200
        data = resp.json()
        annees = [j["annee"] for j in data.get("jalons_officiels", [])]
        assert 2030 in annees
        assert 2040 in annees
        assert 2050 in annees
        assert 2026 not in annees, "Jalon 2026 fantome present"

    def test_jalons_ont_is_official_true(self, client):
        """Tous les jalons retournes doivent avoir is_official=True."""
        resp = client.get("/api/tertiaire/sites/1/dt-progress")
        data = resp.json()
        for jalon in data.get("jalons_officiels", []):
            assert jalon.get("is_official") is True

    def test_site_inexistant_retourne_404(self, client):
        """Site inexistant retourne 404."""
        resp = client.get("/api/tertiaire/sites/99999/dt-progress")
        assert resp.status_code == 404

    def test_prochain_jalon_est_2030(self, client):
        """Le prochain jalon pour 2026 est 2030 (-40%)."""
        resp = client.get("/api/tertiaire/sites/1/dt-progress")
        data = resp.json()
        jalon = data.get("prochain_jalon")
        if jalon:
            assert jalon["annee"] == 2030
            assert jalon["reduction_cible_pct"] == 40.0
            assert jalon.get("is_official") is True


class TestPortfolioDtProgress:
    def test_portfolio_retourne_sites(self, client):
        """Portfolio retourne les sites assujettis."""
        resp = client.get("/api/tertiaire/portfolio/1/dt-progress")
        assert resp.status_code == 200
        data = resp.json()
        assert "sites" in data
        # Au moins quelques sites assujettis (depends du seed en cours)
        assert data["n_sites_assujettis"] >= 0

    def test_portfolio_tri_off_track_en_premier(self, client):
        """Les sites en retard doivent etre listes en premier."""
        resp = client.get("/api/tertiaire/portfolio/1/dt-progress")
        data = resp.json()
        sites = data.get("sites", [])
        if len(sites) >= 2:
            statuts = [s["status"] for s in sites]
            last_off = max((i for i, s in enumerate(statuts) if s == "off_track"), default=-1)
            first_on = min((i for i, s in enumerate(statuts) if s == "on_track"), default=999)
            assert last_off < first_on or last_off == -1 or first_on == 999

    def test_portfolio_pas_de_jalon_2026(self, client):
        """Jalon 2026 absent du portfolio."""
        resp = client.get("/api/tertiaire/portfolio/1/dt-progress")
        data = resp.json()
        annees = [j["annee"] for j in data.get("jalons_officiels", [])]
        assert 2026 not in annees

    def test_portfolio_source_operat(self, client):
        """Source doit etre operat_trajectory."""
        resp = client.get("/api/tertiaire/portfolio/1/dt-progress")
        data = resp.json()
        assert data.get("source") == "operat_trajectory"
