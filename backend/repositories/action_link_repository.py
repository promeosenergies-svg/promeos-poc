"""M2-4.3 — Repository de la sous-ressource ActionLink.

Hérite `BaseRepositoryV4` : org-scopé fail-closed (M2-3.C). FK vers l'item
parent = `item_id`. ActionLink est polymorphe : il relie l'item à n'importe
quel module (`target_module` + `target_id` + `relation`), pas item→item.
"""

from uuid import UUID

from sqlalchemy import func, select

from models.v4.action_links import ActionLink
from repositories.base_v4 import BaseRepositoryV4


class ActionLinkRepository(BaseRepositoryV4[ActionLink]):
    """Liens d'un ActionCenterItem vers d'autres modules."""

    model = ActionLink

    def list_by_item_id(self, item_id: UUID, offset: int = 0, limit: int = 50) -> tuple[list[ActionLink], int]:
        """Liste paginée des liens d'un item, triée `created_at` DESC.

        Org-scopé via `_apply_scope` (fail-closed). Retourne `(items, total)`.
        """
        scoped = self._apply_scope(select(self.model).where(self.model.item_id == item_id))
        items = list(
            self.db.execute(scoped.order_by(self.model.created_at.desc()).offset(offset).limit(limit)).scalars().all()
        )
        total = (
            self.db.execute(
                self._apply_scope(select(func.count()).select_from(self.model).where(self.model.item_id == item_id))
            ).scalar()
            or 0
        )
        return items, total
