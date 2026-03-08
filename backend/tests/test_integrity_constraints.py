"""
PROMEOS — Phase 2A — Integrity & Coherence Tests
Covers:
  1) Unique org siren
  2) Unique portefeuille (EJ, nom)
  3) Unique site (portefeuille, siret)
  4) Unique delivery_point code
  5) Unique batiment (site, nom)
  6) Contract overlap rejection (incl. open-ended)
  7) DeliveryPoint delete → compteur.delivery_point_id SET NULL
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timezone
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    Compteur,
    DeliveryPoint,
    EnergyContract,
    TypeSite,
    TypeCompteur,
    BillingEnergyType,
    DeliveryPointStatus,
    DeliveryPointEnergyType,
)
from database.migrations import run_migrations


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable FK enforcement (required for ON DELETE behavior in SQLite)
    @event.listens_for(eng, "connect")
    def _set_fk_pragma(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(bind=eng)
    # Run migrations to create partial unique indexes + trigger
    run_migrations(eng)
    return eng


@pytest.fixture
def db(engine):
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_org(db, siren="123456789", nom="TestOrg"):
    org = Organisation(nom=nom, siren=siren)
    db.add(org)
    db.flush()
    return org


def _make_ej(db, org_id, siren="987654321", nom="TestEJ"):
    ej = EntiteJuridique(organisation_id=org_id, nom=nom, siren=siren)
    db.add(ej)
    db.flush()
    return ej


def _make_portefeuille(db, ej_id, nom="Portfolio A"):
    p = Portefeuille(entite_juridique_id=ej_id, nom=nom)
    db.add(p)
    db.flush()
    return p


def _make_site(db, portefeuille_id, nom="Site 1", siret=None):
    s = Site(
        nom=nom,
        type=TypeSite.BUREAU,
        portefeuille_id=portefeuille_id,
        siret=siret,
    )
    db.add(s)
    db.flush()
    return s


def _make_batiment(db, site_id, nom="Bat A"):
    b = Batiment(site_id=site_id, nom=nom, surface_m2=100.0)
    db.add(b)
    db.flush()
    return b


def _make_dp(db, site_id, code="12345678901234", energy_type=None):
    dp = DeliveryPoint(
        code=code,
        site_id=site_id,
        energy_type=DeliveryPointEnergyType.ELEC if energy_type is None else energy_type,
        status=DeliveryPointStatus.ACTIVE,
    )
    db.add(dp)
    db.flush()
    return dp


def _make_compteur(db, site_id, dp_id=None, numero_serie="CPT-001"):
    c = Compteur(
        site_id=site_id,
        type=TypeCompteur.ELECTRICITE,
        numero_serie=numero_serie,
        delivery_point_id=dp_id,
    )
    db.add(c)
    db.flush()
    return c


def _make_contract(db, site_id, energy_type=BillingEnergyType.ELEC, start=None, end=None, supplier="EDF"):
    c = EnergyContract(
        site_id=site_id,
        energy_type=energy_type,
        supplier_name=supplier,
        start_date=start,
        end_date=end,
    )
    db.add(c)
    db.flush()
    return c


def _scaffold(db):
    """Create org → EJ → portefeuille → site. Return (org, ej, pf, site)."""
    org = _make_org(db)
    ej = _make_ej(db, org.id)
    pf = _make_portefeuille(db, ej.id)
    site = _make_site(db, pf.id)
    db.commit()
    return org, ej, pf, site


# ========================================
# TEST 1: Unique org siren
# ========================================


class TestUniqueOrgSiren:
    def test_duplicate_siren_rejected(self, db):
        _make_org(db, siren="111111111", nom="Org A")
        db.commit()

        with pytest.raises(IntegrityError):
            org2 = Organisation(nom="Org B", siren="111111111")
            db.add(org2)
            db.flush()
        db.rollback()

    def test_null_siren_allowed_multiple(self, db):
        """Multiple orgs with NULL siren is fine."""
        _make_org(db, siren=None, nom="Org A")
        _make_org(db, siren=None, nom="Org B")
        db.commit()
        assert db.query(Organisation).count() == 2

    def test_soft_deleted_siren_allows_reuse(self, db):
        """A soft-deleted org's siren can be reused by a new active org."""
        from datetime import datetime

        org = _make_org(db, siren="222222222")
        db.commit()
        org.deleted_at = datetime.now(timezone.utc)
        db.commit()

        _make_org(db, siren="222222222", nom="New Org")
        db.commit()  # Should not raise


# ========================================
# TEST 2: Unique portefeuille (EJ + nom)
# ========================================


class TestUniquePortefeuilleNamePerEntite:
    def test_duplicate_name_same_ej_rejected(self, db):
        org = _make_org(db)
        ej = _make_ej(db, org.id)
        _make_portefeuille(db, ej.id, nom="Retail IDF")
        db.commit()

        with pytest.raises(IntegrityError):
            p2 = Portefeuille(entite_juridique_id=ej.id, nom="Retail IDF")
            db.add(p2)
            db.flush()
        db.rollback()

    def test_same_name_different_ej_allowed(self, db):
        org = _make_org(db)
        ej1 = _make_ej(db, org.id, siren="111111111", nom="EJ 1")
        ej2 = _make_ej(db, org.id, siren="222222222", nom="EJ 2")
        _make_portefeuille(db, ej1.id, nom="Retail")
        _make_portefeuille(db, ej2.id, nom="Retail")
        db.commit()
        assert db.query(Portefeuille).count() == 2

    def test_soft_deleted_name_allows_reuse(self, db):
        """Soft-deleted portefeuille name can be reused in same EJ."""
        from datetime import datetime

        org = _make_org(db)
        ej = _make_ej(db, org.id)
        pf = _make_portefeuille(db, ej.id, nom="Recyclé")
        db.commit()
        pf.deleted_at = datetime.now(timezone.utc)
        db.commit()
        _make_portefeuille(db, ej.id, nom="Recyclé")
        db.commit()  # Should not raise


# ========================================
# TEST 3: Unique site (portefeuille + siret)
# ========================================


class TestUniqueSiteSiretPerPortefeuille:
    def test_duplicate_siret_same_portefeuille_rejected(self, db):
        org, ej, pf, _ = _scaffold(db)

        _make_site(db, pf.id, nom="Site A", siret="12345678901234")
        db.commit()

        with pytest.raises(IntegrityError):
            s2 = Site(nom="Site B", type=TypeSite.BUREAU, portefeuille_id=pf.id, siret="12345678901234")
            db.add(s2)
            db.flush()
        db.rollback()

    def test_null_siret_allowed_multiple(self, db):
        org, ej, pf, _ = _scaffold(db)
        _make_site(db, pf.id, nom="Site X", siret=None)
        _make_site(db, pf.id, nom="Site Y", siret=None)
        db.commit()
        # +1 for the site created by _scaffold
        assert db.query(Site).filter(Site.portefeuille_id == pf.id).count() == 3

    def test_same_siret_different_portefeuille_allowed(self, db):
        org = _make_org(db)
        ej = _make_ej(db, org.id)
        pf1 = _make_portefeuille(db, ej.id, nom="PF 1")
        pf2 = _make_portefeuille(db, ej.id, nom="PF 2")
        _make_site(db, pf1.id, nom="S1", siret="12345678901234")
        _make_site(db, pf2.id, nom="S2", siret="12345678901234")
        db.commit()

    def test_soft_deleted_siret_allows_reuse(self, db):
        """Soft-deleted site siret can be reused in same portefeuille."""
        from datetime import datetime

        org, ej, pf, _ = _scaffold(db)
        s = _make_site(db, pf.id, nom="Old", siret="99988877766655")
        db.commit()
        s.deleted_at = datetime.now(timezone.utc)
        db.commit()
        _make_site(db, pf.id, nom="New", siret="99988877766655")
        db.commit()  # Should not raise


# ========================================
# TEST 4: Unique delivery_point code
# ========================================


class TestUniqueDeliveryPointCode:
    def test_duplicate_code_rejected(self, db):
        _, _, _, site = _scaffold(db)

        _make_dp(db, site.id, code="12345678901234")
        db.commit()

        with pytest.raises(IntegrityError):
            dp2 = DeliveryPoint(
                code="12345678901234",
                site_id=site.id,
                energy_type=DeliveryPointEnergyType.ELEC,
                status=DeliveryPointStatus.ACTIVE,
            )
            db.add(dp2)
            db.flush()
        db.rollback()

    def test_soft_deleted_code_allows_reuse(self, db):
        from datetime import datetime

        _, _, _, site = _scaffold(db)

        dp = _make_dp(db, site.id, code="99999999999999")
        db.commit()
        dp.deleted_at = datetime.now(timezone.utc)
        db.commit()

        _make_dp(db, site.id, code="99999999999999")
        db.commit()  # Should not raise


# ========================================
# TEST 5: Unique batiment (site + nom)
# ========================================


class TestUniqueBatimentNamePerSite:
    def test_duplicate_name_same_site_rejected(self, db):
        _, _, _, site = _scaffold(db)

        _make_batiment(db, site.id, nom="Hall A")
        db.commit()

        with pytest.raises(IntegrityError):
            b2 = Batiment(site_id=site.id, nom="Hall A", surface_m2=200.0)
            db.add(b2)
            db.flush()
        db.rollback()

    def test_same_name_different_site_allowed(self, db):
        org = _make_org(db)
        ej = _make_ej(db, org.id)
        pf = _make_portefeuille(db, ej.id)
        s1 = _make_site(db, pf.id, nom="Site A")
        s2 = _make_site(db, pf.id, nom="Site B")
        _make_batiment(db, s1.id, nom="Hall")
        _make_batiment(db, s2.id, nom="Hall")
        db.commit()
        assert db.query(Batiment).count() == 2

    def test_soft_deleted_name_allows_reuse(self, db):
        """Soft-deleted batiment name can be reused on same site."""
        from datetime import datetime

        _, _, _, site = _scaffold(db)
        b = _make_batiment(db, site.id, nom="Hall Recyclé")
        db.commit()
        b.deleted_at = datetime.now(timezone.utc)
        db.commit()
        _make_batiment(db, site.id, nom="Hall Recyclé")
        db.commit()  # Should not raise


# ========================================
# TEST 6: Contract overlap rejection
# ========================================


class TestContractOverlapRejected:
    """Tests for check_contract_overlap via the billing route."""

    def test_overlapping_contracts_rejected(self, db):
        """Two contracts for same site+energy with overlapping dates → 409."""
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        _make_contract(db, site.id, start=date(2024, 1, 1), end=date(2024, 12, 31))
        db.commit()

        # Overlaps: 2024-06-01 to 2025-06-01
        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            date(2024, 6, 1),
            date(2025, 6, 1),
        )
        assert overlap is not None

    def test_non_overlapping_contracts_allowed(self, db):
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        _make_contract(db, site.id, start=date(2024, 1, 1), end=date(2024, 6, 30))
        db.commit()

        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            date(2024, 7, 1),
            date(2024, 12, 31),
        )
        assert overlap is None

    def test_open_ended_contract_overlaps_everything(self, db):
        """A contract with end_date=None (open-ended) overlaps any future date."""
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        _make_contract(db, site.id, start=date(2024, 1, 1), end=None)
        db.commit()

        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            date(2030, 1, 1),
            date(2030, 12, 31),
        )
        assert overlap is not None

    def test_different_energy_type_no_overlap(self, db):
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        _make_contract(db, site.id, energy_type=BillingEnergyType.ELEC, start=date(2024, 1, 1), end=date(2024, 12, 31))
        db.commit()

        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.GAZ,
            date(2024, 6, 1),
            date(2025, 6, 1),
        )
        assert overlap is None

    def test_exclude_self_on_update(self, db):
        """When updating a contract, exclude_id prevents self-match."""
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        c = _make_contract(db, site.id, start=date(2024, 1, 1), end=date(2024, 12, 31))
        db.commit()

        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            date(2024, 1, 1),
            date(2024, 12, 31),
            exclude_id=c.id,
        )
        assert overlap is None

    def test_both_open_ended_overlap(self, db):
        """Two fully open-ended contracts (start=None, end=None) overlap."""
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        _make_contract(db, site.id, start=None, end=None)
        db.commit()

        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            None,
            None,
        )
        assert overlap is not None

    def test_adjacent_contracts_no_overlap(self, db):
        """Back-to-back contracts (end = day before start) do NOT overlap."""
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        _make_contract(db, site.id, start=date(2024, 1, 1), end=date(2024, 6, 30))
        db.commit()

        # Adjacent: starts the day after
        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            date(2024, 7, 1),
            date(2024, 12, 31),
        )
        assert overlap is None

    def test_touching_contracts_overlap(self, db):
        """Contracts sharing a boundary day (end = start) DO overlap."""
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        _make_contract(db, site.id, start=date(2024, 1, 1), end=date(2024, 6, 30))
        db.commit()

        # Starts on same day as end
        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            date(2024, 6, 30),
            date(2024, 12, 31),
        )
        assert overlap is not None


# ========================================
# TEST 6b: Contract update overlap (PATCH guard)
# ========================================


class TestContractUpdateOverlap:
    """Updating a contract's dates must also check for overlap (exclude_id)."""

    def test_update_into_overlap_detected(self, db):
        """Moving a contract's dates to overlap another → check catches it."""
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        c1 = _make_contract(db, site.id, start=date(2024, 1, 1), end=date(2024, 6, 30))
        c2 = _make_contract(db, site.id, start=date(2024, 7, 1), end=date(2024, 12, 31))
        db.commit()

        # Simulate PATCH of c2: extend start_date into c1's range
        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            date(2024, 3, 1),
            date(2024, 12, 31),
            exclude_id=c2.id,
        )
        assert overlap is not None
        assert overlap.id == c1.id

    def test_update_no_overlap_passes(self, db):
        """Moving dates within non-overlapping range → no conflict."""
        from routes.billing import check_contract_overlap

        _, _, _, site = _scaffold(db)

        c1 = _make_contract(db, site.id, start=date(2024, 1, 1), end=date(2024, 6, 30))
        c2 = _make_contract(db, site.id, start=date(2024, 7, 1), end=date(2024, 12, 31))
        db.commit()

        # Simulate PATCH of c2: shrink range (still non-overlapping)
        overlap = check_contract_overlap(
            db,
            site.id,
            BillingEnergyType.ELEC,
            date(2024, 8, 1),
            date(2024, 11, 30),
            exclude_id=c2.id,
        )
        assert overlap is None


# ========================================
# TEST 7: DeliveryPoint delete cascades
# ========================================


class TestDeliveryPointDeleteCascadesCompteur:
    def test_dp_hard_delete_nullifies_compteur_fk(self, db, engine):
        """Hard-deleting a DP sets compteur.delivery_point_id to NULL (trigger)."""
        _, _, _, site = _scaffold(db)

        dp = _make_dp(db, site.id, code="11111111111111")
        db.commit()

        cpt = _make_compteur(db, site.id, dp_id=dp.id, numero_serie="CPT-CASCADE")
        db.commit()
        assert cpt.delivery_point_id == dp.id

        # Hard-delete the DP via raw SQL (trigger fires)
        dp_id = dp.id
        cpt_id = cpt.id
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM delivery_points WHERE id = :id"), {"id": dp_id})

        # Verify compteur still exists but FK is NULL
        db.expire_all()
        cpt_after = db.get(Compteur, cpt_id)
        assert cpt_after is not None, "Compteur should still exist"
        assert cpt_after.delivery_point_id is None, "FK should be NULL after DP deletion"

    def test_dp_soft_delete_preserves_compteur_link(self, db):
        """Soft-deleting a DP does NOT nullify the FK (trigger only fires on hard DELETE)."""
        from datetime import datetime

        _, _, _, site = _scaffold(db)

        dp = _make_dp(db, site.id, code="22222222222222")
        cpt = _make_compteur(db, site.id, dp_id=dp.id, numero_serie="CPT-SOFT")
        db.commit()

        dp.deleted_at = datetime.now(timezone.utc)
        db.commit()

        db.expire_all()
        cpt_after = db.get(Compteur, cpt.id)
        assert cpt_after.delivery_point_id == dp.id, "Soft delete should keep FK intact"
