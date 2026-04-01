"""
PROMEOS — Tests du pont KB Recommendation → ActionItem.
Couvre : creation via POST /api/actions (source_type=insight),
idempotence (idempotency_key=kb-reco:*), champs CO₂/gain,
dedup, format reponse.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    ActionItem,
    ActionSourceType,
    ActionStatus,
    TypeSite,
)
from database import get_db
from main import app


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


def _seed_org_site(db):
    org = Organisation(nom="KB Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ KB", siren="999888777")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF KB")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site KB Test",
        type=TypeSite.BUREAU,
        surface_m2=500,
        actif=True,
    )
    db.add(site)
    db.flush()
    db.commit()
    return org, site


def _kb_action_payload(org_id, site_id, reco_id=42, reco_code="RECO-LED-001", **overrides):
    """Build a KB reco action payload matching kbRecoActionModel.js output."""
    payload = {
        "org_id": org_id,
        "site_id": site_id,
        "source_type": "insight",
        "source_id": f"kb-reco:{reco_id}",
        "source_key": f"{site_id}:{reco_code}",
        "idempotency_key": f"kb-reco:{site_id}:{reco_code}",
        "title": f"Passage LED integral — Site KB Test",
        "rationale": f"Recommandation : Passage LED integral\nEconomie estimee : 15 000 kWh/an\nSoit ~2 400 \u20ac/an",
        "priority": 3,
        "severity": "medium",
        "estimated_gain_eur": 2400.0,
        "co2e_savings_est_kg": 780.0,  # 15000 * 0.052
        "due_date": "2026-06-01",
        "category": "energie",
    }
    payload.update(overrides)
    return payload


class TestKbActionBridgeCreation:
    """POST /api/actions avec source_type=insight cree bien un ActionItem KB."""

    def test_create_kb_action_returns_200(self, client, db):
        org, site = _seed_org_site(db)
        payload = _kb_action_payload(org.id, site.id)
        resp = client.post("/api/actions", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "open"  # ActionStatus.OPEN

    def test_created_action_has_correct_source_type(self, client, db):
        org, site = _seed_org_site(db)
        payload = _kb_action_payload(org.id, site.id)
        data = client.post("/api/actions", json=payload).json()
        assert data["source_type"] == "insight"

    def test_created_action_has_co2e_savings(self, client, db):
        org, site = _seed_org_site(db)
        payload = _kb_action_payload(org.id, site.id)
        data = client.post("/api/actions", json=payload).json()
        assert data.get("co2e_savings_est_kg") == 780.0

    def test_created_action_has_estimated_gain(self, client, db):
        org, site = _seed_org_site(db)
        payload = _kb_action_payload(org.id, site.id)
        data = client.post("/api/actions", json=payload).json()
        assert data.get("estimated_gain_eur") == 2400.0

    def test_created_action_has_idempotency_key_in_db(self, client, db):
        org, site = _seed_org_site(db)
        payload = _kb_action_payload(org.id, site.id)
        data = client.post("/api/actions", json=payload).json()
        action = db.query(ActionItem).filter(ActionItem.id == data["id"]).first()
        assert action.idempotency_key == f"kb-reco:{site.id}:RECO-LED-001"


class TestKbActionBridgeIdempotence:
    """Idempotence : 2x POST avec meme idempotency_key = 1 seul ActionItem."""

    def test_second_post_returns_same_action(self, client, db):
        """Idempotence : 2e POST retourne le meme ActionItem sans en creer un nouveau."""
        org, site = _seed_org_site(db)
        payload = _kb_action_payload(org.id, site.id)
        data1 = client.post("/api/actions", json=payload).json()
        data2 = client.post("/api/actions", json=payload).json()
        assert data1["id"] == data2["id"]
        # Verify only 1 action in DB
        count = db.query(ActionItem).filter(ActionItem.idempotency_key == payload["idempotency_key"]).count()
        assert count == 1

    def test_idempotent_returns_same_id(self, client, db):
        org, site = _seed_org_site(db)
        payload = _kb_action_payload(org.id, site.id)
        data1 = client.post("/api/actions", json=payload).json()
        data2 = client.post("/api/actions", json=payload).json()
        assert data1["id"] == data2["id"]

    def test_different_reco_creates_different_action(self, client, db):
        org, site = _seed_org_site(db)
        p1 = _kb_action_payload(org.id, site.id, reco_id=1, reco_code="RECO-LED-001")
        p2 = _kb_action_payload(org.id, site.id, reco_id=2, reco_code="RECO-BACS-002")
        d1 = client.post("/api/actions", json=p1).json()
        d2 = client.post("/api/actions", json=p2).json()
        assert d1["id"] != d2["id"]
        assert d1["source_type"] == "insight"
        assert d2["source_type"] == "insight"


class TestKbRecoStatusUpdate:
    """Creation d'action KB marque la reco comme IN_PROGRESS."""

    def test_reco_status_updated_to_in_progress(self, client, db):
        from models.energy_models import Recommendation, RecommendationStatus, Meter

        org, site = _seed_org_site(db)
        # Seed a meter + recommendation
        meter = Meter(site_id=site.id, meter_id="PDL-TEST-001", name="Meter Test")
        db.add(meter)
        db.flush()
        reco = Recommendation(
            meter_id=meter.id,
            recommendation_code="RECO-TEST-STATUS",
            title="Test reco status",
            status=RecommendationStatus.PENDING,
        )
        db.add(reco)
        db.commit()

        payload = _kb_action_payload(
            org.id,
            site.id,
            reco_id=reco.id,
            reco_code="RECO-TEST-STATUS",
        )
        client.post("/api/actions", json=payload)
        db.refresh(reco)
        assert reco.status == RecommendationStatus.IN_PROGRESS

    def test_reco_already_in_progress_not_changed(self, client, db):
        from models.energy_models import Recommendation, RecommendationStatus, Meter

        org, site = _seed_org_site(db)
        meter = Meter(site_id=site.id, meter_id="PDL-TEST-002", name="Meter Test 2")
        db.add(meter)
        db.flush()
        reco = Recommendation(
            meter_id=meter.id,
            recommendation_code="RECO-TEST-NOOP",
            title="Test reco noop",
            status=RecommendationStatus.IN_PROGRESS,
        )
        db.add(reco)
        db.commit()

        payload = _kb_action_payload(org.id, site.id, reco_id=reco.id, reco_code="RECO-TEST-NOOP")
        client.post("/api/actions", json=payload)
        db.refresh(reco)
        assert reco.status == RecommendationStatus.IN_PROGRESS


class TestKbActionBridgeSourceGuard:
    """Le facteur CO₂ est bien 0.052 (ADEME), pas 0.0569 (TURPE)."""

    def test_emission_factor_is_ademe_052(self):
        from config.emission_factors import get_emission_factor

        factor = get_emission_factor("ELEC")
        assert factor == 0.052, f"get_emission_factor('ELEC') = {factor}, attendu 0.052"

    def test_co2e_matches_kwh_times_052(self, client, db):
        """15000 kWh * 0.052 = 780 kgCO₂e — verifie la coherence frontend/backend."""
        org, site = _seed_org_site(db)
        payload = _kb_action_payload(org.id, site.id, co2e_savings_est_kg=780.0)
        data = client.post("/api/actions", json=payload).json()
        assert data["co2e_savings_est_kg"] == 780.0
