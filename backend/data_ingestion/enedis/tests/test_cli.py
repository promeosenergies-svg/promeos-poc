"""Tests for the Enedis SGE CLI (SF4 Phase 4).

Tests cmd_ingest() directly (no subprocess) with an in-memory SQLite DB,
mocking SessionLocal/engine to route all DB operations through the test session.
"""

import argparse
import io
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data_ingestion.enedis.enums import FluxStatus, IngestionRunStatus
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxItcC68,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR6x,
    IngestionRun,
)
from data_ingestion.enedis.cli import cmd_ingest, _print_report, _dry_run_report

from .conftest import TEST_IV, TEST_KEY, make_encrypted_zip


# ---------------------------------------------------------------------------
# Shared XML (minimal valid R4H for end-to-end tests)
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

# Second R4H with different data (different hash)
R4H_XML_2 = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<Courbe>
  <Entete>
    <Identifiant_Flux>R4x</Identifiant_Flux>
    <Frequence_Publication>H</Frequence_Publication>
  </Entete>
  <Corps>
    <Identifiant_PRM>30000210411333</Identifiant_PRM>
    <Donnees_Courbe>
      <Horodatage_Debut>2026-03-08T00:00:00+01:00</Horodatage_Debut>
      <Horodatage_Fin>2026-03-08T23:59:59+01:00</Horodatage_Fin>
      <Granularite>5</Granularite>
      <Unite_Mesure>kW</Unite_Mesure>
      <Grandeur_Metier>CONS</Grandeur_Metier>
      <Grandeur_Physique>EA</Grandeur_Physique>
      <Donnees_Point_Mesure Horodatage="2026-03-08T00:00:00+01:00" Valeur_Point="412" Statut_Point="R"/>
    </Donnees_Courbe>
  </Corps>
</Courbe>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_encrypted(directory: Path, filename: str, xml: bytes = R4H_XML) -> Path:
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


def _write_r63_direct(directory: Path) -> Path:
    payload = json.dumps(
        {
            "header": {
                "siDemandeur": "SGE",
                "typeDestinataire": "SI",
                "idDestinataire": "GRD-F001",
                "codeFlux": "R63",
                "idDemande": "M053Q0D3",
                "modePublication": "P",
                "idCanalContact": "WEB",
                "format": "JSON",
            },
            "mesures": [
                {
                    "idPrm": "30000000000001",
                    "etapeMetier": "MESURE",
                    "periode": {"dateDebut": "2026-01-01", "dateFin": "2026-01-02"},
                    "modeCalcul": "BRUT",
                    "grandeur": [
                        {
                            "grandeurMetier": "CONS",
                            "grandeurPhysique": "EA",
                            "unite": "Wh",
                            "points": [{"d": "2026-01-01T00:00:00+01:00", "v": "10", "p": "PT5M", "n": "R"}],
                        }
                    ],
                }
            ],
        }
    ).encode()
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member, payload)
    path = directory / outer
    path.write_bytes(buf.getvalue())
    return path


def _make_args(
    dir_path: str | None = None, dry_run: bool = False, recursive: bool = True, verbose: bool = False
) -> argparse.Namespace:
    """Build an argparse.Namespace matching the CLI parser output."""
    return argparse.Namespace(
        command="ingest",
        dir=dir_path,
        dry_run=dry_run,
        recursive=recursive,
        verbose=verbose,
    )


def _patch_cli_deps(db_session, tmp_path):
    """Return a dict of patches that redirect CLI DB operations to the test session.

    Patches:
    - cli.SessionLocal -> returns the test db session
    - cli.engine -> a mock (used only by _ensure_tables which we also patch)
    - cli._ensure_tables -> no-op (tables already created by conftest db fixture)
    - cli.get_flux_dir -> returns tmp_path (or can be overridden)
    - cli.load_keys_from_env -> returns the test keys
    """
    return {
        "data_ingestion.enedis.cli.SessionLocal": MagicMock(return_value=db_session),
        "data_ingestion.enedis.cli.engine": MagicMock(),
        "data_ingestion.enedis.cli._ensure_tables": MagicMock(),
        "data_ingestion.enedis.cli.load_keys_from_env": MagicMock(return_value=[(TEST_KEY, TEST_IV)]),
        "data_ingestion.enedis.cli.get_flux_dir": MagicMock(return_value=tmp_path),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCliIngest:
    """Normal mode with synthetic files — counters correct, IngestionRun created."""

    def test_normal_ingest_creates_run_and_processes_files(self, db, tmp_path):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip")
        args = _make_args()

        patches = _patch_cli_deps(db, tmp_path)
        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 0

        # Verify critical mocks were actually invoked (guard against import path drift)
        patches["data_ingestion.enedis.cli.get_flux_dir"].assert_called_once()
        patches["data_ingestion.enedis.cli.load_keys_from_env"].assert_called_once()

        # IngestionRun created with status=completed
        run = db.query(IngestionRun).first()
        assert run is not None
        assert run.status == IngestionRunStatus.COMPLETED
        assert run.triggered_by == "cli"
        assert run.dry_run is False
        assert run.finished_at is not None

        # File processed
        files = db.query(EnedisFluxFile).all()
        assert len(files) == 1
        assert files[0].status == FluxStatus.PARSED

        # Measures stored
        assert db.query(EnedisFluxMesureR4x).count() == 1

        # Run counters reflect processing
        assert run.files_received == 1
        assert run.files_parsed == 1

    def test_multiple_files(self, db, tmp_path):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip")
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260302.zip", R4H_XML_2)
        # R172 should be skipped
        (tmp_path / "ENEDIS_23X--TEST_R172_20260301.zip").write_bytes(os.urandom(64))

        args = _make_args()
        patches = _patch_cli_deps(db, tmp_path)
        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 0

        run = db.query(IngestionRun).first()
        assert run.files_received == 3
        assert run.files_parsed == 2
        assert run.files_skipped == 1


class TestCliNonRecursive:
    """--no-recursive flag propagates to pipeline and IngestionRun."""

    def test_non_recursive_skips_subdirectories(self, db, tmp_path):
        # File in subdirectory — should NOT be found with recursive=False
        subdir = tmp_path / "C1-C4"
        subdir.mkdir()
        _write_encrypted(subdir, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip")

        args = _make_args(recursive=False)
        patches = _patch_cli_deps(db, tmp_path)
        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 0

        run = db.query(IngestionRun).first()
        assert run is not None
        assert run.recursive is False
        # No files found (all in subdirectory)
        assert run.files_received == 0
        assert db.query(EnedisFluxFile).count() == 0


class TestCliDryRun:
    """Dry-run mode: no data modifications, IngestionRun with dry_run=True."""

    def test_dry_run_no_data_mutations(self, db, tmp_path):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip")
        args = _make_args(dry_run=True)

        patches = _patch_cli_deps(db, tmp_path)
        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 0

        # IngestionRun created with dry_run=True
        run = db.query(IngestionRun).first()
        assert run is not None
        assert run.dry_run is True
        assert run.status == IngestionRunStatus.COMPLETED

        # No flux files created (dry-run skips DB mutations)
        assert db.query(EnedisFluxFile).count() == 0

        # No measures stored
        assert db.query(EnedisFluxMesureR4x).count() == 0

        # Scan counters still populated on the run
        assert run.files_received == 1


class TestCliVerbose:
    """Verbose flag enables DEBUG logging."""

    def test_verbose_sets_debug_level(self, db, tmp_path):
        args = _make_args(verbose=True)

        _zero_counters = {
            "received": 0,
            "parsed": 0,
            "skipped": 0,
            "error": 0,
            "needs_review": 0,
            "already_processed": 0,
            "retried": 0,
            "max_retries_reached": 0,
            "permanently_failed": 0,
        }

        def mock_ingest(directory, session, keys, **kwargs):
            run = kwargs.get("run")
            if run:
                run.status = IngestionRunStatus.COMPLETED
                run.finished_at = datetime.now(timezone.utc)
                session.commit()
            return _zero_counters

        patches = _patch_cli_deps(db, tmp_path)
        patches["data_ingestion.enedis.cli.ingest_directory"] = MagicMock(side_effect=mock_ingest)
        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 0
        # The enedis logger hierarchy should be set to DEBUG
        enedis_logger = logging.getLogger("promeos.enedis")
        assert enedis_logger.level == logging.DEBUG


class TestCliMissingDir:
    """ENEDIS_FLUX_DIR absent + no --dir -> error, no IngestionRun created."""

    def test_missing_dir_exits_with_error(self, db, tmp_path):
        args = _make_args()

        patches = _patch_cli_deps(db, tmp_path)
        # Override get_flux_dir to raise ValueError
        patches["data_ingestion.enedis.cli.get_flux_dir"] = MagicMock(
            side_effect=ValueError("ENEDIS_FLUX_DIR environment variable is required — set it in .env")
        )

        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 1

        # No IngestionRun created (pre-flight failure)
        assert db.query(IngestionRun).count() == 0


class TestCliMissingKeys:
    """Keys absent -> direct-openable files still run; encrypted files become per-file errors."""

    def test_missing_keys_still_processes_direct_sf5(self, db, tmp_path):
        _write_r63_direct(tmp_path)
        args = _make_args()

        from data_ingestion.enedis.decrypt import MissingKeyError

        patches = _patch_cli_deps(db, tmp_path)
        # Override load_keys_from_env to raise MissingKeyError
        patches["data_ingestion.enedis.cli.load_keys_from_env"] = MagicMock(
            side_effect=MissingKeyError("No decryption keys found in environment variables (KEY_1/IV_1 not set)")
        )

        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 0
        assert db.query(IngestionRun).one().status == IngestionRunStatus.COMPLETED
        assert db.query(EnedisFluxFile).one().status == FluxStatus.PARSED
        assert db.query(EnedisFluxMesureR6x).count() == 1

    def test_missing_keys_records_error_for_encrypted_file(self, db, tmp_path):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip")
        args = _make_args()

        from data_ingestion.enedis.decrypt import MissingKeyError

        patches = _patch_cli_deps(db, tmp_path)
        patches["data_ingestion.enedis.cli.load_keys_from_env"] = MagicMock(side_effect=MissingKeyError("no keys"))

        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 0
        file_row = db.query(EnedisFluxFile).one()
        assert file_row.status == FluxStatus.ERROR
        assert db.query(IngestionRun).one().files_error == 1


def test_print_report_includes_r6x_and_c68_totals(db, capsys):
    run = IngestionRun(
        started_at=datetime.now(timezone.utc),
        directory="/tmp/flux",
        recursive=True,
        dry_run=False,
        status=IngestionRunStatus.COMPLETED,
        triggered_by="cli",
    )
    db.add(run)
    file_r6x = EnedisFluxFile(filename="r63.zip", file_hash="r63", flux_type="R63", status=FluxStatus.PARSED)
    file_c68 = EnedisFluxFile(filename="c68.zip", file_hash="c68", flux_type="C68", status=FluxStatus.PARSED)
    db.add_all([file_r6x, file_c68])
    db.flush()
    db.add(
        EnedisFluxMesureR6x(
            flux_file_id=file_r6x.id,
            flux_type="R63",
            source_format="JSON",
            archive_member_name="payload.json",
            point_id="30000000000001",
            horodatage="2026-01-01T00:00:00+01:00",
        )
    )
    db.add(
        EnedisFluxItcC68(
            flux_file_id=file_c68.id,
            source_format="JSON",
            payload_member_name="payload.json",
            point_id="30000000000002",
            payload_raw='{"idPrm":"30000000000002"}',
        )
    )
    db.commit()

    _print_report(
        {
            "received": 2,
            "parsed": 2,
            "skipped": 0,
            "error": 0,
            "needs_review": 0,
            "retried": 0,
            "max_retries_reached": 0,
            "permanently_failed": 0,
            "already_processed": 0,
        },
        db,
        run,
        0.1,
        Path("/tmp/flux"),
        True,
    )

    output = capsys.readouterr().out
    assert "R6X:" in output
    assert "C68:" in output


class TestCliConcurrentRun:
    """IngestionRun in status "running" exists -> error, no new run created."""

    def test_concurrent_run_rejected(self, db, tmp_path):
        # Pre-seed a running IngestionRun
        existing_run = IngestionRun(
            started_at=datetime.now(timezone.utc),
            directory="/some/dir",
            recursive=True,
            dry_run=False,
            status=IngestionRunStatus.RUNNING,
            triggered_by="api",
        )
        db.add(existing_run)
        db.commit()

        args = _make_args()
        patches = _patch_cli_deps(db, tmp_path)

        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 1

        # Only the pre-existing run — no new run created
        runs = db.query(IngestionRun).all()
        assert len(runs) == 1
        assert runs[0].id == existing_run.id


class TestCliCrashRun:
    """Pipeline crash mid-ingestion -> run.status='failed', counters correct."""

    def test_crash_sets_run_failed_with_error_message(self, db, tmp_path):
        _write_encrypted(tmp_path, "ENEDIS_23X--TEST_R4H_CDC_20260301.zip")
        args = _make_args()

        patches = _patch_cli_deps(db, tmp_path)

        def crashing_ingest(directory, session, keys, **kwargs):
            # Create a partial run state before crashing
            run = kwargs.get("run")
            if run:
                run.files_received = 1
                session.commit()
            raise RuntimeError("simulated pipeline crash")

        patches["data_ingestion.enedis.cli.ingest_directory"] = MagicMock(side_effect=crashing_ingest)

        with patch.multiple("data_ingestion.enedis.cli", **{k.split(".")[-1]: v for k, v in patches.items()}):
            exit_code = cmd_ingest(args)

        assert exit_code == 1

        # IngestionRun exists with status=failed
        run = db.query(IngestionRun).first()
        assert run is not None
        assert run.status == IngestionRunStatus.FAILED
        assert run.finished_at is not None
        assert "simulated pipeline crash" in run.error_message

        # Incremental counters were committed before the crash
        assert run.files_received == 1
