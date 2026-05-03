"""
PROMEOS — Sprint C-1 Phase 4 : Source-guard contre valeurs OPERAT hardcodées.

Force l'usage de OperatValeursAbsoluesService (qui consomme les JSON Annexes I+II
+ resolver zones authentifié) plutôt que des valeurs Cabs/CVC/Coeff DJU
hardcodées dans le code de production.

Patterns interdits dans services/, routes/, regops/services/ (hors tests/configs) :
  1. Valeurs CVC en dur (`cvc.*=\\s*\\d+\\.\\d+`)
  2. Cabs en dur (`cabs.*kwh.*=\\s*\\d`)
  3. Coeff DJU en dur (`coeff.*ch_par_dj.*=\\s*0\\.000\\d`)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]


# Emplacements autorisés à contenir ces valeurs littérales
_ALLOWED_PATH_FRAGMENTS = (
    "config/",  # JSONs/YAMLs sourcés
    "tests/",
    "venv/",
    "venv_python39_backup/",
    "__pycache__/",
    "alembic/",
    "scripts/operat_extract_",
    "data/",
    "docs/",
    "regops/services/operat_cabs_service.py",  # SoT service (commentaires/strings docstrings)
)

_SCAN_PATH_FRAGMENTS = (
    "services/",
    "routes/",
    "regops/services/",
    "regops/rules/",
    "schemas/",
    "api/",
    "middleware/",
    "main.py",
)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for py_file in _BACKEND_ROOT.rglob("*.py"):
        rel = py_file.relative_to(_BACKEND_ROOT).as_posix()
        if any(frag in rel for frag in _ALLOWED_PATH_FRAGMENTS):
            continue
        if not any(frag in rel for frag in _SCAN_PATH_FRAGMENTS):
            continue
        files.append(py_file)
    return files


def _strip_comments_docstrings(content: str) -> str:
    """Retire docstrings + commentaires inline."""
    content = re.sub(r'"""[\s\S]*?"""', "", content)
    content = re.sub(r"'''[\s\S]*?'''", "", content)
    lines = []
    for line in content.splitlines():
        if "#" in line:
            code_part = line.split("#", 1)[0]
            lines.append(code_part)
        else:
            lines.append(line)
    return "\n".join(lines)


def _scan(pattern: re.Pattern) -> list[str]:
    violations: list[str] = []
    for py_file in _iter_python_files():
        try:
            raw = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        sanitized = _strip_comments_docstrings(raw)
        if not pattern.search(sanitized):
            continue
        rel = py_file.relative_to(_BACKEND_ROOT).as_posix()
        for line_no, line in enumerate(sanitized.splitlines(), start=1):
            if pattern.search(line):
                violations.append(f"{rel}:{line_no}  {line.strip()}")
    return violations


# ─── Tests ──────────────────────────────────────────────────────────────────


def test_no_hardcoded_cvc_values():
    """Pas d'assignation `cvci...` ou `cvc_kwh...` en dur dans services/routes.

    Ne matche pas `cvc_power_kw` / `cvc_kw` (puissance CVC du bâtiment, champ
    métier différent — ce n'est pas une valeur OPERAT Annexe I).
    """
    pattern = re.compile(r"\b(cvci\w*|cvc_kwh\w*)\s*=\s*\d+\.?\d*")
    violations = _scan(pattern)
    assert not violations, (
        "Valeur CVCi OPERAT hardcodée détectée. Utiliser OperatValeursAbsoluesService.get_cvci_usei().\n"
        + "\n".join(violations)
    )


def test_no_hardcoded_coeff_dju():
    """Pas de coefficient DJU en dur (ex `coeff_ch_par_dj = 0.000247`)."""
    pattern = re.compile(r"coeff_(ch|fr)_par_dj\s*=\s*0\.000\d")
    violations = _scan(pattern)
    assert not violations, (
        "Coefficient DJU hardcodé détecté. Utiliser OperatValeursAbsoluesService.get_coeff_dju().\n"
        + "\n".join(violations)
    )


def test_no_hardcoded_cabs_values():
    """Pas de valeur Cabs hardcodée hors service/configs."""
    # Chercher des assignations style `cabs_2030_kwh_m2_an = 107.0` ou `cabs_kwh = 85`
    pattern = re.compile(r"cabs_\w*kwh\w*\s*=\s*\d+\.?\d*")
    violations = _scan(pattern)
    assert not violations, (
        "Valeur Cabs hardcodée détectée. Utiliser OperatValeursAbsoluesService.compute_cabs_2030().\n"
        + "\n".join(violations)
    )
