"""
PROMEOS — V83 HELIOS Seed Tests
Validates: TOUSchedule, NotificationEvent, hourly readings, monitoring.
All generated purely via SeedOrchestrator in a fresh SQLite in-memory DB.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base


# ═══════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════


@pytest.fixture(scope="module")
def seeded_db():
    """Create a fresh in-memory DB and run the helios pack seed once."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    from services.demo_seed.orchestrator import SeedOrchestrator

    orch = SeedOrchestrator(session)
    result = orch.seed(pack="helios", size="S", rng_seed=42)

    assert result.get("status") == "ok", f"Seed failed: {result}"
    yield session, result
    session.close()


# ═══════════════════════════════════════════════
# A. TOUSchedule
# ═══════════════════════════════════════════════


class TestTOUSchedule:
    """V83: 1 active TOUSchedule per HELIOS site."""

    def test_tou_count_matches_sites(self, seeded_db):
        """1 TOUSchedule per site."""
        db, result = seeded_db
        from models.tou_schedule import TOUSchedule

        sites_count = result["sites_count"]
        tou_count = db.query(TOUSchedule).count()
        assert tou_count == sites_count, f"Expected {sites_count} TOU schedules, got {tou_count}"

    def test_tou_are_active(self, seeded_db):
        """All seeded TOUSchedules are is_active=True."""
        db, _ = seeded_db
        from models.tou_schedule import TOUSchedule

        inactive = db.query(TOUSchedule).filter(TOUSchedule.is_active == False).count()
        assert inactive == 0

    def test_tou_windows_have_hp_and_hc(self, seeded_db):
        """windows_json contains both HP and HC periods."""
        db, _ = seeded_db
        from models.tou_schedule import TOUSchedule

        first = db.query(TOUSchedule).first()
        assert first is not None
        windows = json.loads(first.windows_json)
        periods = {w["period"] for w in windows}
        assert "HP" in periods, "HP period missing from TOU windows"
        assert "HC" in periods, "HC period missing from TOU windows"

    def test_tou_has_prices(self, seeded_db):
        """price_hp_eur_kwh and price_hc_eur_kwh are set and HP > HC."""
        db, _ = seeded_db
        from models.tou_schedule import TOUSchedule

        for tou in db.query(TOUSchedule).all():
            assert tou.price_hp_eur_kwh is not None
            assert tou.price_hc_eur_kwh is not None
            assert tou.price_hp_eur_kwh > tou.price_hc_eur_kwh, "HP price should exceed HC"

    def test_tou_seed_result_in_output(self, seeded_db):
        """Seed result includes tou key with created count > 0."""
        _, result = seeded_db
        assert "tou" in result
        assert result["tou"]["tou_created"] > 0


# ═══════════════════════════════════════════════
# B. Notifications
# ═══════════════════════════════════════════════


class TestNotifications:
    """V83: 8 NotificationEvent entries with varied types and statuses."""

    def test_notifications_count(self, seeded_db):
        """Exactly 8 NotificationEvent created."""
        db, _ = seeded_db
        from models.notification import NotificationEvent

        count = db.query(NotificationEvent).count()
        assert count == 8, f"Expected 8 notifications, got {count}"

    def test_notifications_have_new_status(self, seeded_db):
        """At least some notifications are NEW (unread)."""
        db, _ = seeded_db
        from models.notification import NotificationEvent
        from models.enums import NotificationStatus

        new_count = db.query(NotificationEvent).filter(NotificationEvent.status == NotificationStatus.NEW).count()
        assert new_count >= 4, f"Expected >= 4 unread, got {new_count}"

    def test_notifications_have_read_status(self, seeded_db):
        """At least some notifications are READ."""
        db, _ = seeded_db
        from models.notification import NotificationEvent
        from models.enums import NotificationStatus

        read_count = db.query(NotificationEvent).filter(NotificationEvent.status == NotificationStatus.READ).count()
        assert read_count >= 1

    def test_notifications_have_site_id(self, seeded_db):
        """Most notifications are linked to a site."""
        db, _ = seeded_db
        from models.notification import NotificationEvent

        with_site = db.query(NotificationEvent).filter(NotificationEvent.site_id.isnot(None)).count()
        assert with_site >= 6, f"Expected >= 6 with site_id, got {with_site}"

    def test_notifications_severities_vary(self, seeded_db):
        """Multiple severity levels present."""
        db, _ = seeded_db
        from models.notification import NotificationEvent
        from models.enums import NotificationSeverity

        sevs = {r[0] for r in db.query(NotificationEvent.severity).distinct().all()}
        assert len(sevs) >= 2, f"Expected >= 2 severity levels, got {sevs}"

    def test_notifications_source_types_vary(self, seeded_db):
        """Multiple source types present (billing, compliance, consumption, action_hub)."""
        db, _ = seeded_db
        from models.notification import NotificationEvent

        types = {r[0] for r in db.query(NotificationEvent.source_type).distinct().all()}
        assert len(types) >= 3, f"Expected >= 3 source types, got {types}"

    def test_notification_batch_created(self, seeded_db):
        """A NotificationBatch record exists for the seed run."""
        db, _ = seeded_db
        from models.notification import NotificationBatch

        batch = db.query(NotificationBatch).first()
        assert batch is not None
        assert batch.triggered_by == "demo_seed"

    def test_notifications_seed_result(self, seeded_db):
        """Seed result includes notifications key with created count."""
        _, result = seeded_db
        assert "notifications" in result
        assert result["notifications"]["notifications_created"] == 8


# ═══════════════════════════════════════════════
# C. Hourly readings for HELIOS
# ═══════════════════════════════════════════════


class TestHourlyReadingsHelios:
    """V83: HELIOS now has both monthly and hourly MeterReadings."""

    def test_hourly_readings_exist(self, seeded_db):
        """HOURLY MeterReadings exist for HELIOS sites."""
        db, _ = seeded_db
        from models import MeterReading
        from models.energy_models import FrequencyType

        hourly_count = db.query(MeterReading).filter(MeterReading.frequency == FrequencyType.HOURLY).count()
        assert hourly_count > 0, "No HOURLY readings found for HELIOS"

    def test_monthly_readings_still_exist(self, seeded_db):
        """MONTHLY MeterReadings still exist (unchanged)."""
        db, _ = seeded_db
        from models import MeterReading
        from models.energy_models import FrequencyType

        monthly_count = db.query(MeterReading).filter(MeterReading.frequency == FrequencyType.MONTHLY).count()
        assert monthly_count > 0, "MONTHLY readings were lost"

    def test_hourly_count_sufficient_for_monitoring(self, seeded_db):
        """At least 720 hourly readings per site (30 days × 24h minimum)."""
        db, result = seeded_db
        from models import Meter, MeterReading
        from models.energy_models import FrequencyType

        sites_count = result["sites_count"]
        total_hourly = db.query(MeterReading).filter(MeterReading.frequency == FrequencyType.HOURLY).count()
        # At least 720 readings per site (30 days × 24h)
        assert total_hourly >= sites_count * 720, f"Expected >= {sites_count * 720} hourly readings, got {total_hourly}"

    def test_seed_result_has_hourly_count(self, seeded_db):
        """Seed result includes hourly_readings_count for HELIOS."""
        _, result = seeded_db
        assert "hourly_readings_count" in result
        assert result["hourly_readings_count"] > 0


# ═══════════════════════════════════════════════
# D. Monitoring now active for HELIOS
# ═══════════════════════════════════════════════


class TestMonitoringHelios:
    """V83: MonitoringSnapshot + alerts now generated for HELIOS."""

    def test_snapshots_exist(self, seeded_db):
        """At least 1 MonitoringSnapshot generated for HELIOS sites."""
        db, _ = seeded_db
        from models import MonitoringSnapshot

        count = db.query(MonitoringSnapshot).count()
        assert count >= 1, f"Expected >= 1 snapshot, got {count}"

    def test_alerts_exist(self, seeded_db):
        """At least 1 MonitoringAlert generated."""
        db, _ = seeded_db
        from models import MonitoringAlert

        count = db.query(MonitoringAlert).count()
        assert count >= 1, f"Expected >= 1 alert, got {count}"

    def test_consumption_insights_exist(self, seeded_db):
        """At least 1 ConsumptionInsight generated."""
        db, _ = seeded_db
        from models import ConsumptionInsight

        count = db.query(ConsumptionInsight).count()
        assert count >= 1, f"Expected >= 1 insight, got {count}"

    def test_monitoring_not_skipped(self, seeded_db):
        """Seed result monitoring is not skipped (no 'skipped' key)."""
        _, result = seeded_db
        monitoring = result.get("monitoring", {})
        assert "skipped" not in monitoring, f"Monitoring was skipped: {monitoring}"
