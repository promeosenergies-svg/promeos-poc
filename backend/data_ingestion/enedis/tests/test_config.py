"""Tests for Enedis SGE pipeline configuration (SF4 Phase 1)."""

import os
from unittest.mock import patch

import pytest

from data_ingestion.enedis.config import MAX_RETRIES, get_flux_dir


# ---------------------------------------------------------------------------
# TestGetFluxDir
# ---------------------------------------------------------------------------


class TestGetFluxDir:
    """Tests for get_flux_dir() resolution logic."""

    def test_env_var_set(self, tmp_path):
        """ENEDIS_FLUX_DIR set → returns correct path."""
        with patch.dict(os.environ, {"ENEDIS_FLUX_DIR": str(tmp_path)}):
            result = get_flux_dir()
            assert result == tmp_path

    def test_env_var_absent_no_override(self):
        """ENEDIS_FLUX_DIR absent + no override → ValueError with explicit message."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure ENEDIS_FLUX_DIR is not set
            os.environ.pop("ENEDIS_FLUX_DIR", None)
            with pytest.raises(ValueError, match="ENEDIS_FLUX_DIR environment variable is required"):
                get_flux_dir()

    def test_override_takes_priority(self, tmp_path):
        """Explicit override → used even if env var is set."""
        override_dir = tmp_path / "override"
        override_dir.mkdir()
        with patch.dict(os.environ, {"ENEDIS_FLUX_DIR": str(tmp_path)}):
            result = get_flux_dir(override=str(override_dir))
            assert result == override_dir

    def test_nonexistent_directory(self, tmp_path):
        """Path that does not exist → ValueError."""
        fake = tmp_path / "does_not_exist"
        with patch.dict(os.environ, {"ENEDIS_FLUX_DIR": str(fake)}):
            with pytest.raises(ValueError, match="is not a directory"):
                get_flux_dir()

    def test_empty_override_falls_back_to_env(self, tmp_path):
        """Empty string override → fallback to env var."""
        with patch.dict(os.environ, {"ENEDIS_FLUX_DIR": str(tmp_path)}):
            result = get_flux_dir(override="")
            assert result == tmp_path

    def test_whitespace_override_falls_back_to_env(self, tmp_path):
        """Whitespace-only override → fallback to env var."""
        with patch.dict(os.environ, {"ENEDIS_FLUX_DIR": str(tmp_path)}):
            result = get_flux_dir(override="   ")
            assert result == tmp_path

    def test_override_nonexistent_directory(self, tmp_path):
        """Override pointing to non-existent dir → ValueError."""
        fake = tmp_path / "nope"
        with pytest.raises(ValueError, match="is not a directory"):
            get_flux_dir(override=str(fake))

    def test_none_override_uses_env(self, tmp_path):
        """None override (default) → uses env var."""
        with patch.dict(os.environ, {"ENEDIS_FLUX_DIR": str(tmp_path)}):
            result = get_flux_dir(override=None)
            assert result == tmp_path


# ---------------------------------------------------------------------------
# TestMaxRetries
# ---------------------------------------------------------------------------


class TestMaxRetries:
    """Tests for MAX_RETRIES constant."""

    def test_value(self):
        """MAX_RETRIES is 3."""
        assert MAX_RETRIES == 3

    def test_type(self):
        """MAX_RETRIES is an int."""
        assert isinstance(MAX_RETRIES, int)
