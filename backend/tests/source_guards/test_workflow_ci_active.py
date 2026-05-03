"""
PROMEOS — Sprint C-1 Phase 2 : Source-guard du source-guard runner.

Objet :
  - Garantir que le dossier `backend/tests/source_guards/` existe.
  - Garantir qu'au moins 15 fichiers source-guards y sont présents.
  - Garantir que le workflow CI `.github/workflows/source_guards.yml` pointe
    bien vers ce dossier (et pas vers un chemin obsolète qui retournait
    silencieusement `0 tests collected` mais sortait en code 0).

Référence audit : R5 audit Phase B 2026-05-03 — workflow CI cassé silencieusement.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import pytest


_TESTS_SOURCE_GUARDS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_SOURCE_GUARDS_DIR.parent.parent  # backend/
_REPO_ROOT = _BACKEND_DIR.parent  # promeos-poc/
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "source_guards.yml"


def test_source_guards_dir_exists():
    """Le dossier backend/tests/source_guards/ doit exister."""
    assert _TESTS_SOURCE_GUARDS_DIR.is_dir(), (
        f"Dossier manquant : {_TESTS_SOURCE_GUARDS_DIR}. "
        "Workflow CI source_guards.yml devient un no-op silencieux si absent."
    )


def test_source_guards_init_present():
    """__init__.py doit être présent (rend le dossier importable)."""
    init_path = _TESTS_SOURCE_GUARDS_DIR / "__init__.py"
    assert init_path.is_file(), f"__init__.py manquant dans {_TESTS_SOURCE_GUARDS_DIR}"


def test_source_guards_files_minimum_count():
    """Au moins 15 fichiers source-guards doivent être présents.

    Référence audit Phase B : 15 fichiers `*_source_guards.py` cumulés à T0
    (audit 2026-05-03), il ne doit pas y en avoir moins.
    """
    pattern = str(_TESTS_SOURCE_GUARDS_DIR / "test_*_source_guards.py")
    files = glob.glob(pattern)
    assert len(files) >= 15, (
        f"Seulement {len(files)} fichiers source-guards trouvés (attendu ≥ 15 selon baseline audit Phase B)."
    )


def test_workflow_ci_yaml_present():
    """Le workflow CI source_guards.yml doit exister."""
    assert _WORKFLOW_PATH.is_file(), (
        f"Workflow CI manquant : {_WORKFLOW_PATH}. Sans lui, les source-guards ne sont jamais exécutés en CI."
    )


def test_workflow_ci_points_to_correct_dir():
    """Le workflow CI doit invoquer pytest sur backend/tests/source_guards/.

    Anti-régression R5 audit Phase B : avant ce fix, le workflow pointait
    vers `tests/source_guards/` (sans préfixe backend/) qui n'existe pas
    quand le workflow tourne depuis la racine du repo → `0 tests collected`
    mais code de sortie 0 = succès factice.
    """
    content = _WORKFLOW_PATH.read_text(encoding="utf-8")

    # Doit contenir l'invocation correcte
    assert re.search(r"pytest\s+backend/tests/source_guards/", content), (
        "Workflow CI ne pointe pas vers `backend/tests/source_guards/`. "
        "Vérifier .github/workflows/source_guards.yml — étape "
        "`Run source-guards pytest suite`."
    )

    # Anti-régression : ne doit PAS contenir l'ancien chemin sans préfixe
    obsolete_pattern = re.search(r"pytest\s+tests/source_guards/(?![\w-])", content)
    if obsolete_pattern:
        # Tolérer si la ligne est commentée
        for line in content.splitlines():
            if obsolete_pattern.re.search(line) and not line.strip().startswith("#"):
                pytest.fail(
                    f"Workflow CI contient encore l'ancien chemin "
                    f"`pytest tests/source_guards/` (sans préfixe `backend/`). "
                    f"Ligne : {line.strip()}"
                )
