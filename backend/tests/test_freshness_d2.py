"""
PROMEOS — D.2 Data Freshness
Tests for compute_site_freshness + endpoint.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from services.data_quality_service import compute_site_freshness


class TestFreshnessStatus:
    """Test status classification based on staleness_days."""

    def _mock_db(self, last_reading=None, last_invoice=None):
        db = MagicMock()
        # Mock meter_ids query
        if last_reading:
            db.query.return_value.filter.return_value.all.return_value = [MagicMock(id=1, parent_meter_id=None)]
            # Mock max(MeterReading.timestamp)
            db.query.return_value.filter.return_value.scalar.side_effect = [
                last_reading,  # meter reading
                last_invoice,  # invoice
            ]
        else:
            db.query.return_value.filter.return_value.all.return_value = []
            db.query.return_value.filter.return_value.scalar.return_value = last_invoice
        return db

    @patch("services.data_quality_service.EnergyInvoice")
    @patch("services.data_quality_service.MeterReading")
    @patch("services.data_quality_service.Meter")
    def test_fresh_within_48h(self, MockMeter, MockReading, MockInvoice):
        today = date(2025, 6, 15)
        yesterday = today - timedelta(days=1)

        db = MagicMock()
        _fake_meter = MagicMock(id=1, parent_meter_id=None)
        db.query.return_value.filter.return_value.all.return_value = [_fake_meter]

        # Simulate: last reading = yesterday, last invoice = 10 days ago
        call_count = [0]

        def scalar_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return yesterday  # last reading
            return today - timedelta(days=10)  # last invoice

        db.query.return_value.filter.return_value.scalar = scalar_side_effect

        result = compute_site_freshness(db, 1, today)

        assert result["status"] == "fresh"
        assert result["label_fr"] == "À jour"
        assert result["staleness_days"] <= 2

    @patch("services.data_quality_service.EnergyInvoice")
    @patch("services.data_quality_service.MeterReading")
    @patch("services.data_quality_service.Meter")
    def test_no_data_status(self, MockMeter, MockReading, MockInvoice):
        today = date(2025, 6, 15)

        db = MagicMock()
        # No meters
        db.query.return_value.filter.return_value.all.return_value = []
        # No invoices
        db.query.return_value.filter.return_value.scalar.return_value = None

        result = compute_site_freshness(db, 1, today)

        assert result["status"] == "no_data"
        assert result["label_fr"] == "Aucune donnée"
        assert result["staleness_days"] == 999
        assert result["last_reading"] is None
        assert result["last_invoice"] is None
        assert len(result["recommendations"]) > 0


class TestFreshnessResult:
    """Test result structure."""

    def test_result_has_required_fields(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.scalar.return_value = None

        result = compute_site_freshness(db, 1, date(2025, 6, 15))

        assert "site_id" in result
        assert "last_reading" in result
        assert "last_invoice" in result
        assert "staleness_days" in result
        assert "status" in result
        assert "label_fr" in result
        assert "recommendations" in result

    def test_status_values_are_valid(self):
        valid_statuses = {"fresh", "recent", "stale", "expired", "no_data"}
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.scalar.return_value = None

        result = compute_site_freshness(db, 1, date(2025, 6, 15))
        assert result["status"] in valid_statuses


class TestFreshnessEndpoint:
    """Verify endpoint exists."""

    def test_freshness_endpoint_exists(self):
        from routes.data_quality import router

        paths = [r.path for r in router.routes]
        assert any("/freshness/{site_id}" in p for p in paths), f"Missing /freshness/{{site_id}} in {paths}"

    def test_freshness_endpoint_is_get(self):
        from routes.data_quality import router

        for r in router.routes:
            if hasattr(r, "path") and "/freshness/{site_id}" in r.path:
                assert "GET" in r.methods


class TestFreshnessRecommendations:
    """Test recommendations based on status."""

    def test_no_data_has_import_recommendation(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.scalar.return_value = None

        result = compute_site_freshness(db, 1, date(2025, 6, 15))

        assert any("import" in r.lower() or "importer" in r.lower() for r in result["recommendations"])

    def test_fresh_has_no_recommendations(self):
        db = MagicMock()
        today = date(2025, 6, 15)
        db.query.return_value.filter.return_value.all.return_value = [MagicMock(id=1, parent_meter_id=None)]

        call_count = [0]

        def scalar_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return today  # last reading = today
            return today  # last invoice = today

        db.query.return_value.filter.return_value.scalar = scalar_side_effect

        result = compute_site_freshness(db, 1, today)
        assert len(result["recommendations"]) == 0
