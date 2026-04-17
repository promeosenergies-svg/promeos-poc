"""
Migration: 2 colonnes Flex Ready (R) sur sites.

New columns on sites :
  - archetype_code (VARCHAR(50)) — archetype Barometre Flex 2026
  - puissance_pilotable_kw (FLOAT) — puissance decalable estimee (kW)

Source : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
Safe to re-run : uses column existence checks.
Backward-compatible : toutes nullable, pas de contrainte NOT NULL.
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


PILOTAGE_COLUMNS = [
    ("archetype_code", "VARCHAR(50)"),
    ("puissance_pilotable_kw", "FLOAT"),
]


def run_migration(db_path: Path = DB_PATH) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    summary: dict = {"columns_added": []}

    for col, col_type in PILOTAGE_COLUMNS:
        if add_column_if_missing(cursor, "sites", col, col_type):
            summary["columns_added"].append(col)

    # Index sur archetype_code pour accelerer les agregations heatmap par archetype
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_sites_archetype_code ON sites(archetype_code)")

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
