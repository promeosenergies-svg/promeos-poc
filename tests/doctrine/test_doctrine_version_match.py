"""Vérifie que le fichier doctrine n'a pas drifté sans bump de version."""
import pytest

from doctrine import doctrine_sha256, DOCTRINE_SHA256_FROZEN, DOCTRINE_VERSION


def test_doctrine_file_sha256_matches_frozen():
    """Si ce test fail : soit bump version (1.1 → 1.2 + nouveau hash), soit revert le .md."""
    if DOCTRINE_SHA256_FROZEN.startswith("FILL_IN"):
        pytest.skip("DOCTRINE_SHA256_FROZEN à remplir lors du premier commit")
    assert doctrine_sha256() == DOCTRINE_SHA256_FROZEN, (
        f"Doctrine file modifiée sans bump version. "
        f"Version actuelle: {DOCTRINE_VERSION}. "
        f"Si modification voulue, bumper DOCTRINE_VERSION et mettre à jour DOCTRINE_SHA256_FROZEN."
    )
