"""
PROMEOS — V96+V97 Reconciliation 3 voies + Resolution Engine
Compteur (PRM/PCE) ↔ Contrat actif ↔ Factures.
Computed on-read, not persisted.
V97: fix_actions[] per check + fixer functions + audit trail.
"""
import json
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Site, DeliveryPoint, EnergyContract, PaymentRule,
    Portefeuille, EntiteJuridique,
    ReconciliationFixLog, ReconciliationStatus,
    PaymentRuleLevel,
)
from models.billing_models import EnergyInvoice


def reconcile_site(db: Session, site_id: int) -> dict:
    """
    3-way reconciliation per site.
    Returns: {site_id, status, score, checks[], summary_fr}
    V97: Each check now includes fix_actions[].
    """
    checks = []
    today = date.today()
    six_months_ago = today - timedelta(days=180)

    # Load site data
    dps = (
        db.query(DeliveryPoint)
        .filter(DeliveryPoint.site_id == site_id, DeliveryPoint.deleted_at.is_(None))
        .all()
    )
    contracts = (
        db.query(EnergyContract)
        .filter(EnergyContract.site_id == site_id)
        .all()
    )
    active_contracts = [
        c for c in contracts
        if (c.start_date is None or c.start_date <= today)
        and (c.end_date is None or c.end_date >= today)
    ]
    invoices = (
        db.query(EnergyInvoice)
        .filter(EnergyInvoice.site_id == site_id)
        .all()
    )
    recent_invoices = [
        inv for inv in invoices
        if inv.issue_date and inv.issue_date >= six_months_ago
    ]

    # Check 1: has_delivery_points
    if dps:
        dp_codes = [dp.code for dp in dps if dp.code]
        checks.append({
            "id": "has_delivery_points",
            "label_fr": "Points de livraison",
            "status": "ok",
            "reason_fr": f"{len(dps)} point(s) de livraison actif(s) ({', '.join(dp_codes[:3])})",
            "suggestion_fr": None,
            "cta": None,
            "fix_actions": [],
        })
    else:
        checks.append({
            "id": "has_delivery_points",
            "label_fr": "Points de livraison",
            "status": "fail",
            "reason_fr": "Aucun point de livraison (PRM/PCE) rattaché",
            "suggestion_fr": "Ajoutez les codes PRM/PCE depuis l'onglet Patrimoine",
            "cta": "patrimoine",
            "fix_actions": [
                {"action": "create_delivery_point", "label_fr": "Créer un point de livraison", "method": "POST"},
            ],
        })

    # Check 2: has_active_contract
    if active_contracts:
        suppliers = list({c.supplier_name for c in active_contracts})
        checks.append({
            "id": "has_active_contract",
            "label_fr": "Contrat actif",
            "status": "ok",
            "reason_fr": f"{len(active_contracts)} contrat(s) actif(s) ({', '.join(suppliers[:2])})",
            "suggestion_fr": None,
            "cta": None,
            "fix_actions": [],
        })
    elif contracts:
        checks.append({
            "id": "has_active_contract",
            "label_fr": "Contrat actif",
            "status": "warn",
            "reason_fr": f"{len(contracts)} contrat(s) existant(s) mais aucun couvrant la date du jour",
            "suggestion_fr": "Vérifiez les dates de vos contrats ou ajoutez un nouveau contrat",
            "cta": "contracts",
            "fix_actions": [
                {"action": "extend_contract", "label_fr": "Prolonger le contrat", "method": "POST"},
            ],
        })
    else:
        checks.append({
            "id": "has_active_contract",
            "label_fr": "Contrat actif",
            "status": "fail",
            "reason_fr": "Aucun contrat énergie rattaché à ce site",
            "suggestion_fr": "Ajoutez un contrat depuis l'onglet Factures",
            "cta": "contracts",
            "fix_actions": [
                {"action": "create_contract", "label_fr": "Créer un contrat", "method": "POST"},
            ],
        })

    # Check 3: has_recent_invoices
    if recent_invoices:
        checks.append({
            "id": "has_recent_invoices",
            "label_fr": "Factures récentes",
            "status": "ok",
            "reason_fr": f"{len(recent_invoices)} facture(s) dans les 6 derniers mois",
            "suggestion_fr": None,
            "cta": None,
            "fix_actions": [],
        })
    elif invoices:
        checks.append({
            "id": "has_recent_invoices",
            "label_fr": "Factures récentes",
            "status": "warn",
            "reason_fr": f"{len(invoices)} facture(s) mais aucune dans les 6 derniers mois",
            "suggestion_fr": "Importez les factures récentes pour compléter le suivi",
            "cta": "invoices",
            "fix_actions": [
                {"action": "navigate_import", "label_fr": "Importer des factures", "method": "NAVIGATE"},
            ],
        })
    else:
        checks.append({
            "id": "has_recent_invoices",
            "label_fr": "Factures récentes",
            "status": "fail",
            "reason_fr": "Aucune facture importée pour ce site",
            "suggestion_fr": "Importez vos factures énergie (CSV ou saisie manuelle)",
            "cta": "invoices",
            "fix_actions": [
                {"action": "navigate_import", "label_fr": "Importer des factures", "method": "NAVIGATE"},
            ],
        })

    # Check 4: period_coherence (invoice dates aligned with contract dates)
    period_ok = True
    period_reason = "Pas de données suffisantes pour vérifier"
    if active_contracts and recent_invoices:
        earliest_contract_start = min(
            (c.start_date for c in active_contracts if c.start_date), default=None
        )
        for inv in recent_invoices:
            if inv.period_start and earliest_contract_start and inv.period_start < earliest_contract_start:
                period_ok = False
                break
        if period_ok:
            period_reason = "Périodes facturées cohérentes avec les contrats actifs"
        else:
            period_reason = "Certaines factures couvrent des périodes antérieures au contrat actif"

    period_fix_actions = []
    if not period_ok:
        period_fix_actions = [
            {"action": "adjust_contract_dates", "label_fr": "Ajuster les dates du contrat", "method": "POST"},
        ]

    checks.append({
        "id": "period_coherence",
        "label_fr": "Cohérence périodes",
        "status": "ok" if period_ok else "warn",
        "reason_fr": period_reason,
        "suggestion_fr": None if period_ok else "Vérifiez l'alignement contrat/factures",
        "cta": None,
        "fix_actions": period_fix_actions,
    })

    # Check 5: energy_type_match (DP energy type matches contract energy type)
    type_match = True
    type_reason = "Types d'énergie cohérents"
    if dps and active_contracts:
        dp_types = {dp.energy_type.name.lower() if dp.energy_type else None for dp in dps} - {None}
        ct_types = {c.energy_type.value.lower() if c.energy_type else None for c in active_contracts} - {None}
        if dp_types and ct_types and not dp_types.intersection(ct_types):
            type_match = False
            type_reason = f"PdL: {', '.join(dp_types)} vs Contrats: {', '.join(ct_types)}"
    elif not dps or not active_contracts:
        type_reason = "Vérification impossible (données manquantes)"

    type_fix_actions = []
    if not type_match:
        type_fix_actions = [
            {"action": "align_energy_type", "label_fr": "Aligner le type énergie", "method": "POST"},
        ]

    checks.append({
        "id": "energy_type_match",
        "label_fr": "Cohérence type énergie",
        "status": "ok" if type_match else "warn",
        "reason_fr": type_reason,
        "suggestion_fr": None if type_match else "Le type énergie PdL ne correspond pas au contrat",
        "cta": None,
        "fix_actions": type_fix_actions,
    })

    # Check 6: has_payment_rule
    from routes.patrimoine import _resolve_payment_rule
    pr = _resolve_payment_rule(db, site_id)
    if pr:
        checks.append({
            "id": "has_payment_rule",
            "label_fr": "Règle de paiement",
            "status": "ok",
            "reason_fr": f"Règle configurée (niveau {pr.level.value})",
            "suggestion_fr": None,
            "cta": None,
            "fix_actions": [],
        })
    else:
        checks.append({
            "id": "has_payment_rule",
            "label_fr": "Règle de paiement",
            "status": "warn",
            "reason_fr": "Aucune règle de paiement configurée",
            "suggestion_fr": "Configurez la matrice facturé/payeur depuis Paiement & Refacturation",
            "cta": "payment-rules",
            "fix_actions": [
                {"action": "create_payment_rule", "label_fr": "Créer une règle de paiement", "method": "POST"},
            ],
        })

    # Compute score & status
    ok_count = sum(1 for c in checks if c["status"] == "ok")
    score = int(100 * ok_count / len(checks)) if checks else 0
    has_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)
    status = "fail" if has_fail else ("warn" if has_warn else "ok")

    summary_map = {
        "ok": "Réconciliation complète — données cohérentes",
        "warn": "Réconciliation partielle — points d'attention détectés",
        "fail": "Réconciliation incomplète — données manquantes",
    }

    return {
        "site_id": site_id,
        "status": status,
        "score": score,
        "checks": checks,
        "summary_fr": summary_map[status],
    }


def reconcile_portfolio(db: Session, org_id: int, portefeuille_id: Optional[int] = None) -> dict:
    """Aggregate reconcile_site for all sites in scope."""
    q = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    if portefeuille_id:
        q = q.filter(Site.portefeuille_id == portefeuille_id)

    sites = q.all()

    results = []
    stats = {"ok": 0, "warn": 0, "fail": 0, "total": len(sites)}

    for site in sites:
        r = reconcile_site(db, site.id)
        results.append({
            "site_id": site.id,
            "nom": site.nom,
            "status": r["status"],
            "score": r["score"],
        })
        stats[r["status"]] += 1

    return {"sites": results, "stats": stats}


# ========================================
# V97: Fixer functions (1-click resolution)
# ========================================

def _log_fix(db: Session, site_id: int, check_id: str, action: str,
             status_before: str, status_after: str, detail: dict = None, applied_by: str = None):
    """Record an audit trail entry for a reconciliation fix."""
    log = ReconciliationFixLog(
        site_id=site_id,
        check_id=check_id,
        action=action,
        status_before=ReconciliationStatus(status_before),
        status_after=ReconciliationStatus(status_after),
        detail_json=json.dumps(detail) if detail else None,
        applied_by=applied_by,
    )
    db.add(log)
    db.flush()
    return log


def fix_create_delivery_point(db: Session, site_id: int, code: str, energy_type: str = "ELEC",
                              applied_by: str = None) -> dict:
    """Fix: Create a delivery point for a site missing PRM/PCE."""
    from models.enums import DeliveryPointEnergyType, DeliveryPointStatus
    dp = DeliveryPoint(
        site_id=site_id,
        code=code,
        energy_type=DeliveryPointEnergyType[energy_type.upper()],
        status=DeliveryPointStatus.ACTIVE,
    )
    db.add(dp)
    db.flush()
    _log_fix(db, site_id, "has_delivery_points", "create_delivery_point",
             "fail", "ok", {"delivery_point_id": dp.id, "code": code}, applied_by)
    return {"delivery_point_id": dp.id, "code": code}


def fix_extend_contract(db: Session, site_id: int, contract_id: int, months: int = 12,
                        applied_by: str = None) -> dict:
    """Fix: Extend an expired contract's end_date by N months."""
    ct = db.query(EnergyContract).filter(
        EnergyContract.id == contract_id,
        EnergyContract.site_id == site_id,
    ).first()
    if not ct:
        return {"error": "Contrat non trouvé"}

    old_end = ct.end_date
    today = date.today()
    new_end = date(today.year + (today.month + months - 1) // 12,
                   (today.month + months - 1) % 12 + 1, 1)
    ct.end_date = new_end
    db.flush()
    _log_fix(db, site_id, "has_active_contract", "extend_contract",
             "warn", "ok",
             {"contract_id": contract_id, "old_end": str(old_end), "new_end": str(new_end)},
             applied_by)
    return {"contract_id": contract_id, "new_end_date": str(new_end)}


def fix_adjust_contract_dates(db: Session, site_id: int, contract_id: int,
                              new_start: str = None, applied_by: str = None) -> dict:
    """Fix: Adjust contract start date to cover invoice periods."""
    ct = db.query(EnergyContract).filter(
        EnergyContract.id == contract_id,
        EnergyContract.site_id == site_id,
    ).first()
    if not ct:
        return {"error": "Contrat non trouvé"}

    # Find earliest invoice period_start for this site
    earliest_inv = (
        db.query(EnergyInvoice)
        .filter(EnergyInvoice.site_id == site_id, EnergyInvoice.period_start.isnot(None))
        .order_by(EnergyInvoice.period_start.asc())
        .first()
    )
    old_start = ct.start_date
    if new_start:
        ct.start_date = date.fromisoformat(new_start)
    elif earliest_inv and earliest_inv.period_start:
        ct.start_date = earliest_inv.period_start
    db.flush()
    _log_fix(db, site_id, "period_coherence", "adjust_contract_dates",
             "warn", "ok",
             {"contract_id": contract_id, "old_start": str(old_start), "new_start": str(ct.start_date)},
             applied_by)
    return {"contract_id": contract_id, "new_start_date": str(ct.start_date)}


def fix_align_energy_type(db: Session, site_id: int, applied_by: str = None) -> dict:
    """Fix: Align contract energy_type with the majority DP energy_type."""
    from models.enums import BillingEnergyType
    dps = (
        db.query(DeliveryPoint)
        .filter(DeliveryPoint.site_id == site_id, DeliveryPoint.deleted_at.is_(None))
        .all()
    )
    if not dps:
        return {"error": "Aucun point de livraison"}

    # Find majority DP energy type
    dp_types = [dp.energy_type.name.lower() for dp in dps if dp.energy_type]
    if not dp_types:
        return {"error": "Type énergie PdL inconnu"}
    majority = max(set(dp_types), key=dp_types.count)

    today = date.today()
    contracts = (
        db.query(EnergyContract)
        .filter(EnergyContract.site_id == site_id)
        .all()
    )
    updated = 0
    for ct in contracts:
        ct_type = ct.energy_type.value.lower() if ct.energy_type else None
        if ct_type != majority:
            ct.energy_type = BillingEnergyType(majority)
            updated += 1

    db.flush()
    if updated:
        _log_fix(db, site_id, "energy_type_match", "align_energy_type",
                 "warn", "ok",
                 {"aligned_to": majority, "contracts_updated": updated},
                 applied_by)
    return {"aligned_to": majority, "contracts_updated": updated}


def fix_create_payment_rule(db: Session, site_id: int, invoice_entity_id: int,
                            payer_entity_id: int = None, cost_center: str = None,
                            applied_by: str = None) -> dict:
    """Fix: Create a site-level payment rule."""
    pr = PaymentRule(
        level=PaymentRuleLevel.SITE,
        site_id=site_id,
        invoice_entity_id=invoice_entity_id,
        payer_entity_id=payer_entity_id,
        cost_center=cost_center,
    )
    db.add(pr)
    db.flush()
    _log_fix(db, site_id, "has_payment_rule", "create_payment_rule",
             "warn", "ok",
             {"payment_rule_id": pr.id, "invoice_entity_id": invoice_entity_id},
             applied_by)
    return {"payment_rule_id": pr.id}


def get_fix_logs(db: Session, site_id: int) -> list:
    """Return audit trail for a site's reconciliation fixes."""
    logs = (
        db.query(ReconciliationFixLog)
        .filter(ReconciliationFixLog.site_id == site_id)
        .order_by(ReconciliationFixLog.applied_at.desc())
        .all()
    )
    return [
        {
            "id": log.id,
            "site_id": log.site_id,
            "check_id": log.check_id,
            "action": log.action,
            "status_before": log.status_before.value if log.status_before else None,
            "status_after": log.status_after.value if log.status_after else None,
            "detail": json.loads(log.detail_json) if log.detail_json else None,
            "applied_by": log.applied_by,
            "applied_at": log.applied_at.isoformat() if log.applied_at else None,
        }
        for log in logs
    ]


def get_evidence_pack(db: Session, site_id: int) -> dict:
    """V97 Phase 4: Generate evidence pack for a site's reconciliation."""
    recon = reconcile_site(db, site_id)
    logs = get_fix_logs(db, site_id)

    site = db.query(Site).filter(Site.id == site_id).first()
    site_name = site.nom if site else f"Site {site_id}"

    return {
        "site_id": site_id,
        "site_name": site_name,
        "generated_at": datetime.utcnow().isoformat(),
        "reconciliation": recon,
        "fix_history": logs,
        "summary": {
            "status": recon["status"],
            "score": recon["score"],
            "checks_total": len(recon["checks"]),
            "checks_ok": sum(1 for c in recon["checks"] if c["status"] == "ok"),
            "checks_warn": sum(1 for c in recon["checks"] if c["status"] == "warn"),
            "checks_fail": sum(1 for c in recon["checks"] if c["status"] == "fail"),
            "fixes_applied": len(logs),
        },
    }
