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


async def verify_parent_item_access(
    item_id: UUID,
    db: Session = Depends(get_db),
) -> ActionCenterItem:
    """Vérifie que l'ActionCenterItem parent existe et est accessible.

    Retourne l'item chargé — les handlers peuvent l'injecter sans re-requêter.
    Lève 404 si introuvable ou cross-org.

    Suppose `populate_org_context` déjà invoqué via `dependencies=[...]` de la
    route. Sinon le repo lève `NoOrgContextError` (→ 401 via error_handler M2-4.2).
    """
    repo = ActionCenterItemRepository(db)
    item = repo.get(item_id)
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
