"""Integration tests — decrypt real Enedis SGE files.

Skipped entirely if KEY_1/IV_1 env vars are not set (CI without keys).
Requires real flux files in the flux_enedis/<FLUX>/ directories.
"""

import pytest
import os

from data_ingestion.enedis.decrypt import (
    classify_flux,
    decrypt_file,
    SKIP_FLUX_TYPES,
)
from data_ingestion.enedis.enums import FluxType

from .conftest import _HAS_REAL_FILES, _HAS_REAL_KEYS, find_real_flux_files

pytestmark = pytest.mark.skipif(
    not (_HAS_REAL_KEYS and _HAS_REAL_FILES),
    reason="Real Enedis keys or flux_enedis/ directory not available",
)


# ========================================================================
# Per-flux-type: decrypt ALL files and validate XML
# ========================================================================


@pytest.mark.parametrize(
    "flux_name, expected_type",
    [
        ("R4H", FluxType.R4H),
        ("R4M", FluxType.R4M),
        ("R4Q", FluxType.R4Q),
        ("R171", FluxType.R171),
        ("R50", FluxType.R50),
        ("R151", FluxType.R151),
    ],
)
def test_decrypt_all_files(real_keys, flux_name, expected_type):
    """Decrypt ALL files of a given type and validate XML output."""
    files = find_real_flux_files(flux_name)
    assert len(files) > 0, f"No {expected_type.value} files found"
    for f in files:
        assert classify_flux(f.name) == expected_type
        xml = decrypt_file(f, real_keys)
        assert xml.startswith(b"<?xml")


@pytest.mark.skipif(
    os.environ.get("PROMEOS_RUN_REAL_SF5_TESTS") != "1",
    reason="Set PROMEOS_RUN_REAL_SF5_TESTS=1 to classify real SF5 samples",
)
@pytest.mark.parametrize(
    "flux_name, expected_type",
    [
        ("R63", FluxType.R63),
        ("R64", FluxType.R64),
        ("C68", FluxType.C68),
    ],
)
def test_classify_real_sf5_files_when_enabled(flux_name, expected_type):
    files = find_real_flux_files(flux_name)
    if not files:
        pytest.skip(f"No {expected_type.value} files found")
    for f in files:
        assert classify_flux(f.name) == expected_type


# ========================================================================
# Skipped flux types: classify correctly without crashing
# ========================================================================


@pytest.mark.parametrize(
    "flux_name, expected_type",
    [
        ("R172", FluxType.R172),
        ("X14", FluxType.X14),
    ],
)
def test_skipped_flux_classified(flux_name, expected_type):
    """Skipped flux types are classified correctly."""
    files = find_real_flux_files(flux_name)
    if not files:
        pytest.skip(f"No local {expected_type.value} samples available")
    for f in files:
        ft = classify_flux(f.name)
        assert ft == expected_type
        assert ft in SKIP_FLUX_TYPES
