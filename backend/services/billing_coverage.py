"""
PROMEOS — Billing Coverage Engine (V67)
Calcule la couverture mensuelle à partir des factures importées.

SoT période:
  1. period_start + period_end si disponibles
  2. Fallback sur issue_date → mois entier (1er→dernier du mois)
  3. Facture sans aucune date → ignorée pour la couverture (R4 l'a signalée)

Règles:
  - Avoirs (total_eur <= 0) exclus du calcul de couverture (inclus dans totaux)
  - Chevauchements gérés par set() de jours → pas de double-comptage
  - COVERAGE_THRESHOLD = 0.80 (configurable)
"""
from __future__ import annotations

import json
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Tuple


COVERAGE_THRESHOLD = 0.80  # 80% des jours du mois = "covered"


@dataclass
class MonthCoverage:
    month_key: str           # "YYYY-MM"
    month_start: date
    month_end: date
    coverage_status: str     # "covered" | "partial" | "missing"
    coverage_ratio: float    # 0.0 → 1.0
    invoices_count: int      # toutes factures incl. avoirs
    total_ttc: Optional[float]  # somme total_eur (incl. avoirs) ou None si vide
    missing_reason: Optional[str]
    energy_kwh: Optional[float] = field(default=None)   # P0-2: somme kWh factures positives
    pdl_prm: Optional[str] = field(default=None)         # P0-2: PDL/PRM depuis raw_json


def _invoice_period(inv) -> Tuple[Optional[date], Optional[date]]:
    """
    Source-of-Truth pour la période d'une facture.
    Priorité: period_start/end → fallback issue_date (mois entier) → None/None.
    """
    if inv.period_start and inv.period_end:
        return inv.period_start, inv.period_end
    if inv.issue_date:
        d = inv.issue_date
        _, last_day = monthrange(d.year, d.month)
        return date(d.year, d.month, 1), date(d.year, d.month, last_day)
    return None, None


def _month_bounds(year: int, month: int) -> Tuple[date, date]:
    _, last_day = monthrange(year, month)
    return date(year, month, 1), date(year, month, last_day)


def _iter_months(start: date, end: date):
    """Génère (year, month) pour chaque mois de [start, end] inclus."""
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


def compute_range(invoices: list) -> Tuple[Optional[date], Optional[date]]:
    """Calcule le range min/max des périodes effectives sur toutes les factures."""
    starts: list[date] = []
    ends: list[date] = []
    for inv in invoices:
        ps, pe = _invoice_period(inv)
        if ps:
            starts.append(ps)
        if pe:
            ends.append(pe)
    if not starts:
        return None, None
    return min(starts), max(ends)


def compute_coverage(invoices: list, range_start: date, range_end: date) -> List[MonthCoverage]:
    """
    Pour chaque mois dans [range_start, range_end] :
    - Compte les jours couverts (factures non-avoir avec période valide)
    - Détermine status et missing_reason
    Retourne la liste de MonthCoverage (du plus ancien au plus récent).
    """
    results: List[MonthCoverage] = []

    for y, m in _iter_months(range_start, range_end):
        ms, me = _month_bounds(y, m)
        nb_days = (me - ms).days + 1
        covered_days: set[date] = set()
        inv_in_month: list = []
        total_ttc = 0.0
        total_kwh = 0.0           # P0-2
        pdl_found: Optional[str] = None  # P0-2

        for inv in invoices:
            ps, pe = _invoice_period(inv)
            if ps is None:
                continue  # pas de période utilisable

            # Intersection avec le mois
            overlap_start = max(ps, ms)
            overlap_end = min(pe, me)
            if overlap_start > overlap_end:
                continue  # facture hors du mois

            inv_in_month.append(inv)
            total_ttc += (inv.total_eur or 0.0)

            # Avoirs (total_eur <= 0) ne contribuent pas à la couverture
            if (inv.total_eur or 0.0) > 0:
                total_kwh += (getattr(inv, "energy_kwh", None) or 0.0)  # P0-2: accumuler kWh
                # P0-2: extraire PDL depuis raw_json si pas encore trouvé
                if pdl_found is None:
                    try:
                        raw = json.loads(getattr(inv, "raw_json", None) or "{}")
                        if raw.get("pdl_prm"):
                            pdl_found = raw["pdl_prm"]
                    except Exception:
                        pass
                d = overlap_start
                while d <= overlap_end:
                    covered_days.add(d)
                    d += timedelta(days=1)

        ratio = len(covered_days) / nb_days if nb_days > 0 else 0.0

        if ratio >= COVERAGE_THRESHOLD:
            status = "covered"
            reason = None
        elif ratio > 0:
            status = "partial"
            reason = f"Couverture {ratio:.0%} ({len(covered_days)}/{nb_days} jours)"
        else:
            status = "missing"
            if not inv_in_month:
                reason = "Aucune facture importée pour ce mois"
            else:
                reason = "Factures présentes mais sans dates valides (vérifier R4)"

        results.append(MonthCoverage(
            month_key=f"{y:04d}-{m:02d}",
            month_start=ms,
            month_end=me,
            coverage_status=status,
            coverage_ratio=round(ratio, 4),
            invoices_count=len(inv_in_month),
            total_ttc=round(total_ttc, 2) if inv_in_month else None,
            missing_reason=reason,
            energy_kwh=round(total_kwh, 1) if inv_in_month else None,  # P0-2
            pdl_prm=pdl_found,                                          # P0-2
        ))

    return results


def compute_top_sites_missing(db, effective_org_id: int, site_id_filter: Optional[int] = None) -> list:
    """
    Calcule le top 10 des sites avec le plus de mois manquants/partiels.
    Retourne: [{"site_id": int, "site_name": str, "missing_months_count": int}]
    """
    from models.billing_models import EnergyInvoice
    from models import Portefeuille, Site, EntiteJuridique

    # Récupérer tous les sites de l'org
    q = (
        db.query(Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == effective_org_id)
    )
    if site_id_filter:
        q = q.filter(Site.id == site_id_filter)
    sites = q.all()

    site_missing: list = []
    for site in sites:
        invs = db.query(EnergyInvoice).filter(EnergyInvoice.site_id == site.id).all()
        if not invs:
            continue
        rstart, rend = compute_range(invs)
        if not rstart:
            continue
        months = compute_coverage(invs, rstart, rend)
        missing_count = sum(1 for mc in months if mc.coverage_status != "covered")
        if missing_count > 0:
            site_missing.append({
                "site_id": site.id,
                "site_name": site.nom,
                "missing_months_count": missing_count,
            })

    site_missing.sort(key=lambda x: x["missing_months_count"], reverse=True)
    return site_missing[:10]
