"""
PROMEOS — Purchase Actions Engine (Sprint 8.1)
Ephemeral, computed purchase action recommendations.
Follows the action_plan_engine.py pattern — not persisted.
"""
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from models import (
    Site, EnergyContract,
    PurchaseScenarioResult, PurchaseAssumptionSet, PurchaseRecoStatus,
)
from services.purchase_service import get_org_site_ids

# Priority weights
_ACTION_WEIGHTS = {
    "renewal_urgent": 100,
    "renewal_soon": 70,
    "renewal_plan": 40,
    "strategy_switch": 60,
    "accept_reco": 50,
}


def compute_purchase_actions(db: Session, org_id: Optional[int] = None) -> dict:
    """
    Build prioritized purchase action list from contracts + scenarios.
    Pure computation, nothing persisted.
    """
    site_ids = get_org_site_ids(db, org_id) if org_id else [s.id for s in db.query(Site.id).filter(Site.actif == True).all()]
    if not site_ids:
        return {"total_actions": 0, "actions": [], "gain_potentiel_eur": 0}

    today = date.today()
    actions = []
    site_map = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()}

    # ── Renewal actions from contracts ──
    contracts = db.query(EnergyContract).filter(
        EnergyContract.site_id.in_(site_ids),
        EnergyContract.end_date.isnot(None),
    ).all()

    for c in contracts:
        days_until_expiry = (c.end_date - today).days
        if days_until_expiry <= 0:
            continue  # Already expired

        notice_deadline = c.end_date - timedelta(days=c.notice_period_days or 90)
        days_until_notice = (notice_deadline - today).days
        site = site_map.get(c.site_id)
        site_nom = site.nom if site else f"Site {c.site_id}"

        if days_until_notice <= 0:
            # Past notice deadline but before expiry
            actions.append({
                "type": "renewal_urgent",
                "priority": _ACTION_WEIGHTS["renewal_urgent"],
                "site_id": c.site_id,
                "site_nom": site_nom,
                "contract_id": c.id,
                "supplier": c.supplier_name,
                "label": f"URGENT: Renouveler contrat {c.supplier_name} pour {site_nom} avant le {c.end_date.strftime('%d/%m/%Y')}",
                "days_until_expiry": days_until_expiry,
                "days_until_notice": days_until_notice,
                "auto_renew": c.auto_renew,
                "severity": "red",
            })
        elif days_until_notice <= 30:
            actions.append({
                "type": "renewal_urgent",
                "priority": _ACTION_WEIGHTS["renewal_urgent"],
                "site_id": c.site_id,
                "site_nom": site_nom,
                "contract_id": c.id,
                "supplier": c.supplier_name,
                "label": f"Renouveler contrat {c.supplier_name} pour {site_nom} avant le {notice_deadline.strftime('%d/%m/%Y')}",
                "days_until_expiry": days_until_expiry,
                "days_until_notice": days_until_notice,
                "auto_renew": c.auto_renew,
                "severity": "red",
            })
        elif days_until_notice <= 60:
            actions.append({
                "type": "renewal_soon",
                "priority": _ACTION_WEIGHTS["renewal_soon"],
                "site_id": c.site_id,
                "site_nom": site_nom,
                "contract_id": c.id,
                "supplier": c.supplier_name,
                "label": f"Planifier renouvellement contrat {c.supplier_name} pour {site_nom} (echeance {c.end_date.strftime('%d/%m/%Y')})",
                "days_until_expiry": days_until_expiry,
                "days_until_notice": days_until_notice,
                "auto_renew": c.auto_renew,
                "severity": "orange",
            })
        elif days_until_notice <= 90:
            actions.append({
                "type": "renewal_plan",
                "priority": _ACTION_WEIGHTS["renewal_plan"],
                "site_id": c.site_id,
                "site_nom": site_nom,
                "contract_id": c.id,
                "supplier": c.supplier_name,
                "label": f"Anticiper renouvellement contrat {c.supplier_name} pour {site_nom} (fin {c.end_date.strftime('%d/%m/%Y')})",
                "days_until_expiry": days_until_expiry,
                "days_until_notice": days_until_notice,
                "auto_renew": c.auto_renew,
                "severity": "yellow",
            })

    # ── Strategy switch / accept actions from scenarios ──
    recos = db.query(PurchaseScenarioResult).filter(
        PurchaseScenarioResult.is_recommended == True,
        PurchaseScenarioResult.reco_status == PurchaseRecoStatus.DRAFT,
    ).all()

    # Batch-fetch assumptions for all recos (avoid N+1 and double query)
    assumption_ids = {r.assumption_set_id for r in recos}
    assumptions_list = db.query(PurchaseAssumptionSet).filter(
        PurchaseAssumptionSet.id.in_(assumption_ids),
    ).all() if assumption_ids else []
    assumption_map = {a.id: a for a in assumptions_list}

    gain_potentiel = 0.0
    for r in recos:
        assumption = assumption_map.get(r.assumption_set_id)
        if not assumption or assumption.site_id not in site_ids:
            continue

        site = site_map.get(assumption.site_id)
        site_nom = site.nom if site else f"Site {assumption.site_id}"
        strategy_label = {"fixe": "prix fixe", "indexe": "indexe", "spot": "spot"}.get(
            r.strategy.value, r.strategy.value
        )

        if r.savings_vs_current_pct and r.savings_vs_current_pct > 5:
            actions.append({
                "type": "strategy_switch",
                "priority": _ACTION_WEIGHTS["strategy_switch"],
                "site_id": assumption.site_id,
                "site_nom": site_nom,
                "label": f"Envisager passage {strategy_label} pour {site_nom} ({r.savings_vs_current_pct}% d'economie)",
                "savings_pct": r.savings_vs_current_pct,
                "strategy": r.strategy.value,
                "severity": "blue",
            })
        else:
            actions.append({
                "type": "accept_reco",
                "priority": _ACTION_WEIGHTS["accept_reco"],
                "site_id": assumption.site_id,
                "site_nom": site_nom,
                "label": f"Valider la recommandation d'achat pour {site_nom}",
                "strategy": r.strategy.value,
                "severity": "blue",
            })

        # Accumulate gain potentiel: savings relative to current cost
        if r.savings_vs_current_pct and r.savings_vs_current_pct > 0 and r.savings_vs_current_pct < 100:
            current_cost = r.total_annual_eur / (1 - r.savings_vs_current_pct / 100)
            gain_potentiel += current_cost * r.savings_vs_current_pct / 100

    # Sort by priority DESC
    actions.sort(key=lambda a: -a["priority"])
    for i, action in enumerate(actions):
        action["rank"] = i + 1

    return {
        "total_actions": len(actions),
        "actions": actions,
        "gain_potentiel_eur": round(gain_potentiel, 2),
    }


