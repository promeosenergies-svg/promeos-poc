"""
PROMEOS - Safe schema migrations (no Alembic).
Adds missing columns/tables to existing schema without dropping anything.
SQLite supports ALTER TABLE ADD COLUMN for nullable columns.
"""

import logging
from sqlalchemy import inspect, text

from config.emission_factors import BASE_PENALTY_EURO, A_RISQUE_PENALTY_EURO

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
    # V101 — Add frequency to meter_reading unique constraint
    _upgrade_meter_reading_unique_constraint(engine)
    # Étape 4 — Action Engine: evidence_required column
    _add_action_evidence_required_column(engine)
    # Fix delivery_points energy_type enum case (elec→ELEC, gaz→GAZ)
    _fix_delivery_point_energy_type_case(engine)
    # Backfill risque_financier_euro from obligations
    _backfill_site_risque_financier(engine)
    # V96 — Patrimoine Unique Monde
    _create_payment_rules_table(engine)
    _add_contract_v96_columns(engine)
    # V97 — Resolution Engine
    _create_reconciliation_fix_logs_table(engine)
    # V100 — Segmentation enrichment
    _migrate_segmentation_v100(engine)
    # Step 25 — Meter unification (Compteur → Meter)
    _add_meter_unified_columns(engine)
    # Step 26 — Geocoding columns on sites
    _add_site_geocoding_columns(engine)
    # V1.1 Usage — usage_id FK + usage enrichment + usage_baselines table
    _migrate_usage_v1_1(engine)
    # Soft-delete coherence — sync actif/deleted_at on dual-field tables
    _sync_soft_delete_coherence(engine)
    # OPERAT trajectory — EFA consumption table + trajectory columns
    _migrate_operat_trajectory(engine)
    # Compliance event log — audit trail
    _migrate_compliance_event_log(engine)
    # BACS hardening
    _migrate_bacs_hardening(engine)
    # BACS regulatory tables
    _migrate_bacs_regulatory(engine)
    # BACS remediation actions
    _migrate_bacs_remediation(engine)
    # Export manifest — chaine de preuve export
    _migrate_operat_export_manifest(engine)
    # Enedis SGE — CDC staging tables
    _rename_enedis_mesure_table(engine)
    _create_enedis_tables(engine)
    _add_enedis_columns(engine)
    # TURPE 7 / HC reprog — delivery_points enrichment
    _add_delivery_point_turpe_columns(engine)
    # P1: FK delivery_points → tou_schedules
    _add_delivery_point_tou_schedule_fk(engine)
    # Audit Energetique / SME (Loi 2025-391)
    _create_audit_energetique_table(engine)
    # V2 Contrats Cadre+Annexe
    _migrate_contracts_v2(engine)
    # APER couverture partielle — champ coverage_pct sur evidences
    _add_evidence_coverage_pct_column(engine)
    # Sprint F — ConnectorToken (OAuth2 tokens for Enedis/GRDF)
    _create_connector_tokens_table(engine)
    # Phase 1 V2 — ContratCadre table + NUMERIC columns on contract_annexes
    _migrate_phase1_contrats_cadre(engine)
    # Phase 5 V2 — energy_invoices.annexe_site_id for cadre-aware shadow billing
    _migrate_phase5_invoice_annexe_site(engine)
    # Sprint 1 CDC — Enedis Open Data benchmark tables
    _create_enedis_opendata_tables(engine)
    # Sprint 3 SF5 — Promotion pipeline tables
    _create_sf5_promotion_tables(engine)
    # Referentiel Sirene — tables isolees (DIAMANT)
    _create_sirene_tables(engine)
    # Market Intelligence — articles & indicateurs veille marché (EuropEnergies)
    _create_market_intelligence_tables(engine)


def _create_market_intelligence_tables(engine):
    """Create market_articles and market_indicators tables if missing (idempotent)."""
    MI_TABLES = ("market_articles", "market_indicators")
    insp = inspect(engine)
    missing = [t for t in MI_TABLES if not insp.has_table(t)]
    if not missing:
        return
    import models.market_article  # noqa: F401
    import models.market_indicator  # noqa: F401
    from models.base import Base

    Base.metadata.create_all(
        bind=engine,
        tables=[Base.metadata.tables[t] for t in MI_TABLES if t in Base.metadata.tables],
        checkfirst=True,
    )
    logger.info("migration: created Market Intelligence tables: %s", missing)


def _create_sirene_tables(engine):
    """Create Sirene reference tables if missing (idempotent)."""
    SIRENE_TABLES = (
        "sirene_unites_legales",
        "sirene_etablissements",
        "sirene_doublons",
        "sirene_sync_runs",
        "customer_creation_traces",
    )
    insp = inspect(engine)
    missing = [t for t in SIRENE_TABLES if not insp.has_table(t)]
    if not missing:
        return
    import models.sirene  # noqa: F401
    from models.base import Base

    Base.metadata.create_all(
        bind=engine,
        tables=[Base.metadata.tables[t] for t in SIRENE_TABLES if t in Base.metadata.tables],
        checkfirst=True,
    )
    logger.info("migration: created Sirene reference tables: %s", missing)


def _create_sf5_promotion_tables(engine):
    """Create SF5 promotion pipeline tables if missing."""
    from data_staging.models import SF5_TABLES

    insp = inspect(engine)
    missing = [t for t in SF5_TABLES if not insp.has_table(t)]
    if missing:
        import data_staging.models  # noqa: F401
        from models.base import Base

        Base.metadata.create_all(
            bind=engine,
            tables=[Base.metadata.tables[t] for t in SF5_TABLES if t in Base.metadata.tables],
            checkfirst=True,
        )
        logger.info("migration: created SF5 promotion tables: %s", missing)


def _create_enedis_opendata_tables(engine):
    """Create Enedis Open Data benchmark tables if missing."""
    tables = ("enedis_opendata_conso_sup36", "enedis_opendata_conso_inf36")
    insp = inspect(engine)
    missing = [t for t in tables if not insp.has_table(t)]
    if missing:
        import models.enedis_opendata  # noqa: F401
        from models.base import Base

        Base.metadata.create_all(
            bind=engine,
            tables=[Base.metadata.tables[t] for t in tables if t in Base.metadata.tables],
            checkfirst=True,
        )
        logger.info("migration: created Enedis Open Data tables: %s", missing)


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
                    conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" ("deleted_at")'))
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
            conn.execute(
                text(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                    f'ON "compteurs" ("meter_id") '
                    f'WHERE "meter_id" IS NOT NULL AND "deleted_at" IS NULL'
                )
            )
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
        conn.execute(
            text("""
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
        """)
        )
        conn.execute(text('CREATE INDEX IF NOT EXISTS "ix_delivery_points_code" ON "delivery_points" ("code")'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS "ix_delivery_points_site_id" ON "delivery_points" ("site_id")'))
        conn.execute(
            text('CREATE INDEX IF NOT EXISTS "ix_delivery_points_deleted_at" ON "delivery_points" ("deleted_at")')
        )
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
        conn.execute(
            text('ALTER TABLE "compteurs" ADD COLUMN "delivery_point_id" INTEGER REFERENCES "delivery_points"("id")')
        )
        conn.execute(
            text('CREATE INDEX IF NOT EXISTS "ix_compteurs_delivery_point_id" ON "compteurs" ("delivery_point_id")')
        )
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
        rows = conn.execute(
            text("""
            SELECT c.id, c.meter_id, c.site_id, c.type, c.data_source, c.data_source_ref
            FROM compteurs c
            WHERE c.meter_id IS NOT NULL
              AND c.meter_id != ''
              AND c.deleted_at IS NULL
              AND c.delivery_point_id IS NULL
            ORDER BY c.site_id, c.meter_id
        """)
        ).fetchall()

        if not rows:
            logger.debug("migration: backfill — no unlinked compteurs with meter_id")
            return

        created = 0
        linked = 0

        for row in rows:
            cpt_id, meter_id, site_id, cpt_type, data_source, data_source_ref = row

            # Check if a DeliveryPoint already exists for this code + site (active)
            existing = conn.execute(
                text("""
                SELECT id FROM delivery_points
                WHERE code = :code AND site_id = :site_id AND deleted_at IS NULL
                LIMIT 1
            """),
                {"code": meter_id, "site_id": site_id},
            ).fetchone()

            if existing:
                dp_id = existing[0]
            else:
                # Auto-detect energy_type from compteur type
                energy_type = _guess_energy_type(cpt_type)
                conn.execute(
                    text("""
                    INSERT INTO delivery_points (code, energy_type, site_id, status,
                        data_source, data_source_ref, created_at, updated_at)
                    VALUES (:code, :energy_type, :site_id, 'active',
                        :data_source, :data_source_ref, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """),
                    {
                        "code": meter_id,
                        "energy_type": energy_type,
                        "site_id": site_id,
                        "data_source": data_source or "backfill",
                        "data_source_ref": data_source_ref or "migration_backfill",
                    },
                )
                dp_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
                created += 1

            # Link compteur to delivery_point
            conn.execute(
                text("""
                UPDATE compteurs SET delivery_point_id = :dp_id WHERE id = :cpt_id
            """),
                {"dp_id": dp_id, "cpt_id": cpt_id},
            )
            linked += 1

        logger.info(
            "migration: backfill — created %d delivery_points, linked %d compteurs",
            created,
            linked,
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
            conn.execute(
                text(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                    f'ON "delivery_points" ("code") '
                    f'WHERE "code" IS NOT NULL AND "deleted_at" IS NULL'
                )
            )
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
            conn.execute(
                text(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                    f'ON "organisations" ("siren") '
                    f'WHERE "siren" IS NOT NULL AND "deleted_at" IS NULL'
                )
            )
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
            conn.execute(
                text(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                    f'ON "portefeuilles" ("entite_juridique_id", "nom") '
                    f'WHERE "deleted_at" IS NULL'
                )
            )
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
            conn.execute(
                text(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                    f'ON "sites" ("portefeuille_id", "siret") '
                    f'WHERE "siret" IS NOT NULL AND "deleted_at" IS NULL'
                )
            )
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
            conn.execute(
                text(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" '
                    f'ON "batiments" ("site_id", "nom") '
                    f'WHERE "deleted_at" IS NULL'
                )
            )
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
        row = conn.execute(
            text("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name=:name"), {"name": trigger_name}
        ).scalar()
        if row and row > 0:
            return
        try:
            conn.execute(
                text(f"""
                CREATE TRIGGER "{trigger_name}"
                BEFORE DELETE ON "delivery_points"
                FOR EACH ROW
                BEGIN
                    UPDATE "compteurs"
                    SET "delivery_point_id" = NULL
                    WHERE "delivery_point_id" = OLD."id";
                END
            """)
            )
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
    """Remove duplicate (meter_id, timestamp, frequency) rows from meter_reading.

    Strategy: keep the row with the best quality_score, ties broken by most
    recent created_at, then highest id.  Idempotent — skips if no duplicates.
    """
    insp = inspect(engine)
    if not insp.has_table("meter_reading"):
        return

    with engine.begin() as conn:
        dupes = conn.execute(
            text("""
            SELECT meter_id, timestamp, frequency, COUNT(*) AS cnt
            FROM meter_reading
            GROUP BY meter_id, timestamp, frequency
            HAVING cnt > 1
        """)
        ).fetchall()

        if not dupes:
            logger.debug("migration: meter_reading — no duplicates found")
            return

        deleted = 0
        for meter_id, ts, freq, cnt in dupes:
            # Keep the best row (highest quality_score, then latest created_at, then highest id)
            keep = conn.execute(
                text("""
                SELECT id FROM meter_reading
                WHERE meter_id = :mid AND timestamp = :ts AND frequency = :freq
                ORDER BY
                    COALESCE(quality_score, -1) DESC,
                    COALESCE(created_at, '1970-01-01') DESC,
                    id DESC
                LIMIT 1
            """),
                {"mid": meter_id, "ts": ts, "freq": freq},
            ).scalar()

            if keep:
                result = conn.execute(
                    text("""
                    DELETE FROM meter_reading
                    WHERE meter_id = :mid AND timestamp = :ts AND frequency = :freq AND id != :keep_id
                """),
                    {"mid": meter_id, "ts": ts, "freq": freq, "keep_id": keep},
                )
                deleted += result.rowcount

        logger.info("migration: meter_reading dedup — removed %d duplicate rows from %d triplets", deleted, len(dupes))


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
            conn.execute(
                text(f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" ON "meter_reading" ("meter_id", "timestamp")')
            )
            logger.info("migration: created unique index %s", idx_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", idx_name, e)


def _upgrade_meter_reading_unique_constraint(engine):
    """Replace (meter_id, timestamp) unique index with (meter_id, timestamp, frequency).

    Different frequencies at the same timestamp are semantically distinct readings.
    Without this, 15-min :00 slots collide with hourly readings causing silent data loss.
    """
    old_name = "uq_meter_reading_meter_ts"
    new_name = "uq_meter_reading_meter_ts_freq"
    insp = inspect(engine)

    if not insp.has_table("meter_reading"):
        return

    existing = {idx["name"] for idx in insp.get_indexes("meter_reading") if idx.get("name")}

    # Always drop the old constraint if it exists (even if new one already
    # exists from create_all — both can coexist and the old one still blocks)
    if old_name in existing:
        with engine.begin() as conn:
            try:
                conn.execute(text(f'DROP INDEX IF EXISTS "{old_name}"'))
                logger.info("migration: dropped old index %s", old_name)
            except Exception as e:
                logger.warning("migration: could not drop index %s: %s", old_name, e)

    if new_name in existing:
        return  # new constraint already exists

    with engine.begin() as conn:
        try:
            conn.execute(
                text(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "{new_name}" '
                    f'ON "meter_reading" ("meter_id", "timestamp", "frequency")'
                )
            )
            logger.info("migration: created unique index %s", new_name)
        except Exception as e:
            logger.warning("migration: could not create index %s: %s", new_name, e)


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
        conn.execute(text('ALTER TABLE "action_items" ADD COLUMN "evidence_required" BOOLEAN NOT NULL DEFAULT 0'))
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
                result = conn.execute(
                    text(f'UPDATE "delivery_points" SET "{col}" = :new WHERE "{col}" = :old'), {"old": old, "new": new}
                )
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

    NON_CONFORME → BASE_PENALTY_EURO
    A_RISQUE     → A_RISQUE_PENALTY_EURO
    Idempotent: only updates sites where current value is 0 but obligations warrant risk.
    """
    insp = inspect(engine)
    if not insp.has_table("sites") or not insp.has_table("obligations"):
        return

    with engine.begin() as conn:
        # Get sites with risque_financier_euro = 0 (or NULL) that have non-conforme/a_risque obligations
        penalty = BASE_PENALTY_EURO
        half_penalty = A_RISQUE_PENALTY_EURO
        rows = conn.execute(
            text(f"""
            SELECT s.id,
                   COALESCE(SUM(CASE WHEN o.statut IN ('NON_CONFORME', 'non_conforme') THEN {penalty} ELSE 0 END), 0)
                   + COALESCE(SUM(CASE WHEN o.statut IN ('A_RISQUE', 'a_risque') THEN {half_penalty} ELSE 0 END), 0)
                   AS risque
            FROM sites s
            LEFT JOIN obligations o ON o.site_id = s.id
            WHERE COALESCE(s.risque_financier_euro, 0) = 0
            GROUP BY s.id
            HAVING risque > 0
        """)
        ).fetchall()

        updated = 0
        for row in rows:
            conn.execute(
                text("UPDATE sites SET risque_financier_euro = :risque WHERE id = :sid"),
                {"risque": row[1], "sid": row[0]},
            )
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
        conn.execute(
            text("""
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
        """)
        )
        conn.execute(
            text('CREATE INDEX IF NOT EXISTS "ix_payment_rules_portefeuille_id" ON "payment_rules" ("portefeuille_id")')
        )
        conn.execute(text('CREATE INDEX IF NOT EXISTS "ix_payment_rules_site_id" ON "payment_rules" ("site_id")'))
        conn.execute(
            text('CREATE INDEX IF NOT EXISTS "ix_payment_rules_contract_id" ON "payment_rules" ("contract_id")')
        )
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
            conn.execute(text(f'ALTER TABLE "energy_contracts" ADD COLUMN "{col_name}" {col_type}'))
            added += 1
            logger.info("migration: added energy_contracts.%s (%s)", col_name, col_type)

    if added > 0:
        logger.info("migration: V96 — added %d column(s) to energy_contracts", added)
    else:
        logger.debug("migration: V96 energy_contracts columns already present — no changes")


# ========================================
# V97 — Resolution Engine
# ========================================


def _create_reconciliation_fix_logs_table(engine):
    """V97: Create reconciliation_fix_logs table for audit trail. Idempotent."""
    insp = inspect(engine)
    if insp.has_table("reconciliation_fix_logs"):
        logger.debug("migration: reconciliation_fix_logs table already exists — skipping")
        return

    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS "reconciliation_fix_logs" (
                "id" INTEGER PRIMARY KEY,
                "site_id" INTEGER NOT NULL REFERENCES "sites"("id"),
                "check_id" VARCHAR(50) NOT NULL,
                "action" VARCHAR(100) NOT NULL,
                "status_before" VARCHAR(20) NOT NULL,
                "status_after" VARCHAR(20) NOT NULL,
                "detail_json" TEXT,
                "applied_by" VARCHAR(200),
                "applied_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )
        conn.execute(
            text('CREATE INDEX IF NOT EXISTS "ix_recon_fix_logs_site_id" ON "reconciliation_fix_logs" ("site_id")')
        )
        conn.execute(
            text('CREATE INDEX IF NOT EXISTS "ix_recon_fix_logs_check_id" ON "reconciliation_fix_logs" ("check_id")')
        )
    logger.info("migration: created reconciliation_fix_logs table with indexes")


# ========================================
# V100 — Segmentation enrichment
# ========================================


def _migrate_segmentation_v100(engine):
    """V100: Add missing columns to segmentation_profiles + create segmentation_answers table.

    Idempotent — skips existing columns/tables.
    """
    insp = inspect(engine)

    # 1. Create segmentation_profiles table if it doesn't exist at all
    if not insp.has_table("segmentation_profiles"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "segmentation_profiles" (
                    "id" INTEGER PRIMARY KEY,
                    "organisation_id" INTEGER NOT NULL REFERENCES "organisations"("id"),
                    "portfolio_id" INTEGER REFERENCES "portefeuilles"("id"),
                    "typologie" VARCHAR(50) NOT NULL,
                    "segment_label" VARCHAR(100),
                    "naf_code" VARCHAR(10),
                    "confidence_score" REAL NOT NULL DEFAULT 0.0,
                    "derived_from" VARCHAR(30) DEFAULT 'mix',
                    "answers_json" TEXT,
                    "reasons_json" TEXT,
                    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_segmentation_profiles_org_id" '
                    'ON "segmentation_profiles" ("organisation_id")'
                )
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_segmentation_profiles_portfolio_id" '
                    'ON "segmentation_profiles" ("portfolio_id")'
                )
            )
        logger.info("migration: V100 — created segmentation_profiles table")
    else:
        # Add V100 columns if missing
        existing_cols = {c["name"] for c in insp.get_columns("segmentation_profiles")}
        v100_columns = [
            ("portfolio_id", 'INTEGER REFERENCES "portefeuilles"("id")'),
            ("segment_label", "VARCHAR(100)"),
            ("derived_from", "VARCHAR(30) DEFAULT 'mix'"),
        ]
        added = 0
        with engine.begin() as conn:
            for col_name, col_type in v100_columns:
                if col_name in existing_cols:
                    continue
                conn.execute(text(f'ALTER TABLE "segmentation_profiles" ADD COLUMN "{col_name}" {col_type}'))
                added += 1
                logger.info("migration: V100 — added segmentation_profiles.%s", col_name)
        if added > 0:
            logger.info("migration: V100 — added %d column(s) to segmentation_profiles", added)

    # 2. Create segmentation_answers table if it doesn't exist
    if not insp.has_table("segmentation_answers"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "segmentation_answers" (
                    "id" INTEGER PRIMARY KEY,
                    "profile_id" INTEGER NOT NULL REFERENCES "segmentation_profiles"("id"),
                    "organisation_id" INTEGER NOT NULL REFERENCES "organisations"("id"),
                    "portfolio_id" INTEGER REFERENCES "portefeuilles"("id"),
                    "question_id" VARCHAR(50) NOT NULL,
                    "answer_value" VARCHAR(100) NOT NULL,
                    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_segmentation_answers_profile_id" '
                    'ON "segmentation_answers" ("profile_id")'
                )
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_segmentation_answers_org_id" '
                    'ON "segmentation_answers" ("organisation_id")'
                )
            )
        logger.info("migration: V100 — created segmentation_answers table")


# ========================================
# Step 25 — Meter unification
# ========================================


def _add_meter_unified_columns(engine):
    """Step 25: Add columns to meter table for Compteur unification. Idempotent."""
    insp = inspect(engine)
    if not insp.has_table("meter"):
        return

    existing_cols = {c["name"] for c in insp.get_columns("meter")}

    columns = [
        ("numero_serie", "VARCHAR(100)"),
        ("type_compteur", "VARCHAR(50)"),
        ("marque", "VARCHAR(100)"),
        ("modele", "VARCHAR(100)"),
        ("date_derniere_releve", "DATETIME"),
        ("delivery_point_id", 'INTEGER REFERENCES "delivery_points"("id")'),
        ("parent_meter_id", 'INTEGER REFERENCES "meter"("id")'),
    ]

    added = 0
    with engine.begin() as conn:
        for col_name, col_type in columns:
            if col_name in existing_cols:
                continue
            try:
                conn.execute(text(f'ALTER TABLE "meter" ADD COLUMN "{col_name}" {col_type}'))
                added += 1
                logger.info("migration: Step 25 — added meter.%s (%s)", col_name, col_type)
            except Exception as e:
                logger.warning("migration: Step 25 — could not add meter.%s: %s", col_name, e)

        # Indexes
        for idx_col in ("numero_serie", "delivery_point_id", "parent_meter_id"):
            idx_name = f"ix_meter_{idx_col}"
            try:
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "meter" ("{idx_col}")'))
            except Exception:
                pass

    if added > 0:
        logger.info("migration: Step 25 — added %d column(s) to meter", added)
    else:
        logger.debug("migration: Step 25 — meter unified columns already present")


def _add_site_geocoding_columns(engine):
    """Step 26 — Add geocoding columns to sites for BAN geocoding persistence."""
    insp = inspect(engine)
    if not insp.has_table("sites"):
        return

    existing_cols = {c["name"] for c in insp.get_columns("sites")}
    columns = [
        ("geocoding_source", "VARCHAR(50)"),
        ("geocoding_score", "FLOAT"),
        ("geocoded_at", "DATETIME"),
        ("geocoding_status", "VARCHAR(20)"),
    ]

    added = 0
    with engine.begin() as conn:
        for col_name, col_type in columns:
            if col_name in existing_cols:
                continue
            try:
                conn.execute(text(f'ALTER TABLE "sites" ADD COLUMN "{col_name}" {col_type}'))
                added += 1
                logger.info("migration: Step 26 — added sites.%s (%s)", col_name, col_type)
            except Exception as e:
                logger.warning("migration: Step 26 — could not add sites.%s: %s", col_name, e)

    if added > 0:
        logger.info("migration: Step 26 — added %d geocoding column(s) to sites", added)
    else:
        logger.debug("migration: Step 26 — sites geocoding columns already present")


def _migrate_usage_v1_1(engine):
    """V1.1 Usage — Ajouter usage_id FK sur meter/recommendation/bacs_cvc_systems,
    enrichir la table usages, creer usage_baselines."""
    insp = inspect(engine)

    # 1. Ajouter usage_id sur les tables existantes
    _usage_v1_1_columns = {
        "meter": [("usage_id", "INTEGER")],
        "recommendation": [("usage_id", "INTEGER")],
        "bacs_cvc_systems": [("usage_id", "INTEGER")],
        "consumption_insights": [("usage_id", "INTEGER")],
        "usages": [
            ("label", "VARCHAR(200)"),
            ("surface_m2", "FLOAT"),
            ("data_source", "VARCHAR(50)"),
            ("is_significant", "BOOLEAN DEFAULT 0"),
            ("pct_of_total", "FLOAT"),
        ],
    }

    added = 0
    with engine.begin() as conn:
        for table_name, columns in _usage_v1_1_columns.items():
            if not insp.has_table(table_name):
                logger.debug("migration: V1.1 Usage — table %s not found, skip", table_name)
                continue
            existing_cols = {c["name"] for c in insp.get_columns(table_name)}
            for col_name, col_type in columns:
                if col_name in existing_cols:
                    continue
                try:
                    conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}'))
                    added += 1
                    logger.info("migration: V1.1 Usage — added %s.%s (%s)", table_name, col_name, col_type)
                except Exception as e:
                    logger.warning("migration: V1.1 Usage — could not add %s.%s: %s", table_name, col_name, e)

    # 2. Creer la table usage_baselines si elle n'existe pas
    if not insp.has_table("usage_baselines"):
        ddl = """
        CREATE TABLE usage_baselines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usage_id INTEGER NOT NULL REFERENCES usages(id),
            period_start DATETIME NOT NULL,
            period_end DATETIME NOT NULL,
            kwh_total FLOAT NOT NULL,
            kwh_m2_year FLOAT,
            peak_kw FLOAT,
            data_source VARCHAR(50),
            confidence FLOAT,
            notes VARCHAR(500),
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        with engine.begin() as conn:
            conn.execute(text(ddl))
            conn.execute(text("CREATE INDEX ix_usage_baselines_usage_id ON usage_baselines(usage_id)"))
        logger.info("migration: V1.1 Usage — created table usage_baselines")
        added += 1

    if added > 0:
        logger.info("migration: V1.1 Usage — %d change(s) applied", added)
    else:
        logger.debug("migration: V1.1 Usage — all columns/tables already present")


# ========================================
# Soft-delete coherence sync
# ========================================


def _sync_soft_delete_coherence(engine):
    """Sync actif/deleted_at on tables that have both fields.

    Fixes two inconsistent states:
    1. actif=0 BUT deleted_at IS NULL → set deleted_at = updated_at
    2. deleted_at IS NOT NULL BUT actif=1 → set actif=0
    Idempotent — no-op when data is already coherent.
    """
    DUAL_TABLES = ["organisations", "sites", "compteurs"]
    insp = inspect(engine)
    total_fixed = 0

    with engine.begin() as conn:
        for table in DUAL_TABLES:
            if not insp.has_table(table):
                continue
            cols = {c["name"] for c in insp.get_columns(table)}
            if "actif" not in cols or "deleted_at" not in cols:
                continue

            # Case 1: actif=0 but deleted_at is NULL
            r1 = conn.execute(
                text(f'UPDATE "{table}" SET deleted_at = updated_at WHERE actif = 0 AND deleted_at IS NULL')
            )
            # Case 2: deleted_at set but actif still 1
            r2 = conn.execute(text(f'UPDATE "{table}" SET actif = 0 WHERE deleted_at IS NOT NULL AND actif = 1'))
            fixed = r1.rowcount + r2.rowcount
            if fixed > 0:
                logger.info("migration: soft-delete sync — %s: %d row(s) fixed", table, fixed)
                total_fixed += fixed

    if total_fixed > 0:
        logger.info("migration: soft-delete coherence — %d total row(s) synced", total_fixed)
    else:
        logger.debug("migration: soft-delete coherence — already in sync")


# ========================================
# OPERAT trajectory — EFA consumption + trajectory columns
# ========================================


def _migrate_operat_trajectory(engine):
    """Create tertiaire_efa_consumption table + add trajectory columns to tertiaire_efa."""
    insp = inspect(engine)
    added = 0

    # 1. Create consumption table
    if not insp.has_table("tertiaire_efa_consumption"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "tertiaire_efa_consumption" (
                    "id" INTEGER PRIMARY KEY,
                    "efa_id" INTEGER NOT NULL REFERENCES "tertiaire_efa"("id") ON DELETE CASCADE,
                    "year" INTEGER NOT NULL,
                    "kwh_total" REAL NOT NULL,
                    "kwh_elec" REAL,
                    "kwh_gaz" REAL,
                    "kwh_reseau" REAL,
                    "is_reference" INTEGER NOT NULL DEFAULT 0,
                    "is_normalized" INTEGER NOT NULL DEFAULT 0,
                    "source" VARCHAR(50),
                    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "updated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE("efa_id", "year")
                )
            """)
            )
            conn.execute(
                text('CREATE INDEX IF NOT EXISTS "ix_efa_consumption_efa_id" ON "tertiaire_efa_consumption" ("efa_id")')
            )
        logger.info("migration: OPERAT — created tertiaire_efa_consumption table")
        added += 1

    # 2. Add trajectory columns to tertiaire_efa
    if insp.has_table("tertiaire_efa"):
        existing = {c["name"] for c in insp.get_columns("tertiaire_efa")}
        new_cols = [
            ("reference_year", "INTEGER"),
            ("reference_year_kwh", "REAL"),
            ("trajectory_status", "VARCHAR(20)"),
            ("trajectory_last_calculated_at", "DATETIME"),
            ("baseline_normalization_status", "VARCHAR(20)"),
            ("baseline_normalization_reason", "VARCHAR(200)"),
        ]
        with engine.begin() as conn:
            for col_name, col_type in new_cols:
                if col_name not in existing:
                    conn.execute(text(f'ALTER TABLE "tertiaire_efa" ADD COLUMN "{col_name}" {col_type}'))
                    logger.info("migration: OPERAT — added tertiaire_efa.%s", col_name)
                    added += 1

    if added == 0:
        logger.debug("migration: OPERAT trajectory — already up to date")

    # 3. Add reliability + normalization columns to consumption table
    if insp.has_table("tertiaire_efa_consumption"):
        existing = {c["name"] for c in insp.get_columns("tertiaire_efa_consumption")}
        norm_cols = [
            ("reliability", "VARCHAR(20) DEFAULT 'unverified'"),
            ("normalized_kwh_total", "REAL"),
            ("normalization_method", "VARCHAR(50)"),
            ("normalization_confidence", "VARCHAR(20)"),
            ("dju_heating", "REAL"),
            ("dju_cooling", "REAL"),
            ("dju_reference", "REAL"),
            ("weather_data_source", "VARCHAR(100)"),
            ("normalized_at", "DATETIME"),
        ]
        with engine.begin() as conn:
            for col_name, col_type in norm_cols:
                if col_name not in existing:
                    conn.execute(text(f'ALTER TABLE "tertiaire_efa_consumption" ADD COLUMN "{col_name}" {col_type}'))
                    logger.info("migration: OPERAT — added tertiaire_efa_consumption.%s", col_name)
            logger.info("migration: OPERAT — added tertiaire_efa_consumption.reliability")


def _migrate_compliance_event_log(engine):
    """Create compliance_event_log table for audit trail."""
    insp = inspect(engine)
    if not insp.has_table("compliance_event_log"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "compliance_event_log" (
                    "id" INTEGER PRIMARY KEY,
                    "entity_type" VARCHAR(100) NOT NULL,
                    "entity_id" INTEGER NOT NULL,
                    "action" VARCHAR(50) NOT NULL,
                    "before_json" TEXT,
                    "after_json" TEXT,
                    "actor" VARCHAR(200) NOT NULL DEFAULT 'system',
                    "source_context" VARCHAR(200),
                    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_compliance_event_entity" '
                    'ON "compliance_event_log" ("entity_type", "entity_id")'
                )
            )
        logger.info("migration: created compliance_event_log table")


def _migrate_operat_export_manifest(engine):
    """Create operat_export_manifest table."""
    insp = inspect(engine)
    if not insp.has_table("operat_export_manifest"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "operat_export_manifest" (
                    "id" INTEGER PRIMARY KEY,
                    "efa_id" INTEGER,
                    "org_id" INTEGER NOT NULL,
                    "generated_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "actor" VARCHAR(200) NOT NULL DEFAULT 'system',
                    "file_name" VARCHAR(500) NOT NULL,
                    "checksum_sha256" VARCHAR(64) NOT NULL,
                    "observation_year" INTEGER NOT NULL,
                    "baseline_year" INTEGER,
                    "baseline_kwh" REAL,
                    "current_kwh" REAL,
                    "baseline_source" VARCHAR(50),
                    "current_source" VARCHAR(50),
                    "baseline_reliability" VARCHAR(20),
                    "current_reliability" VARCHAR(20),
                    "trajectory_status" VARCHAR(20),
                    "efa_count" INTEGER,
                    "evidence_warnings_json" TEXT,
                    "export_version" VARCHAR(20) NOT NULL DEFAULT '1.0'
                )
            """)
            )
            conn.execute(
                text('CREATE INDEX IF NOT EXISTS "ix_export_manifest_org" ON "operat_export_manifest" ("org_id")')
            )
        logger.info("migration: created operat_export_manifest table")

    # Add hardening columns
    if insp.has_table("operat_export_manifest"):
        existing = {c["name"] for c in insp.get_columns("operat_export_manifest")}
        hardening_cols = [
            ("retention_until", "DATETIME"),
            ("archive_status", "VARCHAR(20) DEFAULT 'active'"),
            ("weather_provider", "VARCHAR(100)"),
            ("baseline_normalization_status", "VARCHAR(20)"),
            ("promeos_version", "VARCHAR(20) DEFAULT '2.0'"),
        ]
        with engine.begin() as conn:
            for col_name, col_type in hardening_cols:
                if col_name not in existing:
                    conn.execute(text(f'ALTER TABLE "operat_export_manifest" ADD COLUMN "{col_name}" {col_type}'))
                    logger.info("migration: hardening — added operat_export_manifest.%s", col_name)


def _migrate_bacs_hardening(engine):
    """Add BACS hardening columns to existing tables."""
    insp = inspect(engine)

    # bacs_assets : scope status + soft-delete
    if insp.has_table("bacs_assets"):
        existing = {c["name"] for c in insp.get_columns("bacs_assets")}
        cols = [
            ("bacs_scope_status", "VARCHAR(30)"),
            ("bacs_scope_reason", "VARCHAR(200)"),
            ("deleted_at", "DATETIME"),
            ("deleted_by", "VARCHAR(100)"),
            ("delete_reason", "VARCHAR(200)"),
        ]
        with engine.begin() as conn:
            for col, typ in cols:
                if col not in existing:
                    conn.execute(text(f'ALTER TABLE "bacs_assets" ADD COLUMN "{col}" {typ}'))
                    logger.info("migration: BACS — added bacs_assets.%s", col)

    # bacs_cvc_systems : classe + performance
    if insp.has_table("bacs_cvc_systems"):
        existing = {c["name"] for c in insp.get_columns("bacs_cvc_systems")}
        cols = [
            ("system_class", "VARCHAR(1)"),
            ("system_class_source", "VARCHAR(50)"),
            ("system_class_verified", "INTEGER DEFAULT 0"),
            ("performance_baseline_kwh", "REAL"),
            ("efficiency_loss_threshold_pct", "REAL DEFAULT 10.0"),
        ]
        with engine.begin() as conn:
            for col, typ in cols:
                if col not in existing:
                    conn.execute(text(f'ALTER TABLE "bacs_cvc_systems" ADD COLUMN "{col}" {typ}'))
                    logger.info("migration: BACS — added bacs_cvc_systems.%s", col)

    # bacs_inspections : findings + inspecteur
    if insp.has_table("bacs_inspections"):
        existing = {c["name"] for c in insp.get_columns("bacs_inspections")}
        cols = [
            ("inspector_name", "VARCHAR(200)"),
            ("inspector_qualification", "VARCHAR(100)"),
            ("findings_json", "TEXT"),
            ("findings_count", "INTEGER DEFAULT 0"),
            ("critical_findings_count", "INTEGER DEFAULT 0"),
            ("system_class_observed", "VARCHAR(1)"),
        ]
        with engine.begin() as conn:
            for col, typ in cols:
                if col not in existing:
                    conn.execute(text(f'ALTER TABLE "bacs_inspections" ADD COLUMN "{col}" {typ}'))
                    logger.info("migration: BACS — added bacs_inspections.%s", col)

    # Inspection regulatory columns
    if insp.has_table("bacs_inspections"):
        existing = {c["name"] for c in insp.get_columns("bacs_inspections")}
        reg_cols = [
            ("inspection_type", "VARCHAR(20)"),
            ("report_delivered_at", "DATE"),
            ("report_retention_until", "DATE"),
            ("settings_evaluated", "INTEGER DEFAULT 0"),
            ("functional_analysis_done", "INTEGER DEFAULT 0"),
            ("recommendations_json", "TEXT"),
            ("report_compliant", "INTEGER"),
        ]
        with engine.begin() as conn:
            for col, typ in reg_cols:
                if col not in existing:
                    conn.execute(text(f'ALTER TABLE "bacs_inspections" ADD COLUMN "{col}" {typ}'))
                    logger.info("migration: BACS reg — added bacs_inspections.%s", col)


def _migrate_bacs_regulatory(engine):
    """Create BACS regulatory tables (functional requirements, exploitation, proofs)."""
    insp = inspect(engine)

    if not insp.has_table("bacs_functional_requirements"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "bacs_functional_requirements" (
                    "id" INTEGER PRIMARY KEY,
                    "asset_id" INTEGER NOT NULL REFERENCES "bacs_assets"("id") ON DELETE CASCADE,
                    "continuous_monitoring" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "hourly_timestep" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "functional_zones" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "monthly_retention_5y" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "reference_values" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "efficiency_loss_detection" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "interoperability" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "manual_override" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "autonomous_management" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "data_ownership" VARCHAR(20) DEFAULT 'not_demonstrated',
                    "assessed_at" DATETIME,
                    "assessed_by" VARCHAR(200),
                    "notes" TEXT,
                    "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
                    "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
        logger.info("migration: created bacs_functional_requirements")

    if not insp.has_table("bacs_exploitation_status"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "bacs_exploitation_status" (
                    "id" INTEGER PRIMARY KEY,
                    "asset_id" INTEGER NOT NULL REFERENCES "bacs_assets"("id") ON DELETE CASCADE,
                    "written_procedures" VARCHAR(20) DEFAULT 'absent',
                    "verification_periodicity" VARCHAR(50),
                    "control_points_defined" INTEGER DEFAULT 0,
                    "repair_process_defined" INTEGER DEFAULT 0,
                    "operator_trained" INTEGER DEFAULT 0,
                    "training_date" DATE,
                    "training_provider" VARCHAR(200),
                    "training_certificate_ref" VARCHAR(200),
                    "last_review_at" DATETIME,
                    "reviewed_by" VARCHAR(200),
                    "notes" TEXT,
                    "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
                    "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
        logger.info("migration: created bacs_exploitation_status")

    if not insp.has_table("bacs_proof_documents"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "bacs_proof_documents" (
                    "id" INTEGER PRIMARY KEY,
                    "asset_id" INTEGER NOT NULL REFERENCES "bacs_assets"("id") ON DELETE CASCADE,
                    "document_type" VARCHAR(50) NOT NULL,
                    "label" VARCHAR(300),
                    "source" VARCHAR(100),
                    "actor" VARCHAR(200) NOT NULL DEFAULT 'system',
                    "file_ref" VARCHAR(500),
                    "valid_until" DATE,
                    "notes" TEXT,
                    "linked_entity_type" VARCHAR(50),
                    "linked_entity_id" INTEGER,
                    "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
                    "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
            conn.execute(
                text('CREATE INDEX IF NOT EXISTS "ix_bacs_proof_asset" ON "bacs_proof_documents" ("asset_id")')
            )
        logger.info("migration: created bacs_proof_documents")


def _migrate_bacs_remediation(engine):
    """Create bacs_remediation_actions table."""
    insp = inspect(engine)
    if not insp.has_table("bacs_remediation_actions"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS "bacs_remediation_actions" (
                    "id" INTEGER PRIMARY KEY,
                    "asset_id" INTEGER NOT NULL REFERENCES "bacs_assets"("id") ON DELETE CASCADE,
                    "blocker_code" VARCHAR(100) NOT NULL,
                    "blocker_cause" VARCHAR(300) NOT NULL,
                    "expected_action" VARCHAR(500) NOT NULL,
                    "expected_proof_type" VARCHAR(100),
                    "status" VARCHAR(20) NOT NULL DEFAULT 'open',
                    "priority" VARCHAR(20) NOT NULL DEFAULT 'high',
                    "owner" VARCHAR(200),
                    "due_at" DATE,
                    "created_by" VARCHAR(200) NOT NULL DEFAULT 'system',
                    "proof_id" INTEGER REFERENCES "bacs_proof_documents"("id") ON DELETE SET NULL,
                    "proof_review_status" VARCHAR(20),
                    "proof_reviewed_by" VARCHAR(200),
                    "proof_reviewed_at" DATETIME,
                    "resolution_notes" TEXT,
                    "closed_at" DATETIME,
                    "closed_by" VARCHAR(200),
                    "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
                    "updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
            conn.execute(
                text(
                    'CREATE INDEX IF NOT EXISTS "ix_bacs_remediation_asset" ON "bacs_remediation_actions" ("asset_id")'
                )
            )
        logger.info("migration: created bacs_remediation_actions")


def _rename_enedis_mesure_table(engine):
    """Rename enedis_flux_mesure → enedis_flux_mesure_r4x for existing DBs.

    Also drops old indexes and recreates them with r4x-qualified names.
    Idempotent: skips if old table does not exist or new table already exists.
    """
    insp = inspect(engine)
    if not insp.has_table("enedis_flux_mesure"):
        return
    if insp.has_table("enedis_flux_mesure_r4x"):
        return

    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE "enedis_flux_mesure" RENAME TO "enedis_flux_mesure_r4x"'))
        # Drop old indexes (SQLite doesn't support RENAME INDEX)
        conn.execute(text('DROP INDEX IF EXISTS "ix_enedis_mesure_point_horodatage"'))
        conn.execute(text('DROP INDEX IF EXISTS "ix_enedis_mesure_flux_file"'))
        conn.execute(text('DROP INDEX IF EXISTS "ix_enedis_mesure_flux_type"'))
        # Recreate with r4x-qualified names
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
    logger.info("migration: renamed enedis_flux_mesure → enedis_flux_mesure_r4x")


def _create_enedis_tables(engine):
    """Create Enedis SGE staging tables if any are missing.

    Checks each table individually so that tables added after the initial
    deployment are created on the next migration run.
    """
    all_enedis_tables = (
        "enedis_flux_file",
        "enedis_flux_mesure_r4x",
        "enedis_flux_mesure_r171",
        "enedis_flux_mesure_r50",
        "enedis_flux_mesure_r151",
        "enedis_flux_file_error",
        "enedis_ingestion_run",
    )
    insp = inspect(engine)
    missing = [t for t in all_enedis_tables if not insp.has_table(t)]
    if missing:
        # Import models to register them with Base.metadata
        import data_ingestion.enedis.models  # noqa: F401
        from models.base import Base

        # Use checkfirst=True with the full table list so SQLAlchemy handles
        # FK-dependency ordering correctly (matters for PostgreSQL).
        Base.metadata.create_all(
            bind=engine,
            tables=[Base.metadata.tables[t] for t in all_enedis_tables if t in Base.metadata.tables],
            checkfirst=True,
        )
        logger.info("migration: created Enedis SGE staging tables: %s", missing)

    # Ensure partial unique index for concurrency guard exists (always run,
    # even if all tables already exist, to cover upgraded DBs from SF2/SF3).
    with engine.begin() as conn:
        conn.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS "ix_ingestion_run_single_running" '
                'ON "enedis_ingestion_run" ("status") WHERE "status" = \'running\''
            )
        )


def _add_enedis_columns(engine):
    """Add columns to existing Enedis tables that may have been created before schema evolution.

    Follows the same pattern as _add_soft_delete_columns, _add_site_geocoding_columns, etc.
    When new columns are added to EnedisFluxFile or EnedisFluxMesureR4x models,
    add them to the relevant list below so existing DBs receive them via ALTER TABLE.
    """
    insp = inspect(engine)

    # --- enedis_flux_file columns ---
    # Add new columns here as (col_name, col_type) when evolving the model.
    enedis_flux_file_columns = [
        ("version", "INTEGER DEFAULT 1"),
        ("supersedes_file_id", "INTEGER REFERENCES enedis_flux_file(id) ON DELETE SET NULL"),
        ("frequence_publication", "VARCHAR(5)"),
        ("nature_courbe_demandee", "VARCHAR(20)"),
        ("identifiant_destinataire", "VARCHAR(100)"),
        ("header_raw", "TEXT"),
    ]

    # --- enedis_flux_mesure_r4x columns ---
    enedis_flux_mesure_r4x_columns = [
        # Example for future SF3+:
        # ("new_column_name", "VARCHAR(50)"),
    ]

    # SF3 tables — add evolved columns here when the model grows:
    enedis_flux_mesure_r171_columns = []
    enedis_flux_mesure_r50_columns = []
    enedis_flux_mesure_r151_columns = []

    table_column_map = {
        "enedis_flux_file": enedis_flux_file_columns,
        "enedis_flux_mesure_r4x": enedis_flux_mesure_r4x_columns,
        "enedis_flux_mesure_r171": enedis_flux_mesure_r171_columns,
        "enedis_flux_mesure_r50": enedis_flux_mesure_r50_columns,
        "enedis_flux_mesure_r151": enedis_flux_mesure_r151_columns,
    }

    added = 0
    with engine.begin() as conn:
        for table_name, columns in table_column_map.items():
            if not insp.has_table(table_name) or not columns:
                continue

            existing_cols = {c["name"] for c in insp.get_columns(table_name)}

            for col_name, col_type in columns:
                if col_name in existing_cols:
                    continue
                try:
                    conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}'))
                    added += 1
                    logger.info("migration: added %s.%s (%s)", table_name, col_name, col_type)
                except Exception as e:
                    logger.warning("migration: could not add %s.%s: %s", table_name, col_name, e)

    if added > 0:
        logger.info("migration: added %d Enedis column(s)", added)
    else:
        logger.debug("migration: Enedis columns already present — no changes")


def _add_delivery_point_turpe_columns(engine):
    """Add TURPE 7 / HC reprogrammation columns to delivery_points if missing."""
    insp = inspect(engine)
    if not insp.has_table("delivery_points"):
        return

    existing_cols = {c["name"] for c in insp.get_columns("delivery_points")}

    new_cols = [
        ("tariff_segment", "VARCHAR(10)"),
        ("puissance_souscrite_kva", "FLOAT"),
        ("hc_reprog_phase", "VARCHAR(20)"),
        ("hc_reprog_status", "VARCHAR(20)"),
        ("hc_reprog_date_prevue", "DATE"),
        ("hc_reprog_date_effective", "DATE"),
        ("hc_code_actuel", "VARCHAR(20)"),
        ("hc_code_futur", "VARCHAR(20)"),
        ("hc_libelle_actuel", "VARCHAR(100)"),
        ("hc_libelle_futur", "VARCHAR(100)"),
        ("hc_code_futur_ete", "VARCHAR(20)"),
        ("hc_code_futur_hiver", "VARCHAR(20)"),
        ("hc_saisonnalise", "BOOLEAN DEFAULT 0"),
    ]

    added = 0
    with engine.begin() as conn:
        for col_name, col_type in new_cols:
            if col_name in existing_cols:
                continue
            try:
                conn.execute(text(f'ALTER TABLE "delivery_points" ADD COLUMN "{col_name}" {col_type}'))
                added += 1
                logger.info("migration: added delivery_points.%s (%s)", col_name, col_type)
            except Exception as e:
                logger.warning("migration: could not add delivery_points.%s: %s", col_name, e)

    if added > 0:
        logger.info("migration: added %d TURPE/HC column(s) to delivery_points", added)
    else:
        logger.debug("migration: delivery_points TURPE/HC columns already present")


def _add_delivery_point_tou_schedule_fk(engine):
    """Add tou_schedule_id FK column to delivery_points if missing (P1 HC reprog)."""
    insp = inspect(engine)
    if not insp.has_table("delivery_points"):
        return

    existing_cols = {c["name"] for c in insp.get_columns("delivery_points")}
    if "tou_schedule_id" in existing_cols:
        logger.debug("migration: delivery_points.tou_schedule_id already present")
        return

    with engine.begin() as conn:
        try:
            conn.execute(
                text(
                    'ALTER TABLE "delivery_points" ADD COLUMN "tou_schedule_id" INTEGER REFERENCES "tou_schedules"("id") ON DELETE SET NULL'
                )
            )
            logger.info("migration: added delivery_points.tou_schedule_id (FK → tou_schedules)")
        except Exception as e:
            logger.warning("migration: could not add delivery_points.tou_schedule_id: %s", e)


def _create_audit_energetique_table(engine):
    """Create audit_energetique table if not exists (Loi 2025-391)."""
    insp = inspect(engine)
    if insp.has_table("audit_energetique"):
        logger.debug("migration: audit_energetique table already exists")
        # Table exists but may lack SoftDelete columns (added after initial creation)
        _add_audit_energetique_soft_delete_columns(engine)
        return

    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS audit_energetique (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organisation_id INTEGER REFERENCES organisations(id),
                organisation_libelle VARCHAR(255),
                annee_ref_debut INTEGER,
                annee_ref_fin INTEGER,
                conso_annuelle_moy_kwh FLOAT,
                conso_annuelle_moy_gwh FLOAT,
                detail_vecteurs TEXT,
                obligation VARCHAR(30) NOT NULL DEFAULT 'NON_DETERMINE',
                statut VARCHAR(20) NOT NULL DEFAULT 'NON_DETERMINE',
                date_premier_audit_limite DATE,
                date_dernier_audit DATE,
                date_prochain_audit DATE,
                date_transmission_admin DATE,
                auditeur_identifie BOOLEAN DEFAULT 0,
                audit_realise BOOLEAN DEFAULT 0,
                plan_action_publie BOOLEAN DEFAULT 0,
                transmission_realisee BOOLEAN DEFAULT 0,
                sme_certifie_iso50001 BOOLEAN DEFAULT 0,
                date_certification_sme DATE,
                organisme_certificateur VARCHAR(100),
                score_audit_sme FLOAT,
                source VARCHAR(20) DEFAULT 'manual',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at DATETIME,
                deleted_by VARCHAR(200),
                delete_reason VARCHAR(500)
            )
        """)
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_audit_energetique_org_id ON audit_energetique(organisation_id)")
        )
    logger.info("migration: created audit_energetique table")

    # Backfill: add SoftDelete columns if table was created before SoftDeleteMixin was added
    _add_audit_energetique_soft_delete_columns(engine)


def _add_audit_energetique_soft_delete_columns(engine):
    """Add deleted_at/deleted_by/delete_reason if table exists but columns are missing."""
    insp = inspect(engine)
    if not insp.has_table("audit_energetique"):
        return
    existing_cols = {c["name"] for c in insp.get_columns("audit_energetique")}
    new_cols = [
        ("deleted_at", "DATETIME"),
        ("deleted_by", "VARCHAR(200)"),
        ("delete_reason", "VARCHAR(500)"),
    ]
    added = 0
    with engine.begin() as conn:
        for col_name, col_type in new_cols:
            if col_name in existing_cols:
                continue
            try:
                conn.execute(text(f'ALTER TABLE "audit_energetique" ADD COLUMN "{col_name}" {col_type}'))
                added += 1
                logger.info("migration: added audit_energetique.%s (%s)", col_name, col_type)
            except Exception as e:
                logger.warning("migration: could not add audit_energetique.%s: %s", col_name, e)
    if added > 0:
        logger.info("migration: added %d SoftDelete column(s) to audit_energetique", added)


# ---------------------------------------------------------------------------
# V2 Contrats Cadre + Annexes
# ---------------------------------------------------------------------------


def _migrate_contracts_v2(engine):
    """V2 Contrats Cadre+Annexe — add cadre columns + 4 new tables. Idempotent."""
    insp = inspect(engine)

    # 1. Add columns to energy_contracts
    if insp.has_table("energy_contracts"):
        existing = {c["name"] for c in insp.get_columns("energy_contracts")}
        new_cols = [
            ("is_cadre", "BOOLEAN DEFAULT 0"),
            ("contract_type", "VARCHAR(20) DEFAULT 'UNIQUE'"),
            ("entite_juridique_id", "INTEGER REFERENCES entites_juridiques(id)"),
            ("notice_period_months", "INTEGER"),
            ("is_green", "BOOLEAN DEFAULT 0"),
            ("green_percentage", "FLOAT"),
            ("notes", "TEXT"),
        ]
        with engine.begin() as conn:
            for col_name, col_type in new_cols:
                if col_name in existing:
                    continue
                try:
                    conn.execute(text(f'ALTER TABLE "energy_contracts" ADD COLUMN "{col_name}" {col_type}'))
                    logger.info("migration: added energy_contracts.%s", col_name)
                except Exception as e:
                    logger.warning("migration: could not add energy_contracts.%s: %s", col_name, e)

    # 2. Create contract_annexes
    if not insp.has_table("contract_annexes"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE contract_annexes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contrat_cadre_id INTEGER NOT NULL REFERENCES energy_contracts(id) ON DELETE CASCADE,
                    site_id INTEGER NOT NULL REFERENCES sites(id),
                    delivery_point_id INTEGER REFERENCES delivery_points(id),
                    annexe_ref VARCHAR(100),
                    tariff_option VARCHAR(10),
                    subscribed_power_kva FLOAT,
                    segment_enedis VARCHAR(10),
                    has_price_override BOOLEAN DEFAULT 0,
                    override_pricing_model VARCHAR(30),
                    start_date_override DATE,
                    end_date_override DATE,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted_at DATETIME,
                    deleted_by VARCHAR(200),
                    delete_reason VARCHAR(500),
                    UNIQUE(contrat_cadre_id, site_id)
                )
            """)
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_contract_annexes_cadre ON contract_annexes(contrat_cadre_id)")
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_contract_annexes_site ON contract_annexes(site_id)"))
        logger.info("migration: created contract_annexes table")

    # 3. Create contract_pricing
    if not insp.has_table("contract_pricing"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE contract_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER REFERENCES energy_contracts(id) ON DELETE CASCADE,
                    annexe_id INTEGER REFERENCES contract_annexes(id) ON DELETE CASCADE,
                    period_code VARCHAR(10) NOT NULL,
                    season VARCHAR(10) DEFAULT 'ANNUEL',
                    unit_price_eur_kwh FLOAT,
                    subscription_eur_month FLOAT,
                    effective_from DATE,
                    effective_to DATE,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CHECK (
                        (contract_id IS NOT NULL AND annexe_id IS NULL)
                        OR (contract_id IS NULL AND annexe_id IS NOT NULL)
                    )
                )
            """)
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_contract_pricing_contract ON contract_pricing(contract_id)")
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_contract_pricing_annexe ON contract_pricing(annexe_id)"))
        logger.info("migration: created contract_pricing table")

    # 4. Create volume_commitments
    if not insp.has_table("volume_commitments"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE volume_commitments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    annexe_id INTEGER NOT NULL UNIQUE REFERENCES contract_annexes(id) ON DELETE CASCADE,
                    annual_kwh FLOAT NOT NULL,
                    tolerance_pct_up FLOAT DEFAULT 10.0,
                    tolerance_pct_down FLOAT DEFAULT 10.0,
                    penalty_eur_kwh_above FLOAT,
                    penalty_eur_kwh_below FLOAT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_volume_commitments_annexe ON volume_commitments(annexe_id)")
            )
        logger.info("migration: created volume_commitments table")

    # 5. Create contract_events
    if not insp.has_table("contract_events"):
        with engine.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE contract_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL REFERENCES energy_contracts(id) ON DELETE CASCADE,
                    event_type VARCHAR(30) NOT NULL,
                    event_date DATE NOT NULL,
                    description VARCHAR(500),
                    meta_json TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_contract_events_contract ON contract_events(contract_id)"))
        logger.info("migration: created contract_events table")

    # 6. Backfill existing contracts
    if insp.has_table("energy_contracts"):
        with engine.begin() as conn:
            conn.execute(text("UPDATE energy_contracts SET is_cadre = 0 WHERE is_cadre IS NULL"))
            conn.execute(text("UPDATE energy_contracts SET contract_type = 'UNIQUE' WHERE contract_type IS NULL"))
        logger.info("migration: backfilled energy_contracts V2 defaults")


def _add_evidence_coverage_pct_column(engine):
    """Add coverage_pct (FLOAT, nullable) to evidences table for APER partial coverage."""
    insp = inspect(engine)
    if not insp.has_table("evidences"):
        return
    existing = {c["name"] for c in insp.get_columns("evidences")}
    if "coverage_pct" in existing:
        return
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE "evidences" ADD COLUMN "coverage_pct" FLOAT'))
    logger.info("migration: added evidences.coverage_pct column (APER partial coverage)")


# ---------------------------------------------------------------------------
# Sprint F — ConnectorToken (OAuth2 tokens for Enedis DataConnect / GRDF ADICT)
# ---------------------------------------------------------------------------


def _create_connector_tokens_table(engine):
    """Create connector_tokens table if missing. Idempotent."""
    insp = inspect(engine)
    if insp.has_table("connector_tokens"):
        return
    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE connector_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connector_name VARCHAR(50) NOT NULL,
                    prm VARCHAR(14) NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_type VARCHAR(20) DEFAULT 'Bearer',
                    expires_at DATETIME NOT NULL,
                    scope VARCHAR(200),
                    consent_expiry DATE,
                    consent_status VARCHAR(20) DEFAULT 'unknown',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_connector_token_prm UNIQUE (connector_name, prm)
                )
            """)
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_connector_tokens_connector_name ON connector_tokens(connector_name)")
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_connector_tokens_prm ON connector_tokens(prm)"))
    logger.info("migration: created connector_tokens table (Sprint F)")


# ---------------------------------------------------------------------------
# Phase 1 — ContratCadre entity-level model
# ---------------------------------------------------------------------------


def _migrate_phase1_contrats_cadre(engine):
    """Run the Phase 1 migration script (idempotent). Wire for startup auto-apply."""
    import sqlite3
    from pathlib import Path
    from urllib.parse import urlparse

    # Extract the SQLite path from the engine URL
    url = str(engine.url)
    if not url.startswith("sqlite"):
        logger.warning("migration phase1: only SQLite is supported, skipping")
        return
    db_path = url.split("///", 1)[-1] if "///" in url else None
    if not db_path or db_path == ":memory:":
        return
    db_path = Path(db_path)
    if not db_path.exists():
        return

    try:
        from migrations.add_contrats_cadre_phase1 import migrate as phase1_migrate

        phase1_migrate(str(db_path))
    except Exception as e:
        logger.warning("migration phase1: %s", e)


# ---------------------------------------------------------------------------
# Phase 5 — Invoice annexe_site_id column
# ---------------------------------------------------------------------------


def _migrate_phase5_invoice_annexe_site(engine):
    """Run the Phase 5 migration script (idempotent). Wire for startup auto-apply."""
    from pathlib import Path

    url = str(engine.url)
    if not url.startswith("sqlite"):
        logger.warning("migration phase5: only SQLite is supported, skipping")
        return
    db_path = url.split("///", 1)[-1] if "///" in url else None
    if not db_path or db_path == ":memory:":
        return
    db_path = Path(db_path)
    if not db_path.exists():
        return

    try:
        from migrations.add_invoice_annexe_site_phase5 import migrate as phase5_migrate

        phase5_migrate(str(db_path))
    except Exception as e:
        logger.warning("migration phase5: %s", e)
