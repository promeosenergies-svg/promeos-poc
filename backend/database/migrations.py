"""
PROMEOS - Safe schema migrations (no Alembic).
Adds missing columns/tables to existing schema without dropping anything.
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
    _create_delivery_points_table(engine)
    _add_compteur_delivery_point_fk(engine)
    _backfill_delivery_points(engine)
    _add_unique_delivery_point_code_index(engine)
    # Phase 2A — Integrity constraints
    _add_unique_org_siren_index(engine)
    _add_unique_portefeuille_ej_nom_index(engine)
    _add_unique_site_portefeuille_siret_index(engine)
    _add_unique_batiment_site_nom_index(engine)
    _add_dp_compteur_cascade_trigger(engine)


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


# ========================================
# DeliveryPoint migrations
# ========================================

def _create_delivery_points_table(engine):
    """Create delivery_points table if it does not exist."""
    insp = inspect(engine)
    if insp.has_table("delivery_points"):
        logger.debug("migration: delivery_points table already exists — skipping")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "delivery_points" (
                "id" INTEGER PRIMARY KEY,
                "code" VARCHAR(14) NOT NULL,
                "energy_type" VARCHAR(10),
                "site_id" INTEGER NOT NULL REFERENCES "sites"("id"),
                "status" VARCHAR(10) NOT NULL DEFAULT 'active',
                "data_source" VARCHAR(20),
                "data_source_ref" VARCHAR(200),
                "imported_at" DATETIME,
                "imported_by" INTEGER,
                "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "deleted_at" DATETIME,
                "deleted_by" VARCHAR(200),
                "delete_reason" VARCHAR(500)
            )
        """))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS "ix_delivery_points_code" ON "delivery_points" ("code")'
        ))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS "ix_delivery_points_site_id" ON "delivery_points" ("site_id")'
        ))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS "ix_delivery_points_deleted_at" ON "delivery_points" ("deleted_at")'
        ))
    logger.info("migration: created delivery_points table with indexes")


def _add_compteur_delivery_point_fk(engine):
    """Add delivery_point_id column to compteurs if missing."""
    insp = inspect(engine)
    if not insp.has_table("compteurs"):
        return

    existing_cols = {c["name"] for c in insp.get_columns("compteurs")}
    if "delivery_point_id" in existing_cols:
        logger.debug("migration: compteurs.delivery_point_id already exists — skipping")
        return

    with engine.begin() as conn:
        conn.execute(text(
            'ALTER TABLE "compteurs" ADD COLUMN "delivery_point_id" INTEGER '
            'REFERENCES "delivery_points"("id")'
        ))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS "ix_compteurs_delivery_point_id" '
            'ON "compteurs" ("delivery_point_id")'
        ))
    logger.info("migration: added compteurs.delivery_point_id + index")


def _backfill_delivery_points(engine):
    """Backfill delivery_points from existing compteurs.meter_id.

    Strategy:
    - Only process active (non-deleted) compteurs with meter_id
    - Deduplicate: if N compteurs share the same meter_id on the same site,
      create 1 DeliveryPoint and link all N compteurs
    - If N compteurs share meter_id across different sites, create 1 DP
      per site (meter_id can be on different sites in edge cases)
    - Skip compteurs already linked (delivery_point_id IS NOT NULL)
    - Idempotent: re-running creates no duplicates
    """
    insp = inspect(engine)
    if not insp.has_table("compteurs") or not insp.has_table("delivery_points"):
        return

    with engine.begin() as conn:
        # Find active compteurs with meter_id that are not yet linked
        rows = conn.execute(text("""
            SELECT c.id, c.meter_id, c.site_id, c.type, c.data_source, c.data_source_ref
            FROM compteurs c
            WHERE c.meter_id IS NOT NULL
              AND c.meter_id != ''
              AND c.deleted_at IS NULL
              AND c.delivery_point_id IS NULL
            ORDER BY c.site_id, c.meter_id
        """)).fetchall()

        if not rows:
            logger.debug("migration: backfill — no unlinked compteurs with meter_id")
            return

        created = 0
        linked = 0

        for row in rows:
            cpt_id, meter_id, site_id, cpt_type, data_source, data_source_ref = row

            # Check if a DeliveryPoint already exists for this code + site (active)
            existing = conn.execute(text("""
                SELECT id FROM delivery_points
                WHERE code = :code AND site_id = :site_id AND deleted_at IS NULL
                LIMIT 1
            """), {"code": meter_id, "site_id": site_id}).fetchone()

            if existing:
                dp_id = existing[0]
            else:
                # Auto-detect energy_type from compteur type
                energy_type = _guess_energy_type(cpt_type)
                conn.execute(text("""
                    INSERT INTO delivery_points (code, energy_type, site_id, status,
                        data_source, data_source_ref, created_at, updated_at)
                    VALUES (:code, :energy_type, :site_id, 'active',
                        :data_source, :data_source_ref, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """), {
                    "code": meter_id,
                    "energy_type": energy_type,
                    "site_id": site_id,
                    "data_source": data_source or "backfill",
                    "data_source_ref": data_source_ref or "migration_backfill",
                })
                dp_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
                created += 1

            # Link compteur to delivery_point
            conn.execute(text("""
                UPDATE compteurs SET delivery_point_id = :dp_id WHERE id = :cpt_id
            """), {"dp_id": dp_id, "cpt_id": cpt_id})
            linked += 1

        logger.info(
            "migration: backfill — created %d delivery_points, linked %d compteurs",
            created, linked,
        )


def _guess_energy_type(compteur_type):
    """Guess DeliveryPoint energy_type from compteur type string."""
    if not compteur_type:
        return None
    t = compteur_type.lower() if isinstance(compteur_type, str) else str(compteur_type).lower()
    if "gaz" in t:
        return "gaz"
    if "elec" in t:
        return "elec"
    return None


def _add_unique_delivery_point_code_index(engine):
    """Add unique partial index on delivery_points.code WHERE deleted_at IS NULL.

    Ensures a PRM/PCE code can only exist once among active delivery points.
    """
    idx_name = "uq_delivery_point_code_active"
    insp = inspect(engine)

    if not insp.has_table("delivery_points"):
        return

    existing_indexes = {idx["name"] for idx in insp.get_indexes("delivery_points") if idx.get("name")}
    if idx_name in existing_indexes:
        return

    with engine.begin() as conn:
        try:
            conn.execute(text(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "delivery_points" ("code") '
                f'WHERE "code" IS NOT NULL AND "deleted_at" IS NULL'
            ))
            logger.info("migration: created unique partial index %s", idx_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", idx_name, e)


# ========================================
# Phase 2A — Integrity constraints
# ========================================

def _add_unique_org_siren_index(engine):
    """UNIQUE(siren) on organisations WHERE active (deleted_at IS NULL, siren IS NOT NULL)."""
    idx_name = "uq_org_siren_active"
    insp = inspect(engine)
    if not insp.has_table("organisations"):
        return
    existing = {idx["name"] for idx in insp.get_indexes("organisations") if idx.get("name")}
    if idx_name in existing:
        return
    with engine.begin() as conn:
        try:
            conn.execute(text(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "organisations" ("siren") '
                f'WHERE "siren" IS NOT NULL AND "deleted_at" IS NULL'
            ))
            logger.info("migration: created unique index %s", idx_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", idx_name, e)


def _add_unique_portefeuille_ej_nom_index(engine):
    """UNIQUE(entite_juridique_id, nom) on portefeuilles WHERE active."""
    idx_name = "uq_portefeuille_ej_nom_active"
    insp = inspect(engine)
    if not insp.has_table("portefeuilles"):
        return
    existing = {idx["name"] for idx in insp.get_indexes("portefeuilles") if idx.get("name")}
    if idx_name in existing:
        return
    with engine.begin() as conn:
        try:
            conn.execute(text(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "portefeuilles" ("entite_juridique_id", "nom") '
                f'WHERE "deleted_at" IS NULL'
            ))
            logger.info("migration: created unique index %s", idx_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", idx_name, e)


def _add_unique_site_portefeuille_siret_index(engine):
    """UNIQUE(portefeuille_id, siret) on sites WHERE active and siret IS NOT NULL."""
    idx_name = "uq_site_portefeuille_siret_active"
    insp = inspect(engine)
    if not insp.has_table("sites"):
        return
    existing = {idx["name"] for idx in insp.get_indexes("sites") if idx.get("name")}
    if idx_name in existing:
        return
    with engine.begin() as conn:
        try:
            conn.execute(text(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "sites" ("portefeuille_id", "siret") '
                f'WHERE "siret" IS NOT NULL AND "deleted_at" IS NULL'
            ))
            logger.info("migration: created unique index %s", idx_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", idx_name, e)


def _add_unique_batiment_site_nom_index(engine):
    """UNIQUE(site_id, nom) on batiments WHERE active."""
    idx_name = "uq_batiment_site_nom_active"
    insp = inspect(engine)
    if not insp.has_table("batiments"):
        return
    existing = {idx["name"] for idx in insp.get_indexes("batiments") if idx.get("name")}
    if idx_name in existing:
        return
    with engine.begin() as conn:
        try:
            conn.execute(text(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "batiments" ("site_id", "nom") '
                f'WHERE "deleted_at" IS NULL'
            ))
            logger.info("migration: created unique index %s", idx_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", idx_name, e)


def _add_dp_compteur_cascade_trigger(engine):
    """SET NULL on compteurs.delivery_point_id when a delivery_point is hard-deleted.

    SQLite cannot ALTER FK constraints, so we use a BEFORE DELETE trigger.
    Soft delete (normal path) does not fire this — only hard DELETE.
    """
    trigger_name = "trg_dp_delete_nullify_compteurs"
    with engine.begin() as conn:
        # Check if trigger exists
        row = conn.execute(text(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='trigger' AND name=:name"
        ), {"name": trigger_name}).scalar()
        if row and row > 0:
            return
        try:
            conn.execute(text(f"""
                CREATE TRIGGER "{trigger_name}"
                BEFORE DELETE ON "delivery_points"
                FOR EACH ROW
                BEGIN
                    UPDATE "compteurs"
                    SET "delivery_point_id" = NULL
                    WHERE "delivery_point_id" = OLD."id";
                END
            """))
            logger.info("migration: created trigger %s", trigger_name)
        except Exception as e:
            logger.warning("migration: could not create trigger %s: %s", trigger_name, e)
