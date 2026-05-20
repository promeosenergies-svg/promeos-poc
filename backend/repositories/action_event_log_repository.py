"""M2-4.3 / M2-5.10.E — Repository de la sous-ressource ActionEventLog.

Hérite `BaseRepositoryV4` : org-scopé fail-closed (M2-3.C). FK vers l'item
parent = `action_item_id` (cf. modèle).
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from models.v4.action_center_items import ActionCenterItem
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

    def list_org_journal(
        self,
        *,
        since_days: int = 7,
        limit: int = 100,
    ) -> tuple[list[tuple[ActionEventLog, str]], int]:
        """M2-5.10.E — Journal org-wide cross-items (vue Pilotage Journal).

        Retourne les events des N derniers jours dans toute l'organisation
        (cross-items), enrichis du **titre de l'item parent** via un join
        explicite (évite N+1 côté UI). Tri `occurred_at` DESC.

        - Org-scopé fail-closed via `_apply_scope` (IS3 anti-leak).
        - `since_days` = fenêtre temporelle glissante (cap UI 30j max).
        - `limit` = plafond (cap 200) — pas de pagination MV3, la maquette
          §8.2 présente 7 jours condensés en day-groups.

        Returns:
            tuple (rows, total) où rows = list[(event, item_title)].
            total = compte total des events sur la fenêtre (non limité).
        """
        since = datetime.now(UTC) - timedelta(days=since_days)
        # JOIN explicite pour récupérer le title du parent en 1 requête.
        stmt = (
            self._apply_scope(
                select(self.model, ActionCenterItem.title)
                .join(ActionCenterItem, ActionCenterItem.id == self.model.action_item_id)
                .where(self.model.occurred_at >= since)
            )
            .order_by(self.model.occurred_at.desc())
            .limit(limit)
        )
        rows = [(row[0], row[1]) for row in self.db.execute(stmt).all()]

        # Total non plafonné pour le narrative bar (M3+) et le badge filtre.
        total_stmt = self._apply_scope(
            select(func.count()).select_from(self.model).where(self.model.occurred_at >= since)
        )
        total = self.db.execute(total_stmt).scalar() or 0
        return rows, total
