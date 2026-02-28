"""
PROMEOS - Demo Seed System Integration Tests
Tests seed→status→reset→reseed cycle for Helios (canonical) and Tertiaire (legacy).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, Meter, MeterReading, MonitoringSnapshot
from models import MonitoringAlert, EnergyInvoice, ActionItem, ComplianceFinding
from models import PurchaseScenarioResult, EmsWeatherCache, ConsumptionInsight


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


def _seed(db, pack="helios", size="S"):
    """Run SeedOrchestrator and return result."""
    from services.demo_seed import SeedOrchestrator
    orch = SeedOrchestrator(db)
    return orch.seed(pack=pack, size=size, rng_seed=42, days=30)


class TestSeedHeliosPack:
    def test_helios_s_creates_5_sites(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["status"] == "ok"
        assert result["sites_count"] == 5
        assert result["org_nom"] == "Groupe HELIOS"
        assert db_session.query(Site).count() == 5

    def test_helios_s_creates_meters(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["meters_count"] == 5
        assert db_session.query(Meter).count() == 5

    def test_helios_s_creates_readings(self, db_session):
        result = _seed(db_session, "helios", "S")
        # Monthly + hourly readings
        assert result["readings_count"] > 0

    def test_helios_s_creates_hourly_readings(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result.get("hourly_readings_count", 0) > 0

    def test_helios_s_has_compliance(self, db_session):
        result = _seed(db_session, "helios", "S")
        findings = result["compliance"]["findings_count"]
        assert findings > 0

    def test_helios_s_has_monitoring(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["monitoring"]["snapshots_count"] > 0

    def test_helios_s_has_invoices(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["billing"]["invoices_count"] == 20

    def test_helios_s_has_actions(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["actions"]["actions_count"] == 15

    def test_helios_s_has_purchase(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["purchase"]["scenarios"] > 0

    def test_helios_s_deterministic(self, db_session):
        """Same seed produces same result."""
        r1 = _seed(db_session, "helios", "S")
        assert r1["sites_count"] == 5
        assert r1["org_nom"] == "Groupe HELIOS"


class TestSeedTertiairePack:
    def test_tertiaire_s_creates_10_sites(self, db_session):
        result = _seed(db_session, "tertiaire", "S")
        assert result["status"] == "ok"
        assert result["sites_count"] == 10
        assert result["org_nom"] == "SCI Les Terrasses"

    def test_tertiaire_s_has_monitoring(self, db_session):
        result = _seed(db_session, "tertiaire", "S")
        assert result["monitoring"]["snapshots_count"] > 0

    def test_tertiaire_s_has_invoices(self, db_session):
        result = _seed(db_session, "tertiaire", "S")
        assert result["billing"]["invoices_count"] == 5

    def test_tertiaire_s_has_actions(self, db_session):
        result = _seed(db_session, "tertiaire", "S")
        assert result["actions"]["actions_count"] == 8


class TestSeedStatus:
    def test_status_after_seed(self, db_session):
        _seed(db_session, "helios", "S")
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        status = orch.status()
        assert status["organisations"] == 1
        assert status["sites"] == 5
        assert status["meters"] == 5
        assert status["readings"] > 0

    def test_status_empty_db(self, db_session):
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        status = orch.status()
        assert status["sites"] == 0
        assert status["readings"] == 0


class TestSeedReset:
    def test_reset_hard_clears_all(self, db_session):
        _seed(db_session, "helios", "S")
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)

        assert db_session.query(Site).count() > 0

        result = orch.reset(mode="hard")
        assert result["status"] == "ok"

        assert db_session.query(Site).count() == 0
        assert db_session.query(Meter).count() == 0
        assert db_session.query(MeterReading).count() == 0

    def test_seed_reset_reseed_cycle(self, db_session):
        """Full cycle: seed → status → reset → status → reseed → status."""
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)

        # 1. Seed
        r1 = orch.seed(pack="tertiaire", size="S", rng_seed=42, days=30)
        assert r1["status"] == "ok"
        s1 = orch.status()
        assert s1["sites"] == 10

        # 2. Reset
        orch.reset(mode="hard")
        s2 = orch.status()
        assert s2["sites"] == 0

        # 3. Reseed
        r3 = orch.seed(pack="tertiaire", size="S", rng_seed=42, days=30)
        assert r3["status"] == "ok"
        s3 = orch.status()
        assert s3["sites"] == 10


class TestSeedValidation:
    def test_invalid_pack(self, db_session):
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        result = orch.seed(pack="nonexistent")
        assert "error" in result

    def test_invalid_size(self, db_session):
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        result = orch.seed(pack="helios", size="XL")
        assert "error" in result


class TestSeedConsistency:
    """Verify KPI consistency between monitoring and dashboard."""

    def test_snapshot_kpis_not_null(self, db_session):
        _seed(db_session, "helios", "S")
        snapshots = db_session.query(MonitoringSnapshot).all()
        assert len(snapshots) > 0
        for snap in snapshots:
            assert snap.kpis_json is not None
            kpis = snap.kpis_json
            assert kpis.get("total_kwh", 0) > 0

    def test_alerts_match_snapshots(self, db_session):
        _seed(db_session, "helios", "S")
        alerts = db_session.query(MonitoringAlert).all()
        snap_ids = {s.id for s in db_session.query(MonitoringSnapshot).all()}
        for a in alerts:
            if a.snapshot_id:
                assert a.snapshot_id in snap_ids


class TestIsDemoFlag:
    """Verify is_demo=True is set on seeded data."""

    def test_org_is_demo(self, db_session):
        _seed(db_session, "helios", "S")
        orgs = db_session.query(Organisation).all()
        assert len(orgs) == 1
        assert orgs[0].is_demo is True

    def test_sites_are_demo(self, db_session):
        _seed(db_session, "helios", "S")
        demo_sites = db_session.query(Site).filter_by(is_demo=True).count()
        all_sites = db_session.query(Site).count()
        assert demo_sites == all_sites == 5

    def test_non_demo_sites_unaffected(self, db_session):
        """Manually inserted non-demo site should have is_demo=False."""
        from models import Portefeuille, EntiteJuridique
        # Seed demo data
        _seed(db_session, "tertiaire", "S")
        # Manually add a non-demo site (borrow portefeuille from demo)
        pf = db_session.query(Portefeuille).first()
        manual_site = Site(
            nom="Manual Site", type=Site.__table__.c.type.type.enum_class.BUREAU,
            portefeuille_id=pf.id, actif=True, is_demo=False,
        )
        db_session.add(manual_site)
        db_session.commit()

        assert db_session.query(Site).count() == 11  # 10 demo + 1 manual
        assert db_session.query(Site).filter_by(is_demo=True).count() == 10
        assert db_session.query(Site).filter_by(is_demo=False).count() == 1


class TestSoftReset:
    """Verify soft reset only deletes is_demo=True data."""

    def test_soft_reset_clears_demo_data(self, db_session):
        _seed(db_session, "helios", "S")
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)

        assert db_session.query(Site).count() == 5

        result = orch.reset(mode="soft")
        assert result["status"] == "ok"
        assert result["mode"] == "soft"

        assert db_session.query(Site).count() == 0
        assert db_session.query(Meter).count() == 0
        assert db_session.query(MeterReading).count() == 0
        assert db_session.query(Organisation).count() == 0

    def test_soft_reset_no_demo_data(self, db_session):
        """Soft reset on empty DB returns no_demo_data message."""
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        result = orch.reset(mode="soft")
        assert result["status"] == "ok"
        assert result.get("message") == "no_demo_data"

    def test_soft_reset_then_reseed(self, db_session):
        """Full cycle: seed → soft reset → reseed."""
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)

        r1 = orch.seed(pack="tertiaire", size="S", rng_seed=42, days=30)
        assert r1["status"] == "ok"
        assert db_session.query(Site).count() == 10

        orch.reset(mode="soft")
        assert db_session.query(Site).count() == 0

        r2 = orch.seed(pack="tertiaire", size="S", rng_seed=42, days=30)
        assert r2["status"] == "ok"
        assert db_session.query(Site).count() == 10

    def test_soft_reset_deletes_all_child_tables(self, db_session):
        """Ensure all child tables are cleaned by soft reset."""
        _seed(db_session, "helios", "S")
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)

        assert db_session.query(MonitoringSnapshot).count() > 0
        assert db_session.query(EnergyInvoice).count() > 0
        assert db_session.query(ComplianceFinding).count() > 0

        result = orch.reset(mode="soft")
        assert result["status"] == "ok"

        assert db_session.query(MonitoringSnapshot).count() == 0
        assert db_session.query(MonitoringAlert).count() == 0
        assert db_session.query(EnergyInvoice).count() == 0
        assert db_session.query(ActionItem).count() == 0
        assert db_session.query(ComplianceFinding).count() == 0
        assert db_session.query(ConsumptionInsight).count() == 0
        assert db_session.query(PurchaseScenarioResult).count() == 0


class TestScopeInSeedResult:
    """Verify seed-pack returns org_id, default_site_id, names for scope auto-switch."""

    def test_helios_seed_returns_org_id(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["org_id"] is not None
        assert isinstance(result["org_id"], int)

    def test_helios_seed_returns_org_nom(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["org_nom"] == "Groupe HELIOS"

    def test_helios_seed_returns_default_site_id(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["default_site_id"] is not None
        assert isinstance(result["default_site_id"], int)
        site = db_session.query(Site).filter(Site.id == result["default_site_id"]).first()
        assert site is not None

    def test_helios_seed_returns_default_site_name(self, db_session):
        result = _seed(db_session, "helios", "S")
        assert result["default_site_name"] is not None
        assert len(result["default_site_name"]) > 0

    def test_tertiaire_seed_returns_sci_org(self, db_session):
        result = _seed(db_session, "tertiaire", "S")
        assert result["org_nom"] == "SCI Les Terrasses"
        assert result["org_id"] is not None
        assert result["default_site_id"] is not None
        assert result["default_site_name"] is not None

    def test_status_pack_returns_org_after_seed(self, db_session):
        """status-pack should expose org_id + default_site_id after seed."""
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(db_session)
        seed_result = orch.seed(pack="tertiaire", size="S", rng_seed=42, days=30)

        org = db_session.query(Organisation).first()
        assert org is not None
        assert seed_result["org_id"] == org.id
