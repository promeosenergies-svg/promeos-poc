"""
Migration: Billing Data Model Vague 1 — TaxProfile + grd_code + pass-through.

New table  : tax_profiles
New columns:
  - delivery_points.grd_code (VARCHAR(50) indexed)
  - energy_contracts.cee_pass_through (BOOLEAN, default 0)
  - energy_contracts.accise_pass_through (BOOLEAN, default 1)
  - energy_contracts.network_cost_model (VARCHAR(30), nullable)

Safe to re-run : uses IF NOT EXISTS / column existence checks.
Backward-compatible : new columns are nullable or have safe defaults.
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


def index_exists(cursor, index_name: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cursor.fetchone() is not None


def add_column_if_missing(cursor, table: str, column: str, col_type: str, default=None) -> bool:
    if column_exists(cursor, table, column):
        return False
    stmt = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
    if default is not None:
        stmt += f" DEFAULT {default}"
    cursor.execute(stmt)
    return True


CREATE_TAX_PROFILES = """
CREATE TABLE IF NOT EXISTS tax_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    delivery_point_id INTEGER NOT NULL REFERENCES delivery_points(id) ON DELETE CASCADE,
    accise_category_elec VARCHAR(20),
    accise_category_gaz VARCHAR(20),
    regime_reduit BOOLEAN NOT NULL DEFAULT 0,
    attestation_ref VARCHAR(200),
    eligibility_code VARCHAR(50),
    valid_from DATE,
    valid_to DATE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_TAX_PROFILES_IDX = (
    "CREATE INDEX IF NOT EXISTS ix_tax_profiles_delivery_point_id ON tax_profiles(delivery_point_id)"
)

CREATE_DP_GRD_IDX = "CREATE INDEX IF NOT EXISTS ix_delivery_points_grd_code ON delivery_points(grd_code)"


def run_migration(db_path: Path = DB_PATH) -> dict:
    """Execute migration. Returns dict summary of changes."""
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    summary = {
        "tax_profiles_created": False,
        "grd_code_added": False,
        "cee_pass_through_added": False,
        "accise_pass_through_added": False,
        "network_cost_model_added": False,
        "indexes_created": 0,
    }

    # 1. Create tax_profiles table
    if not table_exists(cursor, "tax_profiles"):
        cursor.execute(CREATE_TAX_PROFILES)
        summary["tax_profiles_created"] = True

    # 2. Add grd_code on delivery_points
    if add_column_if_missing(cursor, "delivery_points", "grd_code", "VARCHAR(50)"):
        summary["grd_code_added"] = True

    # 3. Add pass-through columns on energy_contracts
    if add_column_if_missing(cursor, "energy_contracts", "cee_pass_through", "BOOLEAN", default=0):
        summary["cee_pass_through_added"] = True

    if add_column_if_missing(cursor, "energy_contracts", "accise_pass_through", "BOOLEAN", default=1):
        summary["accise_pass_through_added"] = True

    if add_column_if_missing(cursor, "energy_contracts", "network_cost_model", "VARCHAR(30)"):
        summary["network_cost_model_added"] = True

    # 4. Create indexes
    for idx_stmt, idx_name in [
        (CREATE_TAX_PROFILES_IDX, "ix_tax_profiles_delivery_point_id"),
        (CREATE_DP_GRD_IDX, "ix_delivery_points_grd_code"),
    ]:
        if not index_exists(cursor, idx_name):
            cursor.execute(idx_stmt)
            summary["indexes_created"] += 1

    conn.commit()
    conn.close()
    return summary


if __name__ == "__main__":
    result = run_migration()
    print(f"Migration summary: {result}")
    changed = sum(1 for v in result.values() if v)
    if changed == 0:
        print("Schema was already up to date.")
    else:
        print(f"{changed} changes applied.")
    sys.exit(0)
