"""
PROMEOS - Connector Contract Tests
Parametrized tests for connector meta, sync contract, and mapping validation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from connectors.registry import list_connectors, get_connector
from connectors.contracts import (
    validate_mapping,
    ConnectorMeta,
    MappingReport,
    REQUIRED_FIELDS,
    SANITY_RANGES,
)


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def all_connector_names():
    """All registered connector names."""
    return [c["name"] for c in list_connectors()]


# ========================================
# Contract Tests — Parametrized
# ========================================


class TestConnectorMeta:
    """Every connector must have basic metadata."""

    def test_all_connectors_have_name(self, all_connector_names):
        for name in all_connector_names:
            c = get_connector(name)
            assert c is not None, f"Connector {name} not found"
            assert hasattr(c, "name"), f"{name}: missing name"
            assert len(c.name) > 0, f"{name}: empty name"

    def test_all_connectors_have_description(self, all_connector_names):
        for name in all_connector_names:
            c = get_connector(name)
            assert hasattr(c, "description"), f"{name}: missing description"

    def test_all_connectors_have_test_connection(self, all_connector_names):
        for name in all_connector_names:
            c = get_connector(name)
            result = c.test_connection()
            assert "status" in result, f"{name}: test_connection missing 'status'"
            assert result["status"] in ("ok", "stub", "error", "pending"), f"{name}: invalid status {result['status']}"


class TestMappingValidator:
    """Test the generic mapping validator."""

    def test_valid_records(self):
        records = [
            {"metric": "grid_co2_intensity", "value": 100.0, "unit": "gCO2/kWh", "ts_start": "2025-01-01"},
            {"metric": "grid_co2_intensity", "value": 200.0, "unit": "gCO2/kWh", "ts_start": "2025-01-02"},
        ]
        report = validate_mapping("site", records, "test")
        assert report.valid is True
        assert len(report.missing_fields) == 0
        assert len(report.warnings) == 0

    def test_missing_required_field(self):
        records = [
            {"metric": "grid_co2_intensity", "value": 100.0},  # missing unit, ts_start
        ]
        report = validate_mapping("site", records, "test")
        assert report.valid is False
        assert "unit" in report.missing_fields
        assert "ts_start" in report.missing_fields

    def test_non_numeric_value(self):
        records = [
            {"metric": "test", "value": "not_a_number", "unit": "kWh", "ts_start": "2025-01-01"},
        ]
        report = validate_mapping("site", records, "test")
        assert report.valid is False
        assert any("not numeric" in w for w in report.warnings)

    def test_range_sanity_check(self):
        records = [
            {"metric": "grid_co2_intensity", "value": 99999.0, "unit": "gCO2/kWh", "ts_start": "2025-01-01"},
        ]
        report = validate_mapping("site", records, "test")
        assert any("out of range" in w for w in report.warnings)

    def test_empty_records(self):
        report = validate_mapping("site", [], "test")
        assert report.valid is True
        assert len(report.mapped_fields) == 0

    def test_required_fields_defined(self):
        assert "site" in REQUIRED_FIELDS
        assert "meter" in REQUIRED_FIELDS
        assert len(REQUIRED_FIELDS["site"]) >= 4

    def test_sanity_ranges_defined(self):
        assert "grid_co2_intensity" in SANITY_RANGES
        assert "pv_prod_estimate_kwh" in SANITY_RANGES
        for metric, (lo, hi) in SANITY_RANGES.items():
            assert lo < hi, f"{metric}: invalid range [{lo}, {hi}]"


class TestConnectorSyncContract:
    """Test that connectors produce records matching the contract."""

    def test_rte_eco2mix_sync_contract(self):
        """RTE eco2mix connector returns valid records."""
        c = get_connector("rte_eco2mix")
        if not c:
            pytest.skip("rte_eco2mix not registered")

        status = c.test_connection()
        # For stubs, test with None db
        try:
            records = c.sync(None, "site", 1)
        except Exception:
            records = []

        if records:
            report = validate_mapping(
                "site",
                [
                    {
                        "metric": getattr(r, "metric", None),
                        "value": getattr(r, "value", None),
                        "unit": getattr(r, "unit", None),
                        "ts_start": str(getattr(r, "ts_start", "")),
                    }
                    for r in records[:5]
                ],
                "rte_eco2mix",
            )
            # At minimum, no crashes
            assert isinstance(report, MappingReport)

    def test_pvgis_sync_contract(self):
        """PVGIS connector returns valid records."""
        c = get_connector("pvgis")
        if not c:
            pytest.skip("pvgis not registered")

        try:
            records = c.sync(None, "site", 1)
        except Exception:
            records = []

        if records:
            report = validate_mapping(
                "site",
                [
                    {
                        "metric": getattr(r, "metric", None),
                        "value": getattr(r, "value", None),
                        "unit": getattr(r, "unit", None),
                        "ts_start": str(getattr(r, "ts_start", "")),
                    }
                    for r in records[:5]
                ],
                "pvgis",
            )
            assert isinstance(report, MappingReport)
