"""PROMEOS — Conformité P1 2026-05-23 : endpoint sync remediation actions.

`POST /api/conformite/sync-remediation-actions` — ferme la boucle CadreApplicable
DATA_MISSING → ActionCenterItem.

Consomme le service P0-5 `plan_remediation_actions_for_org` (READ-ONLY) et
matérialise chaque `ActionItemDraft` en `ActionCenterItem` côté Centre d'Action.

Doctrine produit 2026-05-23 respectée :
- Pas de nouveau menu, pas de nouvelle brique.
- `/conformite` reste hub unique (le bouton UI vit dans l'header de la page).
- Aucune référence ACC/PMO/Flex/Partner Hub.

Idempotency :
- Header `Idempotency-Key` recommandé (pattern V4 unifié).
- Idempotency *par item* : si un ActionCenterItem matching (org, kind,
  domain, title) existe et n'est pas clos, on SKIP. Sinon CREATE.
- Items déjà clos par l'utilisateur ne sont JAMAIS re-créés (respect choix utilisateur).

Audit trail :
- Chaque création écrit un event `EventType.CREATED` (whitelist 16 valeurs)
  avec `payload.source = "regulatory_rule"` + métadonnées (rule_code,
  reason_code, scope_level, scope_id, remediation_field).
- Choix de réutiliser `CREATED` plutôt qu'introduire un nouveau event_type
  documenté dans `docs/dev/conformite_action_sync_contract.md` §3.

Doctrine NOT_APPLICABLE :
- Le service P0-5 ne génère que des drafts depuis `DATA_MISSING` (vérifié
  par `test_conformite_action_sync_service.py`). Garanti by design :
  NOT_APPLICABLE ne produit jamais d'action.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from middleware.org_context import current_org_id, populate_org_context
from middleware.rbac import require_v4_role
from models.v4.action_center_items import ActionCenterItem
from models.v4.enums import Domain, Kind, LifecycleState, Role
from repositories.action_center_item_v4_repository import ActionCenterItemRepository
from repositories.action_event_log_repository import ActionEventLogRepository
from services.v4.conformite_action_sync_service import (
    ActionItemDraft,
    plan_remediation_actions_for_org,
)


router = APIRouter(prefix="/api/conformite", tags=["Conformité"])


_PLACEHOLDER_PRIORITY_BRACKET = "P1"  # cf. R6 plancher P1 conformité (doctrine v0.3 §5.6)
_PLACEHOLDER_PRIORITY_SCORE = 60.0  # placeholder — scoring réel via M2-5 PriorityScoringService


def _find_existing_item_for_draft(
    db: Session,
    org_id: int,
    draft: ActionItemDraft,
) -> Optional[ActionCenterItem]:
    """Cherche un ActionCenterItem matching le draft par signature (org, kind, domain, title).

    Pourquoi ce matching (vs colonne `external_ref` dédiée) :
    - Pas de migration Alembic (P1 doctrine = pas de changement schéma).
    - `title_fr` du draft est déterministe (généré depuis rule_code + remediation_label_fr).
    - Signature suffisante car un site ne peut avoir qu'une remédiation par règle/champ.
    """
    return (
        db.query(ActionCenterItem)
        .filter(
            ActionCenterItem.organisation_id == org_id,
            ActionCenterItem.kind == draft.kind,
            ActionCenterItem.domain == draft.domain,
            ActionCenterItem.title == draft.title_fr,
        )
        .first()
    )


def _write_creation_event(
    db: Session,
    *,
    action_item_id: uuid.UUID,
    draft: ActionItemDraft,
) -> None:
    """Écrit un event ActionEventLog `created` avec payload source=regulatory_rule.

    Choix design : on réutilise l'event_type `created` (whitelist 16 valeurs)
    avec un marqueur `source: "regulatory_rule"` dans le payload, plutôt que
    d'introduire `item_created_from_rule` qui nécessiterait une migration DDL.
    Permet de filtrer ces events via SQL : `event_payload->>'source' = 'regulatory_rule'`.

    Cf. `docs/dev/conformite_action_sync_contract.md` §3.
    """
    ActionEventLogRepository(db).create(
        action_item_id=action_item_id,
        event_type="created",  # EventType.CREATED — whitelist 16 valeurs ADR-029
        actor_type="system",
        actor_id=None,
        actor_role=None,
        event_payload={
            "source": "regulatory_rule",
            "external_ref": draft.external_ref,
            "rule_code": draft.rule_code,
            "reason_code": draft.reason_code,
            "scope_level": draft.scope_level,
            "scope_id": draft.scope_id,
            "remediation_field": draft.remediation_field,
        },
        correlation_id=uuid.uuid4(),
    )


@router.post(
    "/sync-remediation-actions",
    dependencies=[Depends(populate_org_context)],
)
async def sync_remediation_actions(
    request: Request,
    idempotency_key: Annotated[
        Optional[str],
        Header(alias="Idempotency-Key", description="UUID v4 — recommandé, rejeu sûr"),
    ] = None,
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.USER, Role.ADMIN)),
) -> dict[str, Any]:
    """Crée les ActionCenterItem pour les DATA_MISSING réglementaires de l'org.

    Headers :
    - `X-Org-Id` (forcé via `populate_org_context` middleware).
    - `Idempotency-Key` (recommandé, UUID v4) — si fourni et invalide, 400.

    Comportement idempotent :
    - Pour chaque draft du plan, recherche un ActionCenterItem matching
      (org_id + kind + domain + title).
    - Si trouvé `closed` → ignoré (`skipped_resolved`).
    - Si trouvé non-clos → ignoré (`skipped_existing`, déjà présent).
    - Sinon → création + event log `created` avec marqueur source.

    Réponse JSON :
    ```
    {
      "org_id": 42,
      "created": [{"id": "...", "title": "..."}, ...],
      "skipped_existing": [{"id": "...", "title": "..."}, ...],
      "skipped_resolved": [{"id": "...", "title": "..."}, ...],
      "summary": {"total_drafts": 7, "created": 5, "skipped_existing": 2, "skipped_resolved": 0},
      "computed_at": "..."
    }
    ```

    Garanties :
    - `NOT_APPLICABLE` ne génère JAMAIS d'item (by design — service P0-5).
    - Replay sûr : 2 appels successifs sans changement → 2e n'ajoute rien.
    - L'utilisateur qui a clôturé un item ne se le voit pas re-créé.
    """
    if idempotency_key is not None:
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "IDEMPOTENCY_KEY_INVALID",
                    "message": "L'en-tête Idempotency-Key doit être un UUID v4 valide.",
                    "hint": "Générez-le avec `uuid.uuid4()` côté client.",
                },
            )

    org_id = current_org_id()
    plan = plan_remediation_actions_for_org(db, org_id)

    repo = ActionCenterItemRepository(db)
    created: list[dict[str, Any]] = []
    skipped_existing: list[dict[str, Any]] = []
    skipped_resolved: list[dict[str, Any]] = []

    for draft in plan.items_to_create:
        existing = _find_existing_item_for_draft(db, org_id, draft)
        if existing is not None:
            entry = {"id": str(existing.id), "title": existing.title}
            if existing.lifecycle_state == LifecycleState.CLOSED.value:
                skipped_resolved.append(entry)
            else:
                skipped_existing.append(entry)
            continue

        item = repo.create(
            kind=draft.kind,
            title=draft.title_fr,
            description=draft.description_fr,
            domain=draft.domain,
            source_module="conformite",
            priority_bracket=_PLACEHOLDER_PRIORITY_BRACKET,
            priority_score=_PLACEHOLDER_PRIORITY_SCORE,
            score_stale=True,
        )
        _write_creation_event(db, action_item_id=item.id, draft=draft)
        created.append({"id": str(item.id), "title": item.title})

    db.commit()

    return {
        "org_id": org_id,
        "created": created,
        "skipped_existing": skipped_existing,
        "skipped_resolved": skipped_resolved,
        "summary": {
            "total_drafts": len(plan.items_to_create),
            "created": len(created),
            "skipped_existing": len(skipped_existing),
            "skipped_resolved": len(skipped_resolved),
            "by_rule": {k.replace("by_rule_", ""): v for k, v in plan.summary.items() if k.startswith("by_rule_")},
        },
        "computed_at": plan.computed_at,
    }
