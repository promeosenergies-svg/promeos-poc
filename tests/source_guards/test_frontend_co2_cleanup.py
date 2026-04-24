"""Source-guard xfail : CO₂ hardcodé frontend — followup P0 résiduel.

Trace la dette documentée dans docs/audit/followups/co2_frontend_cleanup.md.
strict=True : si le followup est fixé sans retirer ce marker, le test XPASS
(échec visible) = rappel automatique de supprimer ce marker.
"""
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend" / "src"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "V120 Option C migration incomplète sur main — "
        "docs/audit/followups/co2_frontend_cleanup.md. "
        "Retirer ce marker une fois ConsoKpiHeader.jsx migré via "
        "useElecCo2Factor()."
    ),
)
def test_no_co2_factor_import_in_frontend() -> None:
    """FAIL attendu tant que CO2E_FACTOR_KG_PER_KWH est importé frontend."""
    if not FRONTEND.exists():
        pytest.skip("frontend absent")
    result = subprocess.run(
        ["grep", "-rn", "CO2E_FACTOR_KG_PER_KWH", str(FRONTEND)],
        capture_output=True, text=True,
    )
    violations = [
        line for line in result.stdout.splitlines()
        if "__tests__" not in line and "sourceGuards" not in line
    ]
    assert not violations, "Imports restants :\n" + "\n".join(violations[:10])
