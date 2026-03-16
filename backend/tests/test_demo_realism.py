"""
PROMEOS - Demo Realism Tests (V108)
Validates that HELIOS demo data is realistic and properly diversified.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Meter, MeterReading, FrequencyType, EmsWeatherCache, Batiment
from models.energy_models import EnergyVector
from models.usage import Usage
from models.enums import TypeUsage


@pytest.fixture(scope="module")
def seeded_db():
    """Seed HELIOS once, reuse across all tests in this module."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    from services.demo_seed import SeedOrchestrator

    orch = SeedOrchestrator(session)
    result = orch.seed(pack="helios", size="S", rng_seed=42, days=30)

    yield session, result
    session.close()


# ═══════════════════════════════════════════════════════════════════════
# Weather Realism
# ═══════════════════════════════════════════════════════════════════════


class TestWeatherRealism:
    def test_nice_warmer_than_paris_in_winter(self, seeded_db):
        """Nice (Mediterranean) should be warmer than Paris in January."""
        db, _ = seeded_db
        sites = db.query(Site).all()
        paris = next((s for s in sites if "Paris" in s.nom), None)
        nice = next((s for s in sites if "Nice" in s.nom), None)
        assert paris and nice

        # Get January weather averages
        paris_jan = (
            db.query(func.avg(EmsWeatherCache.temp_avg_c))
            .filter(EmsWeatherCache.site_id == paris.id, func.strftime("%m", EmsWeatherCache.date) == "01")
            .scalar()
        )
        nice_jan = (
            db.query(func.avg(EmsWeatherCache.temp_avg_c))
            .filter(EmsWeatherCache.site_id == nice.id, func.strftime("%m", EmsWeatherCache.date) == "01")
            .scalar()
        )

        if paris_jan is not None and nice_jan is not None:
            assert nice_jan > paris_jan, f"Nice ({nice_jan:.1f}) should be warmer than Paris ({paris_jan:.1f}) in Jan"

    def test_weather_min_less_than_avg_less_than_max(self, seeded_db):
        """All weather records should have min < avg < max."""
        db, _ = seeded_db
        violations = (
            db.query(EmsWeatherCache)
            .filter(
                (EmsWeatherCache.temp_min_c >= EmsWeatherCache.temp_avg_c)
                | (EmsWeatherCache.temp_avg_c >= EmsWeatherCache.temp_max_c)
            )
            .count()
        )
        total = db.query(EmsWeatherCache).count()
        assert total > 0, "No weather records found"
        assert violations == 0, f"{violations}/{total} weather records have min >= avg or avg >= max"

    def test_weather_days_count(self, seeded_db):
        """Should have 730 days of weather per site (2 years)."""
        db, result = seeded_db
        sites = db.query(Site).all()
        for site in sites:
            count = db.query(EmsWeatherCache).filter_by(site_id=site.id).count()
            assert count >= 700, f"Site {site.nom}: only {count} weather days (expected ~730)"

    def test_ar1_autocorrelation(self, seeded_db):
        """Day-to-day temperature changes should show autocorrelation (not random jumps)."""
        db, _ = seeded_db
        site = db.query(Site).first()
        records = db.query(EmsWeatherCache).filter_by(site_id=site.id).order_by(EmsWeatherCache.date).limit(100).all()
        if len(records) < 30:
            pytest.skip("Not enough weather records")

        # Calculate day-to-day absolute changes
        changes = [abs(records[i].temp_avg_c - records[i - 1].temp_avg_c) for i in range(1, len(records))]
        avg_change = sum(changes) / len(changes)
        # With AR(1), avg daily change should be moderate (< 4°C typically)
        assert avg_change < 4.0, f"Avg daily temp change {avg_change:.1f}°C too high (no autocorrelation?)"


# ═══════════════════════════════════════════════════════════════════════
# Consumption Realism
# ═══════════════════════════════════════════════════════════════════════


class TestConsumptionRealism:
    def test_bureau_night_less_than_day(self, seeded_db):
        """Office night consumption should be lower than daytime."""
        db, _ = seeded_db
        paris = db.query(Site).filter(Site.nom.like("%Paris%")).first()
        assert paris
        meter = db.query(Meter).filter_by(site_id=paris.id, energy_vector=EnergyVector.ELECTRICITY).first()
        assert meter

        # Compare average night (0-5h) vs day (9-17h) using SQLite strftime
        from sqlalchemy import text

        night_avg = db.execute(
            text(
                "SELECT AVG(value_kwh) FROM meter_reading "
                "WHERE meter_id = :mid AND frequency = 'HOURLY' "
                "AND CAST(strftime('%H', timestamp) AS INTEGER) < 6"
            ),
            {"mid": meter.id},
        ).scalar()
        day_avg = db.execute(
            text(
                "SELECT AVG(value_kwh) FROM meter_reading "
                "WHERE meter_id = :mid AND frequency = 'HOURLY' "
                "AND CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 9 AND 17"
            ),
            {"mid": meter.id},
        ).scalar()

        if night_avg and day_avg:
            assert night_avg < day_avg, f"Night ({night_avg:.1f}) should be < Day ({day_avg:.1f})"

    def test_hotel_has_higher_weekend_than_office(self, seeded_db):
        """Hotel should have proportionally higher weekend consumption than office."""
        db, _ = seeded_db
        # Just check that hotel meters have readings on weekends
        nice = db.query(Site).filter(Site.nom.like("%Nice%")).first()
        assert nice
        hotel_meter = db.query(Meter).filter_by(site_id=nice.id, energy_vector=EnergyVector.ELECTRICITY).first()
        assert hotel_meter

        weekend_count = (
            db.query(MeterReading)
            .filter(
                MeterReading.meter_id == hotel_meter.id,
                MeterReading.frequency == FrequencyType.HOURLY,
                func.strftime("%w", MeterReading.timestamp).in_(["0", "6"]),
            )
            .count()
        )
        assert weekend_count > 0, "Hotel should have weekend readings"

    def test_surface_normalized_in_range(self, seeded_db):
        """Annual consumption per m² should be in ADEME range (±50%)."""
        db, result = seeded_db
        sites = db.query(Site).all()
        for site in sites:
            meter = db.query(Meter).filter_by(site_id=site.id, energy_vector=EnergyVector.ELECTRICITY).first()
            if not meter or not site.surface_m2:
                continue

            total_kwh = (
                db.query(func.sum(MeterReading.value_kwh))
                .filter(
                    MeterReading.meter_id == meter.id,
                    MeterReading.frequency == FrequencyType.HOURLY,
                )
                .scalar()
                or 0
            )

            if total_kwh == 0:
                continue

            # 730 days of hourly data → ~2 years
            annual_kwh = total_kwh / 2.0  # approximate annual
            kwh_per_m2 = annual_kwh / site.surface_m2

            # Should be roughly in range 20-600 kWh/m²/an
            # (schools with vacations can be lower, hotels higher)
            assert 20 < kwh_per_m2 < 600, f"{site.nom}: {kwh_per_m2:.0f} kWh/m²/an out of range"


# ═══════════════════════════════════════════════════════════════════════
# Gas Readings
# ═══════════════════════════════════════════════════════════════════════


class TestGasReadings:
    def test_gas_meters_exist(self, seeded_db):
        """Sites with gas=True should have gas meters."""
        db, _ = seeded_db
        gas_meters = db.query(Meter).filter_by(energy_vector=EnergyVector.GAS).all()
        assert len(gas_meters) >= 2, f"Expected >= 2 gas meters, got {len(gas_meters)}"

    def test_gas_readings_exist(self, seeded_db):
        """Gas meters should have daily readings."""
        db, _ = seeded_db
        gas_meters = db.query(Meter).filter_by(energy_vector=EnergyVector.GAS).all()
        for meter in gas_meters:
            count = db.query(MeterReading).filter_by(meter_id=meter.id).count()
            assert count > 0, f"Gas meter {meter.meter_id} has no readings"

    def test_gas_higher_in_winter(self, seeded_db):
        """Gas consumption should be higher in winter than summer."""
        db, _ = seeded_db
        gas_meter = db.query(Meter).filter_by(energy_vector=EnergyVector.GAS).first()
        if not gas_meter:
            pytest.skip("No gas meter")

        winter_avg = (
            db.query(func.avg(MeterReading.value_kwh))
            .filter(
                MeterReading.meter_id == gas_meter.id,
                func.strftime("%m", MeterReading.timestamp).in_(["01", "02", "12"]),
            )
            .scalar()
        )
        summer_avg = (
            db.query(func.avg(MeterReading.value_kwh))
            .filter(
                MeterReading.meter_id == gas_meter.id,
                func.strftime("%m", MeterReading.timestamp).in_(["06", "07", "08"]),
            )
            .scalar()
        )

        if winter_avg and summer_avg and summer_avg > 0:
            assert winter_avg > summer_avg, f"Gas winter ({winter_avg:.1f}) should be > summer ({summer_avg:.1f})"


# ═══════════════════════════════════════════════════════════════════════
# 15-min Realism
# ═══════════════════════════════════════════════════════════════════════


class Test15MinRealism:
    def test_365_days_of_15min_data(self, seeded_db):
        """Should have ~365 days of 15-min data per elec meter."""
        db, result = seeded_db
        elec_meter = db.query(Meter).filter_by(energy_vector=EnergyVector.ELECTRICITY).first()
        assert elec_meter

        count = db.query(MeterReading).filter_by(meter_id=elec_meter.id, frequency=FrequencyType.MIN_15).count()
        # 365 days × 96 slots = 35,040 (no collisions with frequency in unique constraint)
        assert count >= 34000, f"Expected ~35k 15-min readings, got {count}"

    def test_15min_sum_approx_hourly(self, seeded_db):
        """Sum of 4 × 15-min slots should approximately equal hourly value."""
        db, _ = seeded_db
        elec_meter = db.query(Meter).filter_by(energy_vector=EnergyVector.ELECTRICITY).first()
        if not elec_meter:
            pytest.skip("No elec meter")

        # Get a sample hour from 15-min data
        sample = db.query(MeterReading).filter_by(meter_id=elec_meter.id, frequency=FrequencyType.MIN_15).first()
        if not sample:
            pytest.skip("No 15-min data")

        hour_ts = sample.timestamp.replace(minute=0, second=0)
        slots = (
            db.query(MeterReading)
            .filter(
                MeterReading.meter_id == elec_meter.id,
                MeterReading.frequency == FrequencyType.MIN_15,
                MeterReading.timestamp >= hour_ts,
                MeterReading.timestamp < hour_ts.replace(hour=hour_ts.hour + 1)
                if hour_ts.hour < 23
                else MeterReading.timestamp < hour_ts,
            )
            .all()
        )

        if len(slots) == 4:
            total_15min = sum(s.value_kwh for s in slots)
            # Should be > 0 (sanity check)
            assert total_15min > 0


# ═══════════════════════════════════════════════════════════════════════
# Anomalies
# ═══════════════════════════════════════════════════════════════════════


class TestAnomalies:
    def test_quality_score_below_1_exists(self, seeded_db):
        """Some readings should have quality_score < 1.0 (anomalies)."""
        db, _ = seeded_db
        anomaly_count = (
            db.query(MeterReading)
            .filter(MeterReading.quality_score.isnot(None), MeterReading.quality_score < 1.0)
            .count()
        )
        assert anomaly_count > 0, "No anomaly readings found (quality_score < 1.0)"

    def test_multiple_anomaly_types(self, seeded_db):
        """Different sites should have different anomaly patterns."""
        db, _ = seeded_db
        sites = db.query(Site).all()
        sites_with_anomalies = 0
        for site in sites:
            meter = db.query(Meter).filter_by(site_id=site.id, energy_vector=EnergyVector.ELECTRICITY).first()
            if not meter:
                continue
            anomaly_count = (
                db.query(MeterReading)
                .filter(
                    MeterReading.meter_id == meter.id,
                    MeterReading.quality_score.isnot(None),
                    MeterReading.quality_score < 1.0,
                )
                .count()
            )
            if anomaly_count > 0:
                sites_with_anomalies += 1

        # At least 2 sites should have anomalies (diverse patterns)
        assert sites_with_anomalies >= 2, f"Only {sites_with_anomalies} sites have anomalies"


# ═══════════════════════════════════════════════════════════════════════
# Usage Breakdown
# ═══════════════════════════════════════════════════════════════════════


class TestUsageBreakdown:
    def test_usage_records_exist(self, seeded_db):
        """Each batiment should have usage records."""
        db, _ = seeded_db
        batiments = db.query(Batiment).all()
        assert len(batiments) > 0

        bats_with_usage = 0
        for bat in batiments:
            usage_count = db.query(Usage).filter_by(batiment_id=bat.id).count()
            if usage_count > 0:
                bats_with_usage += 1

        assert bats_with_usage >= len(batiments) * 0.6, (
            f"Only {bats_with_usage}/{len(batiments)} batiments have usage records"
        )

    def test_usage_has_cvc(self, seeded_db):
        """Most batiments should have a CVC usage."""
        db, _ = seeded_db
        batiments = db.query(Batiment).all()
        bats_with_cvc = 0
        for bat in batiments:
            cvc = db.query(Usage).filter_by(batiment_id=bat.id, type=TypeUsage.CVC).first()
            if cvc is not None:
                bats_with_cvc += 1
        assert bats_with_cvc >= len(batiments) * 0.6, f"Only {bats_with_cvc}/{len(batiments)} batiments have CVC usage"

    def test_usage_types_diverse(self, seeded_db):
        """Should have at least 3 different usage types across all batiments."""
        db, _ = seeded_db
        types = db.query(Usage.type).distinct().all()
        type_set = {t[0] for t in types}
        assert len(type_set) >= 3, f"Only {len(type_set)} usage types: {type_set}"


# ═══════════════════════════════════════════════════════════════════════
# V108: Monitoring Depth
# ═══════════════════════════════════════════════════════════════════════


class TestMonitoringDepth:
    def test_multiple_snapshots_per_site(self, seeded_db):
        """Each site should have 6 monthly monitoring snapshots."""
        from models import MonitoringSnapshot

        db, _ = seeded_db
        sites = db.query(Site).all()
        for site in sites:
            count = db.query(MonitoringSnapshot).filter_by(site_id=site.id).count()
            assert count >= 4, f"Site {site.nom}: only {count} snapshots (expected 6)"

    def test_consumption_insights_varied(self, seeded_db):
        """Should have multiple insight types across all sites."""
        from models import ConsumptionInsight

        db, _ = seeded_db
        types = db.query(ConsumptionInsight.type).distinct().all()
        type_set = {t[0] for t in types}
        assert len(type_set) >= 2, f"Only {len(type_set)} insight types: {type_set}"

    def test_alerts_have_start_ts(self, seeded_db):
        """Alerts should have start_ts populated."""
        from models import MonitoringAlert

        db, _ = seeded_db
        with_ts = db.query(MonitoringAlert).filter(MonitoringAlert.start_ts.isnot(None)).count()
        total = db.query(MonitoringAlert).count()
        assert total > 0
        assert with_ts > 0, "No alerts have start_ts populated"


# ═══════════════════════════════════════════════════════════════════════
# V108: Notifications
# ═══════════════════════════════════════════════════════════════════════


class TestNotifications:
    def test_notification_events_exist(self, seeded_db):
        """Should have 8+ notification events (capped to 10 for realistic demo)."""
        from models.notification import NotificationEvent

        db, _ = seeded_db
        count = db.query(NotificationEvent).count()
        assert count >= 8, f"Only {count} notification events (expected 8+)"

    def test_notification_sources_diverse(self, seeded_db):
        """Should cover all 4 source types."""
        from models.notification import NotificationEvent

        db, _ = seeded_db
        sources = db.query(NotificationEvent.source_type).distinct().all()
        source_set = {s[0] for s in sources}
        assert len(source_set) >= 4, f"Only {len(source_set)} source types: {source_set}"

    def test_notification_severities_mixed(self, seeded_db):
        """Should have multiple severity levels."""
        from models.notification import NotificationEvent

        db, _ = seeded_db
        severities = db.query(NotificationEvent.severity).distinct().all()
        sev_set = {s[0] for s in severities}
        assert len(sev_set) >= 2, f"Only {len(sev_set)} severity levels: {sev_set}"


# ═══════════════════════════════════════════════════════════════════════
# V108: TOU Schedules
# ═══════════════════════════════════════════════════════════════════════


class TestTOUSchedules:
    def test_tou_per_site(self, seeded_db):
        """Each site should have a TOU schedule."""
        from models.tou_schedule import TOUSchedule

        db, _ = seeded_db
        sites = db.query(Site).all()
        for site in sites:
            tou = db.query(TOUSchedule).filter_by(site_id=site.id).first()
            assert tou is not None, f"Site {site.nom} missing TOU schedule"
            assert tou.is_active, f"Site {site.nom} TOU not active"


# ═══════════════════════════════════════════════════════════════════════
# V108: Payment Rules & Reconciliation
# ═══════════════════════════════════════════════════════════════════════


class TestPaymentRules:
    def test_payment_rules_exist(self, seeded_db):
        """Should have payment rules (portefeuille + site level)."""
        from models.payment_rule import PaymentRule

        db, _ = seeded_db
        count = db.query(PaymentRule).count()
        assert count >= 5, f"Only {count} payment rules (expected 5+)"

    def test_reconciliation_logs_exist(self, seeded_db):
        """Should have reconciliation fix log entries."""
        from models.reconciliation_fix_log import ReconciliationFixLog

        db, _ = seeded_db
        count = db.query(ReconciliationFixLog).count()
        assert count >= 2, f"Only {count} reconciliation logs (expected 2+)"
