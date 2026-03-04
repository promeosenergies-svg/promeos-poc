"""
PROMEOS — Test configuration.

Sets DEMO_MODE=true for the test suite so that unauthenticated
API requests fall back to demo mode (matching dev/CI behavior).

This file MUST be loaded before any backend module import — pytest
discovers conftest.py before test collection, which triggers os.environ
before middleware/auth.py reads the variable at import time.
"""

import os
import pytest

os.environ.setdefault("PROMEOS_DEMO_MODE", "true")


@pytest.fixture(autouse=True)
def _clear_portfolio_cache():
    """Vide le cache portfolio trend avant chaque test pour éviter les interférences.

    Le cache est un dict module-level partagé dans tout le process pytest.
    Sans ce reset, un test qui peuple le cache pour org_id=1 contaminerait
    le test suivant qui recréerait une DB fraîche dont l'org aurait aussi id=1.
    """
    import services.patrimoine_portfolio_cache as _cache

    _cache.clear_all()
    yield
    _cache.clear_all()
