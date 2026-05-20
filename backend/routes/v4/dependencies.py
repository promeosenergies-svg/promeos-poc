"""M2-4.3 — Dependencies réutilisables pour les sous-ressources V4.

`verify_parent_item_access` : utilisée par tout endpoint `/items/{item_id}/*`.
Résout l'item parent via `ActionCenterItemRepository` (org-scopé, fail-closed
M2-3.C). 404 ITEM_NOT_FOUND si l'item n'existe pas OU appartient à une autre
org — 404 délibéré (pas 403), aucune fuite d'existence.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.v4.action_center_items import ActionCenterItem
from repositories.action_center_item_v4_repository import ActionCenterItemRepository


def assert_parent_item_in_scope(db: Session, item_id: UUID) -> ActionCenterItem:
    """Charge l'ActionCenterItem parent org-scopé, ou lève 404 ITEM_NOT_FOUND.

    Cœur partagé de la vérification d'accès : `ActionCenterItemRepository` est
    org-scopé (fail-closed M2-3.C) — un item cross-org renvoie `None`. 404
    délibéré (jamais 403) : aucune fuite d'existence cross-tenant (OWASP).

    Fonction synchrone réutilisable hors dependency FastAPI — pour les routes
    qui dérivent l'`item_id` d'une sous-ressource (verify_evidence,
    resolve_blocker) au lieu de le recevoir en path.
    """
    item = ActionCenterItemRepository(db).get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ITEM_NOT_FOUND",
                "message": f"ActionCenterItem {item_id} not found",
                "hint": "Check the id, or your access scope",
            },
        )
    return item


async def verify_parent_item_access(
    item_id: UUID,
    db: Session = Depends(get_db),
) -> ActionCenterItem:
    """Dependency `/items/{item_id}/*` : vérifie l'item parent org-scopé.

    Délègue à `assert_parent_item_in_scope`. Retourne l'item chargé — les
    handlers peuvent l'injecter sans re-requêter. Lève 404 si introuvable ou
    cross-org.

    Suppose `populate_org_context` déjà invoqué via `dependencies=[...]` de la
    route. Sinon le repo lève `NoOrgContextError` (→ 401 via error_handler M2-4.2).
    """
    return assert_parent_item_in_scope(db, item_id)
