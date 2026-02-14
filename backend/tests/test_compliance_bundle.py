"""
PROMEOS - Tests for /api/compliance/bundle endpoint
Tests scope isolation, empty reason codes, and bundled response.
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
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    ComplianceFinding, TypeSite,
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


def _seed_two_orgs(db_session):
    """Create 2 orgs with different site counts to verify scope isolation."""
    org1 = Organisation(id=1, nom="Nexity")
    org2 = Organisation(id=2, nom="Groupe Casino")
    db_session.add_all([org1, org2])
    db_session.flush()

    ej1 = EntiteJuridique(id=1, nom="EJ Nexity", siren="111111111", organisation_id=1)
    ej2 = EntiteJuridique(id=2, nom="EJ Casino", siren="222222222", organisation_id=2)
    db_session.add_all([ej1, ej2])
    db_session.flush()

    pf1 = Portefeuille(id=1, nom="PF Nexity", entite_juridique_id=1)
    pf2 = Portefeuille(id=2, nom="PF Casino", entite_juridique_id=2)
    db_session.add_all([pf1, pf2])
    db_session.flush()

    # Org1: 3 sites, Org2: 2 sites
    for i in range(1, 4):
        db_session.add(Site(id=i, nom=f"Site Nexity {i}", type=TypeSite.BUREAU,
                            portefeuille_id=1, actif=True))
    for i in range(4, 6):
        db_session.add(Site(id=i, nom=f"Site Casino {i}", type=TypeSite.BUREAU,
                            portefeuille_id=2, actif=True))
    db_session.flush()

    # Findings: org1 has 1 NOK + 2 OK; org2 has 2 OK
    for sid in [1, 2, 3]:
        db_session.add(ComplianceFinding(
            site_id=sid, regulation="bacs", rule_id="BACS_SCOPE",
            status="NOK" if sid == 1 else "OK", severity="high",
            evidence="test nexity",
        ))
    for sid in [4, 5]:
        db_session.add(ComplianceFinding(
            site_id=sid, regulation="bacs", rule_id="BACS_SCOPE",
            status="OK", severity="low", evidence="test casino",
        ))
    db_session.commit()


class TestBundleEndpoint:
    def test_bundle_org_scope_org1(self, client, db_session):
        """GET /bundle?org_id=1 returns only org1 data (3 sites)."""
        _seed_two_orgs(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        assert r.status_code == 200
        data = r.json()
        assert data["scope"]["org_id"] == 1
        assert data["summary"]["total_sites"] == 3
        assert len(data["sites"]) == 3

    def test_bundle_org_scope_org2(self, client, db_session):
        """GET /bundle?org_id=2 returns only org2 data (2 sites, Casino names)."""
        _seed_two_orgs(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 2})
        assert r.status_code == 200
        data = r.json()
        assert data["scope"]["org_id"] == 2
        assert data["summary"]["total_sites"] == 2
        assert len(data["sites"]) == 2
        site_names = [s["site_nom"] for s in data["sites"]]
        assert all("Casino" in n for n in site_names)

    def test_bundle_site_scope(self, client, db_session):
        """GET /bundle?org_id=1&site_id=1 returns single site."""
        _seed_two_orgs(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1, "site_id": 1})
        assert r.status_code == 200
        data = r.json()
        assert data["scope"]["site_id"] == 1
        assert data["summary"]["total_sites"] == 1

    def test_bundle_no_org_fallback(self, client, db_session):
        """GET /bundle without org_id falls back to first org."""
        _seed_two_orgs(db_session)
        r = client.get("/api/compliance/bundle")
        assert r.status_code == 200
        data = r.json()
        assert data["scope"]["org_id"] == 1  # Nexity is first

    def test_empty_reason_no_sites(self, client):
        """GET /bundle?org_id=999 with no sites returns NO_SITES."""
        r = client.get("/api/compliance/bundle", params={"org_id": 999})
        assert r.status_code == 200
        data = r.json()
        assert data["empty_reason_code"] == "NO_SITES"
        assert data["empty_reason_message"] is not None
        assert data["summary"]["total_sites"] == 0

    def test_empty_reason_all_compliant(self, client, db_session):
        """Org2 with all OK findings returns ALL_COMPLIANT."""
        _seed_two_orgs(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 2})
        assert r.status_code == 200
        data = r.json()
        assert data["empty_reason_code"] == "ALL_COMPLIANT"

    def test_bundle_has_trace_id(self, client, db_session):
        """Every bundle response includes a trace_id string."""
        _seed_two_orgs(db_session)
        r = client.get("/api/compliance/bundle", params={"org_id": 1})
        assert r.status_code == 200
        data = r.json()
        assert "trace_id" in data
        assert isinstance(data["trace_id"], str)
        assert len(data["trace_id"]) > 0

    def test_bundle_no_sites_trace_id(self, client):
        """Empty bundle (no sites) also has trace_id."""
        r = client.get("/api/compliance/bundle", params={"org_id": 999})
        assert r.status_code == 200
        data = r.json()
        assert "trace_id" in data

    def test_bundle_no_evaluation(self, client, db_session):
        """Org with sites but no findings returns NOT_EVALUATED_YET or NO_EVALUATION."""
        org = Organisation(id=10, nom="EmptyOrg")
        db_session.add(org)
        db_session.flush()
        ej = EntiteJuridique(id=10, nom="EJ Empty", siren="333333333", organisation_id=10)
        db_session.add(ej)
        db_session.flush()
        pf = Portefeuille(id=10, nom="PF Empty", entite_juridique_id=10)
        db_session.add(pf)
        db_session.flush()
        db_session.add(Site(id=100, nom="Site Vide", type=TypeSite.BUREAU,
                            portefeuille_id=10, actif=True))
        db_session.commit()

        r = client.get("/api/compliance/bundle", params={"org_id": 10})
        assert r.status_code == 200
        data = r.json()
        assert data["empty_reason_code"] == "NO_EVALUATION"
        assert data["summary"]["total_sites"] == 1


class TestDevResetDb:
    def test_reset_db_returns_ok(self, client):
        """POST /api/dev/reset_db returns status ok."""
        r = client.post("/api/dev/reset_db")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["schema"] == "recreated"
