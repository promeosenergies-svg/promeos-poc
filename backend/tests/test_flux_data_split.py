"""Tests for the flux_data.db split boundary."""

from pathlib import Path

from sqlalchemy import create_engine, inspect

import data_staging.models  # noqa: F401
import models  # noqa: F401
from data_ingestion.enedis.migrations import run_flux_data_migrations
from data_ingestion.enedis.models import ENEDIS_RAW_TABLES
from database.flux_data import _adopt_legacy_flux_db_files
from database.migrations import run_migrations
from models.base import Base

SF5_FILE_METADATA_COLUMNS = {
    "code_flux",
    "type_donnee",
    "id_demande",
    "mode_publication",
    "payload_format",
    "num_sequence",
    "siren_publication",
    "code_contrat_publication",
    "publication_horodatage",
    "archive_members_count",
}


def test_main_db_bootstrap_does_not_create_raw_enedis_tables(tmp_path):
    """Main PROMEOS bootstrap must leave raw Enedis tables out of promeos.db."""
    db_path = tmp_path / "promeos.db"
    engine = create_engine(f"sqlite:///{db_path}")

    Base.metadata.create_all(bind=engine)
    run_migrations(engine)

    tables = set(inspect(engine).get_table_names())
    assert not (tables & set(ENEDIS_RAW_TABLES))


def test_flux_data_bootstrap_creates_raw_enedis_tables(tmp_path):
    """Dedicated raw DB bootstrap must create all Enedis archive/control tables."""
    db_path = tmp_path / "flux_data.db"
    engine = create_engine(f"sqlite:///{db_path}")

    run_flux_data_migrations(engine)

    tables = set(inspect(engine).get_table_names())
    assert set(ENEDIS_RAW_TABLES).issubset(tables)
    columns = {c["name"] for c in inspect(engine).get_columns("enedis_flux_file")}
    assert SF5_FILE_METADATA_COLUMNS.issubset(columns)


def test_flux_data_migrations_add_sf5_columns_idempotently(tmp_path):
    """Existing raw DBs should gain SF5 file metadata without data loss."""
    db_path = tmp_path / "flux_data.db"
    engine = create_engine(f"sqlite:///{db_path}")

    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE enedis_flux_file (
                id INTEGER PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                flux_type VARCHAR(10) NOT NULL,
                status VARCHAR(20) NOT NULL,
                measures_count INTEGER
            )
            """
        )
        conn.exec_driver_sql(
            "INSERT INTO enedis_flux_file (filename, file_hash, flux_type, status, measures_count) "
            "VALUES ('legacy.zip', 'hash', 'R4H', 'parsed', 1)"
        )

    run_flux_data_migrations(engine)
    run_flux_data_migrations(engine)

    insp = inspect(engine)
    columns = {c["name"] for c in insp.get_columns("enedis_flux_file")}
    assert SF5_FILE_METADATA_COLUMNS.issubset(columns)
    tables = set(insp.get_table_names())
    assert {"enedis_flux_mesure_r6x", "enedis_flux_itc_c68"}.issubset(tables)

    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT filename, flux_type FROM enedis_flux_file").one()
    assert row == ("legacy.zip", "R4H")


def test_legacy_enedis_db_is_adopted_by_rename(tmp_path):
    """Legacy enedis.db files should move to the canonical flux_data.db name."""
    legacy = tmp_path / "enedis.db"
    legacy.write_bytes(b"legacy-db")
    (tmp_path / "enedis.db-wal").write_bytes(b"wal")
    (tmp_path / "enedis.db-shm").write_bytes(b"shm")

    target = tmp_path / "flux_data.db"
    moved = _adopt_legacy_flux_db_files(str(target), str(legacy))

    assert moved is True
    assert target.read_bytes() == b"legacy-db"
    assert Path(f"{target}-wal").read_bytes() == b"wal"
    assert Path(f"{target}-shm").read_bytes() == b"shm"
    assert not legacy.exists()
