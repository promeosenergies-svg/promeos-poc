"""Tests endpoint public diagnostic — P2 wedge Sirene (acquisition freemium).

Couvre :
  - Validation SIREN (format 9 chiffres)
  - 404 si SIREN introuvable + hydrate échoué
  - Succès : lead_score + compliance_preview pour SIREN hydraté
  - Pydantic extra=forbid (drift detection)
  - Heuristique CBAM potentiel via NAF codes industriels
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base


@pytest.fixture
def _public_client():
    """Client FastAPI avec DB SQLite in-memory + SIREN hydraté fictif."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    def _seed(siren: str, denom: str, naf: str, categorie: str = "ETI", n_etabs: int = 5):
        from models.sirene import SireneEtablissement, SireneUniteLegale

        snapshot = date(2026, 4, 1)
        ul = SireneUniteLegale(
            siren=siren,
            denomination=denom,
            categorie_entreprise=categorie,
            activite_principale=naf,
            etat_administratif="A",
            statut_diffusion="O",
            snapshot_date=snapshot,
        )
        db.add(ul)
        for i in range(n_etabs):
            nic = f"{i:05d}"
            etab = SireneEtablissement(
                siret=f"{siren}{nic}",
                siren=siren,
                nic=nic,
                etat_administratif="A",
                snapshot_date=snapshot,
            )
            db.add(etab)
        db.flush()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    client = TestClient(app, raise_server_exceptions=False)
    yield client, db, _seed
    app.dependency_overrides.clear()


# ──────────────────────────────────── Validation ────────────────────────────────────


def test_diagnostic_siren_invalide_400(_public_client):
    client, _, _ = _public_client
    for bad in ["abc", "123", "1234567890", "12345678A"]:
        r = client.get(f"/api/public/diagnostic/{bad}")
        assert r.status_code == 400, f"SIREN '{bad}' devrait être rejeté"
        assert r.json()["detail"]["code"] == "INVALID_SIREN"


def test_diagnostic_siren_introuvable_404(_public_client):
    """SIREN absent local + hydratation live qui échoue → 404."""
    client, _, _ = _public_client
    with patch("services.sirene_hydrate.hydrate_siren_from_api", side_effect=Exception("API down")):
        r = client.get("/api/public/diagnostic/999999999")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "SIREN_NOT_FOUND"


# ──────────────────────────────────── Succès ────────────────────────────────────


def test_diagnostic_succes_eti_tertiaire(_public_client):
    """ETI tertiaire (NAF bureau) → segment ETI + compliance décret + CBAM non-potentiel."""
    client, _, seed = _public_client
    # NAF 68.20B = location de terrains et autres biens immobiliers (tertiaire)
    seed("123456789", "Test ETI Tertiaire SA", "68.20B", categorie="ETI", n_etabs=10)

    r = client.get("/api/public/diagnostic/123456789")
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["siren"] == "123456789"
    assert data["denomination"] == "Test ETI Tertiaire SA"
    assert data["naf_code"] == "68.20B"
    assert data["n_etablissements_actifs"] == 10

    # Lead score
    assert data["lead_score"]["segment"] == "ETI"
    assert data["lead_score"]["priority"] in {"A", "B", "C"}
    assert data["lead_score"]["mrr_estime_eur_mois"] > 0

    # Compliance preview : ETI tertiaire → décret + BACS probables, CBAM non
    assert data["compliance_preview"]["decret_tertiaire_applicable"] is True
    assert data["compliance_preview"]["bacs_applicable"] is True
    assert data["compliance_preview"]["cbam_potentiel"] is False
    # Coût d'inaction estimé > 0 sur segment ETI
    assert data["compliance_preview"]["estimated_annual_exposure_eur"] > 0

    # Source tracée
    assert "Sirene INSEE" in data["source"]
    assert "CBAM" in data["source"]


def test_diagnostic_cbam_potentiel_sur_naf_metallurgie(_public_client):
    """NAF 24.xx (métallurgie) → cbam_potentiel=True + exposition ×1.5."""
    client, _, seed = _public_client
    seed("987654321", "Aciérie Test", "24.10Z", categorie="GE", n_etabs=50)

    r = client.get("/api/public/diagnostic/987654321")
    assert r.status_code == 200
    data = r.json()

    assert data["compliance_preview"]["cbam_potentiel"] is True
    # Exposition GE = 150k × 1.5 = 225k (vs 150k sans CBAM)
    assert data["compliance_preview"]["estimated_annual_exposure_eur"] == pytest.approx(150_000 * 1.5, rel=1e-3)


def test_diagnostic_tpe_faible_exposition(_public_client):
    """TPE mono-site → segment TPE + exposition faible (2 500 EUR)."""
    client, _, seed = _public_client
    seed("111111111", "TPE Commerce", "47.11F", categorie="PME", n_etabs=1)

    r = client.get("/api/public/diagnostic/111111111")
    assert r.status_code == 200
    data = r.json()

    # PME avec 1 établissement → segment reclassé TPE par `_resolve_segment`
    assert data["lead_score"]["segment"] == "TPE"
    assert data["compliance_preview"]["estimated_annual_exposure_eur"] == 2_500.0


# ──────────────────────────────────── Contract ────────────────────────────────────


def test_diagnostic_schema_exhaustif(_public_client):
    """Payload expose les clés contractuelles (pour widget embeddable)."""
    client, _, seed = _public_client
    seed("222222222", "Schema Test", "68.20B")
    r = client.get("/api/public/diagnostic/222222222")
    assert r.status_code == 200
    data = r.json()

    # Top-level
    for key in (
        "siren",
        "denomination",
        "categorie_insee",
        "naf_code",
        "naf_label",
        "n_etablissements_actifs",
        "lead_score",
        "compliance_preview",
        "source",
    ):
        assert key in data

    # lead_score
    for key in ("segment", "priority", "mrr_estime_eur_mois", "naf_value_tier", "drivers"):
        assert key in data["lead_score"]

    # compliance_preview
    for key in (
        "decret_tertiaire_applicable",
        "bacs_applicable",
        "cbam_potentiel",
        "estimated_annual_exposure_eur",
        "note",
    ):
        assert key in data["compliance_preview"]


def test_diagnostic_endpoint_ne_requiert_pas_auth(_public_client):
    """Endpoint `/api/public/*` accessible sans Authorization header."""
    client, _, seed = _public_client
    seed("333333333", "No Auth Test", "68.20B")
    # Pas de header Authorization → doit passer
    r = client.get("/api/public/diagnostic/333333333")
    assert r.status_code == 200
