"""
Tests — A.1 minor fix: source-guard for consumption_source annotations.
Verifies kpi_engine.py and consumption_diagnostic.py expose consumption_source.
"""
import pytest
from datetime import datetime

pytestmark = pytest.mark.fast

from services.electric_monitoring.kpi_engine import KPIEngine


def _make_readings(n=48):
    """Generate n hourly readings."""
    base = datetime(2025, 1, 6, 0, 0, 0)  # Monday
    return [
        {"timestamp": datetime(2025, 1, 6 + i // 24, i % 24, 0, 0), "value_kwh": 10.0}
        for i in range(n)
    ]


class TestKPIEngineConsumptionSource:
    """kpi_engine.py must expose consumption_source in output."""

    def test_compute_returns_consumption_source(self):
        engine = KPIEngine()
        readings = _make_readings(48)
        result = engine.compute(readings, interval_minutes=60)
        assert "consumption_source" in result
        assert result["consumption_source"] == "metered"

    def test_empty_kpis_returns_consumption_source(self):
        engine = KPIEngine()
        result = engine.compute([])
        assert "consumption_source" in result
        assert result["consumption_source"] == "metered"

    def test_docstring_references_unified_service(self):
        """KPIEngine docstring mentions get_consumption_summary."""
        assert "get_consumption_summary" in KPIEngine.__doc__

    def test_total_kwh_still_present(self):
        """total_kwh is still computed from raw readings."""
        engine = KPIEngine()
        readings = _make_readings(48)
        result = engine.compute(readings, interval_minutes=60)
        assert result["total_kwh"] == 48 * 10.0


class TestDiagnosticConsumptionSource:
    """consumption_diagnostic.py must expose consumption_source in metrics."""

    def test_get_readings_docstring(self):
        """_get_readings docstring mentions unified service."""
        from services.consumption_diagnostic import _get_readings
        assert "get_consumption_summary" in _get_readings.__doc__

    def test_diagnostic_metrics_have_consumption_source(self):
        """run_diagnostic adds consumption_source to insight metrics."""
        import inspect
        from services import consumption_diagnostic
        source = inspect.getsource(consumption_diagnostic)
        assert 'consumption_source' in source
        assert '"metered"' in source or "'metered'" in source

    def test_consumption_source_in_metrics_block(self):
        """consumption_source is set alongside price_ref in metrics."""
        import inspect
        from services import consumption_diagnostic
        source = inspect.getsource(consumption_diagnostic)
        assert 'metrics["consumption_source"]' in source


class TestGlossaryTerms:
    """glossary.js must contain 3 unified consumption terms (checked via source)."""

    def test_glossary_has_conso_metered(self):
        with open("../frontend/src/ui/glossary.js", encoding="utf-8") as f:
            code = f.read()
        assert "conso_metered" in code
        assert "Consommation mesurée" in code

    def test_glossary_has_conso_billed(self):
        with open("../frontend/src/ui/glossary.js", encoding="utf-8") as f:
            code = f.read()
        assert "conso_billed" in code
        assert "Consommation facturée" in code

    def test_glossary_has_reconciliation_conso(self):
        with open("../frontend/src/ui/glossary.js", encoding="utf-8") as f:
            code = f.read()
        assert "reconciliation_conso" in code
        assert "Réconciliation compteur / facture" in code
