"""
PROMEOS - Tests endpoint ROI Flex Ready (R) (Piste 2 V1 innovation).

Couvre :
    1. Gain total = somme des 3 composantes
    2. Composantes toutes >= 0 (pas de gain negatif)
    3. 404 si site absent de DEMO_SITES
    4. Archetype inconnu -> fallback BUREAU_STANDARD
    5. CEE = surface_m2 x 3,5 EUR/m2
    6. Endpoint retourne un schema Pydantic valide (RoiFlexReadyResponse)
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
from models import Base
from routes.pilotage import DEMO_SITES, RoiFlexReadyResponse
from services.pilotage.roi_flex_ready import (
    CEE_BACS_EUR_M2,
    compute_roi_flex_ready,
)


@pytest.fixture
def client():
    """TestClient avec DB SQLite in-memory -- isolation totale."""
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

    app.dependency_overrides[get_db] = _override
    c = TestClient(app, raise_server_exceptions=False)
    yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 1 : gain total = somme des 3 composantes
# ---------------------------------------------------------------------------
def test_roi_gain_total_est_somme_composantes():
    """Le gain annuel total doit etre la somme exacte des 3 composantes."""
    ctx = DEMO_SITES["retail-001"]
    result = compute_roi_flex_ready(
        site_id="retail-001",
        demo_site=ctx,
        archetype_code="COMMERCE_ALIMENTAIRE",
    )
    composantes = result["composantes"]
    somme = composantes["evitement_pointe_eur"] + composantes["decalage_nebco_eur"] + composantes["cee_bacs_eur"]
    # Les 3 composantes et le total sont arrondis a 2 decimales.
    # L'egalite peut porter une erreur d'arrondi < 0.01 ; on tolere ce delta.
    assert abs(result["gain_annuel_total_eur"] - round(somme, 2)) < 0.02


# ---------------------------------------------------------------------------
# Test 2 : toutes les composantes sont >= 0
# ---------------------------------------------------------------------------
def test_roi_composantes_toutes_positives_ou_zero():
    """Aucune composante ne peut etre negative (garde-fou sanity)."""
    for site_id, ctx in DEMO_SITES.items():
        result = compute_roi_flex_ready(
            site_id=site_id,
            demo_site=ctx,
            archetype_code=ctx.get("archetype_code"),
        )
        for name, value in result["composantes"].items():
            assert value >= 0, f"{site_id}/{name} negatif : {value}"
        assert result["gain_annuel_total_eur"] >= 0


# ---------------------------------------------------------------------------
# Test 3 : site inconnu -> 404
# ---------------------------------------------------------------------------
def test_roi_site_inconnu_retourne_404(client):
    """Un site_id absent de DEMO_SITES doit renvoyer 404 avec message explicite."""
    r = client.get("/api/pilotage/roi-flex-ready/inexistant-999")
    assert r.status_code == 404
    payload = r.json()
    # Tolerance sur le format d'erreur (APIError vs detail brut).
    msg = payload.get("detail") or payload.get("message") or ""
    assert "inexistant-999" in msg, f"Payload 404 inattendu : {payload!r}"


# ---------------------------------------------------------------------------
# Test 4 : archetype inconnu -> fallback BUREAU_STANDARD
# ---------------------------------------------------------------------------
def test_roi_archetype_inconnu_fallback_bureau_standard():
    """Un archetype_code inconnu doit retomber sur BUREAU_STANDARD, pas crasher."""
    ctx = dict(DEMO_SITES["bureau-001"])
    result = compute_roi_flex_ready(
        site_id="bureau-001",
        demo_site=ctx,
        archetype_code="ARCHETYPE_FANTAISISTE_XYZ",
    )
    assert result["archetype"] == "BUREAU_STANDARD"
    # Les 3 composantes doivent etre calculees avec le calibrage BUREAU_STANDARD
    assert result["composantes"]["evitement_pointe_eur"] > 0
    assert result["composantes"]["decalage_nebco_eur"] > 0
    assert result["composantes"]["cee_bacs_eur"] > 0


# ---------------------------------------------------------------------------
# Test 5 : CEE = m2 x 3,5
# ---------------------------------------------------------------------------
def test_roi_cee_bacs_formule():
    """La composante CEE doit valoir surface_m2 x CEE_BACS_EUR_M2 (3,5)."""
    ctx = DEMO_SITES["retail-001"]
    result = compute_roi_flex_ready(
        site_id="retail-001",
        demo_site=ctx,
        archetype_code="COMMERCE_ALIMENTAIRE",
    )
    surface = float(ctx["surface_m2"])
    attendu = round(surface * CEE_BACS_EUR_M2, 2)
    assert result["composantes"]["cee_bacs_eur"] == attendu
    # Sanity : retail-001 = 2500 m2 * 3,5 = 8750 EUR
    assert result["composantes"]["cee_bacs_eur"] == 8750.0


# ---------------------------------------------------------------------------
# Test 6 : endpoint retourne un schema Pydantic valide
# ---------------------------------------------------------------------------
def test_roi_endpoint_schema_pydantic_valide(client):
    """L'endpoint doit retourner un payload conforme a RoiFlexReadyResponse."""
    r = client.get("/api/pilotage/roi-flex-ready/retail-001")
    assert r.status_code == 200, f"Status inattendu : {r.status_code} -- {r.text}"
    data = r.json()

    # Validation Pydantic explicite : erreur d'assertion claire en cas de derive schema.
    parsed = RoiFlexReadyResponse.model_validate(data)
    assert parsed.site_id == "retail-001"
    assert parsed.archetype == "COMMERCE_ALIMENTAIRE"
    assert parsed.gain_annuel_total_eur > 0
    assert parsed.confiance == "indicative"
    assert "Barometre Flex 2026" in parsed.source
    # Les 3 composantes doivent etre presentes
    assert parsed.composantes.evitement_pointe_eur >= 0
    assert parsed.composantes.decalage_nebco_eur >= 0
    assert parsed.composantes.cee_bacs_eur >= 0
    # Hypotheses doivent exposer les parametres MVP attendus
    assert parsed.hypotheses["cee_bacs_eur_m2"] == CEE_BACS_EUR_M2
    assert parsed.hypotheses["heures_fenetres_favorables_an"] == 200
    assert parsed.hypotheses["spread_moyen_eur_mwh"] == 60
