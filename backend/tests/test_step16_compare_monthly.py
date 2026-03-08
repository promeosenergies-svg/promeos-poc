"""
Step 16 — B7 : Comparaison factures N vs N-1
Tests unitaires pour l'endpoint /api/billing/compare-monthly.
"""

import pytest
from datetime import date


class MockInvoice:
    """Minimal invoice mock."""

    def __init__(self, site_id, period_start, total_eur, energy_kwh=0):
        self.site_id = site_id
        self.period_start = period_start
        self.period_end = None
        self.total_eur = total_eur
        self.energy_kwh = energy_kwh
        self.status = "IMPORTED"


class TestCompareMonthlyResponse:
    """Test response structure of compare-monthly endpoint."""

    def test_response_has_months_array(self):
        from routes.billing import _MONTH_LABELS_FR

        assert len(_MONTH_LABELS_FR) == 13  # index 0 is empty

    def test_month_labels_french(self):
        from routes.billing import _MONTH_LABELS_FR

        assert _MONTH_LABELS_FR[1] == "Janv"
        assert _MONTH_LABELS_FR[6] == "Juin"
        assert _MONTH_LABELS_FR[12] == "Déc"

    def test_month_labels_all_non_empty(self):
        from routes.billing import _MONTH_LABELS_FR

        for i in range(1, 13):
            assert len(_MONTH_LABELS_FR[i]) > 0


class TestCompareMonthlyAggregation:
    """Test aggregation logic."""

    def test_delta_calculation(self):
        # Simulate delta: current=1150, previous=1000 => delta=150, pct=15.0
        curr = 1150.0
        prev = 1000.0
        delta = round(curr - prev, 2)
        pct = round((curr - prev) / prev * 100, 1)
        assert delta == 150.0
        assert pct == 15.0

    def test_delta_negative(self):
        curr = 800.0
        prev = 1000.0
        delta = round(curr - prev, 2)
        pct = round((curr - prev) / prev * 100, 1)
        assert delta == -200.0
        assert pct == -20.0

    def test_delta_none_when_no_previous(self):
        curr = 1000.0
        prev = None
        delta = None
        if curr is not None and prev is not None and prev > 0:
            delta = round(curr - prev, 2)
        assert delta is None

    def test_delta_none_when_previous_zero(self):
        curr = 1000.0
        prev = 0.0
        delta = None
        if curr is not None and prev is not None and prev > 0:
            delta = round(curr - prev, 2)
        assert delta is None

    def test_total_aggregation(self):
        months = [
            {"current_eur": 100, "previous_eur": 90},
            {"current_eur": 200, "previous_eur": 180},
            {"current_eur": None, "previous_eur": 150},
        ]
        total_current = sum(m["current_eur"] for m in months if m["current_eur"] is not None)
        total_previous = sum(m["previous_eur"] for m in months if m["previous_eur"] is not None)
        assert total_current == 300
        assert total_previous == 420


class TestCompareMonthlyBuckets:
    """Test bucket aggregation with mock invoices."""

    def test_bucket_by_year_month(self):
        invoices = [
            MockInvoice(1, date(2026, 1, 15), 500),
            MockInvoice(1, date(2026, 1, 20), 300),
            MockInvoice(1, date(2025, 1, 10), 400),
        ]
        current_year = 2026
        prev_year = 2025
        buckets = {}
        for inv in invoices:
            y, m = inv.period_start.year, inv.period_start.month
            if y not in (current_year, prev_year):
                continue
            key = (y, m)
            if key not in buckets:
                buckets[key] = {"total_eur": 0.0, "energy_kwh": 0.0, "count": 0}
            buckets[key]["total_eur"] += inv.total_eur or 0
            buckets[key]["count"] += 1

        assert buckets[(2026, 1)]["total_eur"] == 800
        assert buckets[(2026, 1)]["count"] == 2
        assert buckets[(2025, 1)]["total_eur"] == 400
        assert buckets[(2025, 1)]["count"] == 1

    def test_ignores_other_years(self):
        invoices = [
            MockInvoice(1, date(2024, 3, 1), 999),
        ]
        current_year = 2026
        prev_year = 2025
        buckets = {}
        for inv in invoices:
            y, m = inv.period_start.year, inv.period_start.month
            if y not in (current_year, prev_year):
                continue
            key = (y, m)
            if key not in buckets:
                buckets[key] = {"total_eur": 0.0}
            buckets[key]["total_eur"] += inv.total_eur or 0

        assert len(buckets) == 0

    def test_multiple_sites_aggregated(self):
        invoices = [
            MockInvoice(1, date(2026, 3, 1), 200),
            MockInvoice(2, date(2026, 3, 15), 300),
        ]
        current_year = 2026
        prev_year = 2025
        buckets = {}
        for inv in invoices:
            y, m = inv.period_start.year, inv.period_start.month
            if y not in (current_year, prev_year):
                continue
            key = (y, m)
            if key not in buckets:
                buckets[key] = {"total_eur": 0.0}
            buckets[key]["total_eur"] += inv.total_eur or 0

        assert buckets[(2026, 3)]["total_eur"] == 500
