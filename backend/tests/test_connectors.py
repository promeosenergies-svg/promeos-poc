"""
PROMEOS - Tests for Connectors
Tests the connector registry and individual connectors
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from connectors.registry import list_connectors, get_connector
from connectors.rte_eco2mix import RTEEco2MixConnector
from connectors.pvgis import PVGISConnector


# ========================================
# Tests
# ========================================


def test_connector_registry():
    """Test connector auto-discovery"""
    connectors = list_connectors()

    assert len(connectors) >= 5  # We have at least 5 connectors
    connector_names = [c["name"] for c in connectors]

    # Check for expected connectors
    assert "rte_eco2mix" in connector_names
    assert "pvgis" in connector_names
    assert "enedis_dataconnect" in connector_names


def test_get_connector_valid():
    """Test retrieving a valid connector"""
    connector = get_connector("rte_eco2mix")

    assert connector is not None
    assert isinstance(connector, RTEEco2MixConnector)
    assert connector.name == "rte_eco2mix"
    assert connector.requires_auth is False


def test_get_connector_invalid():
    """Test retrieving non-existent connector returns None"""
    connector = get_connector("nonexistent_connector")

    assert connector is None


def test_rte_connector_attributes():
    """Test RTE connector has required attributes"""
    connector = RTEEco2MixConnector()

    assert hasattr(connector, "name")
    assert hasattr(connector, "description")
    assert hasattr(connector, "requires_auth")
    assert hasattr(connector, "test_connection")
    assert hasattr(connector, "sync")


def test_pvgis_connector_attributes():
    """Test PVGIS connector has required attributes"""
    connector = PVGISConnector()

    assert hasattr(connector, "name")
    assert hasattr(connector, "description")
    assert hasattr(connector, "requires_auth")
    assert connector.requires_auth is False  # Public API


def test_connector_test_connection():
    """Test connector test_connection method"""
    connector = RTEEco2MixConnector()

    # Test should return a dict with status
    result = connector.test_connection()

    assert isinstance(result, dict)
    assert "status" in result
    # Public API should work (unless network issues)
    # Result could be 'ok' or 'error' depending on connectivity


def test_connector_interface():
    """Test all connectors implement the base interface"""
    connectors_data = list_connectors()

    for conn_data in connectors_data:
        connector = get_connector(conn_data["name"])
        if connector:
            # Test that essential methods exist
            assert callable(getattr(connector, "test_connection", None))
            assert callable(getattr(connector, "sync", None))
            # Test attributes
            assert hasattr(connector, "name")
            assert hasattr(connector, "description")


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
