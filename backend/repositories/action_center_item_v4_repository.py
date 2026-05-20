"""M2-3.C — ActionCenterItemRepository (PoC concret du pattern BaseRepositoryV4).

Proof-of-concept du pattern repository org-scopé V4 sur le model cardinal
`ActionCenterItem` (table cardinale single-table inheritance Q1-A — Sprint M2-2).

Choix du model PoC : `ActionCenterItem` retenu car :
- C'est le model V4 le plus représentatif (table cardinale, 7 tables filles
  pendent dessus).
- Il a `organisation_id` UUID NOT NULL (IS1 cardinal).
- C'est celui que les 12 endpoints `/api/action-center/*` (Sprint M2-4)
  manipuleront en priorité — le repo PoC sera directement réutilisable.

Scope M2-3.C : ce repository est livré + testé en isolation (tests unit
BaseRepositoryV4). Il n'est PAS encore branché sur une route — aucune route V4
n'existe (Sprint M2-4 livre les endpoints). Le câblage route → repo = M2-4.
"""

from typing import Optional

from sqlalchemy import func, select

from models.v4.action_center_items import ActionCenterItem
from repositories.base_v4 import BaseRepositoryV4


class ActionCenterItemRepository(BaseRepositoryV4[ActionCenterItem]):
    """Repository org-scopé pour `ActionCenterItem` (table cardinale V4).

    Hérite des 5 méthodes CRUD org-scopées de `BaseRepositoryV4` :
    list_all / get / create / update / delete — toutes fail-closed.

    `_scope_column` reste "organisation_id" (défaut hérité — les V4 models
    nomment leur colonne org `organisation_id`, cohérent IS1).

    M2-4.2 ajoute `list_paginated` + `find_by_idempotency_key` pour les
    endpoints template `/api/v4/action-center/items`.
    """

    model = ActionCenterItem

    def list_paginated(self, offset: int = 0, limit: int = 50) -> tuple[list[ActionCenterItem], int]:
        """Liste paginée org-scopée. Retourne `(items, total)`.

        Le scope org est appliqué via `_apply_scope` (fail-closed M2-3.C) —
        aucune fuite cross-org, ni sur les items ni sur le total.
        """
        stmt_items = (
            self._apply_scope(select(self.model)).order_by(self.model.created_at.desc()).offset(offset).limit(limit)
        )
        items = list(self.db.execute(stmt_items).scalars().all())

        stmt_count = self._apply_scope(select(func.count()).select_from(self.model))
        total = self.db.execute(stmt_count).scalar() or 0
        return items, total

    def list_priority_queue(self, limit: int = 5) -> list[ActionCenterItem]:
        """M2-5.10.D — File prioritaire pilotage : top N items P0/P1 actifs.

        Filtres org-scopés (fail-closed) :
        - `priority_bracket IN ('P0', 'P1')` — items urgents/élevés
        - `lifecycle_state != 'closed'` — exclut le terminal
        - tri `priority_score DESC, created_at ASC` (score le plus haut en
          tête ; à score égal, le plus ancien remonte — anti-FIFO inversé)

        Retourne directement la liste (pas de pagination — file = top N
        cardinale, cf. maquette §8.1 « 5 items »).
        """
        stmt = (
            self._apply_scope(select(self.model))
            .where(self.model.priority_bracket.in_(("P0", "P1")))
            .where(self.model.lifecycle_state != "closed")
            .order_by(self.model.priority_score.desc(), self.model.created_at.asc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def find_by_idempotency_key(self, key: str) -> Optional[ActionCenterItem]:
        """Cherche un item par `idempotency_key` dans le scope org courant.

        Retourne None si la clé est inconnue — ou appartient à une autre org
        (`_apply_scope` filtre fail-closed). Base du POST replay-safe (M2-4.2).
        """
        stmt = self._apply_scope(select(self.model).where(self.model.idempotency_key == key))
        return self.db.execute(stmt).scalar_one_or_none()
