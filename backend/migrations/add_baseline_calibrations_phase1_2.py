"""Migration : table baseline_calibrations — Cockpit Sol2 Phase 1.2 (Décisions B+D).

Crée la table `baseline_calibrations` avec index composé (site_id, method)
pour requêtes "dernière calibration pour ce site / cette méthode".

Safe to re-run : utilise CREATE TABLE IF NOT EXISTS (idempotent).
Backward-compatible : nouvelle table, pas de modification de table existante.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.2
Doctrine : §0.D décision D — historisation calibrations, jamais d'UPDATE.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "promeos.db"


def table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def index_exists(cursor, index: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index,))
    return cursor.fetchone() is not None


def run_migration(db_path: Path = DB_PATH) -> dict:
    """Crée la table baseline_calibrations si elle n'existe pas encore.

    Returns:
        dict avec clés "created" (bool) et "index_created" (bool).
    """
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    summary: dict = {"created": False, "index_created": False}

    if not table_exists(cursor, "baseline_calibrations"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS baseline_calibrations (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id          INTEGER NOT NULL REFERENCES sites(id),
                method           VARCHAR(30) NOT NULL,
                calibration_date DATETIME NOT NULL,
                coefficient_a    REAL,
                coefficient_b    REAL,
                ref_year         INTEGER,
                r_squared        REAL,
                data_points      INTEGER NOT NULL,
                confidence       VARCHAR(20) NOT NULL
            )
            """
        )
        summary["created"] = True

    # Index composé site_id + method pour requêtes "dernière calibration"
    idx_name = "ix_baseline_calibrations_site_method"
    if not index_exists(cursor, idx_name):
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON baseline_calibrations (site_id, method)")
        summary["index_created"] = True

    conn.commit()
    conn.close()
    return summary


if __name__ == "__main__":
    result = run_migration()
    if result["created"]:
        print("Created table baseline_calibrations.")
    else:
        print("Table baseline_calibrations already exists — schema is up to date.")
    if result["index_created"]:
        print("Created composite index (site_id, method).")
    sys.exit(0)
