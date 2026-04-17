"""
PROMEOS - Tests scoring portefeuille multi-sites (Piste 3 V1).

Couvre :
    1. Top-10 trie par score decroissant
    2. Heatmap archetype : nb_sites + gain_total coherents
    3. Gain portefeuille = somme des gains top_10 (portefeuille <= 10 sites)
    4. Endpoint /portefeuille-scoring : 200 + schema Pydantic valide
    5. Portefeuille vide -> nb=0, gain=0, top_10=[]
    6. Rangs sequentiels (1, 2, 3, ...)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from middleware.auth import AuthContext, get_optional_auth
from models import Base
from services.pilotage.portefeuille_scoring import compute_portefeuille_scoring


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """TestClient avec DB SQLite in-memory — isolation totale."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def _override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    os.environ["PROMEOS_DEMO_MODE"] = "true"
    app.dependency_overrides[get_db] = _override
    c = TestClient(app, raise_server_exceptions=False)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_portfolio() -> list[dict]:
    """Portefeuille test de 3 sites, archetypes calibrés Baromètre Flex 2026."""
    return [
        {
            "site_id": "retail-001",
            "archetype_code": "COMMERCE_ALIMENTAIRE",
            "puissance_pilotable_kw": 220.0,
        },
        {
            "site_id": "bureau-001",
            "archetype_code": "BUREAU_STANDARD",
            "puissance_pilotable_kw": 120.0,
        },
        {
            "site_id": "entrepot-001",
            "archetype_code": "LOGISTIQUE_FRIGO",
            "puissance_pilotable_kw": 85.0,
        },
    ]


# ---------------------------------------------------------------------------
# Test 1 : Top-10 trie par score decroissant
# ---------------------------------------------------------------------------
def test_top10_trie_score_decroissant(sample_portfolio):
    result = compute_portefeuille_scoring(sample_portfolio)
    top = result["top_10"]
    assert len(top) == 3, "portefeuille 3 sites -> top_10 contient 3 lignes"
    scores = [row["score"] for row in top]
    assert scores == sorted(scores, reverse=True), f"top_10 doit etre trie par score DESC, obtenu {scores}"
    # Sanity check calibrage : COMMERCE_ALIMENTAIRE et LOGISTIQUE_FRIGO ont
    # les plus hauts taux_decalable (0.45 / 0.55) donc scorent > BUREAU_STANDARD.
    archetypes_order = [row["archetype"] for row in top]
    assert archetypes_order[-1] == "BUREAU_STANDARD", f"BUREAU_STANDARD doit etre dernier, ordre : {archetypes_order}"


# ---------------------------------------------------------------------------
# Test 2 : Heatmap archetype agrege correctement
# ---------------------------------------------------------------------------
def test_heatmap_agregation(sample_portfolio):
    result = compute_portefeuille_scoring(sample_portfolio)
    heatmap = result["heatmap_archetype"]

    assert set(heatmap.keys()) == {
        "COMMERCE_ALIMENTAIRE",
        "BUREAU_STANDARD",
        "LOGISTIQUE_FRIGO",
    }

    for archetype, bucket in heatmap.items():
        assert bucket["nb_sites"] == 1, f"{archetype}: 1 site attendu, obtenu {bucket['nb_sites']}"
        assert bucket["gain_total_eur"] > 0
        assert 0.0 <= bucket["score_moyen"] <= 100.0

    # Portefeuille dupliqué → aggregation cumulative
    doubled = sample_portfolio + [
        {
            "site_id": "bureau-002",
            "archetype_code": "BUREAU_STANDARD",
            "puissance_pilotable_kw": 60.0,
        }
    ]
    result2 = compute_portefeuille_scoring(doubled)
    assert result2["heatmap_archetype"]["BUREAU_STANDARD"]["nb_sites"] == 2
    # gain cumulé = gain 120 kW + gain 60 kW, mêmes heures/spread
    gain_cumulatif = result2["heatmap_archetype"]["BUREAU_STANDARD"]["gain_total_eur"]
    assert gain_cumulatif == pytest.approx(
        result["heatmap_archetype"]["BUREAU_STANDARD"]["gain_total_eur"] + round(60.0 * 900 * 0.08)
    )


# ---------------------------------------------------------------------------
# Test 3 : Gain portefeuille = somme des gains top_10
# ---------------------------------------------------------------------------
def test_gain_portefeuille_somme_top10(sample_portfolio):
    """Pour un portefeuille <= 10 sites, gain_portefeuille == sum(top_10)."""
    result = compute_portefeuille_scoring(sample_portfolio)
    somme_top = sum(row["gain_annuel_eur"] for row in result["top_10"])
    assert result["gain_annuel_portefeuille_eur"] == pytest.approx(somme_top)
    # Somme > 0 puisque les 3 sites ont puissance_pilotable > 0
    assert result["gain_annuel_portefeuille_eur"] > 0


# ---------------------------------------------------------------------------
# Test 4 : Endpoint retourne 200 + schema Pydantic
# ---------------------------------------------------------------------------
def test_endpoint_retourne_200_et_schema_valide(client):
    r = client.get("/api/pilotage/portefeuille-scoring")
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    data = r.json()

    # Schema top-level
    assert data["nb_sites_total"] == 3
    assert data["gain_annuel_portefeuille_eur"] > 0
    assert isinstance(data["top_10"], list)
    assert len(data["top_10"]) == 3
    assert "Baromètre Flex 2026" in data["source"]

    # Chaque ligne top_10 a les bons champs + bornes
    for row in data["top_10"]:
        assert set(row.keys()) >= {
            "site_id",
            "archetype",
            "score",
            "gain_annuel_eur",
            "rang",
        }
        assert 0.0 <= row["score"] <= 100.0
        assert row["gain_annuel_eur"] >= 0.0
        assert row["rang"] >= 1

    # Heatmap : 1 entree par archetype demo
    assert set(data["heatmap_archetype"].keys()) == {
        "COMMERCE_ALIMENTAIRE",
        "BUREAU_STANDARD",
        "LOGISTIQUE_FRIGO",
    }


# ---------------------------------------------------------------------------
# Test 5 : Portefeuille vide -> payload zero-consistent
# ---------------------------------------------------------------------------
def test_portefeuille_vide():
    result = compute_portefeuille_scoring([])
    assert result["nb_sites_total"] == 0
    assert result["gain_annuel_portefeuille_eur"] == 0
    assert result["top_10"] == []
    assert result["heatmap_archetype"] == {}
    assert "Baromètre Flex 2026" in result["source"]


# ---------------------------------------------------------------------------
# Test 6 : Rangs sequentiels (1, 2, 3, ...)
# ---------------------------------------------------------------------------
def test_rangs_sequentiels():
    """top_10 doit porter des rangs 1..N sans trou."""
    # 12 sites pour vérifier qu'on capte bien seulement les 10 premiers
    sites = [
        {
            "site_id": f"s-{i:03d}",
            "archetype_code": "BUREAU_STANDARD",
            "puissance_pilotable_kw": 50.0 + i,  # gain croissant par site_id
        }
        for i in range(12)
    ]
    result = compute_portefeuille_scoring(sites)
    top = result["top_10"]
    assert len(top) == 10, "top_10 plafonne à 10 lignes"
    rangs = [row["rang"] for row in top]
    assert rangs == list(range(1, 11)), f"rangs doivent etre 1..10, obtenu {rangs}"

    # nb_sites_total = tous (12), pas seulement le top_10
    assert result["nb_sites_total"] == 12

    # Fallback archetype INCONNU = pas d'archetype -> fallback 50
    sites_inconnu = [
        {
            "site_id": "s-unknown",
            "archetype_code": None,
            "puissance_pilotable_kw": 100.0,
        }
    ]
    result_unknown = compute_portefeuille_scoring(sites_inconnu)
    assert result_unknown["top_10"][0]["score"] == pytest.approx(50.0), (
        f"archetype None -> fallback score 50, obtenu {result_unknown['top_10'][0]['score']}"
    )
    assert result_unknown["top_10"][0]["rang"] == 1


# ---------------------------------------------------------------------------
# Test 7 : auth avec org_id mais aucun site -> payload vide (pas DEMO)
# ---------------------------------------------------------------------------
def test_authenticated_user_without_sites_returns_empty(monkeypatch):
    """
    Fix P1 #2 audit PR #222 : un utilisateur authentifie avec org_id mais
    site_ids vide ne doit PAS voir les donnees DEMO_SITES. Payload vide.

    On s'assure aussi que PROMEOS_DEMO_MODE n'est pas "true" pour ce test
    (sinon le fallback DEMO est autorise explicitement).
    """
    monkeypatch.delenv("PROMEOS_DEMO_MODE", raising=False)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def _override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _fake_auth():
        # Auth authentique avec org_id set mais site_ids vide (pilote pre-seed).
        # user/user_org_role/role ne sont pas utilises par l'endpoint.
        return AuthContext(
            user=None,
            user_org_role=None,
            org_id=42,
            role=None,
            site_ids=[],
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_optional_auth] = _fake_auth
    try:
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/api/pilotage/portefeuille-scoring")
        assert r.status_code == 200
        data = r.json()
        assert data["nb_sites_total"] == 0
        assert data["gain_annuel_portefeuille_eur"] == 0
        assert data["top_10"] == []
        assert data["heatmap_archetype"] == {}
    finally:
        app.dependency_overrides.clear()
