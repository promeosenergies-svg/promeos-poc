"""Migration : table eur_amounts — Cockpit Sol2 Phase 1.1 (Décision A).

Crée la table `eur_amounts` avec CheckConstraint de traçabilité :
  - category=calculated_regulatory → regulatory_article NOT NULL
  - category=calculated_contractual → contract_id NOT NULL

Safe to re-run : utilise CREATE TABLE IF NOT EXISTS.
Backward-compatible : nouvelle table, pas de modification de table existante.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.1
Doctrine : §0.D décision A — tout € traçable réglementaire ou contractuel.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "promeos.db"


def table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def run_migration(db_path: Path = DB_PATH) -> dict:
    """Crée la table eur_amounts si elle n'existe pas encore.

    Returns:
        dict avec clé "created" (bool) indiquant si la table a été créée.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    summary: dict = {"created": False}

    if table_exists(cursor, "eur_amounts"):
        conn.close()
        return summary

    # SQLite ne supporte pas les CheckConstraints nommées via ALTER,
    # mais les supporte à la création. La contrainte enforce la doctrine §0.D.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS eur_amounts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            value_eur        REAL    NOT NULL,
            category         VARCHAR(30) NOT NULL,
            regulatory_article VARCHAR(255),
            contract_id      INTEGER REFERENCES energy_contracts(id),
            formula_text     VARCHAR(500) NOT NULL,
            computed_at      DATETIME NOT NULL,
            CONSTRAINT eur_amount_traceability_check CHECK (
                (category = 'calculated_regulatory' AND regulatory_article IS NOT NULL)
                OR
                (category = 'calculated_contractual' AND contract_id IS NOT NULL)
            )
        )
        """
    )

    conn.commit()
    conn.close()
    summary["created"] = True
    return summary


if __name__ == "__main__":
    result = run_migration()
    if result["created"]:
        print("Created table eur_amounts with traceability CheckConstraint.")
    else:
        print("Table eur_amounts already exists — schema is up to date.")
    sys.exit(0)
