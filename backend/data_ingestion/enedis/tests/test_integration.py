"""Integration tests — decrypt real Enedis SGE files.

Skipped entirely if KEY_1/IV_1 env vars are not set (CI without keys).
Requires real flux files in the flux_enedis/ directory.
"""

import os
from pathlib import Path

import pytest

from data_ingestion.enedis.decrypt import (
    classify_flux,
    decrypt_file,
    load_keys_from_env,
    SKIP_FLUX_TYPES,
)
from data_ingestion.enedis.enums import FluxType

# flux_enedis/ lives outside promeos-poc/, at the Promeos/ root level
_FLUX_DIR = Path(__file__).resolve().parents[5] / "flux_enedis"

_HAS_KEYS = bool(os.environ.get("KEY_1") and os.environ.get("IV_1"))
_HAS_FILES = _FLUX_DIR.is_dir()

pytestmark = pytest.mark.skipif(
    not (_HAS_KEYS and _HAS_FILES),
    reason="Real Enedis keys or flux_enedis/ directory not available",
)


@pytest.fixture(scope="module")
def keys():
    return load_keys_from_env()


def _find_files(subdir: str, pattern: str) -> list[Path]:
    """Find encrypted files matching a glob pattern."""
    base = _FLUX_DIR / subdir if subdir else _FLUX_DIR
    return sorted(base.glob(pattern))


# ========================================================================
# Per-flux-type: decrypt ALL files and validate XML
# ========================================================================


@pytest.mark.parametrize(
    "subdir, pattern, expected_type",
    [
        ("C1-C4", "*_R4H_CDC_*.zip", FluxType.R4H),
        ("C1-C4", "*_R4M_CDC_*.zip", FluxType.R4M),
        ("C1-C4", "*_R4Q_CDC_*.zip", FluxType.R4Q),
        ("C1-C4", "*R171*.zip", FluxType.R171),
        ("C5", "*R50*.zip", FluxType.R50),
        ("C5", "*R151*.zip", FluxType.R151),
    ],
)
def test_decrypt_all_files(keys, subdir, pattern, expected_type):
    """Decrypt ALL files of a given type and validate XML output."""
    files = _find_files(subdir, pattern)
    assert len(files) > 0, f"No {expected_type.value} files found"
    for f in files:
        assert classify_flux(f.name) == expected_type
        xml = decrypt_file(f, keys)
        assert xml.startswith(b"<?xml")


# ========================================================================
# Skipped flux types: classify correctly without crashing
# ========================================================================


@pytest.mark.parametrize(
    "subdir, pattern, expected_type",
    [
        ("C1-C4", "*R172*.zip", FluxType.R172),
        ("", "*X14*.zip", FluxType.X14),
    ],
)
def test_skipped_flux_classified(subdir, pattern, expected_type):
    """Skipped flux types are classified correctly."""
    files = _find_files(subdir, pattern)
    assert len(files) > 0, f"No {expected_type.value} files found"
    for f in files:
        ft = classify_flux(f.name)
        assert ft == expected_type
        assert ft in SKIP_FLUX_TYPES
