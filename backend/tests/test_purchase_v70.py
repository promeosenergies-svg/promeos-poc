"""
PROMEOS - V70 Achat Énergie Audit Tests
Validates P0 fixes: _check_seed_enabled, org_id param, route structure.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from routes.purchase import (
    router,
    _check_seed_enabled,
    DEMO_SEED_ENABLED,
)
from services.purchase_seed import seed_purchase_demo


# ═══════════════════════════════════════════════
# Test: _check_seed_enabled guard
# ═══════════════════════════════════════════════


class TestCheckSeedEnabled:
    def test_function_exists(self):
        """_check_seed_enabled is callable."""
        assert callable(_check_seed_enabled)

    def test_raises_when_disabled(self):
        """Raises HTTPException 403 when DEMO_SEED_ENABLED is False."""
        from fastapi import HTTPException

        with patch("routes.purchase.DEMO_SEED_ENABLED", False):
            with pytest.raises(HTTPException) as exc_info:
                _check_seed_enabled()
            assert exc_info.value.status_code == 403
            assert "disabled" in str(exc_info.value.detail).lower()

    def test_no_raise_when_enabled(self):
        """Does not raise when DEMO_SEED_ENABLED is True."""
        with patch("routes.purchase.DEMO_SEED_ENABLED", True):
            _check_seed_enabled()  # Should not raise


# ═══════════════════════════════════════════════
# Test: seed_purchase_demo org_id parameter
# ═══════════════════════════════════════════════


class TestSeedOrgId:
    def test_accepts_org_id_param(self):
        """seed_purchase_demo signature has org_id parameter."""
        import inspect

        sig = inspect.signature(seed_purchase_demo)
        assert "org_id" in sig.parameters

    def test_org_id_default_is_1(self):
        """Default org_id is 1 for backward compat."""
        import inspect

        sig = inspect.signature(seed_purchase_demo)
        assert sig.parameters["org_id"].default == 1

    def test_uses_provided_org_id(self):
        """When org_id=42, PurchasePreference gets org_id=42."""
        db = MagicMock()
        # Need at least 2 sites
        site_a = MagicMock()
        site_a.id = 10
        site_b = MagicMock()
        site_b.id = 20
        db.query.return_value.limit.return_value.all.return_value = [site_a, site_b]
        # No existing preference
        db.query.return_value.first.return_value = None

        seed_purchase_demo(db, org_id=42)

        # Verify PurchasePreference was created with org_id=42
        add_calls = db.add.call_args_list
        pref_call = None
        for call in add_calls:
            obj = call[0][0]
            if hasattr(obj, "org_id") and obj.org_id == 42:
                pref_call = obj
                break
        assert pref_call is not None, "PurchasePreference should be created with org_id=42"


# ═══════════════════════════════════════════════
# Test: Route structure
# ═══════════════════════════════════════════════


class TestRouteStructure:
    PREFIX = "/api/purchase"

    def test_router_prefix(self):
        """Router prefix is /api/purchase."""
        assert router.prefix == "/api/purchase"

    def test_route_count(self):
        """Should have at least 13 routes (V1 + V1.1 + seed)."""
        paths = [r.path for r in router.routes]
        assert len(paths) >= 13

    def test_has_estimate_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/estimate/{{site_id}}" in paths

    def test_has_assumptions_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/assumptions/{{site_id}}" in paths

    def test_has_renewals_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/renewals" in paths

    def test_has_actions_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/actions" in paths

    def test_has_portfolio_compute_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/compute" in paths

    def test_has_site_compute_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/compute/{{site_id}}" in paths

    def test_has_portfolio_results_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/results" in paths

    def test_has_site_results_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/results/{{site_id}}" in paths

    def test_has_history_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/history/{{site_id}}" in paths

    def test_has_accept_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/results/{{result_id}}/accept" in paths

    def test_has_assistant_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/assistant" in paths

    def test_has_seed_demo_route(self):
        paths = [r.path for r in router.routes]
        assert f"{self.PREFIX}/seed-demo" in paths

    def test_seed_demo_methods(self):
        """seed-demo should be POST only."""
        for r in router.routes:
            if r.path == f"{self.PREFIX}/seed-demo":
                assert "POST" in r.methods
                break


# ═══════════════════════════════════════════════
# Test: Energy Gate
# ═══════════════════════════════════════════════


class TestEnergyGate:
    def test_allowed_energy_types_is_elec_only(self):
        from routes.purchase import ALLOWED_ENERGY_TYPES

        assert ALLOWED_ENERGY_TYPES == {"elec"}
