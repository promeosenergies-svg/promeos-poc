"""Tests pour l'endpoint /api/sites/{site_id}/intelligence"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models.base import Base
from database import get_db
from main import app
from models import Site, Meter
from models.energy_models import UsageProfile, Anomaly, Recommendation
from models.kb_models import KBArchetype, KBVersion, KBStatus, KBConfidence
from models.energy_models import AnomalySeverity, RecommendationStatus
from datetime import datetime, timedelta


@pytest.fixture
def db_session():
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
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_site_with_intelligence(db):
    """Seed a site with KB archetype, anomalies, and recommendations."""
    # KB version
    ver = KBVersion(
        doc_id="TEST",
        version="1.0",
        date="2025-01-01",
        source_path="test",
        source_sha256="a" * 64,
        author="test",
        description="test",
        is_active=True,
        status=KBStatus.VALIDATED,
    )
    db.add(ver)
    db.flush()

    # Archetype
    arch = KBArchetype(
        code="BUREAU_STANDARD",
        title="Bureau standard",
        kwh_m2_min=150,
        kwh_m2_max=250,
        kwh_m2_avg=200,
        confidence=KBConfidence.HIGH,
        status=KBStatus.VALIDATED,
        kb_version_id=ver.id,
        source_section="test",
    )
    db.add(arch)
    db.flush()

    # Site
    site = Site(nom="Test Site", type="BUREAU", surface_m2=1000, actif=True, naf_code="6820B")
    db.add(site)
    db.flush()

    # Meter
    meter = Meter(meter_id="M1", name="Compteur 1", energy_vector="ELECTRICITY", site_id=site.id)
    db.add(meter)
    db.flush()

    # Usage profile
    now = datetime.utcnow()
    profile = UsageProfile(
        meter_id=meter.id,
        archetype_id=arch.id,
        archetype_code="BUREAU_STANDARD",
        archetype_match_score=0.85,
        period_start=now - timedelta(days=90),
        period_end=now,
    )
    db.add(profile)

    # Anomaly
    anom = Anomaly(
        meter_id=meter.id,
        anomaly_code="RULE-BASE-NUIT-001",
        title="Talon nocturne excessif",
        severity=AnomalySeverity.HIGH,
        confidence=0.9,
        is_active=True,
        deviation_pct=35.0,
        measured_value=0.45,
        threshold_value=0.25,
    )
    db.add(anom)

    # Recommendation
    reco = Recommendation(
        meter_id=meter.id,
        recommendation_code="RECO-ECLAIRAGE-LED",
        title="Passage LED integral",
        status=RecommendationStatus.PENDING,
        ice_score=0.504,
        impact_score=7,
        confidence_score=9,
        ease_score=8,
        estimated_savings_pct=45.0,
    )
    db.add(reco)
    db.commit()

    return site


class TestSiteIntelligenceEndpoint:
    def test_returns_200_for_valid_site(self, client, db_session):
        site = _seed_site_with_intelligence(db_session)
        resp = client.get(f"/api/sites/{site.id}/intelligence")
        assert resp.status_code == 200

    def test_returns_404_for_missing_site(self, client):
        resp = client.get("/api/sites/99999/intelligence")
        assert resp.status_code == 404

    def test_response_shape(self, client, db_session):
        site = _seed_site_with_intelligence(db_session)
        data = client.get(f"/api/sites/{site.id}/intelligence").json()
        assert "site_id" in data
        assert "archetype" in data
        assert "anomalies" in data
        assert "recommendations" in data
        assert "summary" in data
        assert "status" in data

    def test_archetype_present(self, client, db_session):
        site = _seed_site_with_intelligence(db_session)
        data = client.get(f"/api/sites/{site.id}/intelligence").json()
        assert data["archetype"] is not None
        assert data["archetype"]["code"] == "BUREAU_STANDARD"
        assert data["archetype"]["match_score"] == 0.85

    def test_anomalies_have_required_fields(self, client, db_session):
        site = _seed_site_with_intelligence(db_session)
        data = client.get(f"/api/sites/{site.id}/intelligence").json()
        assert len(data["anomalies"]) > 0
        a = data["anomalies"][0]
        assert "anomaly_code" in a
        assert "title" in a
        assert "severity" in a
        assert "confidence" in a

    def test_recommendations_have_required_fields(self, client, db_session):
        site = _seed_site_with_intelligence(db_session)
        data = client.get(f"/api/sites/{site.id}/intelligence").json()
        assert len(data["recommendations"]) > 0
        r = data["recommendations"][0]
        assert "recommendation_code" in r
        assert "title" in r
        assert "ice_score" in r
        assert "status" in r

    def test_summary_counts_match(self, client, db_session):
        site = _seed_site_with_intelligence(db_session)
        data = client.get(f"/api/sites/{site.id}/intelligence").json()
        assert data["summary"]["total_anomalies"] == len(data["anomalies"])
        assert data["summary"]["total_recommendations"] == len(data["recommendations"])

    def test_status_analyzed(self, client, db_session):
        site = _seed_site_with_intelligence(db_session)
        data = client.get(f"/api/sites/{site.id}/intelligence").json()
        assert data["status"] == "analyzed"

    def test_no_meters_returns_no_meters_status(self, client, db_session):
        site = Site(nom="Empty Site", type="BUREAU", surface_m2=500, actif=True)
        db_session.add(site)
        db_session.commit()
        data = client.get(f"/api/sites/{site.id}/intelligence").json()
        assert data["status"] == "no_meters"
        assert data["archetype"] is None
        assert data["anomalies"] == []
