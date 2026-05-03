"""
PROMEOS — Sprint C-1 Phase 1 : Tests complétude facteurs CO₂ doctrine.

Objet :
  - Vérifier la présence des 3 facteurs CO₂ canoniques (ELEC, GAZ, GNL).
  - Vérifier la valeur exacte de chaque facteur (sourcing réglementaire).
  - Source-guard : interdire `0.238` (CO2 GNL) hors doctrine/config/tests.

Sources réglementaires :
  - ELEC = 0.052 kgCO2e/kWh : ADEME Base Empreinte V23.6.
  - GAZ NATUREL = 0.227 kgCO2e/kWh : ADEME Base Empreinte V23.6.
  - GNL = 0.238 kgCO2e/kWh : Arrêté du 01/08/2025 NOR ATDL2430864A
    (annexe VII — ajout après 5e ligne tableau facteurs CO₂ vecteurs).

Référence audit : R-bonus B1 (audit Phase B 2026-05-03)
                  + matrice v1 §1 facteurs canoniques.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Tests complétude constantes ─────────────────────────────────────────────


def test_co2_gnl_constant_present():
    """CO2_FACTOR_GNL_KGCO2_PER_KWH doit être importable depuis doctrine."""
    from doctrine.constants import CO2_FACTOR_GNL_KGCO2_PER_KWH

    assert CO2_FACTOR_GNL_KGCO2_PER_KWH == 0.238


def test_co2_factors_sourced():
    """Les 3 facteurs CO₂ canoniques sont distincts et conformes ADEME V23.6 + arrêté."""
    from doctrine.constants import (
        CO2_FACTOR_ELEC_KGCO2_PER_KWH,
        CO2_FACTOR_GAS_KGCO2_PER_KWH,
        CO2_FACTOR_GNL_KGCO2_PER_KWH,
    )

    assert CO2_FACTOR_ELEC_KGCO2_PER_KWH == 0.052
    assert CO2_FACTOR_GAS_KGCO2_PER_KWH == 0.227
    assert CO2_FACTOR_GNL_KGCO2_PER_KWH == 0.238

    # GNL ≠ GAZ NATUREL (impératif doctrinal — ne pas confondre)
    assert CO2_FACTOR_GAS_KGCO2_PER_KWH != CO2_FACTOR_GNL_KGCO2_PER_KWH


def test_co2_gnl_in_all_export():
    """CO2_FACTOR_GNL_KGCO2_PER_KWH doit figurer dans __all__ pour exportation."""
    from doctrine import constants as c

    assert "CO2_FACTOR_GNL_KGCO2_PER_KWH" in c.__all__


# ── Source-guard : 0.238 ne doit apparaître QUE dans des emplacements autorisés ──


def test_co2_gnl_value_not_hardcoded_outside_doctrine():
    """0.238 hardcodé hors constants.py + config/* + tests/* est interdit.

    Pourquoi : éviter qu'un développeur duplique la constante facteur GNL
    dans un service ou route, ce qui ferait diverger silencieusement la
    valeur en cas d'évolution réglementaire (ex : arrêté révisé).
    """
    backend_root = Path(__file__).resolve().parent.parent

    # Patterns autorisés (chemins absolus relatifs à backend/) :
    allowed_path_fragments = [
        "doctrine/constants.py",  # SoT
        "doctrine/__pycache__",
        "config/",  # YAMLs / JSONs sourcés
        "tests/",  # tests + source-guards
        "venv/",  # dépendances tierces (jamais notre code)
        "venv_python39_backup/",
        "__pycache__/",
        "alembic/",  # migrations historiques (figé après commit)
        "scripts/operat_extract_",  # scripts d'extraction OPERAT
        "data/",  # backups DB
    ]

    pattern_value = re.compile(r"\b0\.238\b")
    violations: list[str] = []

    for py_file in backend_root.rglob("*.py"):
        rel = py_file.relative_to(backend_root).as_posix()

        if any(frag in rel for frag in allowed_path_fragments):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        if not pattern_value.search(content):
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            if pattern_value.search(line) and not line.strip().startswith("#"):
                # Tolérer les commentaires inline qui mentionnent la valeur
                # uniquement si la ligne contient #
                if "#" in line:
                    code_part, _, _ = line.partition("#")
                    if not pattern_value.search(code_part):
                        continue
                violations.append(f"{rel}:{line_no}  {line.strip()}")

    assert not violations, (
        "0.238 hardcodé hors emplacements autorisés (doctrine.constants / config / tests). "
        "Importer CO2_FACTOR_GNL_KGCO2_PER_KWH depuis doctrine.constants.\n" + "\n".join(violations)
    )
