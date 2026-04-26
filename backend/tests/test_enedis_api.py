"""
PROMEOS — Tests for Enedis SGE Flux API endpoints (SF4 Phase 5).

Follows the test_bacs_api.py pattern: in-memory SQLite with TestClient,
dependency override for get_db, mock pipeline functions at the import site.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from data_ingestion.enedis.base import FluxDataBase
import data_ingestion.enedis.models  # noqa: F401 — register Enedis tables
from database import get_db, get_flux_data_db
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxFileError,
    EnedisFluxItcC68,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
    EnedisFluxMesureR50,
    EnedisFluxMesureR6x,
    IngestionRun,
)
from data_ingestion.enedis.enums import FluxStatus, IngestionRunStatus


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """TestClient + session tuple with isolated in-memory DB."""
    raw_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    FluxDataBase.metadata.create_all(bind=raw_engine)
    Session = sessionmaker(bind=raw_engine)
    session = Session()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_flux_data_db] = _override
    app.dependency_overrides[get_db] = _override
    yield TestClient(app), session
    app.dependency_overrides.clear()
    session.close()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_flux_file(
    session,
    filename="ENEDIS_R4H_TEST.zip",
    flux_type="R4H",
    status=FluxStatus.PARSED,
    measures_count=10,
    file_hash=None,
    header_raw=None,
    error_message=None,
):
    """Seed an EnedisFluxFile and return it."""
    if file_hash is None:
        file_hash = f"hash_{filename}_{id(session)}"
    f = EnedisFluxFile(
        filename=filename,
        file_hash=file_hash,
        flux_type=flux_type,
        status=status,
        measures_count=measures_count,
        version=1,
        error_message=error_message,
    )
    if header_raw is not None:
        f.header_raw = json.dumps(header_raw, ensure_ascii=False)
    session.add(f)
    session.flush()
    return f


def _seed_run(
    session,
    status=IngestionRunStatus.COMPLETED,
    triggered_by="cli",
    dry_run=False,
    files_parsed=0,
    files_error=0,
    files_skipped=0,
    files_needs_review=0,
):
    """Seed an IngestionRun and return it."""
    run = IngestionRun(
        started_at=datetime(2026, 3, 1, 10, 0, 0),
        finished_at=datetime(2026, 3, 1, 10, 0, 5) if status != IngestionRunStatus.RUNNING else None,
        directory="/tmp/flux",
        recursive=True,
        dry_run=dry_run,
        status=status,
        triggered_by=triggered_by,
        files_parsed=files_parsed,
        files_error=files_error,
        files_skipped=files_skipped,
        files_needs_review=files_needs_review,
    )
    session.add(run)
    session.flush()
    return run


def _seed_measure_r4x(session, flux_file, point_id="30001234567890"):
    """Seed a single R4x measure row."""
    m = EnedisFluxMesureR4x(
        flux_file_id=flux_file.id,
        flux_type="R4H",
        point_id=point_id,
        horodatage="2026-03-07T00:00:00+01:00",
        valeur_point="398",
    )
    session.add(m)
    session.flush()
    return m


def _seed_measure_r171(session, flux_file, point_id="30009876543210"):
    """Seed a single R171 measure row."""
    m = EnedisFluxMesureR171(
        flux_file_id=flux_file.id,
        flux_type="R171",
        point_id=point_id,
        type_mesure="INDEX",
        date_fin="2026-03-01",
    )
    session.add(m)
    session.flush()
    return m


def _seed_measure_r50(session, flux_file, point_id="30001111111111"):
    """Seed a single R50 measure row."""
    m = EnedisFluxMesureR50(
        flux_file_id=flux_file.id,
        flux_type="R50",
        point_id=point_id,
        date_releve="2026-03-01",
        horodatage="2026-03-01T00:00:00+01:00",
    )
    session.add(m)
    session.flush()
    return m


def _seed_measure_r151(session, flux_file, point_id="30002222222222"):
    """Seed a single R151 measure row."""
    m = EnedisFluxMesureR151(
        flux_file_id=flux_file.id,
        flux_type="R151",
        point_id=point_id,
        date_releve="2026-03-01",
        type_donnee="CT_DIST",
    )
    session.add(m)
    session.flush()
    return m


def _seed_measure_r6x(session, flux_file, point_id="30003333333333"):
    m = EnedisFluxMesureR6x(
        flux_file_id=flux_file.id,
        flux_type=flux_file.flux_type,
        source_format="JSON",
        archive_member_name="payload.json",
        point_id=point_id,
        horodatage="2026-03-01T00:00:00+01:00",
    )
    session.add(m)
    session.flush()
    return m


def _seed_itc_c68(session, flux_file, point_id="30004444444444"):
    m = EnedisFluxItcC68(
        flux_file_id=flux_file.id,
        source_format="JSON",
        payload_member_name="payload.json",
        point_id=point_id,
        payload_raw=json.dumps({"idPrm": point_id}),
    )
    session.add(m)
    session.flush()
    return m


def _seed_error_history(session, flux_file, error_message="decrypt failed"):
    """Seed an EnedisFluxFileError entry."""
    e = EnedisFluxFileError(
        flux_file_id=flux_file.id,
        error_message=error_message,
    )
    session.add(e)
    session.flush()
    return e


# ---------------------------------------------------------------------------
# Mock constants
# ---------------------------------------------------------------------------

_FAKE_COUNTERS = {
    "received": 2,
    "parsed": 1,
    "needs_review": 0,
    "skipped": 1,
    "error": 0,
    "permanently_failed": 0,
    "already_processed": 0,
    "retried": 0,
    "max_retries_reached": 0,
}


def _mock_ingest_directory_success(directory, session, keys, *, recursive=True, dry_run=False, run=None, **kwargs):
    """Mock ingest_directory that updates run and returns fake counters."""
    if run:
        run.files_received = _FAKE_COUNTERS["received"]
        run.files_parsed = _FAKE_COUNTERS["parsed"]
        run.files_skipped = _FAKE_COUNTERS["skipped"]
        run.status = IngestionRunStatus.COMPLETED
        run.finished_at = datetime.now(timezone.utc)
        session.commit()
    return dict(_FAKE_COUNTERS)


# ---------------------------------------------------------------------------
# Tests — POST /api/enedis/ingest
# ---------------------------------------------------------------------------


class TestIngestEndpoint:
    """POST /api/enedis/ingest — trigger ingestion."""

    def test_ingest_success(self, client, tmp_path):
        c, session = client

        with (
            patch("routes.enedis.get_flux_dir", return_value=tmp_path),
            patch("routes.enedis.load_keys_from_env", return_value=[(b"\x00" * 16, b"\x00" * 16)]),
            patch("routes.enedis.ingest_directory", side_effect=_mock_ingest_directory_success),
        ):
            r = c.post("/api/enedis/ingest", json={"recursive": True})

        assert r.status_code == 200
        data = r.json()
        assert data["run_id"] >= 1
        assert data["status"] == IngestionRunStatus.COMPLETED
        assert data["dry_run"] is False
        assert data["counters"]["received"] == 2
        assert data["counters"]["parsed"] == 1
        assert isinstance(data["duration_seconds"], float)

    def test_ingest_dry_run(self, client, tmp_path):
        c, session = client

        with (
            patch("routes.enedis.get_flux_dir", return_value=tmp_path),
            patch("routes.enedis.load_keys_from_env", return_value=[(b"\x00" * 16, b"\x00" * 16)]),
            patch("routes.enedis.ingest_directory", side_effect=_mock_ingest_directory_success),
        ):
            r = c.post("/api/enedis/ingest", json={"dry_run": True})

        assert r.status_code == 200
        data = r.json()
        assert data["dry_run"] is True

        # IngestionRun in DB has dry_run=True
        run = session.query(IngestionRun).filter_by(id=data["run_id"]).first()
        assert run.dry_run is True

    def test_ingest_with_errors_in_response(self, client, tmp_path):
        c, session = client

        def _mock_with_error(directory, session, keys, *, recursive=True, dry_run=False, run=None, **kwargs):
            """Mock that creates an error file during pipeline run."""
            # Simulate an error file created during this run
            err_file = EnedisFluxFile(
                filename="CORRUPT.zip",
                file_hash="hash_corrupt_001",
                flux_type="R4H",
                status=FluxStatus.ERROR,
                error_message="none of the 3 keys could decrypt",
                measures_count=0,
                version=1,
            )
            session.add(err_file)
            session.flush()

            if run:
                run.files_received = 1
                run.files_error = 1
                run.status = IngestionRunStatus.COMPLETED
                run.finished_at = datetime.now(timezone.utc)
                session.commit()
            return {
                "received": 1,
                "parsed": 0,
                "needs_review": 0,
                "skipped": 0,
                "error": 1,
                "permanently_failed": 0,
                "already_processed": 0,
                "retried": 0,
                "max_retries_reached": 0,
            }

        with (
            patch("routes.enedis.get_flux_dir", return_value=tmp_path),
            patch("routes.enedis.load_keys_from_env", return_value=[(b"\x00" * 16, b"\x00" * 16)]),
            patch("routes.enedis.ingest_directory", side_effect=_mock_with_error),
        ):
            r = c.post("/api/enedis/ingest", json={})

        assert r.status_code == 200
        data = r.json()
        assert data["counters"]["error"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["filename"] == "CORRUPT.zip"
        assert "decrypt" in data["errors"][0]["error_message"]


class TestIngestPreFlight:
    """POST /api/enedis/ingest — pre-flight validation errors."""

    def test_bad_directory_422(self, client):
        c, _ = client
        with patch("routes.enedis.get_flux_dir", side_effect=ValueError("not a directory")):
            r = c.post("/api/enedis/ingest", json={})
        assert r.status_code == 422
        assert "not a directory" in r.json()["message"]

    def test_missing_keys_422(self, client, tmp_path):
        c, _ = client
        from data_ingestion.enedis.decrypt import MissingKeyError

        with (
            patch("routes.enedis.get_flux_dir", return_value=tmp_path),
            patch("routes.enedis.load_keys_from_env", side_effect=MissingKeyError("no keys")),
            patch("routes.enedis.ingest_directory", side_effect=_mock_ingest_directory_success) as ingest_mock,
        ):
            r = c.post("/api/enedis/ingest", json={})
        assert r.status_code == 200
        ingest_mock.assert_called_once()
        assert ingest_mock.call_args.args[2] == []

    def test_concurrent_run_409(self, client, tmp_path):
        c, session = client
        # Seed a running IngestionRun
        _seed_run(session, status=IngestionRunStatus.RUNNING)

        with (
            patch("routes.enedis.get_flux_dir", return_value=tmp_path),
            patch("routes.enedis.load_keys_from_env", return_value=[(b"\x00" * 16, b"\x00" * 16)]),
        ):
            r = c.post("/api/enedis/ingest", json={})
        assert r.status_code == 409
        assert "already in progress" in r.json()["message"]


class TestIngestCrash:
    """POST /api/enedis/ingest — pipeline crash sets run to failed."""

    def test_pipeline_error_500(self, client, tmp_path):
        c, session = client

        with (
            patch("routes.enedis.get_flux_dir", return_value=tmp_path),
            patch("routes.enedis.load_keys_from_env", return_value=[(b"\x00" * 16, b"\x00" * 16)]),
            patch("routes.enedis.ingest_directory", side_effect=RuntimeError("boom")),
        ):
            r = c.post("/api/enedis/ingest", json={})

        assert r.status_code == 500
        assert "boom" in r.json()["message"]

        # Run marked as failed in DB
        run = session.query(IngestionRun).first()
        assert run is not None
        assert run.status == IngestionRunStatus.FAILED
        assert run.error_message == "boom"
        assert run.finished_at is not None


# ---------------------------------------------------------------------------
# Tests — GET /api/enedis/flux-files
# ---------------------------------------------------------------------------


class TestFluxFilesEndpoint:
    """GET /api/enedis/flux-files — paginated list with filters."""

    def test_list_empty(self, client):
        c, _ = client
        r = c.get("/api/enedis/flux-files")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["limit"] == 24
        assert data["offset"] == 0

    def test_list_with_data(self, client):
        c, session = client
        _seed_flux_file(session, "file1.zip", file_hash="h1")
        _seed_flux_file(session, "file2.zip", file_hash="h2")
        _seed_flux_file(session, "file3.zip", file_hash="h3")

        r = c.get("/api/enedis/flux-files")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_filter_by_status(self, client):
        c, session = client
        _seed_flux_file(session, "ok1.zip", file_hash="h1", status=FluxStatus.PARSED)
        _seed_flux_file(session, "ok2.zip", file_hash="h2", status=FluxStatus.PARSED)
        _seed_flux_file(
            session, "err.zip", file_hash="h3", status=FluxStatus.ERROR, measures_count=0, error_message="fail"
        )

        r = c.get("/api/enedis/flux-files?status=parsed")
        data = r.json()
        assert data["total"] == 2
        assert all(item["status"] == "parsed" for item in data["items"])

    def test_filter_by_flux_type(self, client):
        c, session = client
        _seed_flux_file(session, "r4h.zip", flux_type="R4H", file_hash="h1")
        _seed_flux_file(session, "r171.zip", flux_type="R171", file_hash="h2")

        r = c.get("/api/enedis/flux-files?flux_type=R4H")
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["flux_type"] == "R4H"

    def test_pagination(self, client):
        c, session = client
        for i in range(5):
            _seed_flux_file(session, f"file{i}.zip", file_hash=f"h{i}")

        r = c.get("/api/enedis/flux-files?limit=2&offset=2")
        data = r.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 2

    def test_items_contain_file_hash(self, client):
        c, session = client
        _seed_flux_file(session, "test.zip", file_hash="abc123def")

        r = c.get("/api/enedis/flux-files")
        data = r.json()
        assert data["items"][0]["file_hash"] == "abc123def"

    def test_measures_count_null_becomes_zero(self, client):
        c, session = client
        f = EnedisFluxFile(
            filename="null_mc.zip",
            file_hash="h_null",
            flux_type="R4H",
            status=FluxStatus.RECEIVED,
            measures_count=None,
            version=1,
        )
        session.add(f)
        session.flush()

        r = c.get("/api/enedis/flux-files")
        data = r.json()
        assert data["items"][0]["measures_count"] == 0


# ---------------------------------------------------------------------------
# Tests — GET /api/enedis/flux-files/{id}
# ---------------------------------------------------------------------------


class TestFluxFileDetailEndpoint:
    """GET /api/enedis/flux-files/{id} — detail with header + error history."""

    def test_detail_found(self, client):
        c, session = client
        f = _seed_flux_file(
            session,
            "detail.zip",
            file_hash="h_detail",
            header_raw={"Version": "2.0", "Flux": "R4H"},
        )
        _seed_error_history(session, f, "first error")
        _seed_error_history(session, f, "second error")

        r = c.get(f"/api/enedis/flux-files/{f.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["filename"] == "detail.zip"
        assert data["header_raw"] == {"Version": "2.0", "Flux": "R4H"}
        assert len(data["errors_history"]) == 2
        assert data["errors_history"][0]["error_message"] == "first error"

    def test_detail_not_found(self, client):
        c, _ = client
        r = c.get("/api/enedis/flux-files/99999")
        assert r.status_code == 404

    def test_detail_null_header(self, client):
        c, session = client
        f = _seed_flux_file(session, "no_header.zip", file_hash="h_no_header")

        r = c.get(f"/api/enedis/flux-files/{f.id}")
        assert r.status_code == 200
        assert r.json()["header_raw"] is None

    def test_detail_no_errors(self, client):
        c, session = client
        f = _seed_flux_file(session, "clean.zip", file_hash="h_clean")

        r = c.get(f"/api/enedis/flux-files/{f.id}")
        assert r.status_code == 200
        assert r.json()["errors_history"] == []

    def test_detail_includes_sf5_metadata_and_header_raw(self, client):
        c, session = client
        f = _seed_flux_file(
            session,
            "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip",
            file_hash="h_sf5",
            flux_type="R63",
            header_raw={
                "filename_metadata": {"id_demande": "M053Q0D3"},
                "archive_manifest": {"payload_member_name": "payload.json"},
                "warnings": [{"code": "unknown_json_field"}],
            },
        )
        f.code_flux = "R63"
        f.type_donnee = "CdC"
        f.id_demande = "M053Q0D3"
        f.mode_publication = "P"
        f.payload_format = "JSON"
        f.num_sequence = "00001"
        f.publication_horodatage = "20230918161101"
        f.archive_members_count = 1
        session.commit()

        r = c.get(f"/api/enedis/flux-files/{f.id}")

        assert r.status_code == 200
        data = r.json()
        assert data["code_flux"] == "R63"
        assert data["id_demande"] == "M053Q0D3"
        assert data["payload_format"] == "JSON"
        assert data["header_raw"]["archive_manifest"]["payload_member_name"] == "payload.json"


# ---------------------------------------------------------------------------
# Tests — GET /api/enedis/stats
# ---------------------------------------------------------------------------


class TestStatsEndpoint:
    """GET /api/enedis/stats — aggregated stats."""

    def test_stats_empty(self, client):
        c, _ = client
        r = c.get("/api/enedis/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["files"]["total"] == 0
        assert data["measures"]["total"] == 0
        assert data["prms"]["count"] == 0
        assert data["prms"]["identifiers"] == []
        assert data["last_ingestion"] is None

    def test_stats_with_data(self, client):
        c, session = client

        # Seed 2 PARSED + 1 ERROR files (measures_count must match seeded rows)
        f1 = _seed_flux_file(session, "f1.zip", file_hash="h1", status=FluxStatus.PARSED, measures_count=1)
        f2 = _seed_flux_file(
            session, "f2.zip", file_hash="h2", status=FluxStatus.PARSED, flux_type="R171", measures_count=1
        )
        _seed_flux_file(
            session, "f3.zip", file_hash="h3", status=FluxStatus.ERROR, measures_count=0, error_message="fail"
        )

        # Seed measures
        _seed_measure_r4x(session, f1, "30001234567890")
        _seed_measure_r171(session, f2, "30009876543210")

        # Seed a completed run
        _seed_run(session, status=IngestionRunStatus.COMPLETED, triggered_by="api", files_parsed=2, files_error=1)

        r = c.get("/api/enedis/stats")
        assert r.status_code == 200
        data = r.json()

        assert data["files"]["total"] == 3
        assert data["files"]["by_status"]["parsed"] == 2
        assert data["files"]["by_status"]["error"] == 1
        assert data["files"]["by_flux_type"]["R4H"] == 2
        assert data["files"]["by_flux_type"]["R171"] == 1

        assert data["measures"]["r4x"] == 1
        assert data["measures"]["r171"] == 1
        assert data["measures"]["r6x"] == 0
        assert data["measures"]["c68"] == 0
        assert data["measures"]["total"] == 2

        assert data["last_ingestion"] is not None
        assert data["last_ingestion"]["triggered_by"] == "api"

    def test_stats_include_sf5_r6x_c68_rows_and_prms(self, client):
        c, session = client

        r63_file = _seed_flux_file(session, "r63.zip", file_hash="h_r63", flux_type="R63", measures_count=2)
        c68_file = _seed_flux_file(session, "c68.zip", file_hash="h_c68", flux_type="C68", measures_count=1)
        _seed_measure_r6x(session, r63_file, "30003333333333")
        _seed_measure_r6x(session, r63_file, "30003333333334")
        _seed_itc_c68(session, c68_file, "30004444444444")

        r = c.get("/api/enedis/stats")

        assert r.status_code == 200
        data = r.json()
        assert data["measures"]["r6x"] == 2
        assert data["measures"]["c68"] == 1
        assert data["measures"]["total"] == 3
        assert data["prms"]["count"] == 3
        assert sorted(data["prms"]["identifiers"]) == [
            "30003333333333",
            "30003333333334",
            "30004444444444",
        ]

    def test_stats_prms_distinct(self, client):
        c, session = client

        f1 = _seed_flux_file(session, "f1.zip", file_hash="h1", flux_type="R4H")
        f2 = _seed_flux_file(session, "f2.zip", file_hash="h2", flux_type="R171")

        # PRM A in R4x
        _seed_measure_r4x(session, f1, "30001234567890")
        # PRM B in R171
        _seed_measure_r171(session, f2, "30009876543210")
        # PRM A also in R171 (overlap)
        _seed_measure_r171(session, f2, "30001234567890")

        r = c.get("/api/enedis/stats")
        data = r.json()
        assert data["prms"]["count"] == 2
        assert sorted(data["prms"]["identifiers"]) == [
            "30001234567890",
            "30009876543210",
        ]

    def test_stats_last_ingestion_excludes_dry_run(self, client):
        c, session = client
        # Seed a dry-run completed run
        _seed_run(session, status=IngestionRunStatus.COMPLETED, dry_run=True)

        r = c.get("/api/enedis/stats")
        data = r.json()
        # Dry-run should not appear as last_ingestion
        assert data["last_ingestion"] is None

    def test_stats_last_ingestion_fields(self, client):
        c, session = client
        _seed_run(
            session,
            status=IngestionRunStatus.COMPLETED,
            triggered_by="cli",
            files_parsed=5,
            files_skipped=2,
            files_error=1,
            files_needs_review=1,
        )

        r = c.get("/api/enedis/stats")
        data = r.json()
        last = data["last_ingestion"]
        assert last is not None
        assert last["run_id"] >= 1
        assert last["triggered_by"] == "cli"
        assert last["files_count"] == 9  # 5+2+1+1
        assert last["timestamp"] is not None
