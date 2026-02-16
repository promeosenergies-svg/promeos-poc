"""
PROMEOS - Tests for Casino 36-site seed + bundle obligations.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, EntiteJuridique, Portefeuille
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


def _run_casino_seed(db_session):
    """Run the Casino seed and return result."""
    from scripts.seed_casino import seed_casino_36
    return seed_casino_36(db_session)


class TestSeedCasino:
    def test_seed_casino_org_has_36_sites(self, db_session):
        """Casino seed creates exactly 36 sites."""
        result = _run_casino_seed(db_session)
        assert result["sites_count"] == 36
        assert result["org_nom"] == "Groupe Casino"

        # Verify in DB
        sites = db_session.query(Site).all()
        assert len(sites) == 36

    def test_seed_casino_3_portefeuilles(self, db_session):
        """Casino seed creates 3 portefeuilles."""
        _run_casino_seed(db_session)
        pfs = db_session.query(Portefeuille).all()
        assert len(pfs) == 3
        pf_names = {pf.nom for pf in pfs}
        assert "Hypermarches" in pf_names
        assert "Proximite" in pf_names
        assert "Logistique" in pf_names

    def test_seed_casino_findings_3_regulations(self, db_session):
        """Casino seed creates findings for bacs, decret_tertiaire_operat, aper."""
        _run_casino_seed(db_session)
        from models import ComplianceFinding
        findings = db_session.query(ComplianceFinding).all()
        regulations = {f.regulation for f in findings}
        assert "bacs" in regulations
        assert "decret_tertiaire_operat" in regulations
        assert "aper" in regulations


class TestBundleCasino:
    def test_bundle_casino_returns_36_evaluated_sites(self, client, db_session):
        """Bundle for Casino org returns 36 sites with findings."""
        result = _run_casino_seed(db_session)
        org_id = result["org_id"]

        r = client.get("/api/compliance/bundle", params={"org_id": org_id})
        assert r.status_code == 200
        data = r.json()
        assert data["scope"]["site_count"] == 36
        assert data["summary"]["total_sites"] == 36
        assert data["empty_reason_code"] is None

    def test_bundle_obligations_contains_bacs_tertiaire_aper(self, client, db_session):
        """Bundle findings_by_regulation includes all 3 regulations."""
        result = _run_casino_seed(db_session)
        org_id = result["org_id"]

        r = client.get("/api/compliance/bundle", params={"org_id": org_id})
        data = r.json()
        regs = list(data["summary"]["findings_by_regulation"].keys())
        assert "bacs" in regs
        assert "decret_tertiaire_operat" in regs
        assert "aper" in regs

    def test_obligations_excludes_cee_p6_lever(self, client, db_session):
        """No cee_p6 regulation in findings (levier, not obligation)."""
        result = _run_casino_seed(db_session)
        org_id = result["org_id"]

        r = client.get("/api/compliance/bundle", params={"org_id": org_id})
        data = r.json()
        regs = list(data["summary"]["findings_by_regulation"].keys())
        assert "cee_p6" not in regs

    def test_bundle_has_mixed_statuses(self, client, db_session):
        """Bundle has a mix of OK, NOK, and UNKNOWN sites."""
        result = _run_casino_seed(db_session)
        org_id = result["org_id"]

        r = client.get("/api/compliance/bundle", params={"org_id": org_id})
        data = r.json()
        s = data["summary"]
        assert s["sites_ok"] > 0
        assert s["sites_nok"] > 0
        assert s["sites_unknown"] > 0
