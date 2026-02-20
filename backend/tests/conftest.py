"""
PROMEOS — Test configuration.

Sets DEMO_MODE=true for the test suite so that unauthenticated
API requests fall back to demo mode (matching dev/CI behavior).

This file MUST be loaded before any backend module import — pytest
discovers conftest.py before test collection, which triggers os.environ
before middleware/auth.py reads the variable at import time.
"""
import os

os.environ.setdefault("PROMEOS_DEMO_MODE", "true")
