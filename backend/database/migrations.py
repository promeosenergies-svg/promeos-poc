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
    # V39 — Tertiaire / OPERAT
    _create_tertiaire_tables(engine)
    # V2-Conso — Dedup meter_reading + unique constraint
    _dedup_meter_reading(engine)
    _add_unique_meter_reading_index(engine)
    # Étape 4 — Action Engine: evidence_required column
    _add_action_evidence_required_column(engine)
    # Fix delivery_points energy_type enum case (elec→ELEC, gaz→GAZ)
    _fix_delivery_point_energy_type_case(engine)
    # Backfill risque_financier_euro from obligations
    _backfill_site_risque_financier(engine)
    # V96 — Patrimoine Unique Monde
    _create_payment_rules_table(engine)
    _add_contract_v96_columns(engine)


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
                "status" VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
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
    """Guess DeliveryPoint energy_type from compteur type string.

    Returns enum **name** (ELEC/GAZ) because SQLAlchemy Enum stores names, not values.
    """
    if not compteur_type:
        return None
    t = compteur_type.lower() if isinstance(compteur_type, str) else str(compteur_type).lower()
    if "gaz" in t:
        return "GAZ"
    if "elec" in t:
        return "ELEC"
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


# ========================================
# V39 — Tertiaire / OPERAT tables
# ========================================

_TERTIAIRE_TABLES = {
    "tertiaire_efa": """
        CREATE TABLE IF NOT EXISTS "tertiaire_efa" (
            "id" INTEGER PRIMARY KEY,
            "org_id" INTEGER NOT NULL REFERENCES "organisations"("id"),
            "site_id" INTEGER REFERENCES "sites"("id"),
            "nom" VARCHAR(300) NOT NULL,
            "statut" VARCHAR(20) NOT NULL DEFAULT 'draft',
            "role_assujetti" VARCHAR(30) NOT NULL DEFAULT 'proprietaire',
            "reporting_start" DATE,
            "reporting_end" DATE,
            "closed_at" DATETIME,
            "notes" TEXT,
            "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "deleted_at" DATETIME,
            "deleted_by" VARCHAR(200),
            "delete_reason" VARCHAR(500)
        )
    """,
    "tertiaire_efa_link": """
        CREATE TABLE IF NOT EXISTS "tertiaire_efa_link" (
            "id" INTEGER PRIMARY KEY,
            "child_efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id"),
            "parent_efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id"),
            "reason" VARCHAR(100) NOT NULL,
            "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "tertiaire_efa_building": """
        CREATE TABLE IF NOT EXISTS "tertiaire_efa_building" (
            "id" INTEGER PRIMARY KEY,
            "efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id"),
            "building_id" INTEGER REFERENCES "batiments"("id"),
            "usage_label" VARCHAR(200),
            "surface_m2" REAL,
            "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "tertiaire_responsibility": """
        CREATE TABLE IF NOT EXISTS "tertiaire_responsibility" (
            "id" INTEGER PRIMARY KEY,
            "efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id"),
            "role" VARCHAR(30) NOT NULL,
            "entity_type" VARCHAR(100),
            "entity_value" VARCHAR(300),
            "contact_email" VARCHAR(300),
            "scope_json" TEXT,
            "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "tertiaire_perimeter_event": """
        CREATE TABLE IF NOT EXISTS "tertiaire_perimeter_event" (
            "id" INTEGER PRIMARY KEY,
            "efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id"),
            "type" VARCHAR(50) NOT NULL,
            "effective_date" DATE NOT NULL,
            "description" TEXT,
            "justification" TEXT,
            "attachments_json" TEXT,
            "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "tertiaire_declaration": """
        CREATE TABLE IF NOT EXISTS "tertiaire_declaration" (
            "id" INTEGER PRIMARY KEY,
            "efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id"),
            "year" INTEGER NOT NULL,
            "status" VARCHAR(30) NOT NULL DEFAULT 'draft',
            "checklist_json" TEXT,
            "exported_pack_path" VARCHAR(500),
            "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "tertiaire_proof_artifact": """
        CREATE TABLE IF NOT EXISTS "tertiaire_proof_artifact" (
            "id" INTEGER PRIMARY KEY,
            "efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id"),
            "type" VARCHAR(100) NOT NULL,
            "file_path" VARCHAR(500),
            "kb_doc_id" VARCHAR(200),
            "owner_role" VARCHAR(30),
            "valid_from" DATE,
            "valid_to" DATE,
            "tags_json" TEXT,
            "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "tertiaire_data_quality_issue": """
        CREATE TABLE IF NOT EXISTS "tertiaire_data_quality_issue" (
            "id" INTEGER PRIMARY KEY,
            "efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id"),
            "year" INTEGER,
            "code" VARCHAR(100) NOT NULL,
            "severity" VARCHAR(20) NOT NULL,
            "message_fr" TEXT NOT NULL,
            "impact_fr" TEXT,
            "action_fr" TEXT,
            "status" VARCHAR(30) NOT NULL DEFAULT 'open',
            "proof_required_json" TEXT,
            "proof_owner_role" VARCHAR(100),
            "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
}

_TERTIAIRE_INDEXES = [
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_efa_org_id" ON "tertiaire_efa" ("org_id")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_efa_site_id" ON "tertiaire_efa" ("site_id")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_efa_statut" ON "tertiaire_efa" ("statut")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_efa_deleted_at" ON "tertiaire_efa" ("deleted_at")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_efa_building_efa_id" ON "tertiaire_efa_building" ("efa_id")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_responsibility_efa_id" ON "tertiaire_responsibility" ("efa_id")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_perimeter_event_efa_id" ON "tertiaire_perimeter_event" ("efa_id")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_declaration_efa_id" ON "tertiaire_declaration" ("efa_id")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_proof_artifact_efa_id" ON "tertiaire_proof_artifact" ("efa_id")',
    'CREATE INDEX IF NOT EXISTS "ix_tertiaire_dq_issue_efa_id" ON "tertiaire_data_quality_issue" ("efa_id")',
    'CREATE UNIQUE INDEX IF NOT EXISTS "uq_tertiaire_declaration_efa_year" ON "tertiaire_declaration" ("efa_id", "year")',
]


def _create_tertiaire_tables(engine):
    """V39: Create tertiaire/OPERAT tables if they do not exist. Idempotent."""
    insp = inspect(engine)
    created = 0

    with engine.begin() as conn:
        for table_name, ddl in _TERTIAIRE_TABLES.items():
            if insp.has_table(table_name):
                continue
            try:
                conn.execute(text(ddl))
                created += 1
                logger.info("migration: created table %s", table_name)
            except Exception as e:
                logger.warning("migration: could not create table %s: %s", table_name, e)

        for idx_sql in _TERTIAIRE_INDEXES:
            try:
                conn.execute(text(idx_sql))
            except Exception:
                pass

    if created > 0:
        logger.info("migration: V39 tertiaire — %d table(s) created", created)
    else:
        logger.debug("migration: V39 tertiaire tables already present — no changes")


# ========================================
# V2-Conso — meter_reading dedup + unique
# ========================================

def _dedup_meter_reading(engine):
    """Remove duplicate (meter_id, timestamp) rows from meter_reading.

    Strategy: keep the row with the best quality_score, ties broken by most
    recent created_at, then highest id.  Idempotent — skips if no duplicates.
    """
    insp = inspect(engine)
    if not insp.has_table("meter_reading"):
        return

    with engine.begin() as conn:
        dupes = conn.execute(text("""
            SELECT meter_id, timestamp, COUNT(*) AS cnt
            FROM meter_reading
            GROUP BY meter_id, timestamp
            HAVING cnt > 1
        """)).fetchall()

        if not dupes:
            logger.debug("migration: meter_reading — no duplicates found")
            return

        deleted = 0
        for meter_id, ts, cnt in dupes:
            # Keep the best row (highest quality_score, then latest created_at, then highest id)
            keep = conn.execute(text("""
                SELECT id FROM meter_reading
                WHERE meter_id = :mid AND timestamp = :ts
                ORDER BY
                    COALESCE(quality_score, -1) DESC,
                    COALESCE(created_at, '1970-01-01') DESC,
                    id DESC
                LIMIT 1
            """), {"mid": meter_id, "ts": ts}).scalar()

            if keep:
                result = conn.execute(text("""
                    DELETE FROM meter_reading
                    WHERE meter_id = :mid AND timestamp = :ts AND id != :keep_id
                """), {"mid": meter_id, "ts": ts, "keep_id": keep})
                deleted += result.rowcount

        logger.info("migration: meter_reading dedup — removed %d duplicate rows from %d pairs",
                     deleted, len(dupes))


def _add_unique_meter_reading_index(engine):
    """Add UNIQUE index on (meter_id, timestamp) to prevent future duplicates."""
    idx_name = "uq_meter_reading_meter_ts"
    insp = inspect(engine)

    if not insp.has_table("meter_reading"):
        return

    existing = {idx["name"] for idx in insp.get_indexes("meter_reading") if idx.get("name")}
    if idx_name in existing:
        return

    with engine.begin() as conn:
        try:
            conn.execute(text(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                f'ON "meter_reading" ("meter_id", "timestamp")'
            ))
            logger.info("migration: created unique index %s", idx_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", idx_name, e)


# ========================================
# Étape 4 — Action Engine: evidence_required
# ========================================

def _add_action_evidence_required_column(engine):
    """Add evidence_required BOOLEAN column to action_items if missing.

    Defaults to 0 (False). Idempotent — skips if column already exists.
    """
    insp = inspect(engine)
    if not insp.has_table("action_items"):
        return

    existing_cols = {c["name"] for c in insp.get_columns("action_items")}
    if "evidence_required" in existing_cols:
        logger.debug("migration: action_items.evidence_required already exists — skipping")
        return

    with engine.begin() as conn:
        conn.execute(text(
            'ALTER TABLE "action_items" ADD COLUMN "evidence_required" BOOLEAN NOT NULL DEFAULT 0'
        ))
        logger.info("migration: added action_items.evidence_required")


# ========================================
# Fix delivery_points energy_type enum case
# ========================================

def _fix_delivery_point_energy_type_case(engine):
    """Fix enum values in delivery_points: SQLAlchemy Enum stores names (ELEC/GAZ/ACTIVE),
    not values (elec/gaz/active).

    The _backfill_delivery_points and _create_delivery_points_table migrations previously
    wrote lowercase values.  Idempotent — only updates rows with lowercase values.
    """
    insp = inspect(engine)
    if not insp.has_table("delivery_points"):
        return

    fixes = [
        ("energy_type", [("elec", "ELEC"), ("gaz", "GAZ")]),
        ("status", [("active", "ACTIVE"), ("inactive", "INACTIVE")]),
    ]

    with engine.begin() as conn:
        fixed = 0
        for col, mappings in fixes:
            for old, new in mappings:
                result = conn.execute(text(
                    f'UPDATE "delivery_points" SET "{col}" = :new WHERE "{col}" = :old'
                ), {"old": old, "new": new})
                fixed += result.rowcount

    if fixed > 0:
        logger.info("migration: fixed %d delivery_points enum values (lowercase → uppercase)", fixed)
    else:
        logger.debug("migration: delivery_points enum values already correct — no changes")


# ========================================
# Backfill risque_financier_euro from obligations
# ========================================

def _backfill_site_risque_financier(engine):
    """Compute risque_financier_euro for sites based on their obligations.

    NON_CONFORME → BASE_PENALTY_EURO (7500 €)
    A_RISQUE     → BASE_PENALTY_EURO * 0.5 (3750 €)
    Idempotent: only updates sites where current value is 0 but obligations warrant risk.
    """
    insp = inspect(engine)
    if not insp.has_table("sites") or not insp.has_table("obligations"):
        return

    with engine.begin() as conn:
        # Get sites with risque_financier_euro = 0 (or NULL) that have non-conforme/a_risque obligations
        rows = conn.execute(text("""
            SELECT s.id,
                   COALESCE(SUM(CASE WHEN o.statut IN ('NON_CONFORME', 'non_conforme') THEN 7500.0 ELSE 0 END), 0)
                   + COALESCE(SUM(CASE WHEN o.statut IN ('A_RISQUE', 'a_risque') THEN 3750.0 ELSE 0 END), 0)
                   AS risque
            FROM sites s
            LEFT JOIN obligations o ON o.site_id = s.id
            WHERE COALESCE(s.risque_financier_euro, 0) = 0
            GROUP BY s.id
            HAVING risque > 0
        """)).fetchall()

        updated = 0
        for row in rows:
            conn.execute(text(
                'UPDATE sites SET risque_financier_euro = :risque WHERE id = :sid'
            ), {"risque": row[1], "sid": row[0]})
            updated += 1

        if updated > 0:
            logger.info("migration: backfilled risque_financier_euro for %d sites", updated)
        else:
            logger.debug("migration: risque_financier_euro already correct — no changes")


# ========================================
# V96 — Patrimoine Unique Monde
# ========================================

def _create_payment_rules_table(engine):
    """V96: Create payment_rules table if it does not exist. Idempotent."""
    insp = inspect(engine)
    if insp.has_table("payment_rules"):
        logger.debug("migration: payment_rules table already exists — skipping")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "payment_rules" (
                "id" INTEGER PRIMARY KEY,
                "level" VARCHAR(20) NOT NULL,
                "portefeuille_id" INTEGER REFERENCES "portefeuilles"("id"),
                "site_id" INTEGER REFERENCES "sites"("id"),
                "contract_id" INTEGER REFERENCES "energy_contracts"("id"),
                "invoice_entity_id" INTEGER NOT NULL REFERENCES "entites_juridiques"("id"),
                "payer_entity_id" INTEGER REFERENCES "entites_juridiques"("id"),
                "cost_center" VARCHAR(100),
                "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE("level", "portefeuille_id", "site_id", "contract_id")
            )
        """))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS "ix_payment_rules_portefeuille_id" '
            'ON "payment_rules" ("portefeuille_id")'
        ))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS "ix_payment_rules_site_id" '
            'ON "payment_rules" ("site_id")'
        ))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS "ix_payment_rules_contract_id" '
            'ON "payment_rules" ("contract_id")'
        ))
    logger.info("migration: created payment_rules table with indexes")


def _add_contract_v96_columns(engine):
    """V96: Add offer_indexation, price_granularity, renewal_alert_days, contract_status
    to energy_contracts. Idempotent — skips existing columns."""
    insp = inspect(engine)
    if not insp.has_table("energy_contracts"):
        return

    existing_cols = {c["name"] for c in insp.get_columns("energy_contracts")}

    v96_columns = [
        ("offer_indexation", "VARCHAR(20)"),
        ("price_granularity", "VARCHAR(50)"),
        ("renewal_alert_days", "INTEGER"),
        ("contract_status", "VARCHAR(20)"),
    ]

    added = 0
    with engine.begin() as conn:
        for col_name, col_type in v96_columns:
            if col_name in existing_cols:
                continue
            conn.execute(text(
                f'ALTER TABLE "energy_contracts" ADD COLUMN "{col_name}" {col_type}'
            ))
            added += 1
            logger.info("migration: added energy_contracts.%s (%s)", col_name, col_type)

    if added > 0:
        logger.info("migration: V96 — added %d column(s) to energy_contracts", added)
    else:
        logger.debug("migration: V96 energy_contracts columns already present — no changes")
