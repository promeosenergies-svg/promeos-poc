"""
PROMEOS — Sprint C-1 Phase 5 : Source-guard contre régressions V2 adaptatif.

Patterns interdits dans le code de production :
  1. Pondération figée 45/30/25 hardcodée hors V1 legacy ou regs.yaml
  2. Variable globale POIDS_DT/BACS/APER en str/int hors FRAMEWORK_WEIGHTS référence
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]


_ALLOWED_PATH_FRAGMENTS = (
    "config/",  # YAMLs sources
    "tests/",
    "venv/",
    "venv_python39_backup/",
    "__pycache__/",
    "alembic/",
    "data/",
    "docs/",
    "services/compliance_score_service.py",  # SoT (V1 legacy + V2 adaptive)
    "regops/config/",  # regs.yaml + legal_refs.py
    # Strings descriptives légitimes (pas du code actif de pondération) :
    "schemas/kpi_catalog.py",  # formules en string descriptive
    "services/narrative/narrative_generator.py",  # narratifs user-facing
    # Faux positifs (pondérations désagrégation usage, pas compliance) :
    "services/analytics/usage_disaggregation.py",  # désagrégation HOTEL/BUREAU
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


def test_no_hardcoded_45_30_25_pattern():
    """Triplet 45/30/25 ou 0.45/0.30/0.25 sur même ligne hors compliance_score_service."""
    pattern = re.compile(r"(0\.45[\s,].*0\.30[\s,].*0\.25|45[\s,].*30[\s,].*25)")
    violations = _scan(pattern)
    assert not violations, (
        "Pondération figée 45/30/25 détectée hors emplacements autorisés. "
        "Utiliser compute_site_compliance_score() (wrapper V2 adaptatif).\n" + "\n".join(violations)
    )


def test_no_hardcoded_global_poids_dt_bacs_aper():
    """Variables globales POIDS_DT / POIDS_BACS / POIDS_APER hardcodées."""
    pattern = re.compile(r"\bPOIDS_(DT|BACS|APER)\s*=\s*\d+")
    violations = _scan(pattern)
    assert not violations, (
        "Variables globales POIDS_<dim> hardcodées. "
        "Utiliser FRAMEWORK_WEIGHTS depuis compliance_score_service.\n" + "\n".join(violations)
    )


def test_compliance_score_service_exports_v2_helpers():
    """Le service expose les helpers V2 nécessaires (anti-régression API publique)."""
    import services.compliance_score_service as mod

    required = [
        "compute_site_compliance_score",  # API publique
        "_compute_v1_legacy",
        "_compute_v2_adaptive",
        "_is_dt_assujetti",
        "_is_bacs_assujetti",
        "_get_audit_energetique",
        "_solar_toiture_obligation_active",
        "FRAMEWORK_WEIGHTS",
        "_OFFICIAL_WEIGHTS_V2",
    ]
    missing = [name for name in required if not hasattr(mod, name)]
    assert not missing, f"Helpers V2 manquants : {missing}"
