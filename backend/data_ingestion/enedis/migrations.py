"""Bootstrap and safe migrations for the Enedis raw flux database."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from data_ingestion.enedis.base import FluxDataBase
from data_ingestion.enedis.models import ENEDIS_RAW_TABLES

logger = logging.getLogger(__name__)


def run_flux_data_migrations(engine) -> None:
    """Create or upgrade the Enedis raw schema in flux_data.db."""
    _rename_enedis_mesure_table(engine)
    _create_enedis_tables(engine)
    _add_enedis_columns(engine)


def _rename_enedis_mesure_table(engine) -> None:
    """Rename the legacy SF2 raw table if it still exists."""
    insp = inspect(engine)
    if not insp.has_table("enedis_flux_mesure"):
        return
    if insp.has_table("enedis_flux_mesure_r4x"):
        return

    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE "enedis_flux_mesure" RENAME TO "enedis_flux_mesure_r4x"'))
        conn.execute(text('DROP INDEX IF EXISTS "ix_enedis_mesure_point_horodatage"'))
        conn.execute(text('DROP INDEX IF EXISTS "ix_enedis_mesure_flux_file"'))
        conn.execute(text('DROP INDEX IF EXISTS "ix_enedis_mesure_flux_type"'))
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS "ix_enedis_mesure_r4x_point_horodatage"'
                ' ON "enedis_flux_mesure_r4x" ("point_id", "horodatage")'
            )
        )
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS "ix_enedis_mesure_r4x_flux_file"'
                ' ON "enedis_flux_mesure_r4x" ("flux_file_id")'
            )
        )
        conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS "ix_enedis_mesure_r4x_flux_type" ON "enedis_flux_mesure_r4x" ("flux_type")'
            )
        )
    logger.info("flux-data migration: renamed enedis_flux_mesure to enedis_flux_mesure_r4x")


def _create_enedis_tables(engine) -> None:
    """Create raw Enedis tables if any are missing."""
    insp = inspect(engine)
    missing = [t for t in ENEDIS_RAW_TABLES if not insp.has_table(t)]
    if missing:
        import data_ingestion.enedis.models  # noqa: F401

        FluxDataBase.metadata.create_all(
            bind=engine,
            tables=[FluxDataBase.metadata.tables[t] for t in ENEDIS_RAW_TABLES if t in FluxDataBase.metadata.tables],
            checkfirst=True,
        )
        logger.info("flux-data migration: created raw Enedis tables: %s", missing)

    with engine.begin() as conn:
        conn.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS "ix_ingestion_run_single_running" '
                'ON "enedis_ingestion_run" ("status") WHERE "status" = \'running\''
            )
        )


def _add_enedis_columns(engine) -> None:
    """Add evolutive columns to existing raw Enedis tables."""
    insp = inspect(engine)

    enedis_flux_file_columns = [
        ("version", "INTEGER DEFAULT 1"),
        ("supersedes_file_id", 'INTEGER REFERENCES "enedis_flux_file"("id") ON DELETE SET NULL'),
        ("frequence_publication", "VARCHAR(5)"),
        ("nature_courbe_demandee", "VARCHAR(20)"),
        ("identifiant_destinataire", "VARCHAR(100)"),
        ("code_flux", "VARCHAR(20)"),
        ("type_donnee", "VARCHAR(20)"),
        ("id_demande", "VARCHAR(20)"),
        ("mode_publication", "VARCHAR(5)"),
        ("payload_format", "VARCHAR(10)"),
        ("num_sequence", "VARCHAR(10)"),
        ("siren_publication", "VARCHAR(20)"),
        ("code_contrat_publication", "VARCHAR(50)"),
        ("publication_horodatage", "VARCHAR(20)"),
        ("archive_members_count", "INTEGER"),
        ("header_raw", "TEXT"),
    ]
    enedis_flux_itc_c68_columns = [
        ("type_injection", "VARCHAR(30)"),
    ]

    table_column_map = {
        "enedis_flux_file": enedis_flux_file_columns,
        "enedis_flux_itc_c68": enedis_flux_itc_c68_columns,
    }
    with engine.begin() as conn:
        for table_name, columns in table_column_map.items():
            if not insp.has_table(table_name):
                continue
            existing_cols = {c["name"] for c in insp.get_columns(table_name)}
            for col_name, col_type in columns:
                if col_name in existing_cols:
                    continue
                conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}'))
                logger.info("flux-data migration: added %s.%s", table_name, col_name)
