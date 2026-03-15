"""
PROMEOS — Tests soft-delete coherence.
Covers: SoftDeleteMixin sync, not_deleted() filter, restore(), backfill script.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Organisation,
    Site,
    Compteur,
    EntiteJuridique,
    Portefeuille,
    TypeCompteur,
    EnergyVector,
)
from models.base import not_deleted


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
def org(db):
    o = Organisation(nom="TestOrg", type_client="bureau", actif=True, siren="443061841")
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def site(db, org):
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="443061841")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    s = Site(nom="Site Test", type="bureau", portefeuille_id=pf.id, actif=True)
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def compteur(db, site):
    c = Compteur(
        site_id=site.id,
        type=TypeCompteur.ELECTRICITE,
        numero_serie="CPT-SD-001",
        meter_id="SD-TEST-001",
        energy_vector=EnergyVector.ELECTRICITY,
        actif=True,
    )
    db.add(c)
    db.flush()
    return c


# ── soft_delete() syncs actif ──────────────────────────────────────


class TestSoftDeleteSync:
    """soft_delete() sets actif=False on models that have actif field."""

    def test_org_soft_delete_sets_actif_false(self, db, org):
        assert org.actif is True
        org.soft_delete(by="test", reason="unit test")
        assert org.actif is False
        assert org.deleted_at is not None
        assert org.delete_reason == "unit test"

    def test_site_soft_delete_sets_actif_false(self, db, site):
        assert site.actif is True
        site.soft_delete(by="test")
        assert site.actif is False
        assert site.deleted_at is not None

    def test_compteur_soft_delete_sets_actif_false(self, db, compteur):
        assert compteur.actif is True
        compteur.soft_delete()
        assert compteur.actif is False
        assert compteur.deleted_at is not None


# ── restore() syncs actif ──────────────────────────────────────────


class TestRestoreSync:
    """restore() sets actif=True and clears deleted_at."""

    def test_org_restore_sets_actif_true(self, db, org):
        org.soft_delete(by="test")
        assert org.actif is False
        org.restore()
        assert org.actif is True
        assert org.deleted_at is None
        assert org.deleted_by is None

    def test_site_restore_sets_actif_true(self, db, site):
        site.soft_delete()
        site.restore()
        assert site.actif is True
        assert site.deleted_at is None

    def test_compteur_restore_sets_actif_true(self, db, compteur):
        compteur.soft_delete()
        compteur.restore()
        assert compteur.actif is True
        assert compteur.deleted_at is None


# ── not_deleted() filter ───────────────────────────────────────────


class TestNotDeletedFilter:
    """not_deleted() excludes soft-deleted objects."""

    def test_excludes_soft_deleted_org(self, db, org):
        q = not_deleted(db.query(Organisation), Organisation)
        assert q.count() == 1

        org.soft_delete()
        db.flush()

        q = not_deleted(db.query(Organisation), Organisation)
        assert q.count() == 0

    def test_excludes_actif_false_only(self, db, org):
        """actif=False without deleted_at → still excluded by not_deleted()."""
        org.actif = False
        db.flush()

        q = not_deleted(db.query(Organisation), Organisation)
        assert q.count() == 0

    def test_excludes_deleted_at_only(self, db, org):
        """deleted_at set without actif=False → still excluded by not_deleted()."""
        org.deleted_at = datetime.now(timezone.utc)
        db.flush()

        q = not_deleted(db.query(Organisation), Organisation)
        assert q.count() == 0

    def test_includes_active_org(self, db, org):
        q = not_deleted(db.query(Organisation), Organisation)
        assert q.count() == 1

    def test_restored_org_included(self, db, org):
        org.soft_delete()
        db.flush()
        org.restore()
        db.flush()

        q = not_deleted(db.query(Organisation), Organisation)
        assert q.count() == 1


# ── not_deleted() single-arg (expression mode) ───────────────


class TestNotDeletedExpressionMode:
    """not_deleted(Model) returns a filter expression for use in .filter()."""

    def test_single_arg_excludes_soft_deleted(self, db, org):
        org.soft_delete()
        db.flush()
        q = db.query(Organisation).filter(not_deleted(Organisation))
        assert q.count() == 0

    def test_single_arg_includes_active(self, db, org):
        q = db.query(Organisation).filter(not_deleted(Organisation))
        assert q.count() == 1

    def test_single_arg_with_other_filters(self, db, org):
        q = db.query(Organisation).filter(
            Organisation.id == org.id,
            not_deleted(Organisation),
        )
        assert q.count() == 1

    def test_single_arg_ej_no_actif_field(self, db, org):
        """EntiteJuridique has deleted_at but no actif — single-arg must work."""
        ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="123456789")
        db.add(ej)
        db.flush()

        q = db.query(EntiteJuridique).filter(not_deleted(EntiteJuridique))
        assert q.count() == 1

        ej.soft_delete()
        db.flush()
        assert db.query(EntiteJuridique).filter(not_deleted(EntiteJuridique)).count() == 0

    def test_both_modes_agree(self, db, org):
        """Single-arg and two-arg modes return same results."""
        count_2arg = not_deleted(db.query(Organisation), Organisation).count()
        count_1arg = db.query(Organisation).filter(not_deleted(Organisation)).count()
        assert count_2arg == count_1arg

        org.soft_delete()
        db.flush()
        count_2arg = not_deleted(db.query(Organisation), Organisation).count()
        count_1arg = db.query(Organisation).filter(not_deleted(Organisation)).count()
        assert count_2arg == count_1arg == 0


# ── Backfill script logic ─────────────────────────────────────────


class TestBackfillCoherence:
    """Simulate the fix_soft_delete_coherence backfill cases."""

    def test_case1_actif_false_no_deleted_at(self, db, org):
        """actif=False but deleted_at=NULL → backfill sets deleted_at."""
        org.actif = False
        org.deleted_at = None
        db.flush()

        # Simulate backfill
        now = datetime.now(timezone.utc)
        incoherent = (
            db.query(Organisation)
            .filter(
                Organisation.actif == False,  # noqa: E712
                Organisation.deleted_at.is_(None),
            )
            .all()
        )
        assert len(incoherent) == 1
        for obj in incoherent:
            obj.deleted_at = now
            obj.delete_reason = "sync_from_actif_false"
        db.flush()

        db.refresh(org)
        assert org.deleted_at is not None
        assert org.delete_reason == "sync_from_actif_false"

    def test_case2_deleted_at_set_actif_true(self, db, org):
        """deleted_at set but actif=True → backfill sets actif=False."""
        org.deleted_at = datetime.now(timezone.utc)
        org.actif = True
        db.flush()

        # Simulate backfill
        incoherent = (
            db.query(Organisation)
            .filter(
                Organisation.deleted_at.isnot(None),
                Organisation.actif == True,  # noqa: E712
            )
            .all()
        )
        assert len(incoherent) == 1
        for obj in incoherent:
            obj.actif = False
        db.flush()

        db.refresh(org)
        assert org.actif is False

    def test_coherent_data_untouched(self, db, org):
        """Coherent data (actif=True, deleted_at=None) is not modified."""
        # Case 1 query
        c1 = (
            db.query(Organisation)
            .filter(
                Organisation.actif == False,  # noqa: E712
                Organisation.deleted_at.is_(None),
            )
            .count()
        )
        # Case 2 query
        c2 = (
            db.query(Organisation)
            .filter(
                Organisation.deleted_at.isnot(None),
                Organisation.actif == True,  # noqa: E712
            )
            .count()
        )
        assert c1 == 0
        assert c2 == 0
