"""
PROMEOS — executive_narrative_service (Cockpit P1, 2026-05-25).

Service dédié à l'agrégation Executive Narrative pour /cockpit/strategique :
  1. executive_summary : 5 chiffres clés pour DAF/DG en 30 secondes
  2. top_priorities : Top 3 priorités cross-briques (conformité + billing +
     patrimoine + actions) avec impact + échéance + CTA unique.

Doctrine §8.1 : zéro logique métier frontend — le FE rend `payload.
executive_summary` + `payload.top_priorities` sans recalcul.
Doctrine §6.2 hub unique : chaque CTA pointe vers une page existante
(/conformite, /bill-intel, /centre-action, /patrimoine) — jamais une
nouvelle route.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    BillingInsight,
    EnergyContract,
    EnergyInvoice,
    Organisation,
    Site,
    StatutConformite,
    not_deleted,
)
from models.enums import InsightStatus
from models.v4.action_center_items import ActionCenterItem
from models.v4.enums import Domain, LifecycleState
from services.scope_utils import sites_for_org_query as _sites_for_org


# ─── Helpers KPI metadata ──────────────────────────────────────────────


def _kpi(*, id_, label_fr, value, unit, source, formula, period, scope, sub=None):
    """Format un KPI executive_summary avec metadata complète (doctrine §8.1)."""
    out = {
        "id": id_,
        "label_fr": label_fr,
        "value": value,
        "unit": unit,
        "source": source,
        "formula": formula,
        "period": period,
        "scope": scope,
    }
    if sub:
        out["sub_label_fr"] = sub
    return out


def _priority(
    *,
    id_,
    label_fr,
    why_fr,
    impact_value,
    impact_unit,
    deadline_iso,
    days_remaining,
    perimetre_fr,
    cta_label_fr,
    cta_link,
    priority_rank,
    source_fr,
    action_recommandee_fr,
    category,
):
    """Format une priorité (Top 3) avec tous les champs DAF.

    Cockpit P1.5 (2026-05-25) — ajout source_fr + action_recommandee_fr (Phase
    « Pourquoi cette priorité ? ») + category (clé interne d'ordonnancement
    canonique : 5 catégories préservées pour tri stable côté service).
    """
    return {
        "id": id_,
        "label_fr": label_fr,
        "why_fr": why_fr,
        "source_fr": source_fr,
        "action_recommandee_fr": action_recommandee_fr,
        "impact": {"value": impact_value, "unit": impact_unit},
        "deadline": {"iso": deadline_iso, "days_remaining": days_remaining},
        "perimetre_fr": perimetre_fr,
        "cta": {"label_fr": cta_label_fr, "link": cta_link},
        "priority_rank": priority_rank,
        "category": category,
    }


# ─── 1. Executive summary (5 chiffres clés) ──────────────────────────


def _compute_compliance_score(db: Session, org_id: int) -> tuple[Optional[float], str]:
    """Score conformité unifié org. Retourne (score, confidence)."""
    from services.compliance_score_service import compute_portfolio_compliance

    result = compute_portfolio_compliance(db, org_id) if org_id else {}
    score = result.get("avg_score")
    if score is None or score == 0.0:
        return None, "non_applicable"
    high_conf = result.get("high_confidence_count", 0) or 0
    total = result.get("total_sites", 0) or 0
    if total == 0:
        return None, "non_applicable"
    if high_conf >= total * 0.66:
        return round(score, 1), "high"
    if high_conf >= total * 0.33:
        return round(score, 1), "medium"
    return round(score, 1), "low"


def _compute_actions_ouvertes_count(db: Session, org_id: int) -> int:
    """Nombre total d'actions ouvertes (tous domaines, ActionCenterItem)."""
    return (
        db.query(func.count(ActionCenterItem.id))
        .filter(
            ActionCenterItem.organisation_id == org_id,
            ActionCenterItem.lifecycle_state != LifecycleState.CLOSED.value,
        )
        .scalar()
        or 0
    )


def _compute_next_deadline(db: Session, org_id: int) -> Optional[dict]:
    """Prochaine échéance réglementaire — réutilise la frise timeline."""
    try:
        from routes.compliance import _build_timeline_events

        events = _build_timeline_events(db, org_id)
        return events.get("next_deadline")
    except Exception:
        return None


def _compute_surfacturations_total(db: Session, site_ids: list[int]) -> float:
    """Σ insights ouverts (open + ack) — SoT BillingInsight."""
    if not site_ids:
        return 0.0
    total = (
        not_deleted(
            db.query(func.coalesce(func.sum(BillingInsight.estimated_loss_eur), 0.0)),
            BillingInsight,
        )
        .filter(
            BillingInsight.site_id.in_(site_ids),
            BillingInsight.insight_status.in_([InsightStatus.OPEN, InsightStatus.ACK]),
        )
        .scalar()
        or 0.0
    )
    return round(float(total), 2)


def _compute_sites_in_scope(db: Session, org_id: int) -> int:
    """Nombre de sites actifs dans le périmètre org."""
    return _sites_for_org(db, org_id).with_entities(Site.id).count()


def compute_executive_summary(db: Session, org_id: int) -> dict:
    """Retourne le payload Situation en 30 secondes.

    5 chiffres clés DAF/DG :
      1. score_conformite (/100)
      2. risque_financier_a_contester (€)
      3. prochaine_echeance (date + jours)
      4. actions_ouvertes (count)
      5. sites_dans_perimetre (count, contexte)
    """
    if not org_id:
        return {"kpis": [], "_error": "no_org_id"}

    site_ids = [s.id for s in _sites_for_org(db, org_id).with_entities(Site.id).all()]
    score, confidence = _compute_compliance_score(db, org_id)
    actions_count = _compute_actions_ouvertes_count(db, org_id)
    next_dl = _compute_next_deadline(db, org_id)
    surfact = _compute_surfacturations_total(db, site_ids)
    sites_count = len(site_ids)

    return {
        "kpis": [
            _kpi(
                id_="score_conformite",
                label_fr="Score conformité",
                value=score,
                unit="/100",
                source="compliance_score_service.compute_portfolio_compliance",
                formula="Moyenne pondérée frameworks DT/BACS/APER + pénalité findings critiques (max -20)",
                period="snapshot",
                scope=f"{sites_count} site(s) dans le périmètre",
                sub=f"Fiabilité : {confidence}",
            ),
            _kpi(
                id_="risque_financier_a_contester",
                label_fr="Surfacturations à contester",
                value=surfact,
                unit="€",
                source="BillingInsight.estimated_loss_eur",
                formula="Σ insights status ∈ {open, ack} sur sites du périmètre",
                period="snapshot",
                scope=f"{sites_count} site(s)",
            ),
            _kpi(
                id_="prochaine_echeance",
                label_fr="Prochaine échéance",
                value=next_dl.get("days_remaining") if next_dl else None,
                unit="jours",
                source="compliance.timeline.next_deadline",
                formula="MIN(events.deadline) pour status ∈ {upcoming, future}",
                period="snapshot",
                scope="org",
                sub=(next_dl or {}).get("label"),
            ),
            _kpi(
                id_="actions_ouvertes",
                label_fr="Actions ouvertes",
                value=actions_count,
                unit="actions",
                source="ActionCenterItem (lifecycle_state ≠ closed)",
                formula="COUNT(items) tous domaines (facturation + conformité + autre)",
                period="snapshot",
                scope="org",
            ),
            _kpi(
                id_="sites_dans_perimetre",
                label_fr="Sites suivis",
                value=sites_count,
                unit="sites",
                source="Site.actif=True via scope org",
                formula="COUNT(sites actifs du périmètre org)",
                period="snapshot",
                scope="org",
            ),
        ],
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── 2. Top 3 Priorities (cross-briques) ─────────────────────────────


def _top_billing_priority(db: Session, site_ids: list[int]) -> Optional[dict]:
    """Plus grosse surfacturation à contester (insight le plus coûteux ouvert)."""
    if not site_ids:
        return None
    top = (
        not_deleted(db.query(BillingInsight), BillingInsight)
        .filter(
            BillingInsight.site_id.in_(site_ids),
            BillingInsight.insight_status.in_([InsightStatus.OPEN, InsightStatus.ACK]),
        )
        .order_by(BillingInsight.estimated_loss_eur.desc().nulls_last())
        .first()
    )
    if not top or not top.estimated_loss_eur:
        return None
    return _priority(
        id_=f"billing_{top.id}",
        label_fr=f"Surfacturation à contester ({round(top.estimated_loss_eur)} €)",
        why_fr="Montant à contester",
        source_fr="BillingInsight (insight le plus coûteux, status open/ack)",
        action_recommandee_fr="Ouvrir la facture, vérifier le poste contesté, déclencher un litige fournisseur si confirmé.",
        impact_value=round(float(top.estimated_loss_eur), 2),
        impact_unit="€",
        deadline_iso=None,
        days_remaining=None,
        perimetre_fr=f"Site #{top.site_id}",
        cta_label_fr="Voir la facture",
        cta_link=f"/bill-intel?insight={top.id}",
        priority_rank=1,
        category="billing",
    )


def _top_compliance_priority(db: Session, org_id: int) -> Optional[dict]:
    """Action conformité la plus urgente (next_deadline ou finding critical)."""
    next_dl = _compute_next_deadline(db, org_id)
    if not next_dl or next_dl.get("days_remaining") is None:
        return None
    days = next_dl.get("days_remaining")
    label = next_dl.get("label") or "Échéance réglementaire"
    return _priority(
        id_=f"compliance_{next_dl.get('id', 'next')}",
        label_fr=f"Échéance conformité : {label}",
        why_fr="Risque réglementaire",
        source_fr="compliance.timeline.next_deadline (frise réglementaire ADR-024)",
        action_recommandee_fr="Préparer la déclaration ou les pièces justificatives avant la deadline ; assigner un pilote.",
        impact_value=days,
        impact_unit="jours restants",
        deadline_iso=next_dl.get("deadline"),
        days_remaining=days,
        perimetre_fr="org",
        cta_label_fr="Voir l'obligation",
        cta_link="/conformite",
        priority_rank=2,
        category="regulatory_urgent" if days < 30 else "regulatory",
    )


def _top_patrimoine_priority(db: Session, org_id: int) -> Optional[dict]:
    """Sites avec données manquantes bloquantes — utilise applicability_service."""
    try:
        from regulatory.applicability_service import compute_applicability
        from regulatory.applicability_types import ApplicabilityStatus

        app = compute_applicability(db, org_id) if org_id else {}
        data_missing = 0
        worst_rule = None
        for rule_code, entries in (app or {}).items():
            missing = sum(1 for e in entries if getattr(e, "status", None) == ApplicabilityStatus.DATA_MISSING)
            if missing > data_missing:
                data_missing = missing
                worst_rule = rule_code
        if data_missing == 0:
            return None
        return _priority(
            id_=f"patrimoine_{worst_rule}",
            label_fr=f"Données manquantes ({data_missing} site(s)) — {worst_rule}",
            why_fr="Donnée patrimoine bloquante",
            source_fr=f"applicability_service.compute_applicability (status=DATA_MISSING sur {worst_rule})",
            action_recommandee_fr="Compléter la fiche patrimoine du site (surface, énergie, usage) pour débloquer l'évaluation réglementaire.",
            impact_value=data_missing,
            impact_unit="sites",
            deadline_iso=None,
            days_remaining=None,
            perimetre_fr=f"{data_missing} site(s) concerné(s)",
            cta_label_fr="Compléter les données",
            cta_link=f"/patrimoine?incomplete={worst_rule}",
            priority_rank=3,
            category="patrimoine",
        )
    except Exception:
        return None


def _top_evidence_priority(db: Session, org_id: int) -> Optional[dict]:
    """Action ouverte bloquée par un blocker waiting_evidence (preuve manquante).

    Cockpit P1.5 (2026-05-25) — 4e catégorie de priorité : si un item
    ActionCenter est bloqué côté evidence, on remonte le signal pour que
    le pilote sache exactement quelle pièce produire.
    """
    try:
        from models.v4.action_blockers import ActionBlocker

        row = (
            db.query(ActionCenterItem, ActionBlocker)
            .join(ActionBlocker, ActionBlocker.item_id == ActionCenterItem.id)
            .filter(
                ActionCenterItem.organisation_id == org_id,
                ActionCenterItem.lifecycle_state != LifecycleState.CLOSED.value,
                ActionBlocker.blocker_type == "waiting_evidence",
                ActionBlocker.resolved_at.is_(None),
            )
            .order_by(ActionCenterItem.priority_score.desc().nulls_last())
            .first()
        )
        if not row:
            return None
        item, blocker = row
        return _priority(
            id_=f"evidence_{item.id}",
            label_fr=f"Preuve manquante : {item.title}",
            why_fr="Preuve manquante bloquante",
            source_fr="ActionBlocker.blocker_type='waiting_evidence' (ADR-029 evidence audit trail)",
            action_recommandee_fr=(
                blocker.justification or "Produire ou téléverser la pièce justificative pour débloquer l'action."
            ),
            impact_value=item.priority_score or 0,
            impact_unit="score",
            deadline_iso=None,
            days_remaining=None,
            perimetre_fr=item.domain or "org",
            cta_label_fr="Ouvrir l'action",
            cta_link=f"/centre-action?item={item.id}",
            priority_rank=4,
            category="evidence_missing",
        )
    except Exception:
        return None


def _top_contract_priority(db: Session, site_ids: list[int]) -> Optional[dict]:
    """Contrat énergie à surveiller : end_date < 90 jours.

    Cockpit P1.5 (2026-05-25) — 5e catégorie : alerte DAF sur un contrat
    qui arrive à échéance pour préparer la renégociation/renouvellement.
    """
    if not site_ids:
        return None
    today = date.today()
    horizon = today.toordinal() + 90
    contract = (
        db.query(EnergyContract)
        .filter(
            EnergyContract.site_id.in_(site_ids),
            EnergyContract.end_date.isnot(None),
            EnergyContract.end_date >= today,
        )
        .order_by(EnergyContract.end_date.asc())
        .first()
    )
    if not contract or contract.end_date.toordinal() > horizon:
        return None
    days = (contract.end_date - today).days
    return _priority(
        id_=f"contract_{contract.id}",
        label_fr=f"Contrat énergie à renouveler ({contract.supplier_name or 'fournisseur'})",
        why_fr="Contrat à surveiller",
        source_fr="EnergyContract.end_date (horizon 90 j)",
        action_recommandee_fr="Lancer la consultation marché et préparer la renégociation avant échéance.",
        impact_value=days,
        impact_unit="jours restants",
        deadline_iso=contract.end_date.isoformat(),
        days_remaining=days,
        perimetre_fr=f"Site #{contract.site_id}",
        cta_label_fr="Voir le contrat",
        cta_link=f"/bill-intel?contract={contract.id}",
        priority_rank=5,
        category="contract",
    )


# Ordre canonique Cockpit P1.5 (2026-05-25) — brief Lead Product :
#   1. risque réglementaire urgent  (deadline < 30 j)
#   2. montant facture à contester
#   3. preuve manquante bloquante
#   4. donnée patrimoine bloquante
#   5. contrat énergie à surveiller
# « regulatory » (non urgent) tombe après contract pour ne pas bumper un
# DT 2030 à la place d'une surfact immédiate.
_CATEGORY_ORDER = {
    "regulatory_urgent": 0,
    "billing": 1,
    "evidence_missing": 2,
    "patrimoine": 3,
    "contract": 4,
    "regulatory": 5,
}


def compute_top_priorities(db: Session, org_id: int) -> list[dict]:
    """Agrège Top 3 priorités cross-briques selon l'ordre canonique P1.5.

    5 catégories collectées (billing, compliance, evidence, patrimoine,
    contract). Tri par `_CATEGORY_ORDER` puis cap à 3. Si une catégorie
    est vide, on ne « remplit pas » — vrai signal > N entrées vides.
    """
    if not org_id:
        return []
    site_ids = [s.id for s in _sites_for_org(db, org_id).with_entities(Site.id).all()]
    candidates: list[dict] = []
    for builder in (
        lambda: _top_billing_priority(db, site_ids),
        lambda: _top_compliance_priority(db, org_id),
        lambda: _top_evidence_priority(db, org_id),
        lambda: _top_patrimoine_priority(db, org_id),
        lambda: _top_contract_priority(db, site_ids),
    ):
        p = builder()
        if p:
            candidates.append(p)

    candidates.sort(key=lambda p: _CATEGORY_ORDER.get(p.get("category"), 9))
    top = candidates[:3]
    for idx, p in enumerate(top, start=1):
        p["priority_rank"] = idx
    return top


# ─── Entrée publique combinée ────────────────────────────────────────


def compute_executive_narrative(db: Session, org_id: int) -> dict:
    """Payload Executive Narrative complet — injecté dans /cockpit/strategique.

    Returns:
        {
            "executive_summary": { "kpis": [...5 KPIs] },
            "top_priorities": [...max 3 priorités],
            "computed_at": "ISO",
        }
    """
    return {
        "executive_summary": compute_executive_summary(db, org_id),
        "top_priorities": compute_top_priorities(db, org_id),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
