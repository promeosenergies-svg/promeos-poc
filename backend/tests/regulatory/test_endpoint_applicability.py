"""PROMEOS — Tests Vague A.6 : endpoint /api/regulatory/applicability.

Smoke test intégration avec FastAPI TestClient + DB SQLite in-memory.

Couverture :
  - GET /api/regulatory/applicability répond 200
  - Payload contient les 5 RuleCode keys
  - Payload contient maturity ∈ [0, 1]
  - Payload contient rules_versions (5 entrées)
  - Payload contient computed_at (ISO timestamp)
  - Org-scoping : org_id renvoyé par resolve_org_id
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base, Organisation, Site, TypeSite
from models.entite_juridique import EntiteJuridique
from models.portefeuille import Portefeuille


@pytest.fixture
def env():
    """Isolated SQLite + TestClient environment.

    Construit la hiérarchie complète : Organisation → EntiteJuridique →
    Portefeuille → Site (cf. sites_for_org_query qui joint sur ces 4 niveaux).
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organisation(
        id=1, nom="HELIOS SAS", effectif_total=380, pays="FR", chiffre_affaires_eur=80_000_000.0, is_demo=False
    )
    session.add(org)
    session.flush()
    ej = EntiteJuridique(id=1, organisation_id=1, nom="HELIOS SAS EJ", siren="123456789")
    session.add(ej)
    session.flush()
    pf = Portefeuille(id=1, entite_juridique_id=1, nom="HELIOS Portefeuille")
    session.add(pf)
    session.flush()

    site1 = Site(
        id=10,
        nom="Toulouse Entrepôt",
        type=TypeSite.ENTREPOT,
        portefeuille_id=1,
        surface_m2=2000,
        tertiaire_area_m2=2000,
        usage_principal="BUREAUX",
        parking_area_m2=2000,
        roof_area_m2=500,
        is_demo=False,
    )
    site2 = Site(
        id=11,
        nom="Lyon Petit",
        type=TypeSite.BUREAU,
        portefeuille_id=1,
        surface_m2=850,
        tertiaire_area_m2=850,
        usage_principal="BUREAUX",
        is_demo=False,
    )
    session.add_all([site1, site2])
    session.commit()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    yield client, session
    app.dependency_overrides.clear()
    session.close()


def test_endpoint_returns_200(env):
    client, _ = env
    resp = client.get("/api/regulatory/applicability")
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.text[:300]}"


def test_endpoint_payload_has_5_rules(env):
    client, _ = env
    payload = client.get("/api/regulatory/applicability").json()
    assert set(payload["applicability"].keys()) == {"DT", "BACS", "APER", "SME", "BEGES"}


def test_endpoint_payload_maturity_in_range(env):
    client, _ = env
    payload = client.get("/api/regulatory/applicability").json()
    m = payload["maturity"]
    assert isinstance(m, (int, float))
    assert 0.0 <= m <= 1.0


def test_endpoint_payload_rules_versions(env):
    client, _ = env
    payload = client.get("/api/regulatory/applicability").json()
    versions = payload["rules_versions"]
    assert set(versions.keys()) == {"DT", "BACS", "APER", "SME", "BEGES"}
    assert "DT-2019-771" in versions["DT"]


def test_endpoint_payload_computed_at_iso(env):
    client, _ = env
    payload = client.get("/api/regulatory/applicability").json()
    computed = payload["computed_at"]
    # ISO 8601 doit avoir T et +00:00 ou Z
    assert "T" in computed
    assert ("+" in computed) or computed.endswith("Z")


def test_endpoint_payload_org_id(env):
    client, _ = env
    payload = client.get("/api/regulatory/applicability").json()
    assert payload["org_id"] == 1


def test_endpoint_dt_site_filter(env):
    client, _ = env
    # Sans filtre = 2 sites (DT)
    p_all = client.get("/api/regulatory/applicability").json()
    assert len(p_all["applicability"]["DT"]) == 2
    # Avec filtre = 1 site
    p_one = client.get("/api/regulatory/applicability?site_id=10").json()
    assert len(p_one["applicability"]["DT"]) == 1
    assert p_one["applicability"]["DT"][0]["scope_id"] == 10


def test_endpoint_dt_payload_status_canonical(env):
    """Sanity : site 10 (2000m² BUREAUX) APPLICABLE, site 11 (850m²) NOT_APPLICABLE."""
    client, _ = env
    payload = client.get("/api/regulatory/applicability").json()
    by_id = {e["scope_id"]: e for e in payload["applicability"]["DT"]}
    assert by_id[10]["status"] == "applicable"
    assert by_id[11]["status"] == "not_applicable"


def test_endpoint_sme_applicable_effectif(env):
    """HELIOS effectif 380 → SMÉ APPLICABLE.EFFECTIF."""
    client, _ = env
    payload = client.get("/api/regulatory/applicability").json()
    sme = payload["applicability"]["SME"][0]
    assert sme["status"] == "applicable"
    assert sme["reason_code"] == "SME.APPLICABLE.EFFECTIF"
