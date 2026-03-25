"""Tests for ingest_directory() — SF3-B full pipeline batch ingestion."""

import hashlib
import os
from pathlib import Path

import pytest

from data_ingestion.enedis.enums import FluxStatus
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
)
from data_ingestion.enedis.pipeline import ingest_directory

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
            "skipped": 0, "error": 0, "already_processed": 0,
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

    def test_files_registered_as_received_then_transition(self, db, tmp_path, test_keys):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip", R4H_XML)
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R171_20260301.zip", R171_XML)

        counters = ingest_directory(tmp_path, db, test_keys)

        # After full processing, no file should remain in RECEIVED
        received_files = db.query(EnedisFluxFile).filter_by(status=FluxStatus.RECEIVED).count()
        assert received_files == 0

        # All transitioned to final statuses
        parsed_files = db.query(EnedisFluxFile).filter_by(status=FluxStatus.PARSED).count()
        assert parsed_files == 2
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
