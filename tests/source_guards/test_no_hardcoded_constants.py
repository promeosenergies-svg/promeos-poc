"""Source-guard : aucune constante canonique dupliquée hors SoT autorisées.

Ne flag que les patterns qui constituent une NOUVELLE dette
(pas les dettes déjà documentées via xfail ou followups).

- `CO2E_FACTOR_KG_PER_KWH` frontend → dette V120 Option C, xfail dans
  `test_frontend_co2_cleanup.py`, **pas testé ici**.
- `0.0569` → valeur TURPE 7 LU c_HPH légitime dans
  `backend/services/billing_engine/catalog.py` et `tarifs_reglementaires.yaml`.
  Followup `tarifs_sot_consolidation.md` traite la consolidation SoT,
  **pas testé ici**.
"""
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Patterns FUTURES dettes : si ces constantes apparaissent un jour, ALERTE.
# Aucun pattern aujourd'hui — placeholder pour extensions ultérieures.
FORBIDDEN: list[tuple[str, str]] = []


@pytest.mark.parametrize("pattern,reason", FORBIDDEN)
def test_no_forbidden_constant(pattern: str, reason: str) -> None:
    """Fail si un pattern interdit apparaît hors SoT / exclusions."""
    result = subprocess.run(
        ["grep", "-rnE", pattern, "backend/", "frontend/src/"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    violations = result.stdout.splitlines()
    assert not violations, f"Violation ({reason}) :\n" + "\n".join(violations[:10])


def test_co2_factor_canonical_only_in_sot() -> None:
    """Facteur CO₂ exact 0.052 ne doit apparaître QUE dans emission_factors.py.

    Regex `0\\.052([^0-9]|$)` matche le nombre exact, pas 0.0528 etc.
    """
    result = subprocess.run(
        ["grep", "-rlE", "--include=*.py", r"0\.052([^0-9]|$)", "backend/"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    exclude = ("venv/", "venv_python39_backup/", "__pycache__", "/tests/", "/test_")
    files = [f for f in result.stdout.splitlines() if not any(e in f for e in exclude)]
    stray = [f for f in files if "config/emission_factors.py" not in f]
    assert not stray, "0.052 hardcodé hors SoT :\n" + "\n".join(stray[:10])
