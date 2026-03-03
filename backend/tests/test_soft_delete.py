"""
PROMEOS - Tests Soft Delete
Covers: SoftDeleteMixin fields, restore, list filtering, get 404, tree exclusion.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    Batiment, Compteur, not_deleted, TypeSite, TypeCompteur,
)
from database import get_db
from main import app


# ========================================
# Fixtures
# ========================================

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


def _seed_org_hierarchy(db_session):
    """Create minimal org > ej > portefeuille > site hierarchy."""
    org = Organisation(nom="Test Org", type_client="tertiaire", actif=True)
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test EJ", siren="123456789")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Test", description="Test")
    db_session.add(pf)
    db_session.flush()

    return org, ej, pf


# ========================================
# Tests
# ========================================

class TestSoftDeleteSetsFields:
    """Verify soft_delete() sets deleted_at, deleted_by, delete_reason correctly."""

    def test_soft_delete_sets_fields(self, db_session):
        org, ej, pf = _seed_org_hierarchy(db_session)

        site = Site(
            nom="Site A", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(site)
        db_session.flush()

        assert site.deleted_at is None
        assert site.is_deleted is False

        before = datetime.now(timezone.utc)
        site.soft_delete(by="admin@promeos.fr", reason="Doublon")
        db_session.flush()

        assert site.deleted_at is not None
        assert site.deleted_at >= before
        assert site.deleted_by == "admin@promeos.fr"
        assert site.delete_reason == "Doublon"
        assert site.is_deleted is True

    def test_soft_delete_without_optional_params(self, db_session):
        org, ej, pf = _seed_org_hierarchy(db_session)

        site = Site(
            nom="Site B", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(site)
        db_session.flush()

        site.soft_delete()
        db_session.flush()

        assert site.is_deleted is True
        assert site.deleted_by is None
        assert site.delete_reason is None


class TestRestoreUnsetsFields:
    """Verify restore() clears all soft-delete fields."""

    def test_restore_unsets_fields(self, db_session):
        org, ej, pf = _seed_org_hierarchy(db_session)

        site = Site(
            nom="Site Restore", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(site)
        db_session.flush()

        site.soft_delete(by="admin@promeos.fr", reason="Test")
        db_session.flush()
        assert site.is_deleted is True

        site.restore()
        db_session.flush()

        assert site.deleted_at is None
        assert site.deleted_by is None
        assert site.delete_reason is None
        assert site.is_deleted is False


class TestListSitesExcludesDeleted:
    """Verify GET /api/sites excludes soft-deleted sites."""

    def test_list_sites_excludes_deleted(self, db_session, client):
        org, ej, pf = _seed_org_hierarchy(db_session)

        site_a = Site(
            nom="Site Actif", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        site_b = Site(
            nom="Site Supprime", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add_all([site_a, site_b])
        db_session.flush()

        site_b.soft_delete(by="admin", reason="Test delete")
        db_session.commit()

        resp = client.get("/api/sites")
        assert resp.status_code == 200
        data = resp.json()

        site_names = [s["nom"] for s in data["sites"]]
        assert "Site Actif" in site_names
        assert "Site Supprime" not in site_names
        assert data["total"] == 1

    def test_not_deleted_helper_filters_correctly(self, db_session):
        org, ej, pf = _seed_org_hierarchy(db_session)

        for i in range(5):
            s = Site(
                nom=f"Site {i}", type=TypeSite.BUREAU,
                portefeuille_id=pf.id, actif=True,
            )
            db_session.add(s)
        db_session.flush()

        sites = db_session.query(Site).all()
        sites[0].soft_delete(by="test")
        sites[1].soft_delete(by="test")
        db_session.flush()

        active = not_deleted(db_session.query(Site), Site).all()
        assert len(active) == 3


class TestGetSiteDeletedReturns404:
    """Verify GET /api/sites/{id} returns 404 for soft-deleted site."""

    def test_get_site_deleted_returns_404(self, db_session, client):
        org, ej, pf = _seed_org_hierarchy(db_session)

        site = Site(
            nom="Site Fantome", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(site)
        db_session.flush()
        site_id = site.id

        # Accessible before delete
        resp = client.get(f"/api/sites/{site_id}")
        assert resp.status_code == 200

        # Soft delete
        site.soft_delete(by="admin")
        db_session.commit()

        # 404 after delete
        resp = client.get(f"/api/sites/{site_id}")
        assert resp.status_code == 404


class TestTreeExcludesDeletedNodes:
    """Verify tree queries exclude soft-deleted children (compteurs, batiments)."""

    def test_tree_excludes_deleted_nodes(self, db_session):
        org, ej, pf = _seed_org_hierarchy(db_session)

        site = Site(
            nom="Site Parent", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(site)
        db_session.flush()

        bat_a = Batiment(site_id=site.id, nom="Bat A", surface_m2=500)
        bat_b = Batiment(site_id=site.id, nom="Bat B", surface_m2=300)
        cpt_a = Compteur(
            site_id=site.id, type=TypeCompteur.ELECTRICITE,
            numero_serie="CPT-001",
        )
        cpt_b = Compteur(
            site_id=site.id, type=TypeCompteur.ELECTRICITE,
            numero_serie="CPT-002",
        )
        db_session.add_all([bat_a, bat_b, cpt_a, cpt_b])
        db_session.flush()

        # Soft-delete one batiment and one compteur
        bat_b.soft_delete(by="test")
        cpt_b.soft_delete(by="test")
        db_session.flush()

        # Query with not_deleted
        active_bats = not_deleted(
            db_session.query(Batiment).filter(Batiment.site_id == site.id),
            Batiment,
        ).all()
        assert len(active_bats) == 1
        assert active_bats[0].nom == "Bat A"

        active_cpts = not_deleted(
            db_session.query(Compteur).filter(Compteur.site_id == site.id),
            Compteur,
        ).all()
        assert len(active_cpts) == 1
        assert active_cpts[0].numero_serie == "CPT-001"

    def test_cockpit_excludes_deleted_sites(self, db_session, client):
        """Verify /api/cockpit stats exclude soft-deleted sites."""
        org, ej, pf = _seed_org_hierarchy(db_session)

        site_a = Site(
            nom="Site OK", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
            risque_financier_euro=1000,
        )
        site_b = Site(
            nom="Site Deleted", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
            risque_financier_euro=5000,
        )
        db_session.add_all([site_a, site_b])
        db_session.flush()
        site_b.soft_delete(by="admin")
        db_session.commit()

        resp = client.get("/api/cockpit")
        assert resp.status_code == 200
        data = resp.json()

        assert data["stats"]["total_sites"] == 1
        assert data["stats"]["risque_financier_euro"] == 1000
