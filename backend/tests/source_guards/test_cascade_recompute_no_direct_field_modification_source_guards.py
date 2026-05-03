"""
PROMEOS — Sprint C-1 Phase 6 : Source-guard contre modifications directes
des champs cascade hors orchestrateur cascade_recompute_service.

Force l'usage de cascade_recompute_on_change pour modifier les champs amont
(code_postal, altitude_m, etc.) — sinon les champs aval (zone, palier, Cabs,
compliance) divergent silencieusement de la source.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]


# Emplacements autorisés à écrire directement les champs cascade
_ALLOWED_PATH_FRAGMENTS = (
    "config/",
    "tests/",
    "venv/",
    "venv_python39_backup/",
    "__pycache__/",
    "alembic/",
    "data/",
    "docs/",
    # SoT cascade : seul ce service peut écrire ces champs en bypass
    "regops/services/cascade_recompute_service.py",
    # SoT compliance : sync_site_unified_score persiste compliance_score_*
    "services/compliance_score_service.py",
    # Coordinator legacy : recompute_site_full appelle sync_site_unified_score
    "services/compliance_coordinator.py",
    # Service snapshot legacy : applique des fields métier dont on n'a pas le contrôle
    "services/compliance_readiness_service.py",
    # Service patrimoine (snapshots, soft-delete propagation)
    "services/patrimoine_service.py",
    "services/patrimoine_snapshot.py",
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


def test_no_direct_cabs_kwh_m2_an_assignment():
    """`site.cabs_kwh_m2_an = ...` interdit hors cascade_recompute_service."""
    pattern = re.compile(r"\bsite\.cabs_kwh_m2_an\s*=")
    violations = _scan(pattern)
    assert not violations, (
        "Modification directe Site.cabs_kwh_m2_an détectée. "
        "Utiliser cascade_recompute_on_change pour cohérence aval.\n" + "\n".join(violations)
    )


def test_no_direct_operat_zone_palier_assignment():
    """`site.operat_zone_climatique = ...` ou `site.operat_palier_altitude = ...` interdit."""
    pattern = re.compile(r"\bsite\.(operat_zone_climatique|operat_palier_altitude)\s*=")
    violations = _scan(pattern)
    assert not violations, (
        "Modification directe Site.operat_zone_climatique / operat_palier_altitude détectée. "
        "Utiliser cascade_recompute_on_change.\n" + "\n".join(violations)
    )


def test_cascade_recompute_service_exports_required_helpers():
    """Le service expose les helpers attendus par routes / tests (anti-régression API)."""
    import regops.services.cascade_recompute_service as mod

    required = [
        "cascade_recompute_on_change",
        "cascade_impact_preview",
        "CASCADE_MAP_MVP_SPRINT_C1",
        "CascadeResult",
        "CascadeAction",
        "_resolve_zone",
        "_resolve_palier",
        "_recompute_cabs",
        "_recompute_compliance",
    ]
    missing = [name for name in required if not hasattr(mod, name)]
    assert not missing, f"Helpers cascade manquants : {missing}"
