#!/usr/bin/env python3
"""PROMEOS Sprint C-7 Phase 7.6 — Hook anti-PRAGMA-OFF (ADR-016 Pilier 2).

Vérifie `PRAGMA foreign_keys=ON` actif au connect SQLite event listener
dans `backend/database/connection.py`.

Anti-régression Phase 5.6 F1 — sans cette ligne, les FK `ondelete=SET NULL`
× 4 (RGPD `consentement_*_by` Phase 5.3) sont silencieusement non-enforced
runtime sous SQLite (par défaut désactivé spec SQLite).

Pattern attendu :
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

Usage standalone :
    python scripts/pre_commit_hooks/check_sqlite_pragma_fk.py backend/database/connection.py

Codes retour :
    0 = OK (PRAGMA + event listener présents)
    1 = manquant (régression Phase 5.6 F1)
"""

from __future__ import annotations

import sys
from pathlib import Path


def check_file(filepath: Path) -> tuple[bool, list[str]]:
    """Retourne (ok, missing_markers)."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False, ["fichier introuvable ou illisible"]

    missing: list[str] = []

    has_event_listener = "@event.listens_for" in content and '"connect"' in content
    has_pragma_on = "PRAGMA foreign_keys=ON" in content or "PRAGMA foreign_keys = ON" in content

    if not has_event_listener:
        missing.append("@event.listens_for(engine, 'connect') event listener absent")
    if not has_pragma_on:
        missing.append('PRAGMA foreign_keys=ON absent (cursor.execute("PRAGMA foreign_keys=ON"))')

    return len(missing) == 0, missing


def main(argv: list[str]) -> int:
    files = [Path(f) for f in argv[1:]]

    for filepath in files:
        if not filepath.exists():
            continue
        if filepath.name != "connection.py":
            continue

        ok, missing = check_file(filepath)
        if not ok:
            print("Anti-PRAGMA-OFF (ADR-016 Pilier 2) :", file=sys.stderr)
            print(f"  {filepath} — marqueurs manquants :", file=sys.stderr)
            for m in missing:
                print(f"    • {m}", file=sys.stderr)
            print(file=sys.stderr)
            print(
                "Phase 5.6 F1 a fixe ce pattern. Sans PRAGMA foreign_keys=ON :",
                file=sys.stderr,
            )
            print(
                "  • RGPD ondelete=SET NULL x 4 FK silencieusement non-enforced runtime",
                file=sys.stderr,
            )
            print("  • Cascade DELETE non triggered sous SQLite", file=sys.stderr)
            print(file=sys.stderr)
            print("Pattern attendu :", file=sys.stderr)
            print('  @event.listens_for(engine, "connect")', file=sys.stderr)
            print(
                '  def _set_sqlite_pragma(...): cursor.execute("PRAGMA foreign_keys=ON")',
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
