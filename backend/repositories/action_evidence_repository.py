"""M2-4.3 — Repository de la sous-ressource Evidence (table `action_evidences`).

Hérite `BaseRepositoryV4` : org-scopé fail-closed (M2-3.C). FK vers l'item
parent = `action_item_id`. La classe modèle est `Evidence` (pas `ActionEvidence`).
"""

from uuid import UUID

from sqlalchemy import func, select

from models.v4.evidences import Evidence
from repositories.base_v4 import BaseRepositoryV4


class ActionEvidenceRepository(BaseRepositoryV4[Evidence]):
    """Evidences (preuves uploadées) d'un ActionCenterItem."""

    model = Evidence

    def list_by_item_id(self, item_id: UUID, offset: int = 0, limit: int = 50) -> tuple[list[Evidence], int]:
        """Liste paginée des evidences d'un item, triée `uploaded_at` DESC.

        Org-scopé via `_apply_scope` (fail-closed). Retourne `(items, total)`.
        """
        scoped = self._apply_scope(select(self.model).where(self.model.action_item_id == item_id))
        items = list(
            self.db.execute(scoped.order_by(self.model.uploaded_at.desc()).offset(offset).limit(limit)).scalars().all()
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
