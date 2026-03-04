"""
test_import_surface.py — Tests for _parse_surface() in import_sites.py

Covers: French number formats (spaces, commas, NBSP), edge cases (empty, negative, zero, invalid).
"""

import pytest
from routes.import_sites import _parse_surface


class TestParseSurface:
    """Unit tests for the robust surface parser."""

    def test_simple_integer(self):
        assert _parse_surface("1234") == 1234.0

    def test_french_format_space_comma(self):
        assert _parse_surface("1 234,5") == 1234.5

    def test_dot_decimal(self):
        assert _parse_surface("1234.5") == 1234.5

    def test_space_no_decimal(self):
        assert _parse_surface("1 234") == 1234.0

    def test_nbsp_space(self):
        assert _parse_surface("1\u00a0234,5") == 1234.5

    def test_empty_string(self):
        assert _parse_surface("") is None

    def test_none_value(self):
        assert _parse_surface(None) is None

    def test_whitespace_only(self):
        assert _parse_surface("   ") is None

    def test_invalid_text(self):
        assert _parse_surface("abc") is None

    def test_negative_value(self):
        assert _parse_surface("-5") is None

    def test_zero_value(self):
        assert _parse_surface("0") is None

    def test_small_positive(self):
        assert _parse_surface("0.5") == 0.5

    def test_large_value(self):
        assert _parse_surface("12 345 678") == 12345678.0

    def test_trailing_spaces(self):
        assert _parse_surface("  800  ") == 800.0
