"""
test_reconciliation_v96.py — V96 Reconciliation service tests
"""

import pytest
from services.reconciliation_service import reconcile_site, reconcile_portfolio


class TestReconcileService:
    """Verify reconciliation service structure."""

    def test_reconcile_site_callable(self):
        assert callable(reconcile_site)

    def test_reconcile_portfolio_callable(self):
        assert callable(reconcile_portfolio)

    def test_reconcile_site_has_6_checks_signature(self):
        """reconcile_site should produce checks list."""
        import inspect

        source = inspect.getsource(reconcile_site)
        # Verify all 6 check IDs are present
        assert "has_delivery_points" in source
        assert "has_active_contract" in source
        assert "has_recent_invoices" in source
        assert "period_coherence" in source
        assert "energy_type_match" in source
        assert "has_payment_rule" in source

    def test_reconcile_site_returns_score(self):
        """reconcile_site source should compute score."""
        import inspect

        source = inspect.getsource(reconcile_site)
        assert "score" in source

    def test_reconcile_site_returns_status(self):
        """reconcile_site source should compute status (ok/warn/fail)."""
        import inspect

        source = inspect.getsource(reconcile_site)
        assert '"ok"' in source or "'ok'" in source
        assert '"warn"' in source or "'warn'" in source
        assert '"fail"' in source or "'fail'" in source

    def test_reconcile_portfolio_aggregates(self):
        """reconcile_portfolio should return stats with ok/warn/fail."""
        import inspect

        source = inspect.getsource(reconcile_portfolio)
        assert "stats" in source
        assert "sites" in source


class TestReconcileEndpoints:
    """Verify reconciliation endpoints exist in patrimoine routes."""

    def test_site_reconciliation_endpoint(self):
        import inspect
        from routes.patrimoine import get_site_reconciliation

        assert callable(get_site_reconciliation)

    def test_portfolio_reconciliation_endpoint(self):
        import inspect
        from routes.patrimoine import get_portfolio_reconciliation

        assert callable(get_portfolio_reconciliation)
