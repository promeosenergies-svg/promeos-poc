"""
PROMEOS - Tests Unique PRM/PCE (delivery point)
Covers: quality rule dup_delivery_point_global, activation blocking, soft-delete reuse.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille, Compteur,
    StagingBatch, StagingSite, StagingCompteur, QualityFinding,
    StagingStatus, ImportSourceType, QualityRuleSeverity,
    TypeSite, TypeCompteur, EnergyVector,
)
from services.patrimoine_service import (
    create_staging_batch, run_quality_gate, activate_batch,
)
from services.quality_rules import check_duplicate_delivery_point


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


def _create_org(db_session):
    org = Organisation(nom="Test Org", type_client="bureau", actif=True, siren="123456789")
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test EJ", siren="123456789")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Test", description="Test")
    db_session.add(pf)
    db_session.flush()

    return org, ej, pf


def _create_batch_with_meter(db_session, org_id, meter_id, meter_id_2=None):
    """Create staging batch with 1 site + 1 or 2 compteurs."""
    batch = create_staging_batch(
        db_session, org_id=org_id, user_id=None,
        source_type=ImportSourceType.CSV, mode="import",
    )

    ss = StagingSite(
        batch_id=batch.id, row_number=2, nom="Site Test",
        adresse="1 rue Test", code_postal="75001", ville="Paris",
        surface_m2=500,
    )
    db_session.add(ss)
    db_session.flush()

    sc1 = StagingCompteur(
        batch_id=batch.id, staging_site_id=ss.id,
        row_number=2, numero_serie="SERIE-001",
        meter_id=meter_id, type_compteur="electricite",
    )
    db_session.add(sc1)

    if meter_id_2:
        sc2 = StagingCompteur(
            batch_id=batch.id, staging_site_id=ss.id,
            row_number=3, numero_serie="SERIE-002",
            meter_id=meter_id_2, type_compteur="electricite",
        )
        db_session.add(sc2)

    db_session.flush()
    return batch, ss


# ========================================
# Tests
# ========================================

class TestDuplicatePrmInStagingBlocked:
    """Two staging rows with the same meter_id in the same batch → CRITICAL finding."""

    def test_duplicate_prm_in_staging_blocked(self, db_session):
        org, ej, pf = _create_org(db_session)

        batch = create_staging_batch(
            db_session, org_id=org.id, user_id=None,
            source_type=ImportSourceType.CSV, mode="import",
        )

        ss = StagingSite(
            batch_id=batch.id, row_number=2, nom="Site A",
            adresse="1 rue A", code_postal="75001", ville="Paris",
        )
        db_session.add(ss)
        db_session.flush()

        # Two compteurs with same meter_id
        sc1 = StagingCompteur(
            batch_id=batch.id, staging_site_id=ss.id,
            row_number=2, numero_serie="S-001",
            meter_id="12345678901234", type_compteur="electricite",
        )
        sc2 = StagingCompteur(
            batch_id=batch.id, staging_site_id=ss.id,
            row_number=3, numero_serie="S-002",
            meter_id="12345678901234", type_compteur="electricite",
        )
        db_session.add_all([sc1, sc2])
        db_session.flush()

        findings = check_duplicate_delivery_point(db_session, batch.id)

        assert len(findings) == 1
        f = findings[0]
        assert f["rule_id"] == "dup_delivery_point_global"
        assert f["severity"] == QualityRuleSeverity.CRITICAL
        evidence = json.loads(f["evidence_json"])
        assert evidence["scope"] == "intra_staging"
        assert evidence["value"] == "12345678901234"

    def test_quality_gate_flags_intra_staging_dup(self, db_session):
        """Full quality gate run detects intra-staging duplicate."""
        org, ej, pf = _create_org(db_session)
        batch, ss = _create_batch_with_meter(
            db_session, org.id,
            meter_id="PRM-DUPLICATE",
            meter_id_2="PRM-DUPLICATE",
        )

        results = run_quality_gate(db_session, batch.id)
        critical = [r for r in results if r["rule_id"] == "dup_delivery_point_global"]
        assert len(critical) >= 1
        assert critical[0]["severity"] == "critical"


class TestDuplicatePrmExistingDbBlocked:
    """Staging meter_id already exists in active DB compteurs → CRITICAL finding."""

    def test_duplicate_prm_existing_db_blocked(self, db_session):
        org, ej, pf = _create_org(db_session)

        # Pre-existing active compteur with meter_id
        existing_site = Site(
            nom="Existing Site", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(existing_site)
        db_session.flush()

        existing_cpt = Compteur(
            site_id=existing_site.id, type=TypeCompteur.ELECTRICITE,
            numero_serie="EXIST-001", meter_id="PRM-EXISTING-001",
            actif=True,
        )
        db_session.add(existing_cpt)
        db_session.flush()

        # Staging batch with same meter_id
        batch, ss = _create_batch_with_meter(db_session, org.id, meter_id="PRM-EXISTING-001")

        findings = check_duplicate_delivery_point(db_session, batch.id)

        assert len(findings) == 1
        f = findings[0]
        assert f["rule_id"] == "dup_delivery_point_global"
        assert f["severity"] == QualityRuleSeverity.CRITICAL
        evidence = json.loads(f["evidence_json"])
        assert evidence["scope"] == "vs_existing_db"
        assert evidence["dup_with_existing_id"] == existing_cpt.id


class TestSoftDeletedPrmAllowsReuse:
    """A soft-deleted compteur's meter_id should NOT block a new import."""

    def test_soft_deleted_prm_allows_reuse(self, db_session):
        org, ej, pf = _create_org(db_session)

        # Pre-existing compteur with meter_id — then soft-delete it
        existing_site = Site(
            nom="Old Site", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(existing_site)
        db_session.flush()

        old_cpt = Compteur(
            site_id=existing_site.id, type=TypeCompteur.ELECTRICITE,
            numero_serie="OLD-001", meter_id="PRM-REUSE-001",
            actif=True,
        )
        db_session.add(old_cpt)
        db_session.flush()

        # Soft-delete the old compteur
        old_cpt.soft_delete(by="admin", reason="Decommissioned")
        db_session.flush()

        # New staging batch reuses the same meter_id
        batch, ss = _create_batch_with_meter(db_session, org.id, meter_id="PRM-REUSE-001")

        findings = check_duplicate_delivery_point(db_session, batch.id)

        # No findings — soft-deleted compteur does not block reuse
        assert len(findings) == 0


class TestActivationRollbackOnDuplicate:
    """Activation must fail if meter_id collides with existing active compteur."""

    def test_activation_rollback_on_duplicate(self, db_session):
        org, ej, pf = _create_org(db_session)

        # Pre-existing active compteur
        existing_site = Site(
            nom="Existing Site", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(existing_site)
        db_session.flush()

        existing_cpt = Compteur(
            site_id=existing_site.id, type=TypeCompteur.ELECTRICITE,
            numero_serie="EXIST-ACT-001", meter_id="PRM-BLOCK-001",
            actif=True,
        )
        db_session.add(existing_cpt)
        db_session.flush()

        # Create staging batch with colliding meter_id
        batch, ss = _create_batch_with_meter(db_session, org.id, meter_id="PRM-BLOCK-001")

        # Run quality gate — should detect the collision
        results = run_quality_gate(db_session, batch.id)
        critical = [r for r in results if r["rule_id"] == "dup_delivery_point_global"]
        assert len(critical) >= 1

        # Activation should fail due to unresolved critical findings
        with pytest.raises(ValueError, match="unresolved blocking/critical"):
            activate_batch(db_session, batch.id, pf.id)

        # Batch should NOT be marked as APPLIED
        db_session.refresh(batch)
        assert batch.status != StagingStatus.APPLIED

    def test_activation_pre_check_blocks_even_if_findings_resolved(self, db_session):
        """Even if all findings are manually resolved, pre-activation check still catches collisions."""
        org, ej, pf = _create_org(db_session)

        # Pre-existing active compteur
        existing_site = Site(
            nom="Existing Site 2", type=TypeSite.BUREAU,
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(existing_site)
        db_session.flush()

        existing_cpt = Compteur(
            site_id=existing_site.id, type=TypeCompteur.ELECTRICITE,
            numero_serie="EXIST-PRE-001", meter_id="PRM-PRECHECK-001",
            actif=True,
        )
        db_session.add(existing_cpt)
        db_session.flush()

        # Create staging batch
        batch, ss = _create_batch_with_meter(db_session, org.id, meter_id="PRM-PRECHECK-001")

        # Run quality gate
        run_quality_gate(db_session, batch.id)

        # Forcefully resolve all findings (simulating a bug or manual override)
        findings = db_session.query(QualityFinding).filter(
            QualityFinding.batch_id == batch.id,
        ).all()
        for f in findings:
            f.resolved = True
        db_session.flush()

        # Activation should STILL fail due to pre-activation DB collision check
        with pytest.raises(ValueError, match="duplicate delivery point"):
            activate_batch(db_session, batch.id, pf.id)

    def test_activation_succeeds_with_unique_meter_id(self, db_session):
        """Activation succeeds when meter_id is globally unique."""
        org, ej, pf = _create_org(db_session)

        batch, ss = _create_batch_with_meter(db_session, org.id, meter_id="PRM-UNIQUE-999")

        # Run quality gate — no critical findings expected
        results = run_quality_gate(db_session, batch.id)
        critical = [r for r in results if r["rule_id"] == "dup_delivery_point_global"]
        assert len(critical) == 0

        # Activation should succeed
        result = activate_batch(db_session, batch.id, pf.id)
        assert result["compteurs_created"] >= 1

        # Verify compteur was created with correct meter_id
        cpt = db_session.query(Compteur).filter(Compteur.meter_id == "PRM-UNIQUE-999").first()
        assert cpt is not None
        assert cpt.actif is True
