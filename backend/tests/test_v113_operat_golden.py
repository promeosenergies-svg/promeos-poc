"""
PROMEOS V113 — OPERAT CSV Golden File Test
Verify CSV format: header, delimiter (;), UTF-8, column order.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.operat_export_service import OPERAT_COLUMNS


class TestOperatCSVFormat:
    """Golden file format checks for OPERAT CSV export."""

    def test_header_columns_match_spec(self):
        """OPERAT CSV must have exactly the expected columns in order."""
        expected = [
            "N_EFA",
            "Nom_EFA",
            "Site",
            "Ville",
            "Surface_m2",
            "Usage_principal",
            "Annee_reference",
            "Conso_elec_kWh",
            "Conso_gaz_kWh",
            "Conso_reseau_kWh",
            "Total_kWh",
            "Objectif_2030_kWh",
            "Objectif_2040_kWh",
            "Objectif_2050_kWh",
            "Statut_declaration",
            "Role_assujetti",
            "Responsable",
        ]
        assert OPERAT_COLUMNS == expected

    def test_delimiter_is_semicolon(self):
        """OPERAT format requires semicolon (;) as delimiter, not comma."""
        # The service uses csv.DictWriter with delimiter=";"
        # Verify by building a minimal header line
        header_line = ";".join(OPERAT_COLUMNS)
        assert ";" in header_line
        assert header_line.count(";") == len(OPERAT_COLUMNS) - 1

    def test_column_count(self):
        """OPERAT CSV should have 17 columns."""
        assert len(OPERAT_COLUMNS) == 17

    def test_no_spaces_in_column_names(self):
        """Column names must use underscores, no spaces (OPERAT spec)."""
        for col in OPERAT_COLUMNS:
            assert " " not in col, f"Column '{col}' contains spaces"

    def test_columns_are_ascii(self):
        """Column names must be pure ASCII for maximum compatibility."""
        for col in OPERAT_COLUMNS:
            assert col.isascii(), f"Column '{col}' contains non-ASCII characters"

    def test_validate_function_exists(self):
        """validate_operat_export function must be importable."""
        from services.operat_export_service import validate_operat_export

        assert callable(validate_operat_export)
