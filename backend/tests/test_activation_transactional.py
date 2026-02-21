"""
PROMEOS - Tests Activation Transactionnelle
Covers: atomic rollback, partial failure, idempotence, activation log.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Compteur, Organisation, EntiteJuridique, Portefeuille,
    StagingBatch, StagingSite, StagingCompteur, QualityFinding,
    ActivationLog, ActivationLogStatus,
    StagingStatus, ImportSourceType, QualityRuleSeverity,
)
from services.patrimoine_service import (
    create_staging_batch, run_quality_gate, activate_batch,
)


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
    org = Organisation(nom="Test Org", type_client="bureau", actif=True, siren="443061841")
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test EJ", siren="443061841")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Test", description="Test")
    db_session.add(pf)
    db_session.flush()

    return org, ej, pf


def _create_batch_with_sites(db_session, org_id, sites_data):
    """Create staging batch with multiple sites + compteurs."""
    batch = create_staging_batch(
        db_session, org_id=org_id, user_id=None,
        source_type=ImportSourceType.CSV, mode="import",
    )

    for i, site in enumerate(sites_data, start=1):
        ss = StagingSite(
            batch_id=batch.id, row_number=i + 1,
            nom=site["nom"],
            adresse=site.get("adresse", "1 rue Test"),
            code_postal=site.get("code_postal", "75001"),
            ville=site.get("ville", "Paris"),
            surface_m2=site.get("surface_m2", 500),
        )
        db_session.add(ss)
        db_session.flush()

        for j, meter in enumerate(site.get("meters", []), start=1):
            sc = StagingCompteur(
                batch_id=batch.id, staging_site_id=ss.id,
                row_number=(i * 10) + j,
                numero_serie=meter.get("serie", f"SERIE-{i}-{j}"),
                meter_id=meter.get("meter_id"),
                type_compteur=meter.get("type", "electricite"),
            )
            db_session.add(sc)

    db_session.flush()
    return batch


# ========================================
# Tests
# ========================================

class TestCrashDuringActivationRollback:
    """Crash during entity creation → full rollback, no partial data."""

    def test_crash_during_activation_rollback(self, db_session):
        org, ej, pf = _create_org(db_session)

        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Site A", "meters": [{"meter_id": "11111111111111"}]},
            {"nom": "Site B", "meters": [{"meter_id": "22222222222222"}]},
        ])

        run_quality_gate(db_session, batch.id)

        # Count sites before activation
        sites_before = db_session.query(Site).count()

        # Patch create_site_from_data to fail on the 2nd call
        call_count = {"n": 0}
        original_create = __import__("services.onboarding_service", fromlist=["create_site_from_data"]).create_site_from_data

        def failing_create(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise RuntimeError("Simulated crash on site #2")
            return original_create(*args, **kwargs)

        with patch("services.patrimoine_service.create_site_from_data", side_effect=failing_create):
            with pytest.raises(ValueError, match="Activation failed"):
                activate_batch(db_session, batch.id, pf.id)

        # No new sites should exist — savepoint rolled back everything
        sites_after = db_session.query(Site).count()
        assert sites_after == sites_before

        # Batch should NOT be marked as APPLIED
        db_session.refresh(batch)
        assert batch.status != StagingStatus.APPLIED

    def test_crash_creates_failed_log(self, db_session):
        """Even on crash, ActivationLog is created with FAILED status."""
        org, ej, pf = _create_org(db_session)

        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Site Crash", "meters": [{"meter_id": "33333333333333"}]},
        ])

        run_quality_gate(db_session, batch.id)

        with patch(
            "services.patrimoine_service.create_site_from_data",
            side_effect=RuntimeError("DB explosion"),
        ):
            with pytest.raises(ValueError, match="Activation failed"):
                activate_batch(db_session, batch.id, pf.id)

        # ActivationLog should exist with FAILED status
        log = db_session.query(ActivationLog).filter(
            ActivationLog.batch_id == batch.id,
        ).first()
        assert log is not None
        assert log.status == ActivationLogStatus.FAILED
        assert "DB explosion" in log.error_message


class TestDuplicateMeterActivationBlocked:
    """Duplicate meter_id → activation blocked before any entity created."""

    def test_duplicate_meter_activation_blocked(self, db_session):
        org, ej, pf = _create_org(db_session)

        # Create existing active compteur
        existing_site = Site(
            nom="Existing", type="bureau",
            portefeuille_id=pf.id, actif=True,
        )
        db_session.add(existing_site)
        db_session.flush()

        existing_cpt = Compteur(
            site_id=existing_site.id, type="electricite",
            numero_serie="EXIST-001", meter_id="44444444444444",
            actif=True,
        )
        db_session.add(existing_cpt)
        db_session.flush()

        # Staging batch with colliding meter_id
        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "New Site", "meters": [{"meter_id": "44444444444444"}]},
        ])

        run_quality_gate(db_session, batch.id)

        # Quality gate flagged duplicate as CRITICAL → pre-check blocks on unresolved findings
        with pytest.raises(ValueError, match="unresolved blocking/critical"):
            activate_batch(db_session, batch.id, pf.id)

        # No activation log with SUCCESS
        success_log = db_session.query(ActivationLog).filter(
            ActivationLog.batch_id == batch.id,
            ActivationLog.status == ActivationLogStatus.SUCCESS,
        ).first()
        assert success_log is None


class TestPartialFailureNoEntityPersisted:
    """Partial failure mid-loop → zero entities persisted."""

    def test_partial_failure_no_entity_persisted(self, db_session):
        org, ej, pf = _create_org(db_session)

        # 3 sites — make provision_site fail on the 3rd
        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Site 1", "meters": [{"meter_id": "55555555555551"}]},
            {"nom": "Site 2", "meters": [{"meter_id": "55555555555552"}]},
            {"nom": "Site 3", "meters": [{"meter_id": "55555555555553"}]},
        ])

        run_quality_gate(db_session, batch.id)

        compteurs_before = db_session.query(Compteur).count()

        call_count = {"n": 0}
        original_provision = __import__("services.onboarding_service", fromlist=["provision_site"]).provision_site

        def failing_provision(db, site):
            call_count["n"] += 1
            if call_count["n"] >= 3:
                raise RuntimeError("Simulated failure on site #3")
            return original_provision(db, site)

        with patch("services.patrimoine_service.provision_site", side_effect=failing_provision):
            with pytest.raises(ValueError, match="Activation failed"):
                activate_batch(db_session, batch.id, pf.id)

        # Zero new compteurs — atomic rollback
        compteurs_after = db_session.query(Compteur).count()
        assert compteurs_after == compteurs_before


class TestIdempotentRerun:
    """Double activation → same result, no duplicate entities."""

    def test_idempotent_rerun_no_duplicate(self, db_session):
        org, ej, pf = _create_org(db_session)

        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Unique Site", "meters": [{"meter_id": "66666666666666"}]},
        ])

        run_quality_gate(db_session, batch.id)

        # First activation
        result1 = activate_batch(db_session, batch.id, pf.id)
        assert result1["sites_created"] >= 1
        assert "activation_log_id" in result1

        sites_after_first = db_session.query(Site).count()
        compteurs_after_first = db_session.query(Compteur).count()

        # Second activation — idempotent
        result2 = activate_batch(db_session, batch.id, pf.id)
        assert "already applied" in result2.get("detail", "").lower()

        # No new entities created
        sites_after_second = db_session.query(Site).count()
        compteurs_after_second = db_session.query(Compteur).count()
        assert sites_after_second == sites_after_first
        assert compteurs_after_second == compteurs_after_first


class TestActivationLogCreated:
    """ActivationLog entries created for both success and failure."""

    def test_activation_log_on_success(self, db_session):
        org, ej, pf = _create_org(db_session)

        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Log Site", "meters": [{"meter_id": "77777777777777"}]},
        ])

        run_quality_gate(db_session, batch.id)

        result = activate_batch(db_session, batch.id, pf.id)

        log = db_session.query(ActivationLog).filter(
            ActivationLog.batch_id == batch.id,
            ActivationLog.status == ActivationLogStatus.SUCCESS,
        ).first()

        assert log is not None
        assert log.started_at is not None
        assert log.completed_at is not None
        assert log.sites_created >= 1
        assert log.compteurs_created >= 1
        assert log.activation_hash is not None
        assert log.id == result["activation_log_id"]

    def test_activation_log_on_failure(self, db_session):
        org, ej, pf = _create_org(db_session)

        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Fail Site", "meters": [{"meter_id": "88888888888888"}]},
        ])

        run_quality_gate(db_session, batch.id)

        with patch(
            "services.patrimoine_service.create_site_from_data",
            side_effect=RuntimeError("Controlled failure"),
        ):
            with pytest.raises(ValueError, match="Activation failed"):
                activate_batch(db_session, batch.id, pf.id)

        log = db_session.query(ActivationLog).filter(
            ActivationLog.batch_id == batch.id,
            ActivationLog.status == ActivationLogStatus.FAILED,
        ).first()

        assert log is not None
        assert log.error_message is not None
        assert "Controlled failure" in log.error_message
        assert log.activation_hash is not None

    def test_activation_log_records_hash(self, db_session):
        """Activation hash is deterministic for same batch content."""
        org, ej, pf = _create_org(db_session)

        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Hash Site", "meters": [{"meter_id": "99999999999998"}]},
        ])

        run_quality_gate(db_session, batch.id)

        result = activate_batch(db_session, batch.id, pf.id)

        log = db_session.query(ActivationLog).filter(
            ActivationLog.id == result["activation_log_id"],
        ).first()

        assert log.activation_hash is not None
        assert len(log.activation_hash) == 64  # SHA-256 hex


class TestActivationAtomicityRollback:
    """batch.status + log.status must be consistent after a mid-activation crash.

    Regression: if status updates leak outside the savepoint, a rollback
    can leave batch.status = APPLIED while zero entities were created.
    """

    def test_activation_atomicity_rollback(self, db_session):
        """Crash mid-activation → batch stays VALIDATED, log is FAILED, 0 entities."""
        org, ej, pf = _create_org(db_session)

        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Atom Site A", "meters": [{"meter_id": "10000000000001"}]},
            {"nom": "Atom Site B", "meters": [{"meter_id": "10000000000002"}]},
            {"nom": "Atom Site C", "meters": [{"meter_id": "10000000000003"}]},
        ])

        run_quality_gate(db_session, batch.id)

        # Sanity: batch is VALIDATED before activation
        assert batch.status == StagingStatus.VALIDATED

        sites_before = db_session.query(Site).count()
        compteurs_before = db_session.query(Compteur).count()

        # Force crash after first site — inside the savepoint
        call_count = {"n": 0}
        original_create = __import__(
            "services.onboarding_service", fromlist=["create_site_from_data"]
        ).create_site_from_data

        def crash_on_second(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise RuntimeError("Simulated mid-activation crash")
            return original_create(*args, **kwargs)

        with patch("services.patrimoine_service.create_site_from_data", side_effect=crash_on_second):
            with pytest.raises(ValueError, match="Activation failed"):
                activate_batch(db_session, batch.id, pf.id)

        # ---- Atomicity checks ----

        # 1. Re-read batch from DB (not in-memory cache)
        db_session.expire(batch)
        assert batch.status != StagingStatus.APPLIED, (
            "CRITICAL: batch.status leaked to APPLIED despite rollback"
        )
        assert batch.status == StagingStatus.VALIDATED, (
            "batch.status should stay VALIDATED after failed activation"
        )

        # 2. Zero entities created — full rollback
        assert db_session.query(Site).count() == sites_before
        assert db_session.query(Compteur).count() == compteurs_before

        # 3. ActivationLog exists with FAILED (not SUCCESS, not STARTED)
        log = db_session.query(ActivationLog).filter(
            ActivationLog.batch_id == batch.id,
        ).first()
        assert log is not None
        assert log.status == ActivationLogStatus.FAILED, (
            f"log.status should be FAILED, got {log.status}"
        )
        assert log.error_message is not None
        assert "mid-activation crash" in log.error_message

        # 3b. Counters must be 0 — no stale values leaked from savepoint
        assert log.sites_created == 0 or log.sites_created is None, (
            f"CRITICAL: log.sites_created={log.sites_created} leaked from rolled-back savepoint"
        )
        assert log.compteurs_created == 0 or log.compteurs_created is None, (
            f"CRITICAL: log.compteurs_created={log.compteurs_created} leaked from rolled-back savepoint"
        )

        # 4. Batch can be re-activated (not stuck in inconsistent state)
        result = activate_batch(db_session, batch.id, pf.id)
        assert result["sites_created"] == 3
        db_session.expire(batch)
        assert batch.status == StagingStatus.APPLIED

    def test_failed_log_counters_are_zero(self, db_session):
        """Crash after 1st site → log.sites_created must be 0 (not stale from savepoint)."""
        org, ej, pf = _create_org(db_session)

        batch = _create_batch_with_sites(db_session, org.id, [
            {"nom": "Counter A", "meters": [{"meter_id": "10000000000010"}]},
            {"nom": "Counter B", "meters": [{"meter_id": "10000000000011"}]},
        ])

        run_quality_gate(db_session, batch.id)

        call_count = {"n": 0}
        original_create = __import__(
            "services.onboarding_service", fromlist=["create_site_from_data"]
        ).create_site_from_data

        def crash_on_second(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise RuntimeError("Crash after first site created")
            return original_create(*args, **kwargs)

        with patch("services.patrimoine_service.create_site_from_data", side_effect=crash_on_second):
            with pytest.raises(ValueError, match="Activation failed"):
                activate_batch(db_session, batch.id, pf.id)

        # Re-read log from DB to get actual persisted values
        log = db_session.query(ActivationLog).filter(
            ActivationLog.batch_id == batch.id,
        ).order_by(ActivationLog.id.desc()).first()

        assert log.status == ActivationLogStatus.FAILED
        # Key invariant: counters must be 0, NOT the partial count from inside the savepoint
        assert log.sites_created == 0 or log.sites_created is None
        assert log.compteurs_created == 0 or log.compteurs_created is None
        assert log.error_message is not None
