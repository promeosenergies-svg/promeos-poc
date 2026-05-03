"""
PROMEOS — Sprint C-2 Phase 2 : Source-guard contre modification directe Site.portefeuille_id.

Force l'usage de `services.site_portefeuille_service.transfer_site_to_portefeuille`
plutôt que `site.portefeuille_id = X` direct — sinon l'historique
SitePortefeuilleHistory n'est pas mis à jour et l'invariant cross-EJ peut être violé.

Allowlist : services existants qui créent un site (ne s'agit pas d'une bascule
mais d'une assignation initiale légitime).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]


# Emplacements autorisés à écrire site.portefeuille_id directement
_ALLOWED_PATH_FRAGMENTS = (
    "tests/",
    "venv/",
    "venv_python39_backup/",
    "__pycache__/",
    "alembic/",
    "data/",
    "docs/",
    # SoT bascule : seul ce service peut écrire portefeuille_id en mode bascule
    "services/site_portefeuille_service.py",
    # Création initiale Site (pas une bascule) :
    "services/onboarding_service.py",
    "services/demo_seed/",  # seed orchestration
    "services/import_mapping.py",
    "services/import_service.py",
    "services/sirene_onboarding_service.py",
    "services/patrimoine_service.py",  # creation/staging
    # Routes legacy CRUD (création initiale) :
    "routes/patrimoine_crud.py",
    "routes/patrimoine/staging.py",  # staging activation
    "routes/import_sites.py",
    "routes/sirene.py",
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


def test_no_direct_site_portefeuille_id_assignment():
    """`site.portefeuille_id = ...` interdit hors site_portefeuille_service.py."""
    pattern = re.compile(r"\bsite\.portefeuille_id\s*=")
    violations = _scan(pattern)
    assert not violations, (
        "Modification directe Site.portefeuille_id détectée hors emplacements autorisés. "
        "Utiliser services.site_portefeuille_service.transfer_site_to_portefeuille pour "
        "préserver historique + invariant cross-EJ + audit log.\n" + "\n".join(violations)
    )


def test_site_portefeuille_service_exposes_required_api():
    """Le service expose les helpers attendus (anti-régression API)."""
    import services.site_portefeuille_service as mod

    required = [
        "transfer_site_to_portefeuille",
        "get_site_history",
        "get_portefeuille_at_date",
        "CrossEjTransferError",
        "PortefeuilleNotFoundError",
        "SiteNotFoundError",
    ]
    missing = [name for name in required if not hasattr(mod, name)]
    assert not missing, f"API site_portefeuille_service manquante : {missing}"
