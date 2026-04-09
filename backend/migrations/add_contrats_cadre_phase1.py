"""
Migration: Contrats V2 Phase 1 — ContratCadre + AnnexeSite enrichi.

New table: contrats_cadre (entity-level contract model).
New columns on contract_annexes: cadre_id, prm, pce, prix overrides, volume_engage_kwh.

Safe to re-run: uses IF NOT EXISTS / checks column existence.
Backward-compatible: does NOT alter existing FKs on energy_contracts or energy_invoices.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "promeos.db"


def table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def add_column_if_missing(cursor, table: str, column: str, col_type: str, default=None):
    if column_exists(cursor, table, column):
        return False
    stmt = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
    if default is not None:
        stmt += f" DEFAULT {default}"
    cursor.execute(stmt)
    return True


CREATE_CONTRATS_CADRE = """
CREATE TABLE IF NOT EXISTS contrats_cadre (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    entite_juridique_id INTEGER REFERENCES entites_juridiques(id),
    reference VARCHAR(100) NOT NULL,
    reference_fournisseur VARCHAR(100),
    fournisseur VARCHAR(200) NOT NULL,
    energie VARCHAR(10) NOT NULL,
    date_signature DATE,
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    date_preavis DATE,
    notice_period_months INTEGER,
    auto_renew BOOLEAN DEFAULT 0,
    type_prix VARCHAR(30) NOT NULL,
    prix_hp_eur_kwh REAL,
    prix_hc_eur_kwh REAL,
    prix_base_eur_kwh REAL,
    poids_hp REAL DEFAULT 62.0,
    poids_hc REAL DEFAULT 38.0,
    cee_inclus BOOLEAN DEFAULT 0,
    cee_eur_mwh REAL,
    capacite_incluse BOOLEAN DEFAULT 0,
    capacite_eur_mwh REAL,
    indexation_reference VARCHAR(100),
    indexation_spread_eur_mwh REAL,
    prix_plancher_eur_mwh REAL,
    prix_plafond_eur_mwh REAL,
    statut VARCHAR(20) NOT NULL DEFAULT 'draft',
    is_green BOOLEAN DEFAULT 0,
    green_percentage REAL,
    notes TEXT,
    conditions_particulieres TEXT,
    document_url VARCHAR(500),
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    deleted_at DATETIME,
    deleted_by VARCHAR(200),
    delete_reason VARCHAR(500)
);
"""

CREATE_IDX_CADRE_ORG = "CREATE INDEX IF NOT EXISTS ix_contrats_cadre_org_id ON contrats_cadre(org_id);"
CREATE_IDX_CADRE_EJ = (
    "CREATE INDEX IF NOT EXISTS ix_contrats_cadre_entite_juridique_id ON contrats_cadre(entite_juridique_id);"
)


def migrate(db_path: str = None):
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    actions = []

    # ── Create contrats_cadre table ──────────────────────────────────────
    if not table_exists(cursor, "contrats_cadre"):
        cursor.execute(CREATE_CONTRATS_CADRE)
        cursor.execute(CREATE_IDX_CADRE_ORG)
        cursor.execute(CREATE_IDX_CADRE_EJ)
        actions.append("CREATE TABLE contrats_cadre")

    # ── Add new columns to contract_annexes ──────────────────────────────
    if table_exists(cursor, "contract_annexes"):
        annexe_cols = [
            ("cadre_id", "INTEGER REFERENCES contrats_cadre(id)", None),
            ("prm", "VARCHAR(14)", None),
            ("pce", "VARCHAR(14)", None),
            ("prix_hp_override", "REAL", None),
            ("prix_hc_override", "REAL", None),
            ("prix_base_override", "REAL", None),
            ("volume_engage_kwh", "REAL", None),
        ]
        for col, ctype, default in annexe_cols:
            if add_column_if_missing(cursor, "contract_annexes", col, ctype, default):
                actions.append(f"contract_annexes.{col}")

        # Index on cadre_id
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_contract_annexes_cadre_id'")
        if not cursor.fetchone() and column_exists(cursor, "contract_annexes", "cadre_id"):
            cursor.execute("CREATE INDEX ix_contract_annexes_cadre_id ON contract_annexes(cadre_id);")
            actions.append("INDEX ix_contract_annexes_cadre_id")

    conn.commit()
    conn.close()

    if actions:
        print(f"Migration Phase 1 OK — {len(actions)} actions: {', '.join(actions)}")
    else:
        print("Migration Phase 1 OK — tout existe deja, rien a faire.")
    return actions


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else None
    migrate(db)
