"""
PROMEOS — V99 Contract Renewal Radar Service
Portfolio-level renewal radar for DAF/Direction Achats.
Computed on-read, not persisted.
"""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Site, EnergyContract, Portefeuille, EntiteJuridique,
)


INDEXATION_LABELS = {
    "fixe": "Prix fixe",
    "indexe": "Indexé marché",
    "spot": "Spot",
    "hybride": "Hybride",
}


def _compute_urgency(days_to_end, days_to_notice):
    """Map remaining days to urgency color."""
    if days_to_end is not None and days_to_end <= 0:
        return "red"
    if days_to_notice is not None and days_to_notice <= 0:
        return "red"
    if days_to_notice is not None and days_to_notice <= 30:
        return "orange"
    if days_to_notice is not None and days_to_notice <= 60:
        return "yellow"
    if days_to_end is not None and days_to_end <= 90:
        return "green"
    return "gray"


def _compute_status(end_date, today):
    """Derive contract status from end_date."""
    if end_date is None:
        return "active"
    days = (end_date - today).days
    if days < 0:
        return "expired"
    if days <= 90:
        return "expiring"
    return "active"


def _sort_key(item):
    """Sort: expired first (by days_to_end asc), then expiring, then active."""
    status_order = {"expired": 0, "expiring": 1, "active": 2}
    s = status_order.get(item["contract_status"], 3)
    d = item["days_to_end"] if item["days_to_end"] is not None else 9999
    return (s, d)


def compute_contract_radar(
    db: Session,
    org_id: int,
    portfolio_id: Optional[int] = None,
    horizon_days: int = 90,
) -> dict:
    """Build portfolio-level renewal radar."""
    today = date.today()
    horizon_date = today + timedelta(days=horizon_days)

    # Query all sites for the org (optionally filtered by portfolio)
    q = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    if portfolio_id:
        q = q.filter(Site.portefeuille_id == portfolio_id)
    sites = q.all()

    if not sites:
        return {"total": 0, "horizon_days": horizon_days, "contracts": [], "stats": {"expired": 0, "expiring": 0, "active": 0}}

    site_map = {s.id: s for s in sites}
    site_ids = list(site_map.keys())

    # Query all contracts for those sites
    contracts = (
        db.query(EnergyContract)
        .filter(EnergyContract.site_id.in_(site_ids))
        .all()
    )

    # Include ALL contracts (no filtering) — horizon controls urgency only
    filtered = contracts

    # Cache reconciliation per site (avoid N+1)
    recon_cache = {}

    def _get_recon(sid):
        if sid not in recon_cache:
            try:
                from services.reconciliation_service import reconcile_site
                r = reconcile_site(db, sid)
                recon_cache[sid] = (r["score"], r["status"])
            except Exception:
                recon_cache[sid] = (0, "fail")
        return recon_cache[sid]

    # Cache payment rule per site
    pr_cache = {}

    def _get_payer(sid, cid):
        key = (sid, cid)
        if key not in pr_cache:
            try:
                from routes.patrimoine import _resolve_payment_rule
                pr = _resolve_payment_rule(db, sid, cid)
                if pr:
                    # Resolve entity name
                    ej = db.query(EntiteJuridique).filter(EntiteJuridique.id == pr.payer_entity_id).first() if pr.payer_entity_id else None
                    pr_cache[key] = (ej.nom if ej else None, pr.cost_center)
                else:
                    pr_cache[key] = (None, None)
            except Exception:
                pr_cache[key] = (None, None)
        return pr_cache[key]

    items = []
    for ct in filtered:
        site = site_map.get(ct.site_id)
        if not site:
            continue

        days_to_end = (ct.end_date - today).days if ct.end_date else None
        notice_days = ct.notice_period_days or 90
        days_to_notice = (days_to_end - notice_days) if days_to_end is not None else None
        status = _compute_status(ct.end_date, today)
        urgency = _compute_urgency(days_to_end, days_to_notice)

        indexation_val = ct.offer_indexation.value if ct.offer_indexation else None
        indexation_label = INDEXATION_LABELS.get(indexation_val, "Non renseigné")

        recon_score, recon_status = _get_recon(ct.site_id)
        payer_entity, cost_center = _get_payer(ct.site_id, ct.id)

        # Portfolio info
        pf = db.query(Portefeuille).filter(Portefeuille.id == site.portefeuille_id).first() if site.portefeuille_id else None

        items.append({
            "contract_id": ct.id,
            "site_id": site.id,
            "site_nom": site.nom,
            "portfolio_id": pf.id if pf else None,
            "portfolio_nom": pf.nom if pf else None,
            "supplier_name": ct.supplier_name,
            "energy_type": ct.energy_type.value if ct.energy_type else None,
            "start_date": ct.start_date.isoformat() if ct.start_date else None,
            "end_date": ct.end_date.isoformat() if ct.end_date else None,
            "days_to_end": days_to_end,
            "days_to_notice": days_to_notice,
            "notice_period_days": notice_days,
            "auto_renew": ct.auto_renew or False,
            "contract_status": status,
            "indexation": indexation_val,
            "indexation_label": indexation_label,
            "readiness_score": recon_score,
            "readiness_status": recon_status,
            "payer_entity": payer_entity,
            "cost_center": cost_center,
            "urgency": urgency,
        })

    items.sort(key=_sort_key)

    stats = {
        "expired": sum(1 for i in items if i["contract_status"] == "expired"),
        "expiring": sum(1 for i in items if i["contract_status"] == "expiring"),
        "active": sum(1 for i in items if i["contract_status"] == "active"),
    }

    return {
        "total": len(items),
        "horizon_days": horizon_days,
        "contracts": items,
        "stats": stats,
    }
