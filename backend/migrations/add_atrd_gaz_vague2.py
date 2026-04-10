"""
Migration: Billing Data Model Vague 2 — ATRD gaz détaillé.

New columns on delivery_points :
  - atrd_option (VARCHAR(10)) — T1/T2/T3/T4/TP
  - car_kwh (FLOAT) — Consommation Annuelle de Référence GRDF
  - gas_profile (VARCHAR(20)) — BASE/B0/B1/B2I/MODULANT
  - cjn_mwh_per_day (FLOAT) — Capacité Journalière Normale
  - cja_mwh_per_day (FLOAT) — Capacité Journalière Acheminement

Safe to re-run : uses column existence checks.
Backward-compatible : toutes nullable, pas de contrainte NOT NULL.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "promeos.db"


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def add_column_if_missing(cursor, table: str, column: str, col_type: str) -> bool:
    if column_exists(cursor, table, column):
        return False
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    return True


GAS_COLUMNS = [
    ("atrd_option", "VARCHAR(10)"),
    ("car_kwh", "FLOAT"),
    ("gas_profile", "VARCHAR(20)"),
    ("cjn_mwh_per_day", "FLOAT"),
    ("cja_mwh_per_day", "FLOAT"),
]


def run_migration(db_path: Path = DB_PATH) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    summary: dict = {"columns_added": []}

    for col, col_type in GAS_COLUMNS:
        if add_column_if_missing(cursor, "delivery_points", col, col_type):
            summary["columns_added"].append(col)

    conn.commit()
    conn.close()
    return summary


if __name__ == "__main__":
    result = run_migration()
    added = result["columns_added"]
    if not added:
        print("Schema was already up to date.")
    else:
        print(f"Added {len(added)} columns: {', '.join(added)}")
    sys.exit(0)
