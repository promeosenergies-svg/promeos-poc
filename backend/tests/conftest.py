"""
PROMEOS - Test conftest: ensure DB state is consistent between test files.

Re-seeds HELIOS demo data before the test session to guarantee site_id=1 exists
for all tests using TestClient(app) against the real DB.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_demo_data():
    """Seed HELIOS S once at the start of the test session."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        from models import Site

        site_count = db.query(Site).count()
        if site_count < 5:
            from services.demo_seed import SeedOrchestrator

            orch = SeedOrchestrator(db)
            orch.seed("helios", "S", reset=True)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
