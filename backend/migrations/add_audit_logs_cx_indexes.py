"""
Sprint CX 2.5 hardening (P1-perf) — Indices composite sur audit_logs.

Ajoute 3 indices pour optimiser les queries CX dashboard (T2V, IAR, WAU/MAU)
qui filtrent sur (action, resource_type, created_at) + group_by(resource_id)
+ distinct(user_id).

Idempotent (CREATE INDEX IF NOT EXISTS).

Usage :
    cd backend && python -m migrations.add_audit_logs_cx_indexes
    cd backend && python -m migrations.add_audit_logs_cx_indexes --down
"""

import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "promeos.db"

INDEXES = [
    (
        "ix_audit_cx_action_resource_created",
        "CREATE INDEX IF NOT EXISTS ix_audit_cx_action_resource_created "
        "ON audit_logs (action, resource_type, created_at)",
    ),
    (
        "ix_audit_user_id",
        "CREATE INDEX IF NOT EXISTS ix_audit_user_id ON audit_logs (user_id)",
    ),
    (
        "ix_audit_resource_id",
        "CREATE INDEX IF NOT EXISTS ix_audit_resource_id ON audit_logs (resource_id)",
    ),
]


def _list_existing_indices(conn):
    """Return set of index names on audit_logs."""
    rows = conn.execute("PRAGMA index_list('audit_logs')").fetchall()
    return {row[1] for row in rows}


def run_migration(db_path=DEFAULT_DB):
    """Crée les 3 indices (idempotent). Retourne dict {created, already_present}."""
    conn = sqlite3.connect(str(db_path))
    try:
        before = _list_existing_indices(conn)
        for name, sql in INDEXES:
            conn.execute(sql)
        conn.commit()
        after = _list_existing_indices(conn)
        created = [n for n, _ in INDEXES if n in after and n not in before]
        already = [n for n, _ in INDEXES if n in before]
        return {"created": created, "already_present": already}
    finally:
        conn.close()


def downgrade(db_path=DEFAULT_DB):
    """Drop les 3 indices. Retourne liste des noms droppés."""
    conn = sqlite3.connect(str(db_path))
    try:
        dropped = []
        for name, _ in INDEXES:
            conn.execute(f"DROP INDEX IF EXISTS {name}")
            dropped.append(name)
        conn.commit()
        return dropped
    finally:
        conn.close()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--down":
        dropped = downgrade()
        print(f"Dropped indices: {dropped}")
    else:
        result = run_migration()
        print(f"Created: {result['created']}")
        print(f"Already present: {result['already_present']}")


if __name__ == "__main__":
    main()
