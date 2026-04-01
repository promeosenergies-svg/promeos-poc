"""
PROMEOS - Tests for Usages scope resolver and scoped endpoints.
Tests resolve_site_ids from shared scope_utils + aggregation consistency.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    TypeSite,
)
from services.scope_utils import resolve_site_ids


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_hierarchy(db):
    """Create org -> 2 entities -> 3 portfolios -> 5 sites."""
    org = Organisation(id=1, nom="Groupe HELIOS")
    db.add(org)
    db.flush()

    ej1 = EntiteJuridique(id=1, nom="HELIOS Immobilier", siren="111111111", organisation_id=1)
    ej2 = EntiteJuridique(id=2, nom="HELIOS Industrie", siren="222222222", organisation_id=1)
    db.add_all([ej1, ej2])
    db.flush()

    pf1 = Portefeuille(id=1, nom="Siège & Bureaux", entite_juridique_id=1)
    pf2 = Portefeuille(id=2, nom="Sites Régionaux", entite_juridique_id=1)
    pf3 = Portefeuille(id=3, nom="Sites Industriels", entite_juridique_id=2)
    db.add_all([pf1, pf2, pf3])
    db.flush()

    s1 = Site(id=1, nom="Paris HQ", type=TypeSite.BUREAU, portefeuille_id=1, actif=True, surface_m2=3500)
    s2 = Site(id=2, nom="Lyon Bureau", type=TypeSite.BUREAU, portefeuille_id=1, actif=True, surface_m2=1200)
    s3 = Site(id=3, nom="Marseille", type=TypeSite.BUREAU, portefeuille_id=2, actif=True, surface_m2=2500)
    s4 = Site(id=4, nom="Grenoble Usine", type=TypeSite.USINE, portefeuille_id=3, actif=True, surface_m2=8000)
    s5 = Site(id=5, nom="Toulouse Entrepôt", type=TypeSite.ENTREPOT, portefeuille_id=3, actif=True, surface_m2=4000)
    db.add_all([s1, s2, s3, s4, s5])
    db.commit()

    return org, [ej1, ej2], [pf1, pf2, pf3], [s1, s2, s3, s4, s5]


class TestResolveSiteIds:
    """Tests pour resolve_site_ids dans scope_utils."""

    def test_org_returns_all_sites(self, db):
        _seed_hierarchy(db)
        ids = resolve_site_ids(db, org_id=1)
        assert sorted(ids) == [1, 2, 3, 4, 5]

    def test_entity_returns_subset(self, db):
        _seed_hierarchy(db)
        # Entity 1 (Immobilier) → pf1 + pf2 → sites 1, 2, 3
        ids = resolve_site_ids(db, org_id=1, entity_id=1)
        assert sorted(ids) == [1, 2, 3]

    def test_entity_2_returns_industrial(self, db):
        _seed_hierarchy(db)
        # Entity 2 (Industrie) → pf3 → sites 4, 5
        ids = resolve_site_ids(db, org_id=1, entity_id=2)
        assert sorted(ids) == [4, 5]

    def test_portfolio_returns_correct_sites(self, db):
        _seed_hierarchy(db)
        ids = resolve_site_ids(db, org_id=1, portefeuille_id=1)
        assert sorted(ids) == [1, 2]

    def test_portfolio_2_returns_marseille(self, db):
        _seed_hierarchy(db)
        ids = resolve_site_ids(db, org_id=1, portefeuille_id=2)
        assert ids == [3]

    def test_site_returns_single(self, db):
        _seed_hierarchy(db)
        ids = resolve_site_ids(db, org_id=1, site_id=4)
        assert ids == [4]

    def test_priority_site_over_org(self, db):
        _seed_hierarchy(db)
        ids = resolve_site_ids(db, org_id=1, site_id=2)
        assert ids == [2]

    def test_empty_org(self, db):
        ids = resolve_site_ids(db, org_id=999)
        assert ids == []

    def test_entity_sum_equals_org(self, db):
        """Sum of all entity-level resolutions = org-level resolution."""
        _seed_hierarchy(db)
        org_ids = resolve_site_ids(db, org_id=1)
        ej1_ids = resolve_site_ids(db, org_id=1, entity_id=1)
        ej2_ids = resolve_site_ids(db, org_id=1, entity_id=2)
        assert sorted(ej1_ids + ej2_ids) == sorted(org_ids)

    def test_portfolio_sum_equals_entity(self, db):
        """Sum of portfolio resolutions within entity = entity resolution."""
        _seed_hierarchy(db)
        ej1_ids = resolve_site_ids(db, org_id=1, entity_id=1)
        pf1_ids = resolve_site_ids(db, org_id=1, portefeuille_id=1)
        pf2_ids = resolve_site_ids(db, org_id=1, portefeuille_id=2)
        assert sorted(pf1_ids + pf2_ids) == sorted(ej1_ids)


class TestComplianceBackwardCompat:
    """Vérifie que compliance_rules._resolve_site_ids délègue correctement."""

    def test_delegation_works(self, db):
        _seed_hierarchy(db)
        from services.compliance_rules import _resolve_site_ids

        ids = _resolve_site_ids(db, org_id=1)
        assert sorted(ids) == [1, 2, 3, 4, 5]

    def test_delegation_entity(self, db):
        _seed_hierarchy(db)
        from services.compliance_rules import _resolve_site_ids

        ids = _resolve_site_ids(db, org_id=1, entity_id=2)
        assert sorted(ids) == [4, 5]
