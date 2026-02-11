"""
PROMEOS Referentiel — Tests for manifest builder.
Tests build_manifest + write_manifest + SQLite index on synthetic snapshots.
"""
import sys
import os
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scripts.referential.build_manifest import build_manifest, write_manifest, build_sqlite_index


@pytest.fixture
def tmp_snapshots(tmp_path):
    """Create a temporary snapshots directory with synthetic data."""
    snapshots_dir = tmp_path / "snapshots"
    indices_dir = tmp_path / "indices"
    snapshots_dir.mkdir()
    indices_dir.mkdir()

    # Source 1: two snapshots with different hashes (content change)
    src1_d1 = snapshots_dir / "cre_turpe6_test" / "2025-01-01"
    src1_d2 = snapshots_dir / "cre_turpe6_test" / "2025-02-01"
    src1_d1.mkdir(parents=True)
    src1_d2.mkdir(parents=True)

    meta1_v1 = {
        "source_id": "cre_turpe6_test",
        "url": "https://www.cre.fr/test1",
        "sha256_raw": "aaa111",
        "sha256_md": "bbb111",
        "title": "TURPE6 Test v1",
        "fetched_at_utc": "2025-01-01T10:00:00Z",
        "authority": "CRE",
        "category": "tarif_reseau",
        "energy": "electricite",
        "regulation": "TURPE6",
        "tags": ["turpe", "turpe6"],
    }
    meta1_v2 = {
        **meta1_v1,
        "sha256_raw": "aaa222",
        "sha256_md": "bbb222",
        "title": "TURPE6 Test v2",
        "fetched_at_utc": "2025-02-01T10:00:00Z",
    }
    (src1_d1 / "metadata.json").write_text(json.dumps(meta1_v1), encoding="utf-8")
    (src1_d2 / "metadata.json").write_text(json.dumps(meta1_v2), encoding="utf-8")

    # Source 2: single snapshot (no change)
    src2_d1 = snapshots_dir / "legifrance_atrd7_test" / "2025-01-15"
    src2_d1.mkdir(parents=True)

    meta2 = {
        "source_id": "legifrance_atrd7_test",
        "url": "https://www.legifrance.gouv.fr/test2",
        "sha256_raw": "ccc333",
        "sha256_md": "ddd333",
        "title": "ATRD7 JORF Test",
        "fetched_at_utc": "2025-01-15T12:00:00Z",
        "authority": "Legifrance",
        "category": "tarif_reseau",
        "energy": "gaz",
        "regulation": "ATRD7",
        "tags": ["atrd", "gaz"],
    }
    (src2_d1 / "metadata.json").write_text(json.dumps(meta2), encoding="utf-8")

    return snapshots_dir, indices_dir


# ========================================
# Tests
# ========================================

def test_build_manifest_structure(tmp_snapshots):
    """Manifest has expected top-level keys."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir):
        manifest = build_manifest(window_start="2024-02-01", window_end="2026-02-10")

    assert "generated_at" in manifest
    assert "window" in manifest
    assert "sources" in manifest
    assert "stats" in manifest


def test_build_manifest_sources_count(tmp_snapshots):
    """Manifest discovers all source directories."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir):
        manifest = build_manifest()

    assert manifest["stats"]["total_sources"] == 2
    assert "cre_turpe6_test" in manifest["sources"]
    assert "legifrance_atrd7_test" in manifest["sources"]


def test_build_manifest_snapshots_count(tmp_snapshots):
    """Manifest counts all snapshots correctly."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir):
        manifest = build_manifest()

    assert manifest["stats"]["total_snapshots"] == 3  # 2 + 1


def test_build_manifest_change_detection(tmp_snapshots):
    """Content change detected when hashes differ across snapshots."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir):
        manifest = build_manifest()

    src1 = manifest["sources"]["cre_turpe6_test"]
    assert src1["has_content_changes"] is True

    src2 = manifest["sources"]["legifrance_atrd7_test"]
    assert src2["has_content_changes"] is False


def test_build_manifest_latest(tmp_snapshots):
    """Latest snapshot is the most recent one."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir):
        manifest = build_manifest()

    latest = manifest["sources"]["cre_turpe6_test"]["latest"]
    assert latest["date"] == "2025-02-01"
    assert latest["sha256_raw"] == "aaa222"


def test_build_manifest_history(tmp_snapshots):
    """History includes all snapshots in order."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir):
        manifest = build_manifest()

    history = manifest["sources"]["cre_turpe6_test"]["history"]
    assert len(history) == 2
    assert history[0]["date"] == "2025-01-01"
    assert history[1]["date"] == "2025-02-01"
    assert history[0]["content_changed"] is False  # first snapshot
    assert history[1]["content_changed"] is True  # hash changed


def test_build_manifest_metadata_fields(tmp_snapshots):
    """Source entry includes authority, category, energy, tags from metadata."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir):
        manifest = build_manifest()

    src1 = manifest["sources"]["cre_turpe6_test"]
    assert src1["authority"] == "CRE"
    assert src1["category"] == "tarif_reseau"
    assert src1["energy"] == "electricite"
    assert src1["tags"] == ["turpe", "turpe6"]


def test_write_manifest(tmp_snapshots):
    """write_manifest writes valid JSON to indices dir."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir), \
         patch("scripts.referential.build_manifest.INDICES_DIR", indices_dir):
        manifest = build_manifest()
        out_path = write_manifest(manifest)

    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["stats"]["total_sources"] == 2


def test_build_sqlite_index(tmp_snapshots):
    """SQLite index has correct tables and rows."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir), \
         patch("scripts.referential.build_manifest.INDICES_DIR", indices_dir):
        manifest = build_manifest()
        db_path = build_sqlite_index(manifest)

    assert db_path.exists()

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Check sources table
    cur.execute("SELECT COUNT(*) FROM sources")
    assert cur.fetchone()[0] == 2

    # Check snapshots table
    cur.execute("SELECT COUNT(*) FROM snapshots")
    assert cur.fetchone()[0] == 3

    # Check specific source
    cur.execute("SELECT authority, energy FROM sources WHERE source_id = ?", ("cre_turpe6_test",))
    row = cur.fetchone()
    assert row[0] == "CRE"
    assert row[1] == "electricite"

    conn.close()


def test_build_manifest_empty_dir():
    """Manifest handles missing snapshots dir gracefully."""
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", Path("/nonexistent")):
        manifest = build_manifest()

    assert manifest["stats"]["total_sources"] == 0
    assert manifest["stats"]["total_snapshots"] == 0


def test_sources_with_changes_count(tmp_snapshots):
    """Stats correctly count sources with changes."""
    snapshots_dir, indices_dir = tmp_snapshots
    with patch("scripts.referential.build_manifest.SNAPSHOTS_DIR", snapshots_dir):
        manifest = build_manifest()

    assert manifest["stats"]["sources_with_changes"] == 1


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
