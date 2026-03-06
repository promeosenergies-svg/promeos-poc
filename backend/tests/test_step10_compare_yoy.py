"""
PROMEOS — Step 10: Comparaison temporelle N vs N-1 (YoY)
Verifie que le backend supporte compare=yoy sur timeseries
et l'endpoint compare-summary.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── A. Source structure — timeseries_service.py ─────────────────────────────


class TestTimeseriesServiceSource:
    """Tests source-guard sur timeseries_service.py."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "services", "ems", "timeseries_service.py"
        )
        self.source = open(path).read()

    def test_query_timeseries_has_compare_param(self):
        assert "compare: Optional[str]" in self.source or "compare:" in self.source

    def test_compare_yoy_branch(self):
        assert 'compare == "yoy"' in self.source

    def test_query_yoy_prev_function_exists(self):
        assert "def _query_yoy_prev" in self.source

    def test_shift_timestamp_forward_1y_exists(self):
        assert "def _shift_timestamp_forward_1y" in self.source

    def test_compare_summary_function_exists(self):
        assert "def compare_summary" in self.source

    def test_compare_summary_returns_delta_pct(self):
        assert "delta_pct" in self.source

    def test_compare_summary_returns_current_kwh(self):
        assert "current_kwh" in self.source

    def test_compare_summary_returns_previous_kwh(self):
        assert "previous_kwh" in self.source

    def test_prev_series_key_suffix(self):
        assert "_prev" in self.source

    def test_prev_label_n_minus_1(self):
        assert "N-1" in self.source

    def test_shift_handles_leap_year(self):
        # Feb 29 → Feb 28
        assert "day=28" in self.source


# ── B. Routes wiring — ems.py ──────────────────────────────────────────────


class TestEmsRoutesWiring:
    """Verifie que les routes EMS sont branchees pour compare."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "routes", "ems.py"
        )
        self.source = open(path).read()

    def test_compare_param_in_get_timeseries(self):
        assert "compare" in self.source.split("def get_timeseries")[1].split("def ")[0]

    def test_compare_passed_to_query_timeseries(self):
        assert "compare=compare" in self.source

    def test_compare_summary_endpoint_exists(self):
        assert "def get_timeseries_compare_summary" in self.source

    def test_compare_summary_route(self):
        assert "/timeseries/compare-summary" in self.source

    def test_compare_summary_imports(self):
        assert "from services.ems.timeseries_service import compare_summary" in self.source


# ── C. Function importable ──────────────────────────────────────────────────


class TestFunctionImportable:
    """Verifie que les fonctions sont importables."""

    def test_import_compare_summary(self):
        from services.ems.timeseries_service import compare_summary
        assert callable(compare_summary)

    def test_import_shift_timestamp(self):
        from services.ems.timeseries_service import _shift_timestamp_forward_1y
        assert callable(_shift_timestamp_forward_1y)

    def test_shift_daily(self):
        from services.ems.timeseries_service import _shift_timestamp_forward_1y
        result = _shift_timestamp_forward_1y("2024-03-15")
        assert result == "2025-03-15"

    def test_shift_monthly(self):
        from services.ems.timeseries_service import _shift_timestamp_forward_1y
        result = _shift_timestamp_forward_1y("2024-03")
        assert result == "2025-03"

    def test_shift_datetime(self):
        from services.ems.timeseries_service import _shift_timestamp_forward_1y
        result = _shift_timestamp_forward_1y("2024-06-15 14:00:00")
        assert "2025-06-15" in result
        assert "14:00" in result
