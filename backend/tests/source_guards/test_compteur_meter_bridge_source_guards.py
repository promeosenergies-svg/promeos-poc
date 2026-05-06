"""
Source-guard Phase D-2 hotfix Tier 1 P0.3 — Compteur ↔ Meter bridge cardinal.

Anti-pattern Pilier 8 ADR-016 candidat :
"Self-FK orphelin sans wiring service runtime" — toute self-FK ajoutée à un modèle
SoT-onboarding doit déclarer un bridge explicite vers le SoT runtime.

Ce SG vérifie que tout fichier qui écrit `Compteur.sub_meter_of_id` (wizards onboarding,
seed, ingest CSV, API import) appelle ou délègue à `ensure_meter_pair` du bridge.

Audit cardinal : `docs/audits/AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

# Fichiers exclus du scan (modèle, bridge lui-même, migrations Alembic, tests)
_EXCLUDED_PATHS = (
    "models/compteur.py",  # déclaration du champ
    "services/compteur_meter_bridge.py",  # bridge lui-même
    "alembic/versions/",  # migrations DB
    "tests/",  # tests (libres d'écrire ce qu'ils veulent)
    "scripts/",  # scripts utilitaires hors runtime
    "__pycache__/",
    ".venv/",
    "venv/",
)


def _iter_python_files() -> list[Path]:
    """Retourne tous les .py backend hors exclusions."""
    files: list[Path] = []
    for p in BACKEND_ROOT.rglob("*.py"):
        rel = str(p.relative_to(BACKEND_ROOT))
        if any(rel.startswith(ex) or ex in rel for ex in _EXCLUDED_PATHS):
            continue
        files.append(p)
    return files


def test_sg_compteur_sub_meter_of_id_writers_must_use_bridge():
    """Tout fichier qui SET `Compteur.sub_meter_of_id` ou `compteur.sub_meter_of_id = ...`
    DOIT importer/appeler `compteur_meter_bridge.ensure_meter_pair` dans le même fichier.

    Phase D-2 cardinal : interdit qu'un wizard alimente la hiérarchie patrimoine
    sans matérialiser le wiring runtime Meter.parent_meter_id équivalent.
    """
    write_pattern = re.compile(r"\.sub_meter_of_id\s*=", re.MULTILINE)
    bridge_pattern = re.compile(r"ensure_meter_pair|compteur_meter_bridge", re.MULTILINE)

    violations: list[str] = []

    for py in _iter_python_files():
        try:
            src = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if not write_pattern.search(src):
            continue

        if bridge_pattern.search(src):
            continue

        rel = py.relative_to(BACKEND_ROOT)
        violations.append(f"  - {rel}: écrit `sub_meter_of_id` sans wiring `ensure_meter_pair`")

    if violations:
        msg = (
            "Phase D-2 P0.3 violation : self-FK Compteur.sub_meter_of_id orpheline sans bridge.\n"
            "Fichiers en violation :\n" + "\n".join(violations) + "\n\nAnti-pattern Pilier 8 ADR-016 candidat. Voir "
            "`docs/audits/AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md` Option C.\n"
            + "Fix : importer `from services.compteur_meter_bridge import ensure_meter_pair` "
            + "et l'appeler post-flush du Compteur."
        )
        pytest.fail(msg)


def test_sg_compteur_meter_bridge_module_present():
    """Garantit que le module bridge existe (Phase D-2 hotfix Tier 1 livré)."""
    bridge = BACKEND_ROOT / "services" / "compteur_meter_bridge.py"
    assert bridge.exists(), (
        "Phase D-2 P0.3 BLOQUANT : `services/compteur_meter_bridge.py` absent. "
        "ADR-D-01 Option C prévoit ce module pour résoudre la dualité Compteur/Meter."
    )

    src = bridge.read_text(encoding="utf-8")
    assert "def ensure_meter_pair" in src, "Phase D-2 P0.3 BLOQUANT : `ensure_meter_pair` absent du bridge module."
    assert "def find_meter_by_compteur" in src, "Phase D-2 P0.3 BLOQUANT : `find_meter_by_compteur` helper absent."
