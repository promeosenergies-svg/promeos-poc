#!/usr/bin/env python3
"""PROMEOS Sprint C-7 Phase 7.6 — Hook anti-erreur-arithmétique (ADR-016 Pilier 1).

Détecte formules arithmétiques documentées YAML/ADR + vérifie cohérence
calcul Python (tolérance 5%).

Anti-régression Phase 5.6 F3 — erreur ×1000 invisible aux 3 audits SDK
pré-commit cumulés Sprint C-4 :

    Documenté Phase 4.2 : 3.15 × 1.2 / 8760 = 0.000432 EUR/MWh
    Runtime catalog (faux) : 0.43 EUR/MWh (×1000 trop élevé)

Détectée audit deep Phase 5.5 manuel + corrigée Phase 5.6 F3
(YAML 3.15 → 3150 EUR/MW.an + recalcul cohérent).

Patterns détectés :
    - Format multiplication+division : `X * A / B = R` (ASCII *)
    - Format multiplication+division : `X × A / B = R` (Unicode ×)
    - Tolerance 5% (arrondis acceptables)

Usage standalone :
    python scripts/pre_commit_hooks/check_math_consistency.py <fichier.yaml> [...]

Codes retour :
    0 = OK (toutes formules cohérentes)
    1 = formules incohérentes détectées
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Pattern : "X.Y [*×] A.B / C.D = R.S" (whitespaces variables)
FORMULA_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*[*×x]\s*(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*=\s*(\d+(?:[.,]\d+)?)",
)

TOLERANCE_PCT = 0.05  # 5%
MIN_TOLERANCE_ABS = 1e-6  # éviter division-par-quasi-zéro


def _to_float(s: str) -> float:
    """Parse '3,15' ou '3.15' → 3.15."""
    return float(s.replace(",", "."))


def check_file(filepath: Path) -> list[str]:
    """Retourne liste violations (formules incohérentes)."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    violations: list[str] = []

    for match in FORMULA_PATTERN.finditer(content):
        try:
            a = _to_float(match.group(1))
            b = _to_float(match.group(2))
            c = _to_float(match.group(3))
            expected = _to_float(match.group(4))
        except (ValueError, ZeroDivisionError):
            continue

        if c == 0:
            continue  # division par zéro non testable

        actual = a * b / c
        tolerance = max(abs(expected) * TOLERANCE_PCT, MIN_TOLERANCE_ABS)

        if abs(actual - expected) > tolerance:
            line_no = content[: match.start()].count("\n") + 1
            violations.append(
                f"{filepath}:{line_no} — Formule incoherente :\n"
                f"    Documente : {a} x {b} / {c} = {expected}\n"
                f"    Calcul    : {actual:.10g}\n"
                f"    Ecart     : {abs(actual - expected):.6g} (tolerance {tolerance:.6g})"
            )

    return violations


def main(argv: list[str]) -> int:
    files = [Path(f) for f in argv[1:]]
    all_violations: list[str] = []

    for filepath in files:
        if not filepath.exists():
            continue
        all_violations.extend(check_file(filepath))

    if all_violations:
        print("Anti-erreur-arithmetique (ADR-016 Pilier 1) :", file=sys.stderr)
        print(file=sys.stderr)
        for v in all_violations:
            print(f"  • {v}", file=sys.stderr)
        print(file=sys.stderr)
        print(
            "Phase 5.6 F3 a corrige une erreur x1000 (Capacite 3.15 vs 3150) invisible",
            file=sys.stderr,
        )
        print("aux 3 audits SDK pre-commit cumules Sprint C-4.", file=sys.stderr)
        print("Verifier formule arithmetiquement reproductible avant commit.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
