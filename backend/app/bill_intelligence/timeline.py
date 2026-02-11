"""
PROMEOS Bill Intelligence — Timeline 24 mois
Analyse temporelle : gaps, overlaps, coverage L0-L3, dashboard KPIs.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple

from .domain import Invoice, ShadowLevel, EnergyType


@dataclass
class TimelineSlot:
    """One month slot in the timeline."""
    year: int
    month: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    invoice_id: Optional[str] = None
    has_invoice: bool = False
    shadow_level: str = "L0"
    total_ht: Optional[float] = None
    total_ttc: Optional[float] = None
    conso_kwh: Optional[float] = None
    nb_anomalies: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "month": self.month,
            "period_start": str(self.period_start) if self.period_start else None,
            "period_end": str(self.period_end) if self.period_end else None,
            "invoice_id": self.invoice_id,
            "has_invoice": self.has_invoice,
            "shadow_level": self.shadow_level,
            "total_ht": self.total_ht,
            "total_ttc": self.total_ttc,
            "conso_kwh": self.conso_kwh,
            "nb_anomalies": self.nb_anomalies,
        }


@dataclass
class TimelineGap:
    """A gap (missing invoice) in the timeline."""
    site_id: Optional[int]
    energy_type: str
    pdl_pce: Optional[str]
    gap_start: date
    gap_end: date
    gap_months: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "energy_type": self.energy_type,
            "pdl_pce": self.pdl_pce,
            "gap_start": str(self.gap_start),
            "gap_end": str(self.gap_end),
            "gap_months": self.gap_months,
        }


@dataclass
class TimelineOverlap:
    """An overlap (two invoices covering the same period) in the timeline."""
    site_id: Optional[int]
    energy_type: str
    pdl_pce: Optional[str]
    invoice_a: str
    invoice_b: str
    overlap_start: date
    overlap_end: date

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "energy_type": self.energy_type,
            "pdl_pce": self.pdl_pce,
            "invoice_a": self.invoice_a,
            "invoice_b": self.invoice_b,
            "overlap_start": str(self.overlap_start),
            "overlap_end": str(self.overlap_end),
        }


@dataclass
class SiteTimeline:
    """Complete timeline for one site+energy combination."""
    site_id: Optional[int]
    energy_type: str
    pdl_pce: Optional[str]
    supplier: Optional[str]
    slots: List[TimelineSlot] = field(default_factory=list)
    gaps: List[TimelineGap] = field(default_factory=list)
    overlaps: List[TimelineOverlap] = field(default_factory=list)
    total_months: int = 0
    covered_months: int = 0
    coverage_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "energy_type": self.energy_type,
            "pdl_pce": self.pdl_pce,
            "supplier": self.supplier,
            "total_months": self.total_months,
            "covered_months": self.covered_months,
            "coverage_percent": self.coverage_percent,
            "gaps": [g.to_dict() for g in self.gaps],
            "overlaps": [o.to_dict() for o in self.overlaps],
            "slots": [s.to_dict() for s in self.slots],
        }


def build_timeline(invoices: List[Invoice],
                   start_year: int = 2023, start_month: int = 1,
                   end_year: int = 2024, end_month: int = 12,
                   ) -> List[SiteTimeline]:
    """
    Build a 24-month timeline from a list of invoices.
    Groups by (site_id or pdl_pce, energy_type).
    Detects gaps and overlaps.
    """
    # Group invoices by (site_key, energy_type)
    groups: Dict[Tuple, List[Invoice]] = defaultdict(list)
    for inv in invoices:
        key = (inv.site_id or inv.pdl_pce or "unknown", inv.energy_type.value)
        groups[key].append(inv)

    timelines = []

    for (site_key, energy), group_invoices in sorted(groups.items()):
        # Sort by period_start
        sorted_invoices = sorted(
            group_invoices,
            key=lambda i: i.period_start or date(1970, 1, 1),
        )

        supplier = sorted_invoices[0].supplier if sorted_invoices else None
        pdl_pce = sorted_invoices[0].pdl_pce if sorted_invoices else None
        site_id = sorted_invoices[0].site_id if sorted_invoices else None

        # Build month grid
        slots = []
        month_map: Dict[Tuple[int, int], TimelineSlot] = {}

        y, m = start_year, start_month
        while (y, m) <= (end_year, end_month):
            slot = TimelineSlot(year=y, month=m)
            slots.append(slot)
            month_map[(y, m)] = slot
            m += 1
            if m > 12:
                m = 1
                y += 1

        # Place invoices into slots
        for inv in sorted_invoices:
            if inv.period_start is None:
                continue
            ym = (inv.period_start.year, inv.period_start.month)
            if ym in month_map:
                slot = month_map[ym]
                slot.has_invoice = True
                slot.invoice_id = inv.invoice_id
                slot.period_start = inv.period_start
                slot.period_end = inv.period_end
                slot.total_ht = inv.total_ht
                slot.total_ttc = inv.total_ttc
                slot.conso_kwh = inv.conso_kwh
                slot.shadow_level = inv.shadow_level.value
                slot.nb_anomalies = len(inv.anomalies)

        # Detect gaps
        gaps = []
        gap_start = None
        gap_months_count = 0

        for slot in slots:
            if not slot.has_invoice:
                if gap_start is None:
                    gap_start = date(slot.year, slot.month, 1)
                gap_months_count += 1
            else:
                if gap_start is not None and gap_months_count > 0:
                    prev_slot = slots[slots.index(slot) - 1]
                    from calendar import monthrange
                    _, last_day = monthrange(prev_slot.year, prev_slot.month)
                    gap_end = date(prev_slot.year, prev_slot.month, last_day)
                    gaps.append(TimelineGap(
                        site_id=site_id,
                        energy_type=energy,
                        pdl_pce=pdl_pce,
                        gap_start=gap_start,
                        gap_end=gap_end,
                        gap_months=gap_months_count,
                    ))
                gap_start = None
                gap_months_count = 0

        # Handle trailing gap
        if gap_start is not None and gap_months_count > 0:
            last_slot = slots[-1]
            from calendar import monthrange
            _, last_day = monthrange(last_slot.year, last_slot.month)
            gaps.append(TimelineGap(
                site_id=site_id,
                energy_type=energy,
                pdl_pce=pdl_pce,
                gap_start=gap_start,
                gap_end=date(last_slot.year, last_slot.month, last_day),
                gap_months=gap_months_count,
            ))

        # Detect overlaps
        overlaps = []
        for i in range(len(sorted_invoices) - 1):
            a = sorted_invoices[i]
            b = sorted_invoices[i + 1]
            if a.period_end and b.period_start and a.period_end >= b.period_start:
                overlaps.append(TimelineOverlap(
                    site_id=site_id,
                    energy_type=energy,
                    pdl_pce=pdl_pce,
                    invoice_a=a.invoice_id,
                    invoice_b=b.invoice_id,
                    overlap_start=b.period_start,
                    overlap_end=a.period_end,
                ))

        total_months = len(slots)
        covered_months = sum(1 for s in slots if s.has_invoice)
        coverage_pct = round(covered_months / max(total_months, 1) * 100, 1)

        timelines.append(SiteTimeline(
            site_id=site_id,
            energy_type=energy,
            pdl_pce=pdl_pce,
            supplier=supplier,
            slots=slots,
            gaps=gaps,
            overlaps=overlaps,
            total_months=total_months,
            covered_months=covered_months,
            coverage_percent=coverage_pct,
        ))

    return timelines


def build_coverage_dashboard(invoices: List[Invoice],
                             audit_results: Optional[List] = None,
                             ) -> Dict[str, Any]:
    """
    Build a coverage dashboard with KPIs:
    - Total invoices by energy type
    - Shadow level distribution (L0-L3)
    - Total EUR audited
    - Anomaly counts by severity
    - Coverage by site
    """
    from .engine import audit_invoice

    total_by_energy = defaultdict(int)
    total_by_level = {"L0": 0, "L1": 0, "L2": 0, "L3": 0}
    total_ht = 0.0
    total_ttc = 0.0
    total_anomalies = 0
    anomalies_by_severity = defaultdict(int)
    anomalies_by_type = defaultdict(int)
    sites_coverage = defaultdict(lambda: {"invoices": 0, "anomalies": 0, "total_ht": 0.0})
    suppliers = set()

    for inv in invoices:
        # Audit if not already done
        if not inv.anomalies and inv.status.value != "audited":
            inv = audit_invoice(inv)

        total_by_energy[inv.energy_type.value] += 1
        total_by_level[inv.shadow_level.value] += 1
        total_ht += inv.total_ht or 0
        total_ttc += inv.total_ttc or 0
        total_anomalies += len(inv.anomalies)
        suppliers.add(inv.supplier)

        for a in inv.anomalies:
            anomalies_by_severity[a.severity.value] += 1
            anomalies_by_type[a.anomaly_type.value] += 1

        site_key = str(inv.site_id or inv.pdl_pce or "unknown")
        sites_coverage[site_key]["invoices"] += 1
        sites_coverage[site_key]["anomalies"] += len(inv.anomalies)
        sites_coverage[site_key]["total_ht"] += inv.total_ht or 0

    total_invoices = len(invoices)

    return {
        "total_invoices": total_invoices,
        "total_by_energy": dict(total_by_energy),
        "total_by_level": total_by_level,
        "total_ht_eur": round(total_ht, 2),
        "total_ttc_eur": round(total_ttc, 2),
        "total_anomalies": total_anomalies,
        "anomalies_by_severity": dict(anomalies_by_severity),
        "anomalies_by_type": dict(anomalies_by_type),
        "unique_suppliers": sorted(suppliers),
        "sites_coverage": {k: {
            "invoices": v["invoices"],
            "anomalies": v["anomalies"],
            "total_ht": round(v["total_ht"], 2),
        } for k, v in sites_coverage.items()},
        "coverage_percent": {
            level: round(count / max(total_invoices, 1) * 100, 1)
            for level, count in total_by_level.items()
        },
    }
