"""M2-4.3 — Repository de la sous-ressource ActionEventLog.

Hérite `BaseRepositoryV4` : org-scopé fail-closed (M2-3.C). FK vers l'item
parent = `action_item_id` (cf. modèle).
"""

from uuid import UUID

from sqlalchemy import func, select

from models.v4.action_event_log import ActionEventLog
from repositories.base_v4 import BaseRepositoryV4


class ActionEventLogRepository(BaseRepositoryV4[ActionEventLog]):
    """Events d'un ActionCenterItem (audit trail métier)."""

    model = ActionEventLog

    def list_by_item_id(self, item_id: UUID, offset: int = 0, limit: int = 50) -> tuple[list[ActionEventLog], int]:
        """Liste paginée des events d'un item, triée `occurred_at` DESC.

        Org-scopé via `_apply_scope` (fail-closed) — aucune fuite cross-org.
        Retourne `(items, total)`.
        """
        scoped = self._apply_scope(select(self.model).where(self.model.action_item_id == item_id))
        items = list(
            self.db.execute(scoped.order_by(self.model.occurred_at.desc()).offset(offset).limit(limit)).scalars().all()
        )
        total = (
            self.db.execute(
                self._apply_scope(
                    select(func.count()).select_from(self.model).where(self.model.action_item_id == item_id)
                )
            ).scalar()
            or 0
        )
        return items, total
