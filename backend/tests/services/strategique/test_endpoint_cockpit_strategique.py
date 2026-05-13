"""PROMEOS — Tests Vague C.6 : endpoint GET /api/cockpit/strategique.

Smoke intégration TestClient + SQLite in-memory, scénarios :
  - HELIOS-like (DT APPLICABLE + SMÉ) → REGULATORY_DRIVEN ou fallback
  - MERIDIAN-like (DT NOT_APPLICABLE) → PERFORMANCE_DRIVEN
  - Onboarding-like (maturité faible) → DATA_INSUFFICIENT
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
from models.batiment import Batiment
from models.entite_juridique import EntiteJuridique
from models.portefeuille import Portefeuille


def _make_env(*, scenario: str):
    """Construit un env SQLite selon le scénario demandé."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organisation(
        id=1, nom="ACME", effectif_total=380, pays="FR", chiffre_affaires_eur=80_000_000.0, is_demo=False
    )
    session.add(org)
    session.flush()
    ej = EntiteJuridique(id=1, organisation_id=1, nom="ACME EJ", siren="123456789")
    session.add(ej)
    session.flush()
    pf = Portefeuille(id=1, entite_juridique_id=1, nom="ACME Portefeuille")
    session.add(pf)
    session.flush()

    if scenario == "helios":
        # 2 sites, surfaces tertiaires renseignées, DT APPLICABLE
        s1 = Site(
            id=10,
            nom="Site A",
            type=TypeSite.BUREAU,
            portefeuille_id=1,
            surface_m2=2000,
            tertiaire_area_m2=2000,
            usage_principal="BUREAUX",
            parking_area_m2=2000,
            roof_area_m2=500,
            is_demo=False,
        )
        s2 = Site(
            id=11,
            nom="Site B",
            type=TypeSite.BUREAU,
            portefeuille_id=1,
            surface_m2=1500,
            tertiaire_area_m2=1500,
            usage_principal="BUREAUX",
            parking_area_m2=1800,
            roof_area_m2=400,
            is_demo=False,
        )
        b1 = Batiment(id=100, site_id=10, nom="Bât A1", surface_m2=2000, cvc_power_kw=150)
        b2 = Batiment(id=101, site_id=11, nom="Bât B1", surface_m2=1500, cvc_power_kw=120)
        session.add_all([s1, s2, b1, b2])
    elif scenario == "meridian":
        # Sites trop petits pour DT, mais maturité haute
        s1 = Site(
            id=20,
            nom="Site M1",
            type=TypeSite.BUREAU,
            portefeuille_id=1,
            surface_m2=800,
            tertiaire_area_m2=800,
            usage_principal="BUREAUX",
            parking_area_m2=500,
            roof_area_m2=200,
            is_demo=False,
        )
        s2 = Site(
            id=21,
            nom="Site M2",
            type=TypeSite.BUREAU,
            portefeuille_id=1,
            surface_m2=600,
            tertiaire_area_m2=600,
            usage_principal="BUREAUX",
            parking_area_m2=400,
            roof_area_m2=150,
            is_demo=False,
        )
        b1 = Batiment(id=200, site_id=20, nom="Bât M1", surface_m2=800, cvc_power_kw=30)
        b2 = Batiment(id=201, site_id=21, nom="Bât M2", surface_m2=600, cvc_power_kw=25)
        session.add_all([s1, s2, b1, b2])
    elif scenario == "onboarding":
        # Maturité très faible : sites sans surfaces ni bâtiments
        s1 = Site(id=30, nom="Site O1", type=TypeSite.BUREAU, portefeuille_id=1, is_demo=False)
        s2 = Site(id=31, nom="Site O2", type=TypeSite.BUREAU, portefeuille_id=1, is_demo=False)
        session.add_all([s1, s2])
        org.effectif_total = None
        org.chiffre_affaires_eur = None
    session.commit()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    return client, session


@pytest.fixture
def helios_env():
    client, session = _make_env(scenario="helios")
    yield client, session
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def meridian_env():
    client, session = _make_env(scenario="meridian")
    yield client, session
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def onboarding_env():
    client, session = _make_env(scenario="onboarding")
    yield client, session
    app.dependency_overrides.clear()
    session.close()


# ── Smoke 200 ────────────────────────────────────────────────────────────


def test_endpoint_200_helios(helios_env):
    client, _ = helios_env
    resp = client.get("/api/cockpit/strategique")
    assert resp.status_code == 200, resp.text[:300]


def test_endpoint_200_meridian(meridian_env):
    client, _ = meridian_env
    resp = client.get("/api/cockpit/strategique")
    assert resp.status_code == 200, resp.text[:300]


def test_endpoint_200_onboarding(onboarding_env):
    client, _ = onboarding_env
    resp = client.get("/api/cockpit/strategique")
    assert resp.status_code == 200, resp.text[:300]


# ── Mode discrimination ────────────────────────────────────────────────


def test_helios_mode_is_regulatory(helios_env):
    """HELIOS scenario : DT APPLICABLE → REGULATORY_DRIVEN."""
    client, _ = helios_env
    payload = client.get("/api/cockpit/strategique").json()
    assert payload["strategic_mode"] == "regulatory_driven"
    assert payload["_audit"]["effective_mode"] == "regulatory_driven"


def test_meridian_mode_is_performance(meridian_env):
    """MERIDIAN : sites trop petits + maturité haute → PERFORMANCE."""
    client, _ = meridian_env
    payload = client.get("/api/cockpit/strategique").json()
    assert payload["strategic_mode"] == "performance_driven"


def test_onboarding_mode_is_data_insufficient(onboarding_env):
    """Onboarding : sites vides + org incomplète → DATA_INSUFFICIENT."""
    client, _ = onboarding_env
    payload = client.get("/api/cockpit/strategique").json()
    assert payload["strategic_mode"] == "data_insufficient"


# ── Schéma cardinal ADR-023 §3 ─────────────────────────────────────────


REQUIRED_KEYS = {
    "strategic_mode",
    "applicability",
    "patrimoine_maturity",
    "verdict",
    "hero",
    "kpis",
    "charts",
    "dossier_p1",
    "queue_p2_p3",
    "continuity",
    "footer",
    "_audit",
}


def test_helios_payload_schema(helios_env):
    client, _ = helios_env
    payload = client.get("/api/cockpit/strategique").json()
    assert set(payload.keys()) >= REQUIRED_KEYS
    assert len(payload["kpis"]) == 3
    assert len(payload["charts"]) == 2


def test_meridian_payload_schema(meridian_env):
    client, _ = meridian_env
    payload = client.get("/api/cockpit/strategique").json()
    assert set(payload.keys()) >= REQUIRED_KEYS
    assert len(payload["kpis"]) == 3
    assert len(payload["charts"]) == 2


def test_onboarding_payload_schema(onboarding_env):
    client, _ = onboarding_env
    payload = client.get("/api/cockpit/strategique").json()
    assert set(payload.keys()) >= REQUIRED_KEYS


# ── Persona param ──────────────────────────────────────────────────────


def test_persona_param_propagated(helios_env):
    client, _ = helios_env
    payload = client.get("/api/cockpit/strategique?persona=daf").json()
    assert payload["hero"]["meta"]["persona"] == "daf"


def test_persona_default_dg_comex(helios_env):
    client, _ = helios_env
    payload = client.get("/api/cockpit/strategique").json()
    assert payload["hero"]["meta"]["persona"] == "dg_comex"
