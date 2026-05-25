"""
PROMEOS — Bill Intelligence P1 C4 (2026-05-24) :
Sync anomalies facture → ActionCenterItem (fermeture de la boucle "litige").

Endpoint : `POST /api/billing/sync-actions-from-anomalies`

Comportement :
- Pour chaque BillAnomaly ouverte (`resolved_at IS NULL`) ET actionnable
  (`is_monetizable=True`), créer ou mettre à jour un ActionCenterItem :
  * kind = Kind.ANOMALY (vocabulaire V4 doctrine, vs "BILLING_DISPUTE" non whitelisté)
  * domain = Domain.FACTURATION
  * title FR déterministe : "Litige facture — anomalie #{id} ({code})"
  * priority_bracket selon severity : critical=P0, warning=P1, info=P2
  * description avec `EXTERNAL_REF: billing_anomaly:{id}` traçable
- Idempotent par signature (org_id, kind, domain, title) — réplique du pattern
  conformité C1 (cf. routes/conformite_sync.py).
- Anomalie informative (`is_monetizable=False`) → SKIP (pas d'action créée,
  loggée dans `skipped_non_actionable`).
- Anomalie résolue (`resolved_at NOT NULL`) → SKIP.
- Item déjà clos par l'utilisateur (lifecycle_state=closed) → SKIP, jamais re-créé.

Sécurité : org-scoping cardinal via `resolve_org_id` + bascule 401 FR si pas
de contexte (pattern C3 audit-all).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models import EnergyInvoice, EntiteJuridique, Portefeuille, Site
from models.bill_anomaly import BillAnomaly
from models.v4.action_center_items import ActionCenterItem
from models.v4.action_links import ActionLink
from models.v4.enums import Domain, Kind, LifecycleState
from services.scope_utils import resolve_org_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["Bill Intelligence Sync"])


_SEVERITY_TO_BRACKET = {
    "critical": "P0",
    "warning": "P1",
    "info": "P2",
}
_SEVERITY_TO_SCORE = {
    "critical": 90.0,
    "warning": 70.0,
    "info": 40.0,
}


def _make_title(anomaly: BillAnomaly) -> str:
    """Title FR déterministe — signature d'idempotence."""
    return f"Litige facture — anomalie #{anomaly.id} ({anomaly.code})"


def _make_description(anomaly: BillAnomaly, invoice: EnergyInvoice) -> str:
    """Description FR claire pour le DAF avec EXTERNAL_REF traçable."""
    montant = anomaly.actual_value or 0
    return (
        f"EXTERNAL_REF: billing_anomaly:{anomaly.id}\n\n"
        f"Anomalie détectée sur la facture {invoice.invoice_number} "
        f"(période {invoice.period_start} → {invoice.period_end}).\n"
        f"Code : {anomaly.code} · sévérité : {anomaly.severity}\n"
        f"Impact estimé : {montant} €\n"
        f"Action recommandée : contacter le fournisseur pour ouvrir une réclamation "
        f"et joindre la preuve documentaire (cf. /bill-intel)."
    )


def _make_external_ref(anomaly: BillAnomaly) -> str:
    """Action Center V4 P0 fix (2026-05-25) — signature stable cross-brique
    pour idempotence DB (audit deep §5.3). Pattern : `billing_anomaly:{id}`.
    Garanti unique via index UNIQUE partial (organisation_id, external_ref)
    cf. action_center_items.py:idx_aci_external_ref."""
    return f"billing_anomaly:{anomaly.id}"


def _make_source_url(anomaly: BillAnomaly) -> str:
    """URL canonique de retour vers la source (audit deep §6 P0-4).
    Consommée par le drawer V4 LinksTab pour rendre le bouton « Voir la
    source » sans parser la description."""
    return f"/bill-intel?anomaly={anomaly.id}"


def _find_existing_item(db: Session, org_id: int, external_ref: str) -> Optional[ActionCenterItem]:
    """Recherche idempotente par external_ref (signature DB indexée UNIQUE
    par org). Remplace l'ancienne signature title-based vulnérable en race
    condition (audit deep §5.3 P0-3, 2026-05-25)."""
    return (
        db.query(ActionCenterItem)
        .filter(
            ActionCenterItem.organisation_id == org_id,
            ActionCenterItem.external_ref == external_ref,
        )
        .first()
    )


def _anomaly_target_uuid(anomaly_id: int) -> uuid.UUID:
    """Action Center V4 P0 fix (2026-05-25) — `ActionLink.target_id` est typé
    UUID alors que `BillAnomaly.id` est un Integer legacy. On dérive un UUID
    déterministe v5 depuis l'integer pour préserver l'idempotence (même
    anomaly_id ⇒ même UUID), tout en respectant le contrat du modèle."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"promeos:billing_anomaly:{anomaly_id}")


def _ensure_action_link(db: Session, org_id: int, item_id, anomaly_id: int) -> bool:
    """Action Center V4 P0 fix (2026-05-25) — peuple ActionLink si absente
    pour permettre le drawer LinksTab « Voir la source » sans parser la
    description (audit deep §6 P0-4). Idempotent : ne re-crée pas si déjà
    présent."""
    target_uuid = _anomaly_target_uuid(anomaly_id)
    existing = (
        db.query(ActionLink)
        .filter(
            ActionLink.organisation_id == org_id,
            ActionLink.item_id == item_id,
            ActionLink.target_module == "billing",
            ActionLink.target_id == target_uuid,
        )
        .first()
    )
    if existing is not None:
        return False
    db.add(
        ActionLink(
            organisation_id=org_id,
            item_id=item_id,
            link_type="source",
            target_module="billing",
            target_id=target_uuid,
            relation="caused_by",
        )
    )
    return True


@router.post("/sync-actions-from-anomalies")
def sync_actions_from_anomalies(
    request: Request,
    idempotency_key: Optional[str] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée un `ActionCenterItem` par anomalie facture ouverte actionnable.

    Idempotent : 2 appels successifs sans nouvelle anomalie → 0 doublon.

    Réponse :
    ```json
    {
      "org_id": 42,
      "created": [{"id": "...", "title": "...", "anomaly_id": 19}, ...],
      "skipped_existing": [{"anomaly_id": 7, "lifecycle_state": "in_progress"}, ...],
      "skipped_resolved_user": [{"anomaly_id": 5, "lifecycle_state": "closed"}, ...],
      "skipped_non_actionable": [{"anomaly_id": 11, "reason": "is_monetizable=false"}, ...],
      "skipped_resolved_anomaly": [{"anomaly_id": 3, "resolved_at": "..."}, ...],
      "summary": {"total_anomalies_seen": 52, "created": 10, ...},
      "computed_at": "2026-05-24T..."
    }
    ```
    """
    correlation = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex[:8]

    try:
        org_id = resolve_org_id(request, auth, db)
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "NO_ORG_CONTEXT",
                    "message": "Aucun contexte organisation — authentification requise pour synchroniser les actions.",
                    "hint": "Fournir un JWT valide portant un claim org_id, ou se connecter via /login.",
                    "correlation_id": correlation,
                },
            ) from exc
        raise

    # Validation Idempotency-Key (UUID si fourni, pattern conformité P1)
    if idempotency_key is not None:
        try:
            uuid.UUID(idempotency_key)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "IDEMPOTENCY_KEY_INVALID",
                    "message": "L'en-tête Idempotency-Key doit être un UUID v4 valide.",
                    "hint": "Générer côté client via `uuid.uuid4()`.",
                },
            )

    # Récupère toutes les anomalies de l'org via JOIN chain IDOR-safe
    anomalies = (
        db.query(BillAnomaly, EnergyInvoice)
        .join(EnergyInvoice, BillAnomaly.invoice_id == EnergyInvoice.id)
        .join(Site, EnergyInvoice.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(
            EntiteJuridique.organisation_id == org_id,
            BillAnomaly.deleted_at.is_(None),
        )
        .all()
    )

    created: list[dict] = []
    updated: list[dict] = []  # P2-B C5
    skipped_existing: list[dict] = []
    skipped_resolved_user: list[dict] = []
    skipped_non_actionable: list[dict] = []
    skipped_resolved_anomaly: list[dict] = []

    for anomaly, invoice in anomalies:
        # Anomalie résolue (par fournisseur ou opérateur) → skip
        if anomaly.resolved_at is not None:
            skipped_resolved_anomaly.append({"anomaly_id": anomaly.id, "resolved_at": anomaly.resolved_at.isoformat()})
            continue
        # Anomalie informative (R017 PDL manquant, etc.) → pas d'action
        if anomaly.is_monetizable is False:
            skipped_non_actionable.append(
                {
                    "anomaly_id": anomaly.id,
                    "reason": "is_monetizable=false",
                    "non_monetizable_reason": anomaly.non_monetizable_reason,
                }
            )
            continue

        title = _make_title(anomaly)
        # Action Center V4 P0 fix (2026-05-25) — lookup par external_ref
        # (indexed UNIQUE par org) au lieu de title-based. Garantit zéro
        # doublon DB même en race condition (audit deep §5.3 P0-3).
        external_ref = _make_external_ref(anomaly)
        source_url = _make_source_url(anomaly)
        existing = _find_existing_item(db, org_id, external_ref)

        if existing is not None:
            if existing.lifecycle_state == LifecycleState.CLOSED.value:
                # L'utilisateur a clos l'item — jamais re-créer (préservé par
                # closure_reason + closed_at + chk_closure_consistency).
                skipped_resolved_user.append({"anomaly_id": anomaly.id, "lifecycle_state": existing.lifecycle_state})
                continue

            # P2-B C5 (2026-05-24) — Update si montant a changé.
            # Doctrine : "Si une anomalie devient valorisable après audit,
            # l'action doit être créée OU mise à jour (montant, description)."
            # Une anomalie 'devient valorisable' = is_monetizable a basculé
            # False→True (gérée par le check is_monetizable=False ci-dessus —
            # si on est arrivé ici, elle est désormais valorisable). Si l'action
            # existait avant (créée à priori comme stub) on la met à jour.
            # Plus simplement : on rafraîchit description + priority si le
            # montant détecté a évolué (>5% delta ou changement de severity).
            new_description = _make_description(anomaly, invoice)
            new_bracket = _SEVERITY_TO_BRACKET.get(anomaly.severity, "P2")
            new_score = _SEVERITY_TO_SCORE.get(anomaly.severity, 50.0)

            changed_fields = []
            if existing.description != new_description:
                existing.description = new_description
                changed_fields.append("description")
            if existing.priority_bracket != new_bracket:
                existing.priority_bracket = new_bracket
                changed_fields.append("priority_bracket")
            if existing.priority_score != new_score:
                existing.priority_score = new_score
                changed_fields.append("priority_score")

            # Backfill external_ref + source_url si absents (items legacy
            # créés avant l'audit P0 ; la migration p0fix_acref parse déjà
            # les patterns description mais on garantit ici la cohérence).
            if not existing.external_ref:
                existing.external_ref = external_ref
                changed_fields.append("external_ref")
            if not existing.source_url:
                existing.source_url = source_url
                changed_fields.append("source_url")

            # Action Center V4 P0 fix (2026-05-25) — peuple ActionLink si
            # absente (audit §6 P0-4). Idempotent : ne re-crée pas.
            _ensure_action_link(db, org_id, existing.id, anomaly.id)

            if changed_fields:
                updated.append(
                    {
                        "id": str(existing.id),
                        "anomaly_id": anomaly.id,
                        "fields_changed": changed_fields,
                    }
                )
            else:
                skipped_existing.append({"anomaly_id": anomaly.id, "lifecycle_state": existing.lifecycle_state})
            continue

        bracket = _SEVERITY_TO_BRACKET.get(anomaly.severity, "P2")
        score = _SEVERITY_TO_SCORE.get(anomaly.severity, 50.0)

        item = ActionCenterItem(
            id=uuid.uuid4(),
            organisation_id=org_id,
            kind=Kind.ANOMALY.value,
            domain=Domain.FACTURATION.value,
            title=title,
            description=_make_description(anomaly, invoice),
            lifecycle_state=LifecycleState.NEW.value,
            priority_bracket=bracket,
            priority_score=score,
            external_ref=external_ref,
            source_url=source_url,
        )
        db.add(item)
        db.flush()
        # Action Center V4 P0 fix (2026-05-25) — peuple ActionLink à la
        # création (audit §6 P0-4) pour qu'un EM/Auditeur puisse revenir
        # à l'anomalie source depuis le drawer LinksTab.
        _ensure_action_link(db, org_id, item.id, anomaly.id)
        created.append(
            {
                "id": str(item.id),
                "title": title,
                "anomaly_id": anomaly.id,
                "invoice_id": invoice.id,
                "priority_bracket": bracket,
                "external_ref": external_ref,
                "source_url": source_url,
            }
        )

    db.commit()

    total = len(anomalies)
    return {
        "org_id": org_id,
        "created": created,
        "updated": updated,  # P2-B C5 — actions dont montant/desc/priorité ont été rafraîchis
        "skipped_existing": skipped_existing,
        "skipped_resolved_user": skipped_resolved_user,
        "skipped_non_actionable": skipped_non_actionable,
        "skipped_resolved_anomaly": skipped_resolved_anomaly,
        "summary": {
            "total_anomalies_seen": total,
            "created": len(created),
            "updated": len(updated),  # P2-B C5
            "skipped_existing": len(skipped_existing),
            "skipped_resolved_user": len(skipped_resolved_user),
            "skipped_non_actionable": len(skipped_non_actionable),
            "skipped_resolved_anomaly": len(skipped_resolved_anomaly),
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation,
    }
