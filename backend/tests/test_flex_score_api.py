"""
Tests API des endpoints flex_score.py.
Verifie : montage router, reponses 200, coherence referentiel.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from models import Base


@pytest.fixture
def app_client():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    from main import app
    from database import get_db

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    os.environ["DEMO_MODE"] = "true"
    client = TestClient(app, raise_server_exceptions=False)
    yield client, SessionLocal
    app.dependency_overrides.clear()


class TestFlexScoreRouterMount:
    """Verifier que le router flex_score est monte dans main.py."""

    def test_get_usages_200(self, app_client):
        """GET /api/flex/score/usages -> 200."""
        client, _ = app_client
        resp = client.get("/api/flex/score/usages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_usages"] == 15
        assert len(data["usages"]) == 15

    def test_prix_signal_neutre(self, app_client):
        """GET /api/flex/score/prix-signal?prix_spot_eur_mwh=45 -> signal NEUTRE."""
        client, _ = app_client
        resp = client.get("/api/flex/score/prix-signal", params={"prix_spot_eur_mwh": 45})
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal"] == "NEUTRE"
        assert "usages_cibles" in data

    def test_prix_signal_negatif(self, app_client):
        """GET /api/flex/score/prix-signal?prix_spot_eur_mwh=-15 -> PRIX_NEGATIF."""
        client, _ = app_client
        resp = client.get("/api/flex/score/prix-signal", params={"prix_spot_eur_mwh": -15})
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal"] == "PRIX_NEGATIF"
        assert data["modulation_nebco"] == "ANTICIPATION"
        assert "BATTERIES" in data["usages_cibles"]

    def test_prix_signal_eleve(self, app_client):
        """GET /api/flex/score/prix-signal?prix_spot_eur_mwh=150 -> PRIX_ELEVE."""
        client, _ = app_client
        resp = client.get("/api/flex/score/prix-signal", params={"prix_spot_eur_mwh": 150})
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal"] == "PRIX_ELEVE"
        assert data["modulation_nebco"] == "EFFACEMENT"


class TestFlexScoreSite:
    """Tests sur les endpoints site."""

    def test_site_inexistant_404(self, app_client):
        """Site inexistant -> 404."""
        client, _ = app_client
        resp = client.get("/api/flex/score/sites/99999")
        assert resp.status_code == 404

    def test_site_avec_seed(self, app_client):
        """Site cree via quick-create -> score retourne."""
        client, _ = app_client
        # Creer un site minimal
        client.post("/api/sites/quick-create", json={"nom": "TestFlex", "usage": "bureau"})
        resp = client.get("/api/flex/score/sites/1")
        assert resp.status_code == 200
        data = resp.json()
        assert "score_global_site" in data
        assert 0.0 <= data["score_global_site"] <= 1.0
        assert data["n_usages_evalues"] > 0

    def test_portfolio_vide_retourne_200(self, app_client):
        """Portfolio inexistant -> 404."""
        client, _ = app_client
        resp = client.get("/api/flex/score/portfolios/99999")
        assert resp.status_code == 404


class TestFlexScoreUsagesReferentiel:
    """Coherence du referentiel des 15 usages."""

    def test_irve_top_scoreur(self, app_client):
        """IRVE ou BATTERIES en tete du classement."""
        client, _ = app_client
        resp = client.get("/api/flex/score/usages")
        assert resp.status_code == 200
        usages = resp.json()["usages"]
        top = usages[0]
        assert top["score_global"] >= 0.80
        assert top["code"] in ("IRVE", "BATTERIES", "ECS")

    def test_process_continu_nogo(self, app_client):
        """PROCESS_CONTINU doit avoir nogo_nebco=True."""
        client, _ = app_client
        resp = client.get("/api/flex/score/usages")
        usages = resp.json()["usages"]
        continu = next(u for u in usages if u["code"] == "PROCESS_CONTINU")
        assert continu["nogo_nebco"] is True
        assert continu["score_global"] <= 0.35

    def test_15_usages_presents(self, app_client):
        """Exactement 15 usages."""
        client, _ = app_client
        resp = client.get("/api/flex/score/usages")
        assert resp.json()["n_usages"] == 15

    def test_p_max_filtre_nebco(self, app_client):
        """P_max=50 plafonne score NEBCO, P_max=500 ne plafonne pas."""
        client, _ = app_client
        resp_petit = client.get("/api/flex/score/usages", params={"P_max_kw": 50})
        resp_grand = client.get("/api/flex/score/usages", params={"P_max_kw": 500})
        usages_petit = {u["code"]: u for u in resp_petit.json()["usages"]}
        usages_grand = {u["code"]: u for u in resp_grand.json()["usages"]}
        # CVC_HVAC avec P_max petit devrait avoir un score NEBCO plus bas
        assert usages_petit["CVC_HVAC"]["nebco_score"] <= usages_grand["CVC_HVAC"]["nebco_score"]
