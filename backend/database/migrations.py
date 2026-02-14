"""
PROMEOS - Safe schema migrations (no Alembic).
Adds missing columns to existing tables without dropping anything.
SQLite supports ALTER TABLE ADD COLUMN for nullable columns.
"""
import logging
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)

# Columns to add for SoftDeleteMixin on patrimony tables
SOFT_DELETE_COLUMNS = [
    ("deleted_at", "DATETIME"),
    ("deleted_by", "VARCHAR(200)"),
    ("delete_reason", "VARCHAR(500)"),
]

SOFT_DELETE_TABLES = [
    "organisations",
    "entites_juridiques",
    "portefeuilles",
    "sites",
    "batiments",
    "compteurs",
]


def run_migrations(engine):
    """Run all pending safe migrations. Idempotent — skips existing columns."""
    _add_soft_delete_columns(engine)
    _add_unique_meter_id_index(engine)


def _add_soft_delete_columns(engine):
    """Add deleted_at/deleted_by/delete_reason to patrimony tables if missing."""
    insp = inspect(engine)
    added = 0

    with engine.begin() as conn:
        for table_name in SOFT_DELETE_TABLES:
            if not insp.has_table(table_name):
                continue

            existing_cols = {c["name"] for c in insp.get_columns(table_name)}

            for col_name, col_type in SOFT_DELETE_COLUMNS:
                if col_name in existing_cols:
                    continue

                stmt = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}'
                conn.execute(text(stmt))
                added += 1
                logger.info("migration: added %s.%s (%s)", table_name, col_name, col_type)

        # Add index on deleted_at for each table (if not exists)
        for table_name in SOFT_DELETE_TABLES:
            if not insp.has_table(table_name):
                continue
            idx_name = f"ix_{table_name}_deleted_at"
            existing_indexes = {idx["name"] for idx in insp.get_indexes(table_name) if idx.get("name")}
            if idx_name not in existing_indexes:
                try:
                    conn.execute(text(
                        f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" ("deleted_at")'
                    ))
                    logger.info("migration: created index %s", idx_name)
                except Exception:
                    pass  # index may already exist under different name

    if added > 0:
        logger.info("migration: %d column(s) added across %d table(s)", added, len(SOFT_DELETE_TABLES))
    else:
        logger.debug("migration: soft-delete columns already present — no changes")


def _add_unique_meter_id_index(engine):
    """Add unique partial index on compteurs.meter_id WHERE deleted_at IS NULL.

    Ensures a PRM/PCE can only exist once among active (non-deleted) compteurs.
    SQLite supports partial indexes via WHERE clause.
    """
    idx_name = "uq_compteur_meter_id_active"
    insp = inspect(engine)

    if not insp.has_table("compteurs"):
        return

    existing_indexes = {idx["name"] for idx in insp.get_indexes("compteurs") if idx.get("name")}
    if idx_name in existing_indexes:
        return

    with engine.begin() as conn:
        try:
            conn.execute(text(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "compteurs" ("meter_id") '
                f'WHERE "meter_id" IS NOT NULL AND "deleted_at" IS NULL'
            ))
            logger.info("migration: created unique partial index %s", idx_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", idx_name, e)
