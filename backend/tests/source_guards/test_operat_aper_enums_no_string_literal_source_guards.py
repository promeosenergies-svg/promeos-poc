"""
PROMEOS — Sprint C-1 Phase 3 : Source-guard contre string littéraux Enum.

Force l'usage des classes Enum (`OperatZoneClimatiqueEnum`, `AperCategorieTailleEnum`,
etc.) plutôt que des string littéraux dans les services / routes / API.

Patterns interdits :
  1. Zones climatiques en string littéral (H1a..H3) hors emplacements autorisés
  2. APER catégorie en string littéral (SMALL/LARGE)
  3. Modulation motif en string littéral (4 motifs officiels)
  4. DOM zones en string littéral (Guadeloupe/Martinique/Guyane/Réunion/Mayotte)

Allowlist temporaire (legacy refactor reporté) :
  Voir `_LEGACY_FILES_GRANDFATHERED` ci-dessous.
  Tracker dette : docs/audits/DETTE_TECHNIQUE_TRACKER.md#D-Phase3-Legacy-Zones-001

Référence : matrice v1 §4.4.C/D + audit Phase B doctrine "no hard-code constants".
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


# ─── Allowlist legacy (D-Phase3-Legacy-Zones-001) ────────────────────────────
# Fichiers contenant des zones OPERAT (H1a..H3) en string littéral, dont le
# refactor vers OperatZoneClimatiqueEnum est reporté à un sprint séparé.
# Réf : docs/audits/DETTE_TECHNIQUE_TRACKER.md#D-Phase3-Legacy-Zones-001
# Paths exacts (pas de glob) pour traçabilité fine — ajouter une entrée à
# chaque allowlist requiert une mise à jour explicite du tracker.
_LEGACY_FILES_GRANDFATHERED = {
    "backend/regops/rules/cee_p6.py",  # CEE P6 calculs zone-spécifiques
    "backend/services/weather_provider.py",  # Lookup altitude + département → zone
    "backend/services/aper_service.py",  # Mapping régions DJU + heures équiv solaire
}


# Emplacements autorisés à contenir ces strings littéraux (par dossier/nature)
_ALLOWED_PATH_FRAGMENTS = (
    "models/enums.py",  # SoT enums
    "models/__pycache__",
    "config/",  # YAMLs / JSONs sourcés réglementairement
    "tests/",  # tests + source-guards
    "venv/",
    "venv_python39_backup/",
    "__pycache__/",
    "alembic/",  # migrations historiques
    "scripts/operat_extract_",  # scripts d'extraction OPERAT
    "regops/operat_zones.py",  # resolver zone authentifié
    "data/",
    "docs/",
)

# Périmètre scanné : services + routes + regops/services + schemas
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
    """Liste les fichiers .py à scanner (services + routes + schemas).

    Si `emit_grandfathered_warnings`, émet un DeprecationWarning par fichier
    grandfathered visité (visibilité de la dette à chaque run).
    """
    files: list[Path] = []
    for py_file in _BACKEND_ROOT.rglob("*.py"):
        rel_backend = py_file.relative_to(_BACKEND_ROOT).as_posix()
        rel_repo = py_file.relative_to(_REPO_ROOT).as_posix()

        if any(frag in rel_backend for frag in _ALLOWED_PATH_FRAGMENTS):
            continue
        if not any(frag in rel_backend for frag in _SCAN_PATH_FRAGMENTS):
            continue

        if rel_repo in _LEGACY_FILES_GRANDFATHERED:
            if emit_grandfathered_warnings:
                warnings.warn(
                    f"[GRANDFATHERED] {rel_repo} contient des zones OPERAT en "
                    "string littéral. Refactor reporté — voir "
                    "docs/audits/DETTE_TECHNIQUE_TRACKER.md#D-Phase3-Legacy-Zones-001.",
                    category=DeprecationWarning,
                    stacklevel=2,
                )
            continue

        files.append(py_file)
    return files


def _strip_python_comments_and_docstrings(content: str) -> str:
    """Retire docstrings + commentaires inline pour réduire les faux positifs."""
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


def _scan_pattern(
    pattern: re.Pattern,
    allowed_context: re.Pattern | None = None,
    emit_legacy_warnings: bool = True,
) -> list[str]:
    """Scanne tous les fichiers et retourne les violations."""
    violations: list[str] = []
    for py_file in _iter_python_files(emit_grandfathered_warnings=emit_legacy_warnings):
        try:
            raw = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        sanitized = _strip_python_comments_and_docstrings(raw)
        if not pattern.search(sanitized):
            continue

        rel = py_file.relative_to(_BACKEND_ROOT).as_posix()
        for line_no, line in enumerate(sanitized.splitlines(), start=1):
            if pattern.search(line):
                if allowed_context and allowed_context.search(line):
                    continue
                violations.append(f"{rel}:{line_no}  {line.strip()}")
    return violations


# ─── Tests anti-régression ──────────────────────────────────────────────────


def test_no_hardcoded_zone_climatique_metropole():
    """Patterns H1a/H1b/.../H3 ne doivent pas apparaître en string hors enums/config.

    Allowlist : 3 fichiers legacy (cf. _LEGACY_FILES_GRANDFATHERED).
    """
    pattern = re.compile(r'["\']\b(H1a|H1b|H1c|H2a|H2b|H2c|H2d|H3)\b["\']')
    allowed = re.compile(r"OperatZoneClimatiqueEnum\.\w+")
    violations = _scan_pattern(pattern, allowed)
    assert not violations, (
        "Zone climatique en string littéral détectée hors emplacements autorisés. "
        "Utiliser OperatZoneClimatiqueEnum.\n" + "\n".join(violations)
    )


def test_no_hardcoded_zone_dom():
    """DOM zones en string littéral hors enums/config."""
    pattern = re.compile(r'["\'](Guadeloupe|Martinique|Guyane|Réunion|Mayotte)["\']')
    allowed = re.compile(r"OperatZoneClimatiqueEnum\.\w+")
    violations = _scan_pattern(pattern, allowed)
    assert not violations, "Zone DOM en string littéral détectée. Utiliser OperatZoneClimatiqueEnum.\n" + "\n".join(
        violations
    )


def test_no_hardcoded_aper_categorie():
    """aper_categorie_taille = 'SMALL'/'LARGE' interdit hors enum."""
    pattern = re.compile(r"aper_categorie\w*\s*[=:]\s*[\"']?(SMALL|LARGE)[\"']?")
    allowed = re.compile(r"AperCategorieTailleEnum\.\w+")
    violations = _scan_pattern(pattern, allowed)
    assert not violations, "aper_categorie_taille en string littéral. Utiliser AperCategorieTailleEnum.\n" + "\n".join(
        violations
    )


def test_no_hardcoded_modulation_motifs():
    """Les 4 motifs officiels art. 12 ne doivent pas être hardcodés."""
    pattern = re.compile(
        r'["\'](COUT_DISPROPORTIONNE|CONSEQUENCES_NEGATIVES|PATRIMOINE_INCOMPATIBILITE|CHANGEMENT_ACTIVITE)["\']'
    )
    allowed = re.compile(r"OperatModulationMotifEnum\.\w+")
    violations = _scan_pattern(pattern, allowed)
    assert not violations, "Motif modulation DT en string littéral. Utiliser OperatModulationMotifEnum.\n" + "\n".join(
        violations
    )


# ─── Test méta-allowlist ────────────────────────────────────────────────────


def test_grandfathered_files_still_exist():
    """Tous les fichiers de l'allowlist doivent encore exister (anti-zombies).

    Si un fichier grandfathered est supprimé, retirer aussi son entrée de
    `_LEGACY_FILES_GRANDFATHERED` ET du tracker dette technique.
    """
    for rel_path in _LEGACY_FILES_GRANDFATHERED:
        full_path = _REPO_ROOT / rel_path
        assert full_path.is_file(), (
            f"Fichier grandfathered absent : {rel_path}. Retirer de _LEGACY_FILES_GRANDFATHERED + tracker dette."
        )


def test_grandfathered_documented_in_tracker():
    """Tracker dette technique doit référencer chaque fichier grandfathered."""
    tracker_path = _REPO_ROOT / "docs" / "audits" / "DETTE_TECHNIQUE_TRACKER.md"
    if not tracker_path.is_file():
        pytest.fail(f"Tracker dette manquant : {tracker_path}. Doit contenir D-Phase3-Legacy-Zones-001.")
    content = tracker_path.read_text(encoding="utf-8")
    assert "D-Phase3-Legacy-Zones-001" in content, "Entrée D-Phase3-Legacy-Zones-001 manquante dans le tracker dette."
    for rel_path in _LEGACY_FILES_GRANDFATHERED:
        # Le tracker peut citer le fichier avec ou sans préfixe backend/
        filename = Path(rel_path).name
        assert filename in content, f"Fichier grandfathered '{filename}' non référencé dans le tracker."
