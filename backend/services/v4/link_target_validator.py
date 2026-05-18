"""M2-4.4 — Vérification polymorphe de la cible d'un ActionLink.

Seul le handler `action_center_item` est implémenté dans ce sprint. Les 6 autres
modules lèvent 501 NOT_IMPLEMENTED — différés M2-5/M2-6, le temps que les
repositories V4 (site/building/meter/invoice/contract/regulatory_obligation)
existent. Aucun fallback « trust the user » : un module non géré → 501 explicite.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.v4.enums.target_module import TargetModule


def verify_link_target(target_module: TargetModule, target_id: UUID, db: Session) -> None:
    """Vérifie que la cible du lien existe DANS le scope org courant.

    Lève :
    - 404 TARGET_NOT_FOUND si la cible est absente ou cross-org ;
    - 501 TARGET_MODULE_NOT_IMPLEMENTED pour les modules différés.
    """
    if target_module == TargetModule.ACTION_CENTER_ITEM:
        # Repo V4 org-scopé fail-closed : un get cross-org renvoie None.
        from repositories.action_center_item_v4_repository import ActionCenterItemRepository

        if ActionCenterItemRepository(db).get(target_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TARGET_NOT_FOUND",
                    "message": f"Target {target_module.value}/{target_id} not found",
                    "hint": "Verify the target exists within your org scope",
                },
            )
        return

    # Modules différés (repos V4 absents) — 501 explicite, pas de lien orphelin.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "TARGET_MODULE_NOT_IMPLEMENTED",
            "message": f"target_module '{target_module.value}' is not yet supported",
            "hint": "This target type will be enabled in a later sprint (M2-5/M2-6)",
        },
    )
