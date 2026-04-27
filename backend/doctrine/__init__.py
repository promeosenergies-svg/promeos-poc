"""Doctrine PROMEOS Sol — version exécutable.

Source de vérité narrative : docs/doctrine/doctrine_promeos_sol_v1_1.md
Source de vérité exécutable : ce module.
"""

import hashlib
from pathlib import Path

DOCTRINE_VERSION = "1.1"
DOCTRINE_DATE = "2026-04-27"
DOCTRINE_FILE = Path(__file__).resolve().parents[2] / "docs/doctrine/doctrine_promeos_sol_v1_1.md"


def doctrine_sha256() -> str:
    """SHA256 du fichier doctrine source — utilisé pour détecter les drifts."""
    if not DOCTRINE_FILE.exists():
        raise FileNotFoundError(f"Doctrine file missing: {DOCTRINE_FILE}")
    return hashlib.sha256(DOCTRINE_FILE.read_bytes()).hexdigest()


# Hash gelé v1.1 — toute modification du .md sans bump version → test fail
DOCTRINE_SHA256_FROZEN = "0b08266d1e613bfcd547dbb937762f8e7a09f51191830e2426055f5cdff55d1e"


from .constants import *  # noqa: F401, F403, E402
from .kpi_registry import KPI_REGISTRY  # noqa: F401, E402
from .error_codes import StandardError, ErrorCode  # noqa: F401, E402
