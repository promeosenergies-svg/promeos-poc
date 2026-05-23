"""PROMEOS — Tests Sprint P0 Conformité : endpoint GET /api/aper/status.

Sprint P0 (2026-05-20) — doctrine C1.
L'endpoint /api/aper/status alimente l'encart <AperEncart> qui remplace
la page dédiée AperPage.jsx (supprimée). Contrat strict :

  - status ∈ {concerned, not_concerned, to_verify}
  - recommendations ≤ 3
  - source.regulation == "Loi APER" + source.reference non vide
  - pas de champ estimated_penalty_eur / penalty_eur / pvgis
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import (
    Base,
    EntiteJuridique,
    Organisation,
    ParkingType,
    Portefeuille,
    Site,
    TypeSite,
)


VALID_STATUSES = {"concerned", "not_concerned", "to_verify"}


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_org_with_sites(db, *, parking_area_m2=None, parking_type=None, roof_area_m2=None):
    """Seed minimal : org + EJ + portefeuille + 1 site avec attributs APER."""
    org = Organisation(nom="Org APER", type_client="bureau", actif=True, siren="987654321")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ APER", siren="987654321")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF APER")
    db.add(pf)
    db.flush()
    parking_enum = ParkingType(parking_type) if isinstance(parking_type, str) else parking_type
    site = Site(
        nom="Site APER",
        type=TypeSite.BUREAU,
        surface_m2=1000,
        portefeuille_id=pf.id,
        actif=True,
        parking_area_m2=parking_area_m2,
        parking_type=parking_enum,
        roof_area_m2=roof_area_m2,
    )
    db.add(site)
    db.commit()
    db.refresh(org)
    db.refresh(site)
    return org, site


def _hdr(org_id: int) -> dict:
    return {"X-Org-Id": str(org_id)}


# ─── Schéma et invariants génériques ────────────────────────────────────────


def test_aper_status_returns_200(client, db):
    org, _ = _seed_org_with_sites(db, parking_area_m2=None, parking_type=None, roof_area_m2=None)
    res = client.get("/api/aper/status", headers=_hdr(org.id))
    assert res.status_code == 200


def test_aper_status_schema(client, db):
    org, _ = _seed_org_with_sites(db, parking_area_m2=2000, parking_type="outdoor", roof_area_m2=600)
    res = client.get("/api/aper/status", headers=_hdr(org.id))
    payload = res.json()
    for key in ("status", "parking_surface_m2", "reasoning", "missing_data", "recommendations", "source"):
        assert key in payload, f"clé manquante : {key}"
    assert payload["status"] in VALID_STATUSES
    assert isinstance(payload["recommendations"], list)
    assert isinstance(payload["missing_data"], list)
    assert isinstance(payload["source"], dict)


def test_aper_status_recommendations_max_3(client, db):
    org, _ = _seed_org_with_sites(db, parking_area_m2=12000, parking_type="outdoor", roof_area_m2=1000)
    res = client.get("/api/aper/status", headers=_hdr(org.id))
    payload = res.json()
    assert len(payload["recommendations"]) <= 3


def test_aper_status_source_reference_present(client, db):
    org, _ = _seed_org_with_sites(db, parking_area_m2=0, parking_type="outdoor", roof_area_m2=0)
    res = client.get("/api/aper/status", headers=_hdr(org.id))
    src = res.json()["source"]
    assert src.get("regulation") == "Loi APER"
    assert isinstance(src.get("reference"), str) and len(src["reference"]) > 0
    assert "evaluated_at" in src


def test_aper_status_no_penalty_no_pvgis_fields(client, db):
    org, _ = _seed_org_with_sites(db, parking_area_m2=2000, parking_type="outdoor", roof_area_m2=600)
    res = client.get("/api/aper/status", headers=_hdr(org.id))
    payload = res.json()
    forbidden = {
        "estimated_penalty_eur",
        "penalty_eur",
        "penalty_eur_year",
        "penalty_risk",
        "production_annuelle_kwh",
        "pvgis_result",
    }
    assert forbidden.isdisjoint(payload.keys()), f"L'encart ne doit pas exposer : {forbidden & payload.keys()}"


# ─── Statuts métier ─────────────────────────────────────────────────────────


def test_aper_status_concerned_when_parking_outdoor_above_threshold(client, db):
    org, site = _seed_org_with_sites(db, parking_area_m2=2500, parking_type="outdoor", roof_area_m2=100)
    res = client.get(
        "/api/aper/status",
        params={"site_id": site.id},
        headers=_hdr(org.id),
    )
    payload = res.json()
    assert payload["status"] == "concerned"
    assert payload["parking_surface_m2"] == 2500
    assert payload["recommendations"], "doit fournir au moins une reco"


def test_aper_status_not_concerned_when_below_thresholds(client, db):
    org, site = _seed_org_with_sites(db, parking_area_m2=500, parking_type="outdoor", roof_area_m2=100)
    res = client.get(
        "/api/aper/status",
        params={"site_id": site.id},
        headers=_hdr(org.id),
    )
    payload = res.json()
    assert payload["status"] == "not_concerned"
    assert payload["recommendations"] == []


def test_aper_status_to_verify_when_data_missing(client, db):
    org, site = _seed_org_with_sites(db, parking_area_m2=None, parking_type=None, roof_area_m2=None)
    res = client.get(
        "/api/aper/status",
        params={"site_id": site.id},
        headers=_hdr(org.id),
    )
    payload = res.json()
    assert payload["status"] == "to_verify"
    assert "parking_area_m2" in payload["missing_data"]
    assert payload["recommendations"], "doit guider l'utilisateur quand les données manquent"


def test_aper_status_org_level_aggregates(client, db):
    """Sans site_id, l'endpoint retourne un statut agrégé sur l'org."""
    org, _ = _seed_org_with_sites(db, parking_area_m2=2000, parking_type="outdoor", roof_area_m2=600)
    res = client.get("/api/aper/status", headers=_hdr(org.id))
    payload = res.json()
    assert payload["status"] in VALID_STATUSES
    # Au niveau org, parking_surface_m2 est null (agrégat indicatif uniquement).
    assert payload["parking_surface_m2"] is None


def test_aper_status_indoor_parking_not_concerned(client, db):
    """Parking couvert (indoor) ≥ 1 500 m² ne doit PAS rendre concerné."""
    org, site = _seed_org_with_sites(db, parking_area_m2=2500, parking_type="indoor", roof_area_m2=50)
    res = client.get(
        "/api/aper/status",
        params={"site_id": site.id},
        headers=_hdr(org.id),
    )
    payload = res.json()
    assert payload["status"] == "not_concerned"
