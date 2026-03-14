"""
Migration: Add Billing Engine V2 columns.

New columns on:
  - energy_contracts: subscribed_power_kva, tariff_option, pass_through_items,
    price_hpe_eur_kwh, price_hce_eur_kwh, price_hp_eur_kwh, price_hc_eur_kwh,
    price_base_eur_kwh
  - energy_invoices: invoice_type, is_estimated, start_index, end_index
  - energy_invoice_lines: period_code, line_category

Safe to re-run: uses IF NOT EXISTS / checks column existence.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "promeos.db"


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


def migrate(db_path: str = None):
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    added = []

    # ── energy_contracts ─────────────────────────────────────────────────
    contract_cols = [
        ("subscribed_power_kva", "REAL", None),
        ("tariff_option", "VARCHAR(10)", None),
        ("pass_through_items", "TEXT", None),
        ("price_hpe_eur_kwh", "REAL", None),
        ("price_hce_eur_kwh", "REAL", None),
        ("price_hp_eur_kwh", "REAL", None),
        ("price_hc_eur_kwh", "REAL", None),
        ("price_base_eur_kwh", "REAL", None),
    ]
    for col, ctype, default in contract_cols:
        if add_column_if_missing(cursor, "energy_contracts", col, ctype, default):
            added.append(f"energy_contracts.{col}")

    # ── energy_invoices ──────────────────────────────────────────────────
    invoice_cols = [
        ("invoice_type", "VARCHAR(20)", "'normal'"),
        ("is_estimated", "BOOLEAN", "0"),
        ("start_index", "REAL", None),
        ("end_index", "REAL", None),
    ]
    for col, ctype, default in invoice_cols:
        if add_column_if_missing(cursor, "energy_invoices", col, ctype, default):
            added.append(f"energy_invoices.{col}")

    # ── energy_invoice_lines ─────────────────────────────────────────────
    line_cols = [
        ("period_code", "VARCHAR(10)", None),
        ("line_category", "VARCHAR(50)", None),
    ]
    for col, ctype, default in line_cols:
        if add_column_if_missing(cursor, "energy_invoice_lines", col, ctype, default):
            added.append(f"energy_invoice_lines.{col}")

    conn.commit()
    conn.close()

    if added:
        print(f"Migration OK — {len(added)} colonnes ajoutées: {', '.join(added)}")
    else:
        print("Migration OK — toutes les colonnes existent déjà, rien à faire.")
    return added


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else None
    migrate(db)
