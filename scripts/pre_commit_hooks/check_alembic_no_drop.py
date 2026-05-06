#!/usr/bin/env python3
"""PROMEOS Sprint C-7 Phase 7.6 — Hook anti-DROP Alembic (ADR-016 Pilier 5).

Bloque `op.drop_table` / `op.drop_index` / `op.drop_constraint` dans migrations Alembic.

Anti-régression cardinal : ~270+ drop_table autogenerate retirés cumul Phase C
(11 migrations propres / 0 destructive).

Cumul Phase C détaillé :
- Phase 4.4 (17 retirés) — Cascade Org/EJ/PF
- Phase 5.1 (14 retirés) — BillAnomaly
- Phase 5.3 (63 retirés) — RGPD consentement_by + cgu_version
- Phase 5.8 (63 retirés) — BillAnomaly UNIQUE
- Phase 7.1 (63 retirés) — Site s_ce_m2
- ... + autres < Phase 4

Override autorisé via commentaire ligne précédente :
    # ALEMBIC_DROP_AUTHORIZED: <justification>
    op.drop_table("legacy_table_archived")

Usage standalone :
    python scripts/pre_commit_hooks/check_alembic_no_drop.py <fichier.py> [...]

Codes retour :
    0 = OK (aucun drop ou tous overrides justifiés)
    1 = violations détectées (drop sans override)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN_PATTERNS = [
    re.compile(r"^\s*op\.drop_table\s*\(", re.MULTILINE),
    re.compile(r"^\s*op\.drop_index\s*\(", re.MULTILINE),
    re.compile(r"^\s*op\.drop_constraint\s*\(", re.MULTILINE),
]

OVERRIDE_PATTERN = re.compile(r"#\s*ALEMBIC_DROP_AUTHORIZED:\s*\S+")
DOWNGRADE_DEF_PATTERN = re.compile(r"^def\s+downgrade\s*\(", re.MULTILINE)
UPGRADE_DEF_PATTERN = re.compile(r"^def\s+upgrade\s*\(", re.MULTILINE)


def _is_in_downgrade(content: str, char_pos: int) -> bool:
    """True si la position char est à l'intérieur d'une fonction downgrade().

    Stratégie : trouver le `def downgrade(` le plus proche en amont
    et le prochain `def ` (ou `def upgrade`). Si char_pos est entre les deux,
    on est dans downgrade.
    """
    # Dernier def downgrade() avant char_pos
    last_downgrade = None
    for match in DOWNGRADE_DEF_PATTERN.finditer(content):
        if match.start() < char_pos:
            last_downgrade = match.start()
        else:
            break
    if last_downgrade is None:
        return False

    # Prochain def (peu importe lequel) après last_downgrade
    next_def = re.search(r"^def\s+\w+\s*\(", content[last_downgrade + 1 :], re.MULTILINE)
    if next_def is None:
        # downgrade est la dernière fonction du fichier
        return char_pos > last_downgrade

    next_def_pos = last_downgrade + 1 + next_def.start()
    return last_downgrade < char_pos < next_def_pos


def check_file(filepath: Path) -> list[str]:
    """Retourne liste violations (chaque violation = 1 string ligne:contenu).

    Skip légitimes :
    - drops dans `def downgrade()` (reverse de upgrade — pattern Alembic standard)
    - override `# ALEMBIC_DROP_AUTHORIZED: <justification>` dans les 3 lignes
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    violations: list[str] = []
    lines = content.split("\n")

    for pattern in FORBIDDEN_PATTERNS:
        for match in pattern.finditer(content):
            # Skip si dans def downgrade() (légitime Alembic)
            if _is_in_downgrade(content, match.start()):
                continue

            line_no = content[: match.start()].count("\n") + 1
            line_content = lines[line_no - 1].strip() if line_no - 1 < len(lines) else ""

            # Vérifier override sur 3 lignes précédentes
            start = max(0, line_no - 3)
            window = "\n".join(lines[start:line_no])
            if OVERRIDE_PATTERN.search(window):
                continue  # Override autorisé

            violations.append(
                f"{filepath}:{line_no} — {line_content}\n"
                f"  → Override autorisé via commentaire ligne précédente : "
                f"`# ALEMBIC_DROP_AUTHORIZED: <justification>`"
            )

    return violations


def main(argv: list[str]) -> int:
    files = [Path(f) for f in argv[1:]]
    all_violations: list[str] = []

    for filepath in files:
        if not filepath.exists():
            continue
        # Skip backups autogenerate (préservés pour audit)
        if filepath.name.endswith(".original-autogenerate"):
            continue
        all_violations.extend(check_file(filepath))

    if all_violations:
        print("Anti-DROP Alembic — violations detectees (ADR-016 Pilier 5) :", file=sys.stderr)
        print(file=sys.stderr)
        for v in all_violations:
            print(f"  • {v}", file=sys.stderr)
        print(file=sys.stderr)
        print(
            "Cumul Phase C : 11 migrations propres / 0 destructive (~270 drop autogenerate retires).",
            file=sys.stderr,
        )
        print(
            "Doctrine anti-DROP cardinale. Justifier override avec contexte legal/business.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
