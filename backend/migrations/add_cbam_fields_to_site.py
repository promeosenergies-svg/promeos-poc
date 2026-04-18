"""Migration : colonnes CBAM JSON sur `sites` (P3 wedge post-ARENH).

New columns on sites :
  - cbam_imports_tonnes (JSON) — volumes annuels d'importation hors UE par scope
  - cbam_intensities_tco2_per_t (JSON) — intensités site-specific (override défauts CE)

Source : Règlement UE 2023/956 (CBAM), activé 07/04/2026 à 75,36 €/tCO2.
Safe to re-run : uses column existence checks.
Backward-compatible : both nullable, pas de contrainte NOT NULL.
"""

from __future__ import annotations

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


# SQLite stocke JSON en TEXT (compatible avec SQLAlchemy JSON type).
CBAM_COLUMNS = [
    ("cbam_imports_tonnes", "TEXT"),
    ("cbam_intensities_tco2_per_t", "TEXT"),
]


def run_migration(db_path: Path = DB_PATH) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    summary: dict = {"columns_added": []}

    for col, col_type in CBAM_COLUMNS:
        if add_column_if_missing(cursor, "sites", col, col_type):
            summary["columns_added"].append(col)

    conn.commit()
    conn.close()
    return summary


if __name__ == "__main__":
    result = run_migration()
    added = result["columns_added"]
    if not added:
        print("Schema CBAM was already up to date.")
    else:
        print(f"Added {len(added)} CBAM columns to sites: {', '.join(added)}")
    sys.exit(0)
