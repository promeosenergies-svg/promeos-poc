"""
PROMEOS Bill Intelligence — Tests for timeline and dashboard.
AC: timeline 24 mois, gaps/overlaps detection, coverage dashboard.
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.bill_intelligence.parsers.json_parser import load_all_demo_invoices
from app.bill_intelligence.engine import audit_invoice
from app.bill_intelligence.timeline import (
    build_timeline,
    build_coverage_dashboard,
    TimelineSlot,
    TimelineGap,
    SiteTimeline,
)
from app.bill_intelligence.domain import (
    Invoice,
    InvoiceComponent,
    EnergyType,
    ShadowLevel,
    ComponentType,
)


# ========================================
# Timeline tests
# ========================================


def test_build_timeline_from_demo():
    """Timeline built from demo corpus contains multiple site/energy groups."""
    invoices = load_all_demo_invoices()
    timelines = build_timeline(invoices)
    # Should have at least 3 groups: site1-elec, site1-gaz, site2-elec
    assert len(timelines) >= 3


def test_timeline_24_months():
    """Each timeline has 24 monthly slots (2023-01 to 2024-12)."""
    invoices = load_all_demo_invoices()
    timelines = build_timeline(invoices)
    for t in timelines:
        assert t.total_months == 24


def test_timeline_site1_elec_full_coverage():
    """Site 1 elec should have full 24-month coverage."""
    invoices = load_all_demo_invoices()
    invoices = [i for i in invoices if i.site_id == 1 and i.energy_type == EnergyType.ELEC]
    timelines = build_timeline(invoices)
    assert len(timelines) == 1
    t = timelines[0]
    assert t.covered_months == 24
    assert t.coverage_percent == 100.0
    assert len(t.gaps) == 0


def test_timeline_site2_has_gaps():
    """Site 2 elec should have gaps (months 4, 8, 11 are missing)."""
    invoices = load_all_demo_invoices()
    invoices = [i for i in invoices if i.site_id == 2 and i.energy_type == EnergyType.ELEC]
    timelines = build_timeline(invoices)
    assert len(timelines) == 1
    t = timelines[0]
    # 6 months missing (3 per year x 2 years)
    assert t.covered_months == 18
    assert len(t.gaps) >= 6  # Each missing month is a separate gap
    assert t.coverage_percent < 100.0


def test_timeline_gap_structure():
    """Gap objects have correct fields."""
    invoices = load_all_demo_invoices()
    invoices = [i for i in invoices if i.site_id == 2]
    timelines = build_timeline(invoices)
    for t in timelines:
        for gap in t.gaps:
            assert gap.site_id == 2
            assert gap.gap_start is not None
            assert gap.gap_end is not None
            assert gap.gap_months >= 1


def test_timeline_slot_has_invoice_data():
    """Slots with invoices carry amount/conso data."""
    invoices = load_all_demo_invoices()
    invoices = [i for i in invoices if i.site_id == 1 and i.energy_type == EnergyType.ELEC]
    timelines = build_timeline(invoices)
    t = timelines[0]
    filled = [s for s in t.slots if s.has_invoice]
    assert len(filled) >= 24
    for s in filled:
        assert s.invoice_id is not None
        assert s.total_ht is not None
        assert s.total_ht > 0


def test_timeline_custom_range():
    """Timeline with custom date range."""
    invoices = load_all_demo_invoices()
    timelines = build_timeline(invoices, start_year=2024, start_month=1, end_year=2024, end_month=6)
    for t in timelines:
        assert t.total_months == 6


def test_timeline_overlap_detection():
    """Detect overlapping invoices."""
    # Create two invoices with overlapping periods
    inv_a = Invoice(
        invoice_id="OVL-A",
        energy_type=EnergyType.ELEC,
        supplier="Test",
        site_id=99,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
    )
    inv_b = Invoice(
        invoice_id="OVL-B",
        energy_type=EnergyType.ELEC,
        supplier="Test",
        site_id=99,
        period_start=date(2024, 1, 15),
        period_end=date(2024, 2, 28),
    )
    timelines = build_timeline([inv_a, inv_b], start_year=2024, start_month=1, end_year=2024, end_month=3)
    assert len(timelines) == 1
    t = timelines[0]
    assert len(t.overlaps) == 1
    assert t.overlaps[0].invoice_a == "OVL-A"
    assert t.overlaps[0].invoice_b == "OVL-B"


def test_timeline_to_dict():
    """Timeline serialization."""
    invoices = load_all_demo_invoices()
    invoices = [i for i in invoices if i.site_id == 1 and i.energy_type == EnergyType.ELEC]
    timelines = build_timeline(invoices)
    d = timelines[0].to_dict()
    assert "site_id" in d
    assert "energy_type" in d
    assert "slots" in d
    assert "gaps" in d
    assert "coverage_percent" in d
    assert len(d["slots"]) == 24


# ========================================
# Dashboard tests
# ========================================


def test_coverage_dashboard():
    """Dashboard returns all expected KPIs."""
    invoices = load_all_demo_invoices()
    dashboard = build_coverage_dashboard(invoices)
    assert "total_invoices" in dashboard
    assert "total_by_energy" in dashboard
    assert "total_by_level" in dashboard
    assert "total_ht_eur" in dashboard
    assert "total_anomalies" in dashboard
    assert "anomalies_by_severity" in dashboard
    assert "sites_coverage" in dashboard
    assert "coverage_percent" in dashboard


def test_dashboard_total_invoices():
    """Dashboard total matches loaded invoices count."""
    invoices = load_all_demo_invoices()
    dashboard = build_coverage_dashboard(invoices)
    assert dashboard["total_invoices"] == len(invoices)
    assert dashboard["total_invoices"] >= 60  # We generated 66+3 hand-crafted


def test_dashboard_energy_split():
    """Dashboard has both elec and gaz."""
    invoices = load_all_demo_invoices()
    dashboard = build_coverage_dashboard(invoices)
    assert "elec" in dashboard["total_by_energy"]
    assert "gaz" in dashboard["total_by_energy"]
    assert dashboard["total_by_energy"]["elec"] > 0
    assert dashboard["total_by_energy"]["gaz"] > 0


def test_dashboard_sites_coverage():
    """Dashboard has per-site coverage data."""
    invoices = load_all_demo_invoices()
    dashboard = build_coverage_dashboard(invoices)
    # At least site 1 and site 2
    assert len(dashboard["sites_coverage"]) >= 2


def test_dashboard_total_ht():
    """Dashboard total HT is positive and reasonable."""
    invoices = load_all_demo_invoices()
    dashboard = build_coverage_dashboard(invoices)
    assert dashboard["total_ht_eur"] > 0
    assert dashboard["total_ttc_eur"] > dashboard["total_ht_eur"]


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
