"""
PROMEOS — Sprint C-2 Phase 1.2 : Source-guard contre écritures AuditLog directes.

Force l'usage de `services.audit_log_service.log_*()` plutôt que `AuditLog(...)` direct.
Pourquoi : centraliser la logique audit (correlation_id, org_id, format payload)
dans un seul service testé/auditable.

Allowlist temporaire : 7 callsites legacy (cf. D-Phase1-Audit-Log-Legacy-Callsites-001).
Refactor progressif vers le service planifié Sprint C-4.
"""

from __future__ import annotations

import os
import re
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent


# ─── Allowlist legacy callsites (D-Phase1-Audit-Log-Legacy-Callsites-001) ────
# Paths relatifs au repo. Refactor progressif Sprint C-4.
# NB : routes/patrimoine/sites.py:508,554 ont été MIGRÉS en Phase 1.2.
_LEGACY_CALLSITES_GRANDFATHERED = {
    "backend/middleware/cx_logger.py",
    "backend/services/intake_service.py",
    "backend/services/operat_export_service.py",
    "backend/services/copilot_engine.py",
    "backend/services/iam_service.py",
}


# Emplacements autorisés à instancier AuditLog directement
_ALLOWED_PATH_FRAGMENTS = (
    "models/iam.py",  # définition de la classe
    "models/__pycache__",
    "tests/",
    "venv/",
    "venv_python39_backup/",
    "__pycache__/",
    "alembic/",
    "data/",
    "docs/",
    # SoT du service : seul ce fichier peut instancier AuditLog en bypass
    "services/audit_log_service.py",
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


def _iter_python_files(emit_grandfathered_warnings: bool = False) -> list[Path]:
    files: list[Path] = []
    for py_file in _BACKEND_ROOT.rglob("*.py"):
        rel_backend = py_file.relative_to(_BACKEND_ROOT).as_posix()
        rel_repo = py_file.relative_to(_REPO_ROOT).as_posix()

        if any(frag in rel_backend for frag in _ALLOWED_PATH_FRAGMENTS):
            continue
        if not any(frag in rel_backend for frag in _SCAN_PATH_FRAGMENTS):
            continue

        if rel_repo in _LEGACY_CALLSITES_GRANDFATHERED:
            if emit_grandfathered_warnings:
                warnings.warn(
                    f"[GRANDFATHERED] {rel_repo} crée des AuditLog directement. "
                    "Refactor reporté — voir D-Phase1-Audit-Log-Legacy-Callsites-001.",
                    category=DeprecationWarning,
                    stacklevel=2,
                )
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


def _scan(pattern: re.Pattern, emit_warnings: bool = True) -> list[str]:
    violations: list[str] = []
    for py_file in _iter_python_files(emit_grandfathered_warnings=emit_warnings):
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


def test_no_direct_audit_log_instantiation():
    """`AuditLog(` création directe interdite hors audit_log_service.py."""
    pattern = re.compile(r"\bAuditLog\(")
    violations = _scan(pattern)
    assert not violations, (
        "Création directe AuditLog() détectée hors emplacements autorisés. "
        "Utiliser services.audit_log_service.log_patrimoine_change() ou log_cascade().\n" + "\n".join(violations)
    )


def test_grandfathered_callsites_still_exist():
    """Tous les fichiers de l'allowlist doivent encore exister (anti-zombies)."""
    for rel_path in _LEGACY_CALLSITES_GRANDFATHERED:
        full_path = _REPO_ROOT / rel_path
        assert full_path.is_file(), (
            f"Fichier grandfathered absent : {rel_path}. Retirer de _LEGACY_CALLSITES_GRANDFATHERED + tracker dette."
        )


def test_grandfathered_documented_in_tracker():
    """Tracker dette doit référencer D-Phase1-Audit-Log-Legacy-Callsites-001."""
    tracker = _REPO_ROOT / "docs" / "audits" / "DETTE_TECHNIQUE_TRACKER.md"
    assert tracker.is_file(), f"Tracker manquant : {tracker}"
    content = tracker.read_text(encoding="utf-8")
    assert "D-Phase1-Audit-Log-Legacy-Callsites-001" in content


def test_audit_log_service_exposes_required_api():
    """audit_log_service expose les helpers attendus."""
    import services.audit_log_service as mod

    required = ["log_patrimoine_change", "log_cascade", "query_audit_trail"]
    missing = [name for name in required if not hasattr(mod, name)]
    assert not missing, f"API audit_log_service manquante : {missing}"
