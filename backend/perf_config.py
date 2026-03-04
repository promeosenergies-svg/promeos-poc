"""
PROMEOS — Performance Budget Configuration
Central thresholds for backend performance budgets.
All values overridable via environment variables.
"""

import os

PERF_THRESHOLDS = {
    # Middleware: log warning for any request slower than this
    "slow_request_ms": float(os.environ.get("PROMEOS_SLOW_REQUEST_MS", "300")),
    # Test budgets: max acceptable response time per critical endpoint
    "test_cockpit_ms": float(os.environ.get("PROMEOS_PERF_COCKPIT_MS", "500")),
    "test_dashboard_2min_ms": float(os.environ.get("PROMEOS_PERF_DASHBOARD_MS", "500")),
    "test_sites_list_ms": float(os.environ.get("PROMEOS_PERF_SITES_MS", "300")),
}
