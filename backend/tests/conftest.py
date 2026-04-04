"""
PROMEOS - Test conftest: ensure DB state is consistent between test files.

Re-seeds HELIOS demo data when the real DB has fewer than 5 sites.
Runs as an autouse module-scoped fixture so that destructive tests
(reset_db, reset-pack hard) don't break subsequent test modules.
"""

import pytest


def _ensure_seeded():
    """Seed HELIOS S if the real DB has < 5 sites."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        from models import Site

        if db.query(Site).count() < 5:
            from services.demo_seed import SeedOrchestrator

            orch = SeedOrchestrator(db)
            orch.seed("helios", "S", reset=True)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def ensure_demo_data():
    """Re-seed before each test module if the DB was wiped by a prior module."""
    _ensure_seeded()
