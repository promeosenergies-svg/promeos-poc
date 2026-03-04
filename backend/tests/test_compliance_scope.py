"""
PROMEOS - Tests for Compliance scope filtering
Tests _resolve_site_ids, get_summary, get_sites_findings with entity/site scope.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    ComplianceFinding,
    TypeSite,
)
from services.compliance_rules import (
    _resolve_site_ids,
    get_summary,
    get_sites_findings,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_org(db):
    """Create org -> entity -> portfolio -> 3 sites + findings."""
    org = Organisation(id=1, nom="TestOrg")
    db.add(org)
    db.flush()

    ej = EntiteJuridique(id=1, nom="EJ1", siren="111111111", organisation_id=1)
    db.add(ej)
    db.flush()

    pf = Portefeuille(id=1, nom="PF1", entite_juridique_id=1)
    db.add(pf)
    db.flush()

    s1 = Site(id=1, nom="Site Alpha", type=TypeSite.BUREAU, portefeuille_id=1, actif=True)
    s2 = Site(id=2, nom="Site Beta", type=TypeSite.BUREAU, portefeuille_id=1, actif=True)
    s3 = Site(id=3, nom="Site Gamma", type=TypeSite.BUREAU, portefeuille_id=1, actif=True)
    db.add_all([s1, s2, s3])
    db.flush()

    # Findings: site1 NOK, site2 OK, site3 UNKNOWN
    f1 = ComplianceFinding(
        site_id=1,
        regulation="bacs",
        rule_id="BACS_SCOPE",
        status="NOK",
        severity="high",
        evidence="Non conforme",
        deadline=date(2025, 12, 31),
    )
    f2 = ComplianceFinding(
        site_id=2,
        regulation="bacs",
        rule_id="BACS_SCOPE",
        status="OK",
        severity="low",
        evidence="Conforme",
    )
    f3 = ComplianceFinding(
        site_id=3,
        regulation="decret_tertiaire_operat",
        rule_id="DT_SCOPE",
        status="UNKNOWN",
        severity="medium",
        evidence="Donnees manquantes",
    )
    db.add_all([f1, f2, f3])
    db.commit()
    return org, ej, pf, [s1, s2, s3], [f1, f2, f3]


class TestResolveSiteIds:
    def test_org_scope(self, db):
        _seed_org(db)
        ids = _resolve_site_ids(db, org_id=1)
        assert sorted(ids) == [1, 2, 3]

    def test_entity_scope(self, db):
        _seed_org(db)
        ids = _resolve_site_ids(db, org_id=1, entity_id=1)
        assert sorted(ids) == [1, 2, 3]

    def test_site_scope(self, db):
        _seed_org(db)
        ids = _resolve_site_ids(db, org_id=1, site_id=2)
        assert ids == [2]

    def test_empty_org(self, db):
        ids = _resolve_site_ids(db, org_id=999)
        assert ids == []


class TestGetSummaryScope:
    def test_full_org_summary(self, db):
        _seed_org(db)
        result = get_summary(db, org_id=1)
        assert result["total_sites"] == 3
        assert result["sites_nok"] == 1
        assert result["sites_ok"] == 1
        assert result["sites_unknown"] == 1

    def test_site_scope_nok(self, db):
        _seed_org(db)
        result = get_summary(db, org_id=1, site_id=1)
        assert result["total_sites"] == 1
        assert result["sites_nok"] == 1
        assert result["sites_ok"] == 0

    def test_site_scope_ok(self, db):
        _seed_org(db)
        result = get_summary(db, org_id=1, site_id=2)
        assert result["total_sites"] == 1
        assert result["sites_ok"] == 1
        assert result["sites_nok"] == 0

    def test_empty_reason_no_sites(self, db):
        result = get_summary(db, org_id=999)
        assert result["empty_reason"] == "NO_SITES"
        assert result["total_sites"] == 0

    def test_empty_reason_all_compliant(self, db):
        _seed_org(db)
        result = get_summary(db, org_id=1, site_id=2)
        assert result.get("empty_reason") == "ALL_COMPLIANT"


class TestGetSitesFindingsScope:
    def test_full_org(self, db):
        _seed_org(db)
        result = get_sites_findings(db, org_id=1)
        assert len(result) == 3
        all_site_ids = {s["site_id"] for s in result}
        assert all_site_ids == {1, 2, 3}

    def test_site_filter(self, db):
        _seed_org(db)
        result = get_sites_findings(db, org_id=1, site_id=1)
        assert len(result) == 1
        assert result[0]["site_id"] == 1
        assert result[0]["findings"][0]["status"] == "NOK"

    def test_regulation_filter(self, db):
        _seed_org(db)
        result = get_sites_findings(db, org_id=1, regulation="bacs")
        site_ids = {s["site_id"] for s in result}
        assert 3 not in site_ids  # site 3 has decret_tertiaire, not bacs

    def test_empty_returns_empty_list(self, db):
        result = get_sites_findings(db, org_id=999)
        assert result == []
