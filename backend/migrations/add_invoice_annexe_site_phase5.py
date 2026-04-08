"""
Migration: Contrats V2 Phase 5 — Wire billing → resolve_pricing.

New column on energy_invoices: annexe_site_id (FK → contract_annexes.id).
Safe to re-run: checks column existence before ALTER.
Backward-compatible: nullable column, no existing data changed.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "promeos.db"


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def migrate(db_path: str = None):
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    actions = []

    # Add annexe_site_id to energy_invoices
    if not column_exists(cursor, "energy_invoices", "annexe_site_id"):
        cursor.execute("ALTER TABLE energy_invoices ADD COLUMN annexe_site_id INTEGER REFERENCES contract_annexes(id)")
        actions.append("energy_invoices.annexe_site_id")

    # Index for annexe_site_id
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_energy_invoices_annexe_site_id'")
    if not cursor.fetchone() and column_exists(cursor, "energy_invoices", "annexe_site_id"):
        cursor.execute("CREATE INDEX ix_energy_invoices_annexe_site_id ON energy_invoices(annexe_site_id);")
        actions.append("INDEX ix_energy_invoices_annexe_site_id")

    conn.commit()
    conn.close()

    if actions:
        print(f"Migration Phase 5 OK — {len(actions)} actions: {', '.join(actions)}")
    else:
        print("Migration Phase 5 OK — tout existe deja, rien a faire.")
    return actions


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else None
    migrate(db)
