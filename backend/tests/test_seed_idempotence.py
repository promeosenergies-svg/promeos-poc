"""
Tests — Seed idempotence (Playbook 1.2).
Verify seeding twice produces the same counts without errors.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models import Site, Organisation, Portefeuille, EntiteJuridique


@pytest.fixture()
def fresh_db():
    """In-memory SQLite database with all tables."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()
    engine.dispose()


def _count_entities(db):
    """Count key entity types."""
    return {
        "organisations": db.query(Organisation).count(),
        "entites_juridiques": db.query(EntiteJuridique).count(),
        "portefeuilles": db.query(Portefeuille).count(),
        "sites": db.query(Site).count(),
    }


def _seed_once(db, pack="helios", size="S"):
    """Run seed orchestrator once."""
    from services.demo_seed.orchestrator import SeedOrchestrator

    orch = SeedOrchestrator(db)
    result = orch.seed(pack=pack, size=size, rng_seed=42)
    db.commit()
    return result


class TestSeedIdempotence:
    """Seed twice with same params → same counts, no crash."""

    def test_first_seed_creates_data(self, fresh_db):
        """First seed creates non-zero entities."""
        _seed_once(fresh_db)
        counts = _count_entities(fresh_db)
        assert counts["organisations"] > 0, "Should create at least 1 org"
        assert counts["sites"] > 0, "Should create at least 1 site"

    def test_reset_and_reseed_same_counts(self, fresh_db):
        """Reset + re-seed with same rng_seed → exactly same counts."""
        _seed_once(fresh_db)
        counts_1 = _count_entities(fresh_db)

        # Reset + re-seed — counts should be identical
        from services.demo_seed.orchestrator import SeedOrchestrator
        orch = SeedOrchestrator(fresh_db)
        orch.reset(mode="hard")
        fresh_db.commit()

        _seed_once(fresh_db)
        counts_2 = _count_entities(fresh_db)

        assert counts_2["organisations"] == counts_1["organisations"], \
            f"Orgs changed: {counts_1['organisations']} → {counts_2['organisations']}"
        assert counts_2["sites"] == counts_1["sites"], \
            f"Sites changed: {counts_1['sites']} → {counts_2['sites']}"

    def test_no_exception_on_reset_reseed(self, fresh_db):
        """Reset + re-seeding does not raise any exception."""
        _seed_once(fresh_db)
        from services.demo_seed.orchestrator import SeedOrchestrator
        orch = SeedOrchestrator(fresh_db)
        orch.reset(mode="hard")
        fresh_db.commit()
        try:
            _seed_once(fresh_db)
        except Exception as exc:
            pytest.fail(f"Reset + re-seed raised: {exc}")

    def test_dialect_is_sqlite(self, fresh_db):
        """In-memory DB uses SQLite dialect."""
        dialect = fresh_db.bind.dialect.name
        assert dialect == "sqlite"
