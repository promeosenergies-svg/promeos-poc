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
    assert {"enedis_flux_mesure_r63", "enedis_flux_index_r64", "enedis_flux_itc_c68"}.issubset(tables)
    assert "enedis_flux_mesure_r6x" in set(inspect(engine).get_view_names())
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
    assert {"enedis_flux_mesure_r63", "enedis_flux_index_r64", "enedis_flux_itc_c68"}.issubset(tables)
    assert "enedis_flux_mesure_r6x" in set(insp.get_view_names())

    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT filename, flux_type FROM enedis_flux_file").one()
    assert row == ("legacy.zip", "R4H")


def test_flux_data_migrations_split_legacy_r6x_table_into_canonical_tables(tmp_path):
    """Existing shared R6X raw rows should migrate into business-specific tables."""
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
            """
            CREATE TABLE enedis_flux_mesure_r6x (
                id INTEGER PRIMARY KEY,
                flux_file_id INTEGER NOT NULL,
                flux_type VARCHAR(10) NOT NULL,
                source_format VARCHAR(10) NOT NULL,
                archive_member_name VARCHAR(255) NOT NULL,
                point_id VARCHAR(14) NOT NULL,
                periode_date_debut VARCHAR(50),
                periode_date_fin VARCHAR(50),
                etape_metier VARCHAR(20),
                mode_calcul VARCHAR(20),
                contexte_releve VARCHAR(20),
                type_releve VARCHAR(20),
                motif_releve VARCHAR(20),
                grandeur_metier VARCHAR(20),
                grandeur_physique VARCHAR(20),
                unite VARCHAR(20),
                horodatage VARCHAR(50) NOT NULL,
                pas VARCHAR(20),
                nature_point VARCHAR(10),
                type_correction VARCHAR(10),
                valeur VARCHAR(30),
                indice_vraisemblance VARCHAR(10),
                etat_complementaire VARCHAR(10),
                code_grille VARCHAR(20),
                id_calendrier VARCHAR(30),
                libelle_calendrier VARCHAR(100),
                libelle_grille VARCHAR(100),
                id_classe_temporelle VARCHAR(30),
                libelle_classe_temporelle VARCHAR(100),
                code_cadran VARCHAR(30),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO enedis_flux_mesure_r6x (
                id, flux_file_id, flux_type, source_format, archive_member_name,
                point_id, horodatage, pas, nature_point, valeur, id_calendrier,
                code_cadran, created_at, updated_at
            )
            VALUES
                (1, 10, 'R63', 'JSON', 'r63.json', '30000000000001',
                 '2026-01-01T00:00:00+01:00', 'PT5M', 'R', '10', NULL,
                 NULL, '2026-01-01', '2026-01-01'),
                (2, 11, 'R64', 'JSON', 'r64.json', '30000000000002',
                 '2026-01-01T00:00:00+01:00', NULL, NULL, '100', 'CAL1',
                 '01', '2026-01-01', '2026-01-01')
            """
        )

    run_flux_data_migrations(engine)

    insp = inspect(engine)
    assert "enedis_flux_mesure_r6x" not in set(insp.get_table_names())
    assert "enedis_flux_mesure_r6x" in set(insp.get_view_names())

    with engine.connect() as conn:
        r63 = conn.exec_driver_sql("SELECT valeur, pas, nature_point FROM enedis_flux_mesure_r63").one()
        r64 = conn.exec_driver_sql("SELECT valeur, id_calendrier, code_cadran FROM enedis_flux_index_r64").one()
        compat_count = conn.exec_driver_sql("SELECT COUNT(*) FROM enedis_flux_mesure_r6x").scalar_one()

    assert r63 == ("10", "PT5M", "R")
    assert r64 == ("100", "CAL1", "01")
    assert compat_count == 2


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
