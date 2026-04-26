"""E2E tests — full pipeline with real encrypted Enedis SGE files.

Runs: decrypt -> parse -> store in DB -> validate stored data.
Skipped entirely if KEY_1/IV_1 env vars or flux_enedis/ directory are not available.
"""

import os
import re
from pathlib import Path

import pytest

from data_ingestion.enedis.decrypt import decrypt_file
from data_ingestion.enedis.enums import FluxStatus
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
    EnedisFluxMesureR6x,
    EnedisFluxItcC68,
)
from data_ingestion.enedis.pipeline import ingest_directory, ingest_file

from .conftest import _HAS_REAL_FILES, _HAS_REAL_KEYS, find_real_flux_files

pytestmark = pytest.mark.skipif(
    not (_HAS_REAL_KEYS and _HAS_REAL_FILES),
    reason="Real Enedis keys or flux_enedis/ directory not available",
)

# PRM format: 14 digits
_PRM_RE = re.compile(r"^\d{14}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_error_details(db) -> str:
    """Return error details for failed flux files (for assertion messages)."""
    errors = db.query(EnedisFluxFile).filter_by(status=FluxStatus.ERROR).all()
    if not errors:
        return "no errors"
    return "; ".join(f"{e.filename}: {e.error_message}" for e in errors)


def _find_first(flux_name: str) -> Path:
    """Find the first real file for one flux family. Fail if none found."""
    files = find_real_flux_files(flux_name)
    assert len(files) > 0, f"No local files found for {flux_name}"
    return files[0]


def _build_supported_flux_tree(base_dir: Path) -> Path:
    """Create a temporary recursive root containing only supported flux families."""
    root = base_dir / "supported_flux_enedis"
    root.mkdir(parents=True, exist_ok=True)

    for flux_name in SUPPORTED_FLUX_NAMES:
        target_dir = root / flux_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for source_file in find_real_flux_files(flux_name):
            os.symlink(source_file, target_dir / source_file.name)

    return root


# ---------------------------------------------------------------------------
# Flux type specifications for parametrized tests
# ---------------------------------------------------------------------------

FLUX_SPECS = [
    ("R4H", EnedisFluxMesureR4x, ["point_id", "horodatage", "valeur_point", "flux_type"]),
    ("R4M", EnedisFluxMesureR4x, ["point_id", "horodatage", "valeur_point", "flux_type"]),
    ("R4Q", EnedisFluxMesureR4x, ["point_id", "horodatage", "valeur_point", "flux_type"]),
    ("R171", EnedisFluxMesureR171, ["point_id", "type_mesure", "date_fin", "valeur"]),
    ("R50", EnedisFluxMesureR50, ["point_id", "date_releve", "horodatage"]),
    ("R151", EnedisFluxMesureR151, ["point_id", "date_releve", "type_donnee"]),
]

SUPPORTED_FLUX_NAMES = [spec[0] for spec in FLUX_SPECS]

_RUN_REAL_SF5 = os.environ.get("PROMEOS_RUN_REAL_SF5_TESTS") == "1"
SF5_FLUX_SPECS = [
    ("R63", EnedisFluxMesureR6x, ["point_id", "horodatage", "valeur", "flux_type"]),
    ("R64", EnedisFluxMesureR6x, ["point_id", "horodatage", "valeur", "flux_type"]),
    ("C68", EnedisFluxItcC68, ["point_id", "payload_raw"]),
]


# ===========================================================================
# Single-file E2E tests
# ===========================================================================


class TestSingleFileE2E:
    """Ingest one real file per flux type, validate DB state."""

    @pytest.mark.parametrize(
        "flux_name, model_cls, required_cols",
        FLUX_SPECS,
        ids=[s[0] for s in FLUX_SPECS],
    )
    def test_single_file_e2e(
        self,
        db,
        real_keys,
        real_flux_dir,
        flux_name,
        model_cls,
        required_cols,
    ):
        first_file = _find_first(flux_name)

        status = ingest_file(first_file, db, real_keys)

        assert status == FluxStatus.PARSED, (
            f"Expected PARSED for {first_file.name}, got {status}. Errors: {_get_error_details(db)}"
        )

        # Verify FluxFile record
        flux_file = db.query(EnedisFluxFile).first()
        assert flux_file is not None
        assert flux_file.status == FluxStatus.PARSED
        assert flux_file.flux_type == flux_name
        assert flux_file.measures_count > 0
        assert len(flux_file.file_hash) == 64
        assert flux_file.get_header_raw() is not None
        assert flux_file.version == 1
        assert flux_file.error_message is None

        # Verify measures in correct table
        measures = db.query(model_cls).all()
        assert len(measures) == flux_file.measures_count, (
            f"DB has {len(measures)} measures but flux_file.measures_count = {flux_file.measures_count}"
        )

        # Required columns non-null
        for m in measures:
            for col in required_cols:
                assert getattr(m, col) is not None, f"{col} is None on measure id={m.id} in {first_file.name}"

        # PRM format
        for m in measures:
            assert _PRM_RE.match(m.point_id), f"Invalid PRM format: {m.point_id}"

    @pytest.mark.parametrize(
        "flux_name, expected_freq",
        [
            ("R4H", "H"),
            ("R4M", "M"),
            ("R4Q", "Q"),
        ],
        ids=["R4H", "R4M", "R4Q"],
    )
    def test_r4x_specific_fields(
        self,
        db,
        real_keys,
        real_flux_dir,
        flux_name,
        expected_freq,
    ):
        """R4x files: verify frequence_publication and field formats."""
        first_file = _find_first(flux_name)
        status = ingest_file(first_file, db, real_keys)
        assert status == FluxStatus.PARSED

        flux_file = db.query(EnedisFluxFile).first()
        assert flux_file.frequence_publication == expected_freq

        measures = db.query(EnedisFluxMesureR4x).all()
        assert len(measures) > 0

        for m in measures:
            assert m.grandeur_physique is not None
            assert m.unite_mesure is not None
            # valeur_point should be a numeric string (may be negative)
            if m.valeur_point is not None:
                assert m.valeur_point.lstrip("-").isdigit(), f"Non-numeric valeur_point: {m.valeur_point}"


@pytest.mark.skipif(
    not _RUN_REAL_SF5,
    reason="Set PROMEOS_RUN_REAL_SF5_TESTS=1 to run real SF5 corpus tests",
)
class TestSF5RealSamples:
    """Opt-in real SF5 ingestion tests. No real payloads are committed."""

    @pytest.mark.parametrize(
        "flux_name, model_cls, required_cols",
        SF5_FLUX_SPECS,
        ids=[s[0] for s in SF5_FLUX_SPECS],
    )
    def test_single_sf5_file_e2e(self, db, real_keys, flux_name, model_cls, required_cols):
        files = find_real_flux_files(flux_name)
        if not files:
            pytest.skip(f"No local {flux_name} samples available")

        status = ingest_file(files[0], db, real_keys)

        assert status == FluxStatus.PARSED, (
            f"Expected PARSED for {files[0].name}, got {status}. Errors: {_get_error_details(db)}"
        )
        flux_file = db.query(EnedisFluxFile).first()
        assert flux_file.flux_type == flux_name
        assert flux_file.measures_count > 0
        assert flux_file.payload_format in {"JSON", "CSV"}
        assert flux_file.get_header_raw()["archive_manifest"]

        rows = db.query(model_cls).all()
        assert len(rows) == flux_file.measures_count
        for row in rows:
            for col in required_cols:
                assert getattr(row, col) is not None, f"{col} is None on row id={row.id} in {files[0].name}"
            assert _PRM_RE.match(row.point_id), f"Invalid PRM format: {row.point_id}"

    @pytest.mark.parametrize(
        "flux_name, sample_name",
        [
            ("R63", "ENEDIS_R63_P_CdC_M06DSGVE_00001_20240528163243.zip"),
            ("C68", "ENEDIS_C68_P_ITC_M082FQJM_00001_20250424205829.zip"),
        ],
    )
    def test_known_malformed_sf5_samples_error_cleanly(self, db, real_keys, flux_name, sample_name):
        matches = [path for path in find_real_flux_files(flux_name) if path.name == sample_name]
        if not matches:
            pytest.skip(f"No local malformed {sample_name} sample available")

        status = ingest_file(matches[0], db, real_keys)

        assert status == FluxStatus.ERROR
        assert db.query(EnedisFluxFile).one().error_message

    def test_supported_legacy_and_sf5_tree_when_enabled(self, db, real_keys, tmp_path):
        root = _build_supported_flux_tree(tmp_path)
        for flux_name in ("R63", "R64", "C68"):
            target_dir = root / flux_name
            target_dir.mkdir(parents=True, exist_ok=True)
            for source_file in find_real_flux_files(flux_name):
                os.symlink(source_file, target_dir / source_file.name)

        counters = ingest_directory(root, db, real_keys, recursive=True)

        assert counters["error"] == 0, f"Ingestion errors: {_get_error_details(db)}"
        assert db.query(EnedisFluxMesureR6x).count() > 0
        assert db.query(EnedisFluxItcC68).count() > 0


# ===========================================================================
# Full directory ingestion
# ===========================================================================


class TestFullDirectoryIngestion:
    """Ingest the entire flux_enedis/ directory, validate supported counters."""

    def test_ingest_all_files(self, db, real_keys, tmp_path):
        """Ingest all supported real Enedis files — zero errors expected."""
        supported_root = _build_supported_flux_tree(tmp_path)
        counters = ingest_directory(
            supported_root,
            db,
            real_keys,
            recursive=True,
        )

        # Zero errors
        assert counters["error"] == 0, f"Ingestion errors: {_get_error_details(db)}"

        # Only the currently supported families should be parsed.
        expected_parsed = sum(len(find_real_flux_files(flux_name)) for flux_name in SUPPORTED_FLUX_NAMES)
        assert counters["parsed"] == expected_parsed, f"Expected {expected_parsed} parsed, got {counters['parsed']}"

        # All 4 measure tables have rows
        r4x_count = db.query(EnedisFluxMesureR4x).count()
        r171_count = db.query(EnedisFluxMesureR171).count()
        r50_count = db.query(EnedisFluxMesureR50).count()
        r151_count = db.query(EnedisFluxMesureR151).count()

        assert r4x_count > 0, "No R4x measures stored"
        assert r171_count > 0, "No R171 measures stored"
        assert r50_count > 0, "No R50 measures stored"
        assert r151_count > 0, "No R151 measures stored"

        total_measures = r4x_count + r171_count + r50_count + r151_count

        print(f"\n{'=' * 60}")
        print("FULL DIRECTORY INGESTION REPORT")
        print(f"{'=' * 60}")
        print(f"Counters: {counters}")
        print(f"R4x measures:  {r4x_count:>8,}")
        print(f"R171 measures: {r171_count:>8,}")
        print(f"R50 measures:  {r50_count:>8,}")
        print(f"R151 measures: {r151_count:>8,}")
        print(f"TOTAL measures:{total_measures:>8,}")
        print(f"{'=' * 60}")

    def test_idempotence_on_real_files(self, db, real_keys, tmp_path):
        """Second ingest_directory run produces zero new ingestions."""
        supported_root = _build_supported_flux_tree(tmp_path)
        counters1 = ingest_directory(
            supported_root,
            db,
            real_keys,
            recursive=True,
        )
        counters2 = ingest_directory(
            supported_root,
            db,
            real_keys,
            recursive=True,
        )

        assert counters2["received"] == 0
        assert counters2["already_processed"] == counters1["received"]
        assert counters2["parsed"] == 0
        assert counters2["error"] == 0


# ===========================================================================
# Decrypted XML capture
# ===========================================================================


class TestDecryptedXmlCapture:
    """Decrypt one sample of each flux type and validate output."""

    SAMPLES = [
        "R4H",
        "R4M",
        "R4Q",
        "R171",
        "R50",
        "R151",
    ]

    def test_capture_decrypted_xml_samples(self, real_keys, real_flux_dir, tmp_path):
        """Decrypt one sample per flux type and write XML to archive_dir."""
        archive_dir = tmp_path / "decrypted_xml"

        for flux_name in self.SAMPLES:
            first_file = _find_first(flux_name)
            xml_bytes = decrypt_file(first_file, real_keys, archive_dir=archive_dir)

            expected_xml = archive_dir / (first_file.stem + ".xml")
            assert expected_xml.exists(), f"Archive file not created for {flux_name}"
            assert expected_xml.read_bytes() == xml_bytes
            assert xml_bytes.startswith(b"<?xml"), f"{flux_name} XML does not start with <?xml"

        saved = sorted(archive_dir.glob("*.xml"))
        assert len(saved) == len(self.SAMPLES)

        print(f"\nDecrypted XML samples saved to: {archive_dir}")
        for p in saved:
            print(f"  {p.name} ({p.stat().st_size:,} bytes)")
