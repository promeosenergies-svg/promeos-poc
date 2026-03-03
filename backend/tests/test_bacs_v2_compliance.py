"""
PROMEOS - Tests for BACS v2 bundle enrichment + config loading.
Pattern: TestClient + in-memory SQLite + StaticPool (same as test_compliance_bundle.py).
"""
import sys
import os
import json
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    ComplianceFinding, TypeSite,
    BacsAsset, BacsCvcSystem, BacsAssessment,
    CvcSystemType, CvcArchitecture, BacsTriggerReason,
)
from database import get_db
from main import app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", echo=False,
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


def _seed_bacs_sites(db_session):
    """Create org with 4 sites at different BACS tiers."""
    org = Organisation(id=1, nom="TestOrg")
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(id=1, nom="EJ1", siren="111111111", organisation_id=1)
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(id=1, nom="PF1", entite_juridique_id=1)
    db_session.add(pf)
    db_session.flush()

    # 4 sites
    for i in range(1, 5):
        db_session.add(Site(id=i, nom=f"Site {i}", type=TypeSite.BUREAU,
                            portefeuille_id=1, actif=True))
    db_session.flush()

    # Site 1: CVC 350 kW (tier1, >290, deadline 2025)
    asset1 = BacsAsset(id=1, site_id=1, is_tertiary_non_residential=True)
    db_session.add(asset1)
    db_session.flush()
    db_session.add(BacsCvcSystem(
        id=1, asset_id=1, system_type=CvcSystemType.HEATING,
        architecture=CvcArchitecture.INDEPENDENT,
        units_json=json.dumps([{"label": "PAC1", "kw": 350}]),
    ))
    db_session.add(BacsAssessment(
        id=1, asset_id=1, assessed_at=datetime.now(timezone.utc),
        threshold_applied=290, is_obligated=True,
        deadline_date=date(2025, 1, 1),
        trigger_reason=BacsTriggerReason.THRESHOLD_290,
        tri_exemption_possible=False, tri_years=5.0,
        confidence_score=0.9, compliance_score=20.0,
        engine_version="bacs_v2.0",
    ))

    # Site 2: CVC 150 kW (tier2, 70-290, deadline 2030)
    asset2 = BacsAsset(id=2, site_id=2, is_tertiary_non_residential=True)
    db_session.add(asset2)
    db_session.flush()
    db_session.add(BacsCvcSystem(
        id=2, asset_id=2, system_type=CvcSystemType.COOLING,
        architecture=CvcArchitecture.CASCADE,
        units_json=json.dumps([{"label": "Clim1", "kw": 80}, {"label": "Clim2", "kw": 70}]),
    ))
    db_session.add(BacsAssessment(
        id=2, asset_id=2, assessed_at=datetime.now(timezone.utc),
        threshold_applied=70, is_obligated=True,
        deadline_date=date(2030, 1, 1),
        trigger_reason=BacsTriggerReason.THRESHOLD_70,
        tri_exemption_possible=True, tri_years=12.0,
        confidence_score=0.85, compliance_score=40.0,
        engine_version="bacs_v2.0",
    ))

    # Site 3: CVC 50 kW (not applicable, <70) — no BacsAsset
    # Site 4: No CVC data (missing) — no BacsAsset

    # Add compliance findings for all sites
    for sid in [1, 2, 3, 4]:
        status = "NOK" if sid <= 2 else "UNKNOWN"
        db_session.add(ComplianceFinding(
            site_id=sid, regulation="bacs", rule_id="BACS_SCOPE",
            status=status, severity="high", evidence="test",
        ))
    db_session.commit()


class TestBacsV2Bundle:
    def test_bundle_includes_bacs_v2_field(self, client, db_session):
        """Bundle response includes bacs_v2 key."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        assert r.status_code == 200
        data = r.json()
        assert "bacs_v2" in data
        assert isinstance(data["bacs_v2"], dict)

    def test_bacs_tier1_290_data(self, client, db_session):
        """Site 1 (350 kW) has applicable=True, threshold=290, deadline=2025-01-01."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        data = r.json()
        bacs = data["bacs_v2"]
        # site_id=1 should be present
        site1 = bacs.get("1") or bacs.get(1)
        assert site1 is not None
        assert site1["applicable"] is True
        assert site1["threshold_kw"] == 290
        assert site1["deadline"] == "2025-01-01"

    def test_bacs_tier2_70_data(self, client, db_session):
        """Site 2 (150 kW) has applicable=True, threshold=70, deadline=2030-01-01."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        data = r.json()
        bacs = data["bacs_v2"]
        site2 = bacs.get("2") or bacs.get(2)
        assert site2 is not None
        assert site2["applicable"] is True
        assert site2["threshold_kw"] == 70
        assert site2["deadline"] == "2030-01-01"
        assert site2["tri_exemption"] is True

    def test_bacs_not_applicable_under_70(self, client, db_session):
        """Site 3 (50 kW, no BacsAsset) is not in bacs_v2."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        data = r.json()
        bacs = data["bacs_v2"]
        assert bacs.get("3") is None
        assert bacs.get(3) is None

    def test_bacs_missing_data_not_in_bacs_v2(self, client, db_session):
        """Site 4 (no CVC data, no BacsAsset) not in bacs_v2."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        data = r.json()
        bacs = data["bacs_v2"]
        assert bacs.get("4") is None
        assert bacs.get(4) is None

    def test_bundle_meta_has_generated_at(self, client, db_session):
        """meta.generated_at is an ISO datetime string."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        data = r.json()
        assert "meta" in data
        assert "generated_at" in data["meta"]
        # Should be parseable as ISO datetime
        datetime.fromisoformat(data["meta"]["generated_at"])

    def test_bundle_meta_has_engine_versions(self, client, db_session):
        """meta.engine_versions.bacs == 'bacs_v2.0'."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        data = r.json()
        assert data["meta"]["engine_versions"]["bacs"] == "bacs_v2.0"
        assert data["meta"]["engine_versions"]["compliance"] == "1.0"

    def test_bacs_config_loads_from_yaml(self):
        """_load_bacs_config() returns valid thresholds and deadlines."""
        from services.bacs_engine import _load_bacs_config
        cfg = _load_bacs_config()
        assert cfg["thresholds_kw"]["tier1"] == 290
        assert cfg["thresholds_kw"]["tier2"] == 70
        assert cfg["deadlines"]["tier1"] == "2025-01-01"
        assert cfg["deadlines"]["tier2"] == "2030-01-01"
        assert cfg["engine_version"] == "bacs_v2.0"


class TestBacsV2Putile:
    def test_putile_from_bundle_site1(self, client, db_session):
        """Site 1 bacs_v2 includes putile_kw from CVC systems."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        data = r.json()
        bacs = data["bacs_v2"]
        site1 = bacs.get("1") or bacs.get(1)
        assert site1["putile_kw"] == 350

    def test_putile_from_bundle_site2_cascade(self, client, db_session):
        """Site 2 (cascade) putile is sum of units = 80+70=150."""
        _seed_bacs_sites(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        data = r.json()
        bacs = data["bacs_v2"]
        site2 = bacs.get("2") or bacs.get(2)
        assert site2["putile_kw"] == 150


class TestHealthEngineVersions:
    def test_health_includes_engine_versions(self, client):
        """GET /api/health includes engine_versions."""
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert "engine_versions" in data
        assert data["engine_versions"]["bacs"] == "bacs_v2.0"
        assert data["engine_versions"]["compliance"] == "1.0"
