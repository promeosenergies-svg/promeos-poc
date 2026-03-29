"""
Tests — Coherence cross-modules : tous les modules retournent
le meme chiffre de consommation pour un meme site et une meme periode.
"""

import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.fast

from models.base import Base
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
)
from models.enums import TypeSite
from models.energy_models import Meter, MeterReading, EnergyVector, FrequencyType
from models.billing_models import EnergyInvoice, BillingInvoiceStatus
from services.consumption_unified_service import (
    get_consumption_summary,
    get_portfolio_consumption,
    reconcile_metered_billed,
    check_reconciliation_alert,
)


@pytest.fixture()
def db():
    """In-memory SQLite with seed data for coherence tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed: org -> EJ -> portfolio -> site -> meter -> readings + invoices
    org = Organisation(id=1, nom="Test Org", siren="123456789", type_client="tertiaire")
    session.add(org)
    session.flush()

    ej = EntiteJuridique(id=1, nom="Test EJ", siren="123456789", organisation_id=1)
    session.add(ej)
    session.flush()

    ptf = Portefeuille(id=1, nom="Test Ptf", entite_juridique_id=1)
    session.add(ptf)
    session.flush()

    site = Site(
        id=1,
        nom="Site Test Alpha",
        portefeuille_id=1,
        type=TypeSite.BUREAU,
        actif=True,
        surface_m2=500,
        annual_kwh_total=120000,
    )
    session.add(site)
    session.flush()

    meter = Meter(
        id=1,
        meter_id="PDL-TEST-001",
        name="Compteur Test",
        site_id=1,
        energy_vector=EnergyVector.ELECTRICITY,
        is_active=True,
    )
    session.add(meter)
    session.flush()

    # Add daily readings for 2025 (365 days)
    for day_offset in range(365):
        ts = datetime(2025, 1, 1) + __import__("datetime").timedelta(days=day_offset)
        reading = MeterReading(
            meter_id=1,
            timestamp=ts,
            value_kwh=300.0,  # 300 kWh/day = 109,500 kWh/year
            frequency=FrequencyType.DAILY,
        )
        session.add(reading)

    # Add monthly invoices for 2025
    for month in range(1, 13):
        from datetime import timedelta

        m_start = date(2025, month, 1)
        if month == 12:
            m_end = date(2026, 1, 1) - timedelta(days=1)
        else:
            m_end = date(2025, month + 1, 1) - timedelta(days=1)

        invoice = EnergyInvoice(
            site_id=1,
            invoice_number=f"INV-2025-{month:02d}",
            period_start=m_start,
            period_end=m_end,
            energy_kwh=9000.0,  # 9000 * 12 = 108,000 kWh/year
            total_eur=1200.0,
            status=BillingInvoiceStatus.VALIDATED,
        )
        session.add(invoice)

    session.commit()
    yield session
    session.close()


class TestCoherenceSameSourceSameResult:
    """Tous les appels get_consumption_summary retournent le meme chiffre."""

    def test_unified_returns_consistent_value(self, db):
        """Deux appels identiques retournent le meme resultat."""
        r1 = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 12, 31))
        r2 = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 12, 31))
        assert r1["value_kwh"] == r2["value_kwh"]
        assert r1["source_used"] == r2["source_used"]

    def test_metered_preferred_when_coverage_high(self, db):
        """Avec 365 jours de lectures, metered est prefere."""
        r = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 12, 31))
        assert r["source_used"] == "metered"
        assert r["confidence"] == "high"
        assert r["value_kwh"] > 0

    def test_portfolio_matches_site_sum(self, db):
        """Le portfolio total == la somme des sites individuels."""
        portfolio = get_portfolio_consumption(db, 1, date(2025, 1, 1), date(2025, 12, 31))
        site_r = get_consumption_summary(db, 1, date(2025, 1, 1), date(2025, 12, 31))

        # Portfolio n'a qu'un seul site, donc total doit etre egal
        assert abs(portfolio["total_kwh"] - site_r["value_kwh"]) < 1.0


class TestReconciliation:
    """Reconciliation metered vs billed."""

    def test_reconcile_returns_delta(self, db):
        """Reconciliation retourne un delta coherent."""
        r = reconcile_metered_billed(db, 1, date(2025, 1, 1), date(2025, 12, 31))
        assert r["metered_kwh"] > 0
        assert r["billed_kwh"] > 0
        assert r["delta_pct"] is not None
        # metered = 365 * 300 = 109,500 ; billed = 12 * 9000 = 108,000
        # delta = 1.4%
        assert abs(r["delta_pct"]) < 5  # Aligned, not divergent

    def test_check_reconciliation_no_alert_when_aligned(self, db):
        """Pas d'alerte si delta < 10%."""
        result = check_reconciliation_alert(db, 1, date(2025, 1, 1), date(2025, 12, 31))
        assert result is None  # delta ~1.4%, below threshold
