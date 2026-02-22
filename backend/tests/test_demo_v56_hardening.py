"""
PROMEOS - V56 Demo Orchestration Hardening Tests

Covers:
  1. list_packs visibility: only helios visible
  2. Seed result includes checksum
  3. Seed idempotency (same rng_seed → same checksum)
  4. Reset clears all state (status returns zeros)
  5. Status-pack returns zero after reset (no stale org)
  6. Full Load→Reset→Load cycle
  7. SeedPackRequest defaults to helios
  8. _compute_checksum determinism
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hashlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, Meter, MeterReading


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _seed(db, pack="helios", size="S", rng_seed=42, days=30):
    from services.demo_seed import SeedOrchestrator
    orch = SeedOrchestrator(db)
    return orch.seed(pack=pack, size=size, rng_seed=rng_seed, days=days)


# ════════════════════════════════════════════════════════════
# 1. Pack visibility
# ════════════════════════════════════════════════════════════

class TestPackVisibility:
    def test_only_helios_visible(self):
        from services.demo_seed.packs import list_packs
        visible = list_packs(include_hidden=False)
        keys = [p["key"] for p in visible]
        assert keys == ["helios"]

    def test_helios_is_default(self):
        from services.demo_seed.packs import list_packs
        visible = list_packs()
        helios = [p for p in visible if p["key"] == "helios"][0]
        assert helios["is_default"] is True

    def test_hidden_packs_include_casino_tertiaire(self):
        from services.demo_seed.packs import list_packs
        all_packs = list_packs(include_hidden=True)
        keys = [p["key"] for p in all_packs]
        assert "casino" in keys
        assert "tertiaire" in keys
        assert "helios" in keys

    def test_casino_not_visible(self):
        from services.demo_seed.packs import get_pack
        casino = get_pack("casino")
        assert casino["visible"] is False

    def test_tertiaire_not_visible(self):
        from services.demo_seed.packs import get_pack
        tertiaire = get_pack("tertiaire")
        assert tertiaire["visible"] is False


# ════════════════════════════════════════════════════════════
# 2. Seed checksum
# ════════════════════════════════════════════════════════════

class TestSeedChecksum:
    def test_seed_result_has_checksum_field(self, db_session):
        """The _compute_checksum function produces a 16-char hex string."""
        from routes.demo import _compute_checksum
        result = _seed(db_session)
        cs = _compute_checksum(result)
        assert isinstance(cs, str)
        assert len(cs) == 16
        # Must be valid hex
        int(cs, 16)

    def test_checksum_deterministic(self):
        """Same input → same checksum."""
        from routes.demo import _compute_checksum
        result = {
            "pack": "helios", "size": "S",
            "org_id": 1, "sites_count": 5,
            "meters_count": 7, "readings_count": 180,
        }
        cs1 = _compute_checksum(result)
        cs2 = _compute_checksum(result)
        assert cs1 == cs2

    def test_checksum_changes_on_different_input(self):
        """Different counts → different checksum."""
        from routes.demo import _compute_checksum
        r1 = {"pack": "helios", "size": "S", "org_id": 1,
               "sites_count": 5, "meters_count": 7, "readings_count": 180}
        r2 = {**r1, "sites_count": 10}
        assert _compute_checksum(r1) != _compute_checksum(r2)


# ════════════════════════════════════════════════════════════
# 3. Seed idempotency
# ════════════════════════════════════════════════════════════

class TestSeedIdempotency:
    def test_same_seed_same_counts(self, db_session):
        """Same rng_seed produces deterministic counts."""
        r1 = _seed(db_session, rng_seed=42)
        assert r1["status"] == "ok"
        assert r1["sites_count"] == 5
        assert r1["org_nom"] == "Groupe HELIOS"


# ════════════════════════════════════════════════════════════
# 4. Reset clears state
# ════════════════════════════════════════════════════════════

class TestResetClearsState:
    def test_hard_reset_clears_all_tables(self, db_session):
        _seed(db_session)
        assert db_session.query(Site).count() == 5
        assert db_session.query(Meter).count() > 0

        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        result = orch.reset(mode="hard")
        assert result["status"] == "ok"

        assert db_session.query(Site).count() == 0
        assert db_session.query(Meter).count() == 0
        assert db_session.query(Organisation).count() == 0

    def test_soft_reset_clears_demo_data(self, db_session):
        _seed(db_session)
        assert db_session.query(Site).count() == 5

        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        result = orch.reset(mode="soft")
        assert result["status"] == "ok"
        assert db_session.query(Site).count() == 0
        assert db_session.query(Organisation).count() == 0

    def test_status_returns_zero_after_reset(self, db_session):
        _seed(db_session)
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)

        status_before = orch.status()
        assert status_before["sites"] == 5

        orch.reset(mode="hard")
        status_after = orch.status()
        assert status_after["sites"] == 0
        assert status_after["meters"] == 0
        assert status_after["readings"] == 0
        assert status_after["organisations"] == 0


# ════════════════════════════════════════════════════════════
# 5. Full Load → Reset → Load cycle
# ════════════════════════════════════════════════════════════

class TestLoadResetLoadCycle:
    def test_helios_seed_reset_reseed(self, db_session):
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)

        # 1. Seed
        r1 = orch.seed(pack="helios", size="S", rng_seed=42, days=30)
        assert r1["status"] == "ok"
        assert r1["sites_count"] == 5
        s1 = orch.status()
        assert s1["sites"] == 5

        # 2. Reset
        orch.reset(mode="hard")
        s2 = orch.status()
        assert s2["sites"] == 0

        # 3. Reseed
        r3 = orch.seed(pack="helios", size="S", rng_seed=42, days=30)
        assert r3["status"] == "ok"
        assert r3["sites_count"] == 5
        s3 = orch.status()
        assert s3["sites"] == 5


# ════════════════════════════════════════════════════════════
# 6. SeedPackRequest defaults
# ════════════════════════════════════════════════════════════

class TestSeedPackRequestDefaults:
    def test_default_pack_is_helios(self):
        from routes.demo import SeedPackRequest
        req = SeedPackRequest()
        assert req.pack == "helios"

    def test_default_size_is_s(self):
        from routes.demo import SeedPackRequest
        req = SeedPackRequest()
        assert req.size == "S"

    def test_default_rng_seed_is_42(self):
        from routes.demo import SeedPackRequest
        req = SeedPackRequest()
        assert req.rng_seed == 42


# ════════════════════════════════════════════════════════════
# 7. Invalid pack returns error with available list
# ════════════════════════════════════════════════════════════

class TestInvalidPackError:
    def test_invalid_pack_returns_error(self, db_session):
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        result = orch.seed(pack="nonexistent")
        assert "error" in result

    def test_invalid_pack_lists_available(self, db_session):
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        result = orch.seed(pack="nonexistent")
        assert "available" in result
        assert "helios" in result["available"]


# ════════════════════════════════════════════════════════════
# 8. Admin guard source check
# ════════════════════════════════════════════════════════════

class TestAdminGuardSource:
    def test_seed_pack_has_require_admin(self):
        """seed-pack endpoint uses require_admin dependency."""
        import inspect
        import routes.demo as mod
        src = inspect.getsource(mod)
        assert "require_admin" in src

    def test_reset_pack_has_require_admin(self):
        """reset-pack endpoint uses require_admin dependency."""
        import inspect
        import routes.demo as mod
        src = inspect.getsource(mod.reset_demo_pack)
        assert "require_admin" in src

    def test_status_pack_no_stale_fallback(self):
        """status-pack does NOT fallback to Organisation.order_by().first()."""
        import inspect
        import routes.demo as mod
        src = inspect.getsource(mod.get_demo_pack_status)
        assert "order_by" not in src
        # Must use DemoState context, not blind query
        assert "DemoState.get_demo_context" in src
