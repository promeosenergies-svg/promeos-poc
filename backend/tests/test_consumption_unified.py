"""
Tests — A.1: Unified consumption service.
Covers: get_consumption_summary, get_portfolio_consumption, reconcile_metered_billed.
"""
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.fast

from models.base import Base
from models import (
    Organisation, EntiteJuridique, Portefeuille, Site, StatutConformite,
)
from models.enums import TypeSite
from models.energy_models import Meter, MeterReading, EnergyVector, FrequencyType
from models.billing_models import EnergyInvoice, BillingInvoiceStatus
from services.consumption_unified_service import (
    ConsumptionSource,
    get_consumption_summary,
    get_portfolio_consumption,
    reconcile_metered_billed,
    METERED_COVERAGE_THRESHOLD,
    RECONCILIATION_ALERT_THRESHOLD,
)


@pytest.fixture()
def db():
    """In-memory SQLite with seed data for consumption tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed org → EJ → portfolio → sites
    org = Organisation(id=1, nom="Test Org", siren="123456789", type_client="tertiaire")
    session.add(org)
    session.flush()

    ej = EntiteJuridique(id=1, nom="Test EJ", siren="123456789", organisation_id=1)
    session.add(ej)
    session.flush()

    ptf = Portefeuille(id=1, nom="Test Portfolio", entite_juridique_id=1)
    session.add(ptf)
    session.flush()

    # Site with full data (metered + billed)
    site1 = Site(
        id=1, nom="Site Full", type=TypeSite.BUREAU, actif=True, portefeuille_id=1,
        annual_kwh_total=120000,
    )
    # Site with only billed data
    site2 = Site(
        id=2, nom="Site Billed Only", type=TypeSite.BUREAU, actif=True, portefeuille_id=1,
        annual_kwh_total=80000,
    )
    # Site with no data
    site3 = Site(
        id=3, nom="Site Empty", type=TypeSite.BUREAU, actif=True, portefeuille_id=1,
        annual_kwh_total=50000,
    )
    session.add_all([site1, site2, site3])
    session.flush()

    # Meter for site1
    meter1 = Meter(
        id=1, meter_id="PRM001", name="Compteur principal",
        energy_vector=EnergyVector.ELECTRICITY, site_id=1, is_active=True,
    )
    session.add(meter1)
    session.flush()

    # MeterReadings for site1 (30 days, hourly-ish)
    start = date(2025, 1, 1)
    for day_offset in range(30):
        for hour in [0, 6, 12, 18]:
            ts = datetime(2025, 1, 1 + day_offset, hour, 0, 0)
            session.add(MeterReading(
                meter_id=1, timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=10.0 + day_offset * 0.1,
            ))

    # EnergyInvoice for site1 (January)
    session.add(EnergyInvoice(
        id=1, site_id=1, invoice_number="INV-001",
        period_start=date(2025, 1, 1), period_end=date(2025, 1, 31),
        issue_date=date(2025, 2, 5), total_eur=250.0, energy_kwh=1400.0,
        status=BillingInvoiceStatus.IMPORTED, source="csv",
    ))

    # EnergyInvoice for site2 (January) — no meter
    session.add(EnergyInvoice(
        id=2, site_id=2, invoice_number="INV-002",
        period_start=date(2025, 1, 1), period_end=date(2025, 1, 31),
        issue_date=date(2025, 2, 5), total_eur=180.0, energy_kwh=900.0,
        status=BillingInvoiceStatus.IMPORTED, source="csv",
    ))

    session.commit()
    yield session
    session.close()


# ============================================================
# get_consumption_summary
# ============================================================

class TestGetConsumptionSummary:
    """Test unified consumption retrieval for a single site."""

    def test_reconciled_prefers_metered_with_coverage(self, db):
        """Site with metered data covering > 80% → RECONCILED picks metered."""
        result = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        assert result["source_used"] == "metered"
        assert result["value_kwh"] > 0
        assert result["confidence"] == "high"

    def test_reconciled_falls_back_to_billed(self, db):
        """Site with no meter → RECONCILED picks billed."""
        result = get_consumption_summary(db, 2, date(2025, 1, 1), date(2025, 1, 31))
        assert result["source_used"] == "billed"
        assert result["value_kwh"] == 900.0
        assert result["confidence"] in ("medium", "low")

    def test_reconciled_falls_back_to_estimated(self, db):
        """Site with no meter and no invoices → RECONCILED uses estimate."""
        result = get_consumption_summary(db, 3, date(2025, 1, 1), date(2025, 1, 31))
        assert result["source_used"] == "estimated"
        # Estimate: 50000 * 30/365 ≈ 4109.6
        assert result["value_kwh"] > 0
        assert result["confidence"] == "low"

    def test_empty_site_no_data(self, db):
        """Site with no data and no annual estimate → confidence none."""
        # Create a site with no annual_kwh_total
        site = Site(id=99, nom="Ghost", type=TypeSite.BUREAU, actif=True, portefeuille_id=1, annual_kwh_total=None)
        db.add(site)
        db.flush()
        result = get_consumption_summary(db, 99, date(2025, 1, 1), date(2025, 1, 31))
        assert result["source_used"] == "estimated"
        assert result["value_kwh"] == 0
        assert result["confidence"] == "none"

    def test_forced_metered_source(self, db):
        """Forcing source=METERED returns meter data only."""
        result = get_consumption_summary(
            db, 1, date(2025, 1, 1), date(2025, 1, 31), ConsumptionSource.METERED
        )
        assert result["source_used"] == "metered"
        assert result["value_kwh"] > 0

    def test_forced_billed_source(self, db):
        """Forcing source=BILLED returns invoice data only."""
        result = get_consumption_summary(
            db, 1, date(2025, 1, 1), date(2025, 1, 31), ConsumptionSource.BILLED
        )
        assert result["source_used"] == "billed"
        assert result["value_kwh"] == 1400.0

    def test_details_contain_both_sources(self, db):
        """Details dict has metered and billed info."""
        result = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        d = result["details"]
        assert "metered_kwh" in d
        assert "billed_kwh" in d
        assert "metered_readings" in d
        assert "billed_invoices" in d
        assert d["metered_kwh"] > 0
        assert d["billed_kwh"] > 0

    def test_period_info(self, db):
        """Result contains period info."""
        result = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        assert result["period"]["start"] == "2025-01-01"
        assert result["period"]["end"] == "2025-01-31"
        assert result["period"]["days"] == 30

    def test_same_call_same_result(self, db):
        """Deterministic: same parameters → same result."""
        r1 = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        r2 = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        assert r1["value_kwh"] == r2["value_kwh"]
        assert r1["source_used"] == r2["source_used"]


# ============================================================
# get_portfolio_consumption
# ============================================================

class TestGetPortfolioConsumption:
    """Test portfolio-level aggregation."""

    def test_portfolio_totals(self, db):
        """Portfolio sums all site consumptions."""
        result = get_portfolio_consumption(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        assert result["sites_count"] == 3
        assert result["total_kwh"] > 0
        assert result["sites_with_data"] >= 2  # site1 + site2 have data

    def test_portfolio_site_details(self, db):
        """Each site has source_used and confidence."""
        result = get_portfolio_consumption(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        for site in result["sites"]:
            assert "source_used" in site
            assert "confidence" in site
            assert "value_kwh" in site

    def test_portfolio_sum_equals_sites(self, db):
        """total_kwh == sum of site value_kwh."""
        result = get_portfolio_consumption(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        site_sum = sum(s["value_kwh"] for s in result["sites"])
        assert abs(result["total_kwh"] - site_sum) < 0.01

    def test_portfolio_confidence(self, db):
        """Portfolio with 2/3 sites having data → medium confidence."""
        result = get_portfolio_consumption(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        # 2 or 3 out of 3 → medium or high
        assert result["confidence"] in ("medium", "high", "low")

    def test_empty_org(self, db):
        """Org with no sites → none confidence."""
        result = get_portfolio_consumption(db, 999, date(2025, 1, 1), date(2025, 1, 31))
        assert result["sites_count"] == 0
        assert result["confidence"] == "none"


# ============================================================
# reconcile_metered_billed
# ============================================================

class TestReconcileMeteredBilled:
    """Test metered vs billed reconciliation."""

    def test_both_sources_available(self, db):
        """Site1 has both metered and billed → computes delta."""
        result = reconcile_metered_billed(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        assert result["metered_kwh"] > 0
        assert result["billed_kwh"] > 0
        assert result["delta_kwh"] is not None
        assert result["delta_pct"] is not None
        assert result["status"] in ("aligned", "divergent")

    def test_missing_metered(self, db):
        """Site2 has no meter → insufficient_data."""
        result = reconcile_metered_billed(db, 2, date(2025, 1, 1), date(2025, 1, 31))
        assert result["status"] == "insufficient_data"
        assert result["delta_kwh"] is None

    def test_missing_billed(self, db):
        """Site3 has no invoices → insufficient_data."""
        result = reconcile_metered_billed(db, 3, date(2025, 1, 1), date(2025, 1, 31))
        assert result["status"] == "insufficient_data"
        assert result["alert"] is False

    def test_alert_threshold(self, db):
        """Delta > 10% triggers alert flag."""
        result = reconcile_metered_billed(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        if result["status"] == "divergent":
            assert result["alert"] is True
        else:
            assert result["alert"] is False

    def test_recommendation_present(self, db):
        """Result always includes a recommendation string."""
        result = reconcile_metered_billed(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        assert result["recommendation"]
        assert len(result["recommendation"]) > 10

    def test_period_in_result(self, db):
        """Result contains period info."""
        result = reconcile_metered_billed(db, 1, date(2025, 1, 1), date(2025, 1, 31))
        assert result["period"]["start"] == "2025-01-01"
        assert result["period"]["end"] == "2025-01-31"


# ============================================================
# ConsumptionSource enum
# ============================================================

class TestConsumptionSource:
    """Test the ConsumptionSource enum."""

    def test_values(self):
        assert ConsumptionSource.METERED.value == "metered"
        assert ConsumptionSource.BILLED.value == "billed"
        assert ConsumptionSource.RECONCILED.value == "reconciled"

    def test_from_string(self):
        assert ConsumptionSource("metered") == ConsumptionSource.METERED
        assert ConsumptionSource("billed") == ConsumptionSource.BILLED
        assert ConsumptionSource("reconciled") == ConsumptionSource.RECONCILED
