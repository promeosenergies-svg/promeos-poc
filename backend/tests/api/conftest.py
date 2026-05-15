"""Conftest local backend/tests/api/ — Sprint M2-3.

Override l'autouse parent `_ensure_seeded` (qui exige DB HELIOS réelle)
pour les tests API qui ne touchent pas la DB métier.

Cohérent pattern Sprint M2-2 backend/tests/unit/conftest.py.
"""

import pytest


@pytest.fixture(scope="module", autouse=True)
def _ensure_seeded():
    """Override le parent conftest._ensure_seeded — tests API standalone."""
    return  # no-op
