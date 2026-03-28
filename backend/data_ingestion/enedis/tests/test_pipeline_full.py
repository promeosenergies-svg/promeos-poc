"""Tests for ingest_directory() — SF3-B full pipeline batch ingestion."""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from data_ingestion.enedis.config import MAX_RETRIES
from data_ingestion.enedis.enums import FluxStatus, IngestionRunStatus
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxFileError,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
    IngestionRun,
)
from data_ingestion.enedis.pipeline import ingest_directory, ingest_file

from .conftest import TEST_IV, TEST_KEY, make_encrypted_zip


# ---------------------------------------------------------------------------
# Shared XML fixtures (minimal valid XML per flux type)
# ---------------------------------------------------------------------------

R4H_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<Courbe>
  <Entete>
    <Identifiant_Flux>R4x</Identifiant_Flux>
    <Frequence_Publication>H</Frequence_Publication>
  </Entete>
  <Corps>
    <Identifiant_PRM>30000210411333</Identifiant_PRM>
    <Donnees_Courbe>
      <Horodatage_Debut>2026-03-07T00:00:00+01:00</Horodatage_Debut>
      <Horodatage_Fin>2026-03-07T23:59:59+01:00</Horodatage_Fin>
      <Granularite>5</Granularite>
      <Unite_Mesure>kW</Unite_Mesure>
      <Grandeur_Metier>CONS</Grandeur_Metier>
      <Grandeur_Physique>EA</Grandeur_Physique>
      <Donnees_Point_Mesure Horodatage="2026-03-07T00:00:00+01:00" Valeur_Point="398" Statut_Point="R"/>
    </Donnees_Courbe>
  </Corps>
</Courbe>"""

R171_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<R171>
  <entete><emetteur>Enedis</emetteur><flux>R171</flux></entete>
  <serieMesuresDateesListe>
    <serieMesuresDatees>
      <prmId>30000550506121</prmId>
      <type>INDEX</type>
      <grandeurPhysique>EA</grandeurPhysique>
      <unite>Wh</unite>
      <mesuresDateesListe>
        <mesureDatee>
          <dateFin>2026-03-01T00:00:00</dateFin>
          <valeur>1320</valeur>
        </mesureDatee>
      </mesuresDateesListe>
    </serieMesuresDatees>
  </serieMesuresDateesListe>
</R171>"""

R50_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<R50>
  <En_Tete_Flux><Identifiant_Flux>R50</Identifiant_Flux></En_Tete_Flux>
  <PRM>
    <Id_PRM>30001234567890</Id_PRM>
    <Donnees_Releve>
      <Date_Releve>2026-03-01</Date_Releve>
      <PDC><H>2026-03-01T00:00:00+01:00</H><V>20710</V></PDC>
    </Donnees_Releve>
  </PRM>
</R50>"""

R151_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<R151>
  <En_Tete_Flux><Identifiant_Flux>R151</Identifiant_Flux></En_Tete_Flux>
  <PRM>
    <Id_PRM>30001234567890</Id_PRM>
    <Donnees_Releve>
      <Date_Releve>2026-03-01</Date_Releve>
      <Classe_Temporelle_Distributeur>
        <Id_Classe_Temporelle>HCB</Id_Classe_Temporelle>
        <Valeur>83044953</Valeur>
      </Classe_Temporelle_Distributeur>
    </Donnees_Releve>
  </PRM>
</R151>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_encrypted(directory: Path, filename: str, xml: bytes) -> Path:
    """Write an encrypted zip file to *directory* with the given filename."""
    ct = make_encrypted_zip(xml, "inner.xml", TEST_KEY, TEST_IV)
    path = directory / filename
    path.write_bytes(ct)
    return path


def _write_corrupt(directory: Path, filename: str) -> Path:
    """Write a corrupt (random bytes) file to *directory*."""
    path = directory / filename
    path.write_bytes(os.urandom(256))
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBatchMixed:
    """Directory with multiple flux types — all processed correctly."""

    def test_mixed_flux_types(self, db, tmp_path, test_keys):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260301.zip", R171_XML)
        _write_encrypted(tmp_path, "ERDF_R50_23X--TEST_20260301.zip", R50_XML)
        _write_encrypted(tmp_path, "ERDF_R151_23X--TEST_20260301.zip", R151_XML)

        # R172 — should be skipped
        (tmp_path / "ENEDIS_23X--TEST_R172_20260301.zip").write_bytes(os.urandom(64))

        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["received"] == 5
        assert counters["parsed"] == 4
        assert counters["skipped"] == 1
        assert counters["error"] == 0
        assert counters["already_processed"] == 0

        # Verify all flux types present in DB
        flux_types = {f.flux_type for f in db.query(EnedisFluxFile).all()}
        assert flux_types == {"R4H", "R171", "R50", "R151", "R172"}

        # Verify measures stored in correct tables
        assert db.query(EnedisFluxMesureR4x).count() == 1
        assert db.query(EnedisFluxMesureR171).count() == 1
        assert db.query(EnedisFluxMesureR50).count() == 1
        assert db.query(EnedisFluxMesureR151).count() == 1


class TestIdempotenceBatch:
    """Running ingest_directory twice is a no-op."""

    def test_second_run_all_already_processed(self, db, tmp_path, test_keys):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260301.zip", R171_XML)

        counters1 = ingest_directory(tmp_path, db, test_keys)
        counters2 = ingest_directory(tmp_path, db, test_keys)

        assert counters1["received"] == 2
        assert counters1["parsed"] == 2

        assert counters2["received"] == 0
        assert counters2["already_processed"] == 2
        assert counters2["parsed"] == 0

        # No duplicate data
        assert db.query(EnedisFluxFile).count() == 2
        assert db.query(EnedisFluxMesureR4x).count() == 1
        assert db.query(EnedisFluxMesureR171).count() == 1


class TestResilience:
    """Mix of valid, corrupt, and out-of-scope files."""

    def test_corrupt_does_not_block_batch(self, db, tmp_path, test_keys):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_corrupt(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_CORRUPT.zip")
        (tmp_path / "ENEDIS_23X--TEST_R172_20260301.zip").write_bytes(os.urandom(64))

        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["received"] == 3
        assert counters["parsed"] == 1
        assert counters["error"] == 1
        assert counters["skipped"] == 1

        # All 3 files recorded — no crash
        assert db.query(EnedisFluxFile).count() == 3


class TestEmptyDirectory:
    """Empty directory returns zero counters."""

    def test_empty_dir(self, db, tmp_path, test_keys):
        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters == {
            "received": 0, "parsed": 0, "needs_review": 0,
            "skipped": 0, "error": 0, "permanently_failed": 0,
            "already_processed": 0,
            "retried": 0, "max_retries_reached": 0,
        }
        assert db.query(EnedisFluxFile).count() == 0


class TestAllSkipped:
    """Directory with only out-of-scope files."""

    def test_only_r172(self, db, tmp_path, test_keys):
        (tmp_path / "ENEDIS_23X--TEST_R172_A.zip").write_bytes(os.urandom(64))
        (tmp_path / "ENEDIS_23X--TEST_R172_B.zip").write_bytes(os.urandom(64))

        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["received"] == 2
        assert counters["skipped"] == 2
        assert counters["parsed"] == 0


class TestLifecycleReceived:
    """RECEIVED status lifecycle — files are registered before processing."""

    def test_intermediate_received_state_visible_between_phases(self, db, tmp_path, test_keys):
        """After Phase 1 scan, files must be RECEIVED. After Phase 2, they transition."""
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260301.zip", R171_XML)

        # Capture the intermediate DB state between Phase 1 (register) and Phase 2 (process)
        # by wrapping ingest_file to snapshot statuses before it runs.
        intermediate_statuses: list[str] = []
        original_ingest_file = ingest_file.__wrapped__ if hasattr(ingest_file, "__wrapped__") else ingest_file

        def capturing_ingest_file(file_path, session, keys, chunk_size=1000, archive_dir=None):
            # On first call, capture the state of ALL files (both should be RECEIVED)
            if not intermediate_statuses:
                for f in session.query(EnedisFluxFile).all():
                    intermediate_statuses.append(f.status)
            return original_ingest_file(file_path, session, keys, chunk_size, archive_dir)

        with patch("data_ingestion.enedis.pipeline.ingest_file", side_effect=capturing_ingest_file):
            counters = ingest_directory(tmp_path, db, test_keys)

        # Between phases: both files were RECEIVED
        assert len(intermediate_statuses) == 2
        assert all(s == FluxStatus.RECEIVED for s in intermediate_statuses)

        # After processing: no file remains RECEIVED
        assert db.query(EnedisFluxFile).filter_by(status=FluxStatus.RECEIVED).count() == 0
        assert db.query(EnedisFluxFile).filter_by(status=FluxStatus.PARSED).count() == 2
        assert counters["received"] == 2
        assert counters["parsed"] == 2


class TestReceivedStale:
    """Crash recovery: stale RECEIVED records are re-processed."""

    def test_stale_received_reprocessed(self, db, tmp_path, test_keys):
        """Simulate a crash: manually create a RECEIVED record, then run ingest_directory."""
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        file_path = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_20260301.zip"
        file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        # Simulate crash: file registered as RECEIVED but never processed
        stale_record = EnedisFluxFile(
            filename="ENEDIS_23X--TEST_R4H_CDC_20260301.zip",
            file_hash=file_hash,
            flux_type="R4H",
            status=FluxStatus.RECEIVED,
            measures_count=0,
        )
        db.add(stale_record)
        db.commit()
        stale_id = stale_record.id

        # Run ingest_directory — should re-process the stale file
        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["received"] == 1  # stale RECEIVED counted
        assert counters["parsed"] == 1
        assert counters["already_processed"] == 0

        # The original record was updated in-place (same id)
        f = db.query(EnedisFluxFile).first()
        assert f.id == stale_id
        assert f.status == FluxStatus.PARSED
        assert f.measures_count == 1
        # Header fields populated by the update-in-place path
        assert f.get_header_raw() is not None
        assert f.frequence_publication == "H"

        # Measures stored
        assert db.query(EnedisFluxMesureR4x).count() == 1


class TestCrossFluxQuery:
    """After ingesting all flux types, verify querying by PRM across tables."""

    def test_query_by_prm_across_tables(self, db, tmp_path, test_keys):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260301.zip", R171_XML)
        _write_encrypted(tmp_path, "ERDF_R50_23X--TEST_20260301.zip", R50_XML)
        _write_encrypted(tmp_path, "ERDF_R151_23X--TEST_20260301.zip", R151_XML)

        ingest_directory(tmp_path, db, test_keys)

        # Query R4x PRM
        r4x = db.query(EnedisFluxMesureR4x).filter_by(point_id="30000210411333").all()
        assert len(r4x) == 1

        # Query R171 PRM
        r171 = db.query(EnedisFluxMesureR171).filter_by(point_id="30000550506121").all()
        assert len(r171) == 1

        # Query R50/R151 shared PRM
        r50 = db.query(EnedisFluxMesureR50).filter_by(point_id="30001234567890").all()
        assert len(r50) == 1
        r151 = db.query(EnedisFluxMesureR151).filter_by(point_id="30001234567890").all()
        assert len(r151) == 1


class TestNonZipIgnored:
    """Non-.zip files in the directory are completely ignored."""

    def test_non_zip_files_ignored(self, db, tmp_path, test_keys):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        # Non-zip files — should be invisible
        (tmp_path / "readme.txt").write_text("ignore me")
        (tmp_path / "data.csv").write_text("a,b,c")
        (tmp_path / "ENEDIS_R4H.xml").write_text("<xml/>")

        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["received"] == 1
        assert counters["parsed"] == 1
        assert db.query(EnedisFluxFile).count() == 1


class TestSortOrder:
    """Files are processed in filename order (chronological for Enedis naming)."""

    def test_files_sorted_by_name(self, db, tmp_path, test_keys):
        # Write in reverse order — each with a unique inner filename to produce
        # distinct hashes (otherwise idempotency would skip duplicates).
        for day, inner in [("20260303", "c.xml"), ("20260301", "a.xml"), ("20260302", "b.xml")]:
            ct = make_encrypted_zip(R4H_XML, inner, TEST_KEY, TEST_IV)
            (tmp_path / f"ENEDIS_23X--TEST_R4H_CDC_{day}.zip").write_bytes(ct)

        ingest_directory(tmp_path, db, test_keys)

        files = db.query(EnedisFluxFile).order_by(EnedisFluxFile.id).all()
        filenames = [f.filename for f in files]
        assert filenames == [
            "ENEDIS_23X--TEST_R4H_CDC_20260301.zip",
            "ENEDIS_23X--TEST_R4H_CDC_20260302.zip",
            "ENEDIS_23X--TEST_R4H_CDC_20260303.zip",
        ]


# ===========================================================================
# Edge case tests
# ===========================================================================


class TestFileDisappears:
    """File deleted between Phase 1 (scan) and Phase 2 (process)."""

    def test_file_removed_after_scan_records_error(self, db, tmp_path, test_keys):
        """If a file is deleted between scan and processing, it should not abort the batch."""
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260302.zip", R171_XML)

        # Wrap ingest_file: delete the R4H file just before its first call
        call_count = 0
        original_ingest = ingest_file.__wrapped__ if hasattr(ingest_file, "__wrapped__") else ingest_file

        def delete_first_then_ingest(file_path, session, keys, chunk_size=1000, archive_dir=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Delete the file before ingest_file reads it
                file_path.unlink()
            return original_ingest(file_path, session, keys, chunk_size, archive_dir)

        with patch("data_ingestion.enedis.pipeline.ingest_file", side_effect=delete_first_then_ingest):
            counters = ingest_directory(tmp_path, db, test_keys)

        # First file → error (deleted), second file → parsed (still exists)
        assert counters["error"] == 1
        assert counters["parsed"] == 1
        assert counters["received"] == 2

        # The deleted file's RECEIVED record transitioned to ERROR
        error_files = db.query(EnedisFluxFile).filter_by(status=FluxStatus.ERROR).all()
        assert len(error_files) == 1
        assert "not found" in error_files[0].error_message.lower()

        # No file stuck in RECEIVED
        assert db.query(EnedisFluxFile).filter_by(status=FluxStatus.RECEIVED).count() == 0


class TestDbStorageErrorInBatch:
    """DB storage error on one file does not block the rest of the batch."""

    def test_storage_error_transitions_received_to_error(self, db, tmp_path, test_keys):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260302.zip", R171_XML)

        call_count = 0
        original_bulk_save = db.bulk_save_objects

        def fail_first_bulk_save(objects):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("simulated disk full")
            return original_bulk_save(objects)

        with patch.object(db, "bulk_save_objects", side_effect=fail_first_bulk_save):
            counters = ingest_directory(tmp_path, db, test_keys)

        # First file fails at storage, second succeeds
        assert counters["error"] == 1
        assert counters["parsed"] == 1

        # The failed file's record transitioned from RECEIVED → ERROR (not stuck)
        error_file = db.query(EnedisFluxFile).filter_by(status=FluxStatus.ERROR).first()
        assert error_file is not None
        assert "simulated disk full" in error_file.error_message

        # No file stuck in RECEIVED
        assert db.query(EnedisFluxFile).filter_by(status=FluxStatus.RECEIVED).count() == 0


class TestRecursiveDirectory:
    """Recursive scanning of subdirectories."""

    def test_recursive_finds_nested_files(self, db, tmp_path, test_keys):
        # Mimic real Enedis directory structure
        c1c4 = tmp_path / "C1-C4"
        c5 = tmp_path / "C5"
        c1c4.mkdir()
        c5.mkdir()

        _write_encrypted(c1c4, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(c1c4, "ENEDIS_23X--TEST_R171_20260301.zip", R171_XML)
        _write_encrypted(c5, "ERDF_R50_23X--TEST_20260301.zip", R50_XML)
        _write_encrypted(c5, "ERDF_R151_23X--TEST_20260301.zip", R151_XML)

        # Non-recursive: should find nothing (files are in subdirs)
        counters_flat = ingest_directory(tmp_path, db, test_keys)
        assert counters_flat["received"] == 0

        # Recursive: should find all 4
        counters_recursive = ingest_directory(tmp_path, db, test_keys, recursive=True)
        assert counters_recursive["received"] == 4
        assert counters_recursive["parsed"] == 4


class TestRepublicationInBatch:
    """Republication (same filename, different hash) within a single batch directory."""

    def test_republication_detected_in_batch(self, db, tmp_path, test_keys):
        """Two files with the same Enedis filename but different content in the same batch.

        This can't happen in a single flat directory (filenames must be unique),
        but can happen across two runs. Here we verify that a pre-existing PARSED
        file is detected as already_processed, and a new republication variant
        (different hash via different inner XML) is ingested with needs_review.
        """
        # First run: ingest v1
        ct1 = make_encrypted_zip(R4H_XML, "a.xml", TEST_KEY, TEST_IV)
        path1 = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_20260301.zip"
        path1.write_bytes(ct1)

        counters1 = ingest_directory(tmp_path, db, test_keys)
        assert counters1["parsed"] == 1

        # Second run: same filename, different content (republication)
        ct2 = make_encrypted_zip(R4H_XML, "b.xml", TEST_KEY, TEST_IV)
        path1.write_bytes(ct2)

        counters2 = ingest_directory(tmp_path, db, test_keys)
        assert counters2["received"] == 1
        assert counters2["needs_review"] == 1
        assert counters2["already_processed"] == 0  # old hash no longer on disk

        # Both versions in DB
        files = db.query(EnedisFluxFile).order_by(EnedisFluxFile.version).all()
        assert len(files) == 2
        assert files[0].version == 1
        assert files[0].status == FluxStatus.PARSED
        assert files[1].version == 2
        assert files[1].status == FluxStatus.NEEDS_REVIEW


# ===========================================================================
# SF4 Phase 3 — Error retry in batch
# ===========================================================================


class TestErrorRetryInBatch:
    """ERROR files are retried in ingest_directory(), with error history preserved."""

    def test_error_file_retried_and_history_preserved(self, db, tmp_path, test_keys):
        """An ERROR file is retried in a subsequent ingest_directory() run.
        Error history is preserved via EnedisFluxFileError."""
        path = _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        # Pre-seed an ERROR record for this file (simulating a prior failed run)
        error_record = EnedisFluxFile(
            filename=path.name,
            file_hash=file_hash,
            flux_type="R4H",
            status=FluxStatus.ERROR,
            error_message="previous decrypt error",
        )
        db.add(error_record)
        db.commit()
        original_id = error_record.id

        # Run ingest_directory — should retry the ERROR file
        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["retried"] == 1
        assert counters["parsed"] == 1
        assert counters["already_processed"] == 0

        # Record updated in-place
        f = db.query(EnedisFluxFile).filter_by(file_hash=file_hash).first()
        assert f.id == original_id
        assert f.status == FluxStatus.PARSED
        # Error history preserved
        assert len(f.errors) == 1
        assert f.errors[0].error_message == "previous decrypt error"

    def test_max_retries_reached_transitions_to_permanently_failed(self, db, tmp_path, test_keys):
        """File at MAX_RETRIES errors → PERMANENTLY_FAILED, counted in max_retries_reached."""
        path = _write_corrupt(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_MAXR.zip")
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        # Pre-seed ERROR record with MAX_RETRIES error entries
        error_record = EnedisFluxFile(
            filename=path.name,
            file_hash=file_hash,
            flux_type="R4H",
            status=FluxStatus.ERROR,
            error_message="latest error",
        )
        db.add(error_record)
        db.flush()
        for i in range(MAX_RETRIES):
            db.add(EnedisFluxFileError(
                flux_file_id=error_record.id,
                error_message=f"error attempt {i+1}",
            ))
        db.commit()

        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["max_retries_reached"] == 1
        assert counters["retried"] == 0

        f = db.query(EnedisFluxFile).filter_by(file_hash=file_hash).first()
        assert f.status == FluxStatus.PERMANENTLY_FAILED

    def test_permanently_failed_skipped_in_next_run(self, db, tmp_path, test_keys):
        """A PERMANENTLY_FAILED file is skipped (not retried) in subsequent runs."""
        path = _write_corrupt(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_PF.zip")
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        # Pre-seed as PERMANENTLY_FAILED
        pf = EnedisFluxFile(
            filename=path.name,
            file_hash=file_hash,
            flux_type="R4H",
            status=FluxStatus.PERMANENTLY_FAILED,
            error_message="gave up",
        )
        db.add(pf)
        db.commit()

        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["max_retries_reached"] == 1
        assert counters["retried"] == 0
        assert counters["received"] == 0

        # Status unchanged
        f = db.query(EnedisFluxFile).first()
        assert f.status == FluxStatus.PERMANENTLY_FAILED


class TestPermanentlyFailedInPhase2:
    """ingest_file() returning PERMANENTLY_FAILED in Phase 2 must not crash counters."""

    def test_permanently_failed_from_ingest_file_no_keyerror(self, db, tmp_path, test_keys):
        """If ingest_file() returns PERMANENTLY_FAILED during Phase 2,
        counters['permanently_failed'] is incremented without KeyError."""
        path = _write_corrupt(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_PF2.zip")
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        # Pre-seed ERROR record eligible for retry (errors < MAX_RETRIES)
        error_record = EnedisFluxFile(
            filename=path.name,
            file_hash=file_hash,
            flux_type="R4H",
            status=FluxStatus.ERROR,
            error_message="some error",
        )
        db.add(error_record)
        db.flush()
        db.add(EnedisFluxFileError(
            flux_file_id=error_record.id,
            error_message="past error",
        ))
        db.commit()

        # Mock ingest_file to return PERMANENTLY_FAILED (simulates concurrency)
        with patch(
            "data_ingestion.enedis.pipeline.ingest_file",
            return_value=FluxStatus.PERMANENTLY_FAILED,
        ):
            counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["permanently_failed"] == 1
        assert counters["retried"] == 1


class TestNeedsReviewNoRetry:
    """NEEDS_REVIEW files are not retried — counted as already_processed."""

    def test_needs_review_not_retried(self, db, tmp_path, test_keys):
        path = _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_NR.zip", R4H_XML)
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        # Pre-seed as NEEDS_REVIEW
        nr = EnedisFluxFile(
            filename=path.name,
            file_hash=file_hash,
            flux_type="R4H",
            status=FluxStatus.NEEDS_REVIEW,
            measures_count=1,
        )
        db.add(nr)
        db.commit()

        counters = ingest_directory(tmp_path, db, test_keys)

        assert counters["already_processed"] == 1
        assert counters["received"] == 0
        assert counters["retried"] == 0

        # Status unchanged
        f = db.query(EnedisFluxFile).first()
        assert f.status == FluxStatus.NEEDS_REVIEW


# ===========================================================================
# SF4 Phase 3 — Incremental counters (IngestionRun)
# ===========================================================================


class TestIncrementalCounters:
    """IngestionRun counters are updated incrementally during ingest_directory()."""

    def _make_run(self, db, tmp_path, *, dry_run=False):
        """Create an IngestionRun for testing."""
        run = IngestionRun(
            triggered_by="cli",
            directory=str(tmp_path),
            recursive=False,
            dry_run=dry_run,
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        return run

    def test_run_counters_updated_after_each_file(self, db, tmp_path, test_keys):
        """Counters on the IngestionRun reflect per-file updates, not batch."""
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260301.zip", R171_XML)
        # R172 → skipped
        (tmp_path / "ENEDIS_23X--TEST_R172_20260301.zip").write_bytes(os.urandom(64))

        run = self._make_run(db, tmp_path)

        counters = ingest_directory(tmp_path, db, test_keys, run=run)

        db.refresh(run)
        assert run.status == IngestionRunStatus.COMPLETED
        assert run.finished_at is not None
        assert run.files_received == 3
        assert run.files_parsed == 2
        assert run.files_skipped == 1
        assert run.files_error == 0
        assert run.files_needs_review == 0

    def test_run_counters_reflect_partial_work_on_crash(self, db, tmp_path, test_keys):
        """If processing crashes mid-run, counters reflect the work completed so far."""
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260302.zip", R171_XML)

        run = self._make_run(db, tmp_path)

        call_count = 0
        original_ingest = ingest_file.__wrapped__ if hasattr(ingest_file, "__wrapped__") else ingest_file

        def crash_on_second(file_path, session, keys, chunk_size=1000, archive_dir=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("simulated crash")
            return original_ingest(file_path, session, keys, chunk_size, archive_dir)

        with patch("data_ingestion.enedis.pipeline.ingest_file", side_effect=crash_on_second):
            counters = ingest_directory(tmp_path, db, test_keys, run=run)

        db.refresh(run)
        # First file parsed successfully, second crashed → error
        assert run.files_parsed == 1
        assert run.files_error == 1
        assert run.files_received == 2
        # Run completed (crash was caught by ingest_directory's except block)
        assert run.status == IngestionRunStatus.COMPLETED

    def test_run_scan_counters_include_retried_and_max_retries(self, db, tmp_path, test_keys):
        """Scan phase counters include retried and max_retries_reached."""
        # Valid file
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)

        # ERROR file eligible for retry (0 previous errors)
        retry_path = _write_corrupt(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_RETRY.zip")
        retry_hash = hashlib.sha256(retry_path.read_bytes()).hexdigest()
        retry_record = EnedisFluxFile(
            filename=retry_path.name,
            file_hash=retry_hash,
            flux_type="R4H",
            status=FluxStatus.ERROR,
            error_message="previous error",
        )
        db.add(retry_record)
        db.commit()

        run = self._make_run(db, tmp_path)
        counters = ingest_directory(tmp_path, db, test_keys, run=run)

        db.refresh(run)
        assert run.files_retried == 1
        assert run.files_received == 2  # new + retried

    def test_dry_run_with_run_sets_completed(self, db, tmp_path, test_keys):
        """Even in dry-run mode, the IngestionRun is marked completed."""
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)

        run = self._make_run(db, tmp_path, dry_run=True)

        counters = ingest_directory(tmp_path, db, test_keys, dry_run=True, run=run)

        db.refresh(run)
        assert run.status == IngestionRunStatus.COMPLETED
        assert run.finished_at is not None
        assert run.files_received == 1
        # Phase 2 skipped → processing counters stay 0
        assert run.files_parsed == 0
