"""
test_top_recommendation.py — Tests endpoint GET /api/sites/{id}/top-recommendation.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    TypeSite,
)
from database import get_db
from main import app
from services.demo_state import DemoState


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
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
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_org_site(db, nom="TestOrg"):
    org = Organisation(nom=nom, actif=True)
    db.add(org)
    db.flush()
    siren = str(abs(hash(nom)) % 10**9).zfill(9)
    ej = EntiteJuridique(nom=f"EJ {nom}", organisation_id=org.id, siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom=f"PF {nom}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(nom=f"Site {nom}", type=TypeSite.BUREAU, portefeuille_id=pf.id, actif=True)
    db.add(site)
    db.commit()
    return org, pf, site


class TestTopRecommendation:
    def test_returns_fallback_no_meters(self, client, db):
        """Site sans compteurs → fallback gracieux."""
        org, _, site = _make_org_site(db, "NoMeters")
        resp = client.get(f"/api/sites/{site.id}/top-recommendation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False
        assert data["source"] == "fallback"
        assert "label" in data

    def test_returns_fallback_no_recos(self, client, db):
        """Site avec compteurs mais sans recos → fallback."""
        from models.energy_models import Meter, EnergyVector

        org, _, site = _make_org_site(db, "NoRecos")
        meter = Meter(
            site_id=site.id,
            meter_id="M1-NoRecos",
            name="Meter 1",
            energy_vector=EnergyVector.ELECTRICITY,
        )
        db.add(meter)
        db.commit()

        resp = client.get(f"/api/sites/{site.id}/top-recommendation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False

    def test_returns_kb_with_recos(self, client, db):
        """Site avec recos → retourne top reco avec source=kb."""
        from models.energy_models import Meter, EnergyVector, Recommendation

        org, _, site = _make_org_site(db, "WithRecos")
        meter = Meter(
            site_id=site.id,
            meter_id="M1-WithRecos",
            name="Meter 1",
            energy_vector=EnergyVector.ELECTRICITY,
        )
        db.add(meter)
        db.flush()

        reco = Recommendation(
            meter_id=meter.id,
            recommendation_code="RECO-LED",
            title="Passage LED intégral",
            estimated_savings_eur_year=1500.0,
            estimated_savings_kwh_year=5000.0,
            ice_score=0.504,
            impact_score=7,
            confidence_score=9,
            ease_score=8,
        )
        db.add(reco)
        db.commit()

        resp = client.get(f"/api/sites/{site.id}/top-recommendation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["source"] == "kb"
        assert data["code"] == "RECO-LED"
        assert data["ice_score"] == 0.504
        assert data["savings_eur"] == 1500.0
        assert data["total_recos"] >= 1

    def test_deduplicates_across_meters(self, client, db):
        """Même reco sur 2 compteurs → total_recos=1, savings agrégés."""
        from models.energy_models import Meter, EnergyVector, Recommendation

        org, _, site = _make_org_site(db, "DedupMeters")
        m1 = Meter(site_id=site.id, meter_id="M1-Dedup", name="M1", energy_vector=EnergyVector.ELECTRICITY)
        m2 = Meter(site_id=site.id, meter_id="M2-Dedup", name="M2", energy_vector=EnergyVector.ELECTRICITY)
        db.add_all([m1, m2])
        db.flush()

        r1 = Recommendation(
            meter_id=m1.id,
            recommendation_code="RECO-LED",
            title="LED",
            estimated_savings_eur_year=1000.0,
            ice_score=0.5,
            impact_score=7,
            confidence_score=9,
            ease_score=8,
        )
        r2 = Recommendation(
            meter_id=m2.id,
            recommendation_code="RECO-LED",
            title="LED",
            estimated_savings_eur_year=800.0,
            ice_score=0.45,
            impact_score=7,
            confidence_score=9,
            ease_score=8,
        )
        db.add_all([r1, r2])
        db.commit()

        resp = client.get(f"/api/sites/{site.id}/top-recommendation")
        data = resp.json()
        assert data["available"] is True
        assert data["total_recos"] == 1  # deduplicated
        assert data["savings_eur"] == 1800.0  # aggregated

    def test_site_not_found_404(self, client, db):
        """Site inexistant → 404."""
        resp = client.get("/api/sites/99999/top-recommendation")
        assert resp.status_code == 404
