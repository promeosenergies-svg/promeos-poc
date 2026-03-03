"""
PROMEOS — V96 Reconciliation 3 voies
Compteur (PRM/PCE) ↔ Contrat actif ↔ Factures.
Computed on-read, not persisted.
"""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Site, DeliveryPoint, EnergyContract, PaymentRule,
    Portefeuille, EntiteJuridique,
)
from models.billing_models import EnergyInvoice


def reconcile_site(db: Session, site_id: int) -> dict:
    """
    3-way reconciliation per site.
    Returns: {site_id, status, score, checks[], summary_fr}
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
        })
    else:
        checks.append({
            "id": "has_delivery_points",
            "label_fr": "Points de livraison",
            "status": "fail",
            "reason_fr": "Aucun point de livraison (PRM/PCE) rattaché",
            "suggestion_fr": "Ajoutez les codes PRM/PCE depuis l'onglet Patrimoine",
            "cta": "patrimoine",
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
        })
    elif contracts:
        checks.append({
            "id": "has_active_contract",
            "label_fr": "Contrat actif",
            "status": "warn",
            "reason_fr": f"{len(contracts)} contrat(s) existant(s) mais aucun couvrant la date du jour",
            "suggestion_fr": "Vérifiez les dates de vos contrats ou ajoutez un nouveau contrat",
            "cta": "contracts",
        })
    else:
        checks.append({
            "id": "has_active_contract",
            "label_fr": "Contrat actif",
            "status": "fail",
            "reason_fr": "Aucun contrat énergie rattaché à ce site",
            "suggestion_fr": "Ajoutez un contrat depuis l'onglet Factures",
            "cta": "contracts",
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
        })
    elif invoices:
        checks.append({
            "id": "has_recent_invoices",
            "label_fr": "Factures récentes",
            "status": "warn",
            "reason_fr": f"{len(invoices)} facture(s) mais aucune dans les 6 derniers mois",
            "suggestion_fr": "Importez les factures récentes pour compléter le suivi",
            "cta": "invoices",
        })
    else:
        checks.append({
            "id": "has_recent_invoices",
            "label_fr": "Factures récentes",
            "status": "fail",
            "reason_fr": "Aucune facture importée pour ce site",
            "suggestion_fr": "Importez vos factures énergie (CSV ou saisie manuelle)",
            "cta": "invoices",
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

    checks.append({
        "id": "period_coherence",
        "label_fr": "Cohérence périodes",
        "status": "ok" if period_ok else "warn",
        "reason_fr": period_reason,
        "suggestion_fr": None if period_ok else "Vérifiez l'alignement contrat/factures",
        "cta": None,
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

    checks.append({
        "id": "energy_type_match",
        "label_fr": "Cohérence type énergie",
        "status": "ok" if type_match else "warn",
        "reason_fr": type_reason,
        "suggestion_fr": None if type_match else "Le type énergie PdL ne correspond pas au contrat",
        "cta": None,
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
        })
    else:
        checks.append({
            "id": "has_payment_rule",
            "label_fr": "Règle de paiement",
            "status": "warn",
            "reason_fr": "Aucune règle de paiement configurée",
            "suggestion_fr": "Configurez la matrice facturé/payeur depuis Paiement & Refacturation",
            "cta": "payment-rules",
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
