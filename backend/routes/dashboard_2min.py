"""
PROMEOS - Dashboard "2 minutes"
GET /api/dashboard/2min - Vue synthetique en 3 blocs pour un prospect
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from models import (
    Portefeuille, EntiteJuridique,
    Organisation, Site, Obligation, Compteur, ComplianceFinding,
    ConsumptionInsight, StatutConformite, TypeObligation,
    EnergyInvoice, BillingInsight, BillingInvoiceStatus,
    PurchaseScenarioResult, PurchaseRecoStatus,
    ActionItem, ActionStatus,
    NotificationEvent, NotificationStatus, NotificationSeverity,
    not_deleted,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard 2min"])


def _sites_for_org_query(db: Session, org_id: int):
    """Base query: non-deleted sites scoped to org_id via join chain."""
    return (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )


@router.get("/2min")
def get_dashboard_2min(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Retourne un JSON minimal pour le cockpit "2 minutes":
    - conformite_status: etat global conformite
    - pertes_estimees_eur: risque financier total
    - action_1: action prioritaire (#1)
    - organisation: nom + type
    - completude: % de remplissage du patrimoine

    Scope: X-Org-Id header > auth.org_id > last-created org (fallback).
    """
    # DEMO_MODE-aware scope resolution (auth > header > demo fallback > 401)
    try:
        effective_org_id = resolve_org_id(request, auth, db)
        org = db.query(Organisation).filter(Organisation.id == effective_org_id).first()
    except HTTPException:
        org = None

    if not org:
        return {
            "has_data": False,
            "conformite_status": None,
            "pertes_estimees_eur": None,
            "action_1": None,
            "organisation": None,
            "completude": _empty_completude(),
        }

    # Stats sites — scoped to org
    q_sites = _sites_for_org_query(db, org.id)
    total_sites = q_sites.count()
    sites_actifs = q_sites.filter(Site.actif == True).count()
    site_ids = [s.id for s in q_sites.with_entities(Site.id).all()]
    total_compteurs = (
        not_deleted(db.query(Compteur), Compteur)
        .filter(Compteur.site_id.in_(site_ids))
        .count()
    ) if site_ids else 0

    # Conformite globale — scoped to org's sites
    obligations = (
        db.query(Obligation).filter(Obligation.site_id.in_(site_ids)).all()
        if site_ids else []
    )
    if obligations:
        nb_conforme = sum(1 for o in obligations if o.statut == StatutConformite.CONFORME)
        nb_non_conforme = sum(1 for o in obligations if o.statut == StatutConformite.NON_CONFORME)
        nb_a_risque = sum(1 for o in obligations if o.statut == StatutConformite.A_RISQUE)
        total_obl = len(obligations)

        if nb_non_conforme > 0:
            conformite_label = "Non conforme"
            conformite_color = "red"
        elif nb_a_risque > 0:
            conformite_label = "A risque"
            conformite_color = "orange"
        elif nb_conforme == total_obl:
            conformite_label = "Conforme"
            conformite_color = "green"
        else:
            conformite_label = "En cours"
            conformite_color = "blue"

        conformite_status = {
            "label": conformite_label,
            "color": conformite_color,
            "obligations_total": total_obl,
            "conformes": nb_conforme,
            "a_risque": nb_a_risque,
            "non_conformes": nb_non_conforme,
        }
    else:
        conformite_status = {
            "label": "A evaluer",
            "color": "gray",
            "obligations_total": 0,
            "conformes": 0,
            "a_risque": 0,
            "non_conformes": 0,
        }

    # Risque financier — scoped to org's sites
    risque_total = (
        _sites_for_org_query(db, org.id)
        .with_entities(func.sum(Site.risque_financier_euro))
        .scalar() or 0
    )
    pertes_conso = (
        db.query(func.sum(ConsumptionInsight.estimated_loss_eur))
        .filter(ConsumptionInsight.site_id.in_(site_ids))
        .scalar() or 0
    ) if site_ids else 0
    pertes_billing = (
        db.query(func.sum(BillingInsight.estimated_loss_eur))
        .filter(BillingInsight.site_id.in_(site_ids))
        .scalar() or 0
    ) if site_ids else 0

    # Action prioritaire #1
    action_1 = _get_top_action(db, obligations)

    # Completude du patrimoine
    completude = _compute_completude(total_sites, total_compteurs, org)

    # ComplianceFinding-based summary (Sprint 4) — scoped
    findings = (
        db.query(ComplianceFinding).filter(ComplianceFinding.site_id.in_(site_ids)).all()
        if site_ids else []
    )
    nok_findings = [f for f in findings if f.status == "NOK"]
    unknown_findings = [f for f in findings if f.status == "UNKNOWN"]

    findings_summary = None
    if findings:
        findings_summary = {
            "total": len(findings),
            "nok": len(nok_findings),
            "unknown": len(unknown_findings),
            "ok": sum(1 for f in findings if f.status == "OK"),
            "workflow": {
                "open": sum(1 for f in findings if getattr(f, 'insight_status', None) and f.insight_status.value == "open"),
                "ack": sum(1 for f in findings if getattr(f, 'insight_status', None) and f.insight_status.value == "ack"),
                "resolved": sum(1 for f in findings if getattr(f, 'insight_status', None) and f.insight_status.value == "resolved"),
            },
        }
        # Override action_1 from findings if more specific
        if nok_findings:
            import json
            nok_findings.sort(
                key=lambda f: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(f.severity, 0),
                reverse=True,
            )
            top = nok_findings[0]
            actions = json.loads(top.recommended_actions_json) if top.recommended_actions_json else []
            if actions:
                action_1 = {
                    "texte": actions[0],
                    "priorite": top.severity or "high",
                    "nb_sites_concernes": len(set(f.site_id for f in nok_findings if f.rule_id == top.rule_id)),
                    "reglementation": top.regulation,
                }

    # V1.1: If no critical compliance NOK, try top conso insight for action_1
    if not nok_findings:
        import json as _json
        top_insight = (
            db.query(ConsumptionInsight)
            .filter(
                ConsumptionInsight.site_id.in_(site_ids),
                ConsumptionInsight.estimated_loss_eur > 0,
            )
            .order_by(ConsumptionInsight.estimated_loss_eur.desc())
            .first()
        ) if site_ids else None
        if top_insight and top_insight.recommended_actions_json:
            rec = _json.loads(top_insight.recommended_actions_json)
            if rec:
                site_obj = db.query(Site).filter(Site.id == top_insight.site_id).first()
                action_1 = {
                    "texte": rec[0]["title"],
                    "priorite": top_insight.severity or "high",
                    "nb_sites_concernes": 1,
                    "reglementation": None,
                    "source": "conso_insight",
                    "site_nom": site_obj.nom if site_obj else None,
                    "expected_gain_eur": rec[0].get("expected_gain_eur", 0),
                }

    return {
        "has_data": True,
        "organisation": {
            "nom": org.nom,
            "type_client": org.type_client,
        },
        "conformite_status": conformite_status,
        "pertes_estimees_eur": round(risque_total + pertes_conso + pertes_billing, 2),
        "action_1": action_1,
        "completude": completude,
        "findings_summary": findings_summary,
        "stats": {
            "total_sites": total_sites,
            "sites_actifs": sites_actifs,
            "total_compteurs": total_compteurs,
            "total_obligations": len(obligations),
        },
        "billing": _billing_summary(db, site_ids),
        "achat": _purchase_summary(db, site_ids),
        "action_hub": _action_hub_summary(db, org.id),
        "alerts": _notifications_summary(db, org.id),
    }


def _get_top_action(db: Session, obligations) -> dict:
    """Determine l'action prioritaire #1."""
    # Priorite: non_conforme decret_tertiaire > non_conforme bacs > a_risque decret > a_risque bacs
    priority_order = [
        (TypeObligation.DECRET_TERTIAIRE, StatutConformite.NON_CONFORME,
         "Declarer vos consommations sur OPERAT", "critical"),
        (TypeObligation.BACS, StatutConformite.NON_CONFORME,
         "Installer un systeme GTB/GTC conforme", "critical"),
        (TypeObligation.DECRET_TERTIAIRE, StatutConformite.A_RISQUE,
         "Accelerer votre trajectoire Decret Tertiaire 2030", "high"),
        (TypeObligation.BACS, StatutConformite.A_RISQUE,
         "Planifier la mise en conformite BACS", "high"),
    ]

    for obl_type, obl_statut, action_text, priority in priority_order:
        matching = [o for o in obligations if o.type == obl_type and o.statut == obl_statut]
        if matching:
            return {
                "texte": action_text,
                "priorite": priority,
                "nb_sites_concernes": len(set(o.site_id for o in matching)),
                "reglementation": obl_type.value,
            }

    # Si tout est conforme ou pas d'obligations
    if not obligations:
        return {
            "texte": "Ajouter vos sites pour evaluer votre conformite",
            "priorite": "info",
            "nb_sites_concernes": 0,
            "reglementation": None,
        }

    return {
        "texte": "Maintenir votre conformite et surveiller les echeances",
        "priorite": "low",
        "nb_sites_concernes": 0,
        "reglementation": None,
    }


def _compute_completude(total_sites: int, total_compteurs: int, org) -> dict:
    """Calcule le % de completude du patrimoine."""
    checks = {
        "organisation": org is not None,
        "sites": total_sites > 0,
        "compteurs": total_compteurs > 0,
    }
    done = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "pct": round(done / total * 100),
        "checks": checks,
        "message": "Patrimoine complet" if done == total else f"{total - done} etape(s) restante(s)",
    }


def _empty_completude() -> dict:
    return {
        "pct": 0,
        "checks": {"organisation": False, "sites": False, "compteurs": False},
        "message": "Creez votre organisation pour commencer",
    }


def _purchase_summary(db: Session, site_ids: list) -> dict:
    """Achat energie summary for dashboard 2min. Scoped to site_ids."""
    from datetime import date as _date
    from models import EnergyContract, PurchaseAssumptionSet

    if not site_ids:
        return None

    q_base = (
        db.query(PurchaseScenarioResult)
        .join(PurchaseAssumptionSet, PurchaseAssumptionSet.id == PurchaseScenarioResult.assumption_set_id)
        .filter(PurchaseAssumptionSet.site_id.in_(site_ids))
    )

    total_results = q_base.count()
    if total_results == 0:
        return None

    recommended = q_base.filter(
        PurchaseScenarioResult.is_recommended == True
    ).first()

    base = {
        "total_scenarios": total_results,
        "recommendation": None,
    }

    if recommended:
        base["recommendation"] = {
            "strategy": recommended.strategy.value if recommended.strategy else None,
            "price_eur_per_kwh": recommended.price_eur_per_kwh,
            "total_annual_eur": recommended.total_annual_eur,
            "risk_score": recommended.risk_score,
            "savings_vs_current_pct": recommended.savings_vs_current_pct,
            "reco_status": recommended.reco_status.value if recommended.reco_status else None,
        }

    # V1.1: gain_potentiel_eur — scoped
    draft_recos = (
        db.query(PurchaseScenarioResult)
        .join(PurchaseAssumptionSet, PurchaseAssumptionSet.id == PurchaseScenarioResult.assumption_set_id)
        .filter(
            PurchaseAssumptionSet.site_id.in_(site_ids),
            PurchaseScenarioResult.is_recommended == True,
            PurchaseScenarioResult.reco_status == PurchaseRecoStatus.DRAFT,
        )
        .all()
    )
    gain = sum(
        abs(r.savings_vs_current_pct or 0) / 100 * r.total_annual_eur
        for r in draft_recos
        if r.savings_vs_current_pct and r.savings_vs_current_pct > 0
    )
    base["gain_potentiel_eur"] = round(gain, 2)

    # V1.1: prochain_renouvellement — scoped
    today = _date.today()
    next_contract = (
        db.query(EnergyContract)
        .filter(
            EnergyContract.site_id.in_(site_ids),
            EnergyContract.end_date.isnot(None),
            EnergyContract.end_date >= today,
        )
        .order_by(EnergyContract.end_date.asc())
        .first()
    )
    if next_contract:
        site = db.query(Site).filter(Site.id == next_contract.site_id).first()
        base["prochain_renouvellement"] = {
            "end_date": next_contract.end_date.isoformat(),
            "site_id": next_contract.site_id,
            "site_nom": site.nom if site else None,
            "supplier_name": next_contract.supplier_name,
            "days_remaining": (next_contract.end_date - today).days,
        }
    else:
        base["prochain_renouvellement"] = None

    return base


def _billing_summary(db: Session, site_ids: list) -> dict:
    """Billing intelligence summary for dashboard 2min. Scoped to site_ids."""
    if not site_ids:
        return None
    total_invoices = (
        db.query(EnergyInvoice)
        .filter(EnergyInvoice.site_id.in_(site_ids))
        .count()
    )
    if total_invoices == 0:
        return None
    total_eur = (
        db.query(func.sum(EnergyInvoice.total_eur))
        .filter(EnergyInvoice.site_id.in_(site_ids))
        .scalar() or 0
    )
    anomalies_count = (
        db.query(BillingInsight)
        .filter(BillingInsight.site_id.in_(site_ids))
        .count()
    )
    total_loss = (
        db.query(func.sum(BillingInsight.estimated_loss_eur))
        .filter(BillingInsight.site_id.in_(site_ids))
        .scalar() or 0
    )
    return {
        "total_invoices": total_invoices,
        "total_eur": round(total_eur, 2),
        "anomalies_count": anomalies_count,
        "total_loss_eur": round(total_loss, 2),
    }


def _action_hub_summary(db: Session, org_id: int) -> dict:
    """Action Hub summary for dashboard 2min. Returns None if no actions exist."""
    items = db.query(ActionItem).filter(ActionItem.org_id == org_id).all()
    if not items:
        return None

    action_stats = {
        "open": sum(1 for a in items if a.status == ActionStatus.OPEN),
        "in_progress": sum(1 for a in items if a.status == ActionStatus.IN_PROGRESS),
        "done": sum(1 for a in items if a.status == ActionStatus.DONE),
        "total": len(items),
    }

    # Top action: open, by priority ASC then due_date ASC NULLS LAST
    open_actions = [a for a in items if a.status in (ActionStatus.OPEN, ActionStatus.IN_PROGRESS)]
    open_actions.sort(key=lambda a: (a.priority or 5, str(a.due_date or "9999-12-31")))

    top_action = None
    if open_actions:
        a = open_actions[0]
        top_action = {
            "id": a.id,
            "texte": a.title,
            "priorite": a.severity or "high",
            "nb_sites_concernes": 1,
            "source": "action_hub",
        }

    total_gain = sum(a.estimated_gain_eur or 0 for a in items if a.status != ActionStatus.DONE)

    return {
        "action_stats": action_stats,
        "top_action": top_action,
        "total_gain_eur": round(total_gain, 2),
    }


def _notifications_summary(db: Session, org_id: int) -> dict:
    """Notifications summary for dashboard 2min. Returns None if no events exist."""
    events = (
        db.query(NotificationEvent)
        .filter(NotificationEvent.org_id == org_id)
        .all()
    )
    if not events:
        return None

    new_critical = sum(
        1 for e in events
        if e.status == NotificationStatus.NEW and e.severity == NotificationSeverity.CRITICAL
    )
    new_warn = sum(
        1 for e in events
        if e.status == NotificationStatus.NEW and e.severity == NotificationSeverity.WARN
    )
    new_total = sum(1 for e in events if e.status == NotificationStatus.NEW)

    # Top alert: NEW + CRITICAL first, then WARN, ordered by created_at desc
    new_events = [e for e in events if e.status == NotificationStatus.NEW]
    sev_order = {NotificationSeverity.CRITICAL: 0, NotificationSeverity.WARN: 1, NotificationSeverity.INFO: 2}
    new_events.sort(key=lambda e: (sev_order.get(e.severity, 9), -(e.id or 0)))

    top_alert = None
    if new_events:
        e = new_events[0]
        top_alert = {
            "id": e.id,
            "title": e.title,
            "severity": e.severity.value if e.severity else "info",
            "deeplink_path": e.deeplink_path,
            "source_type": e.source_type.value if e.source_type else None,
        }

    return {
        "new_critical": new_critical,
        "new_warn": new_warn,
        "new_total": new_total,
        "total": len(events),
        "top_alert": top_alert,
    }
