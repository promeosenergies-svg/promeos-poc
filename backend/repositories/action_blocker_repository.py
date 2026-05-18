"""M2-4.3 — Repository de la sous-ressource ActionBlocker.

Hérite `BaseRepositoryV4` : org-scopé fail-closed (M2-3.C). FK vers l'item
parent = `item_id`. Le modèle n'a PAS de colonne `severity` — tri simple sur
`added_at` DESC (la colonne datetime de création est `added_at`, pas `created_at`).
"""

from uuid import UUID

from sqlalchemy import func, select

from models.v4.action_blockers import ActionBlocker
from repositories.base_v4 import BaseRepositoryV4


class ActionBlockerRepository(BaseRepositoryV4[ActionBlocker]):
    """Blockers d'un ActionCenterItem."""

    model = ActionBlocker

    def list_by_item_id(self, item_id: UUID, offset: int = 0, limit: int = 50) -> tuple[list[ActionBlocker], int]:
        """Liste paginée des blockers d'un item, triée `added_at` DESC.

        Org-scopé via `_apply_scope` (fail-closed). Retourne `(items, total)`.
        """
        scoped = self._apply_scope(select(self.model).where(self.model.item_id == item_id))
        items = list(
            self.db.execute(scoped.order_by(self.model.added_at.desc()).offset(offset).limit(limit)).scalars().all()
        )
        total = (
            self.db.execute(
                self._apply_scope(select(func.count()).select_from(self.model).where(self.model.item_id == item_id))
            ).scalar()
            or 0
        )
        return items, total
