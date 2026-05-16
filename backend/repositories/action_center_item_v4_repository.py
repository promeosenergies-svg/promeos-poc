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

from models.v4.action_center_items import ActionCenterItem
from repositories.base_v4 import BaseRepositoryV4


class ActionCenterItemRepository(BaseRepositoryV4[ActionCenterItem]):
    """Repository org-scopé pour `ActionCenterItem` (table cardinale V4).

    Hérite des 5 méthodes CRUD org-scopées de `BaseRepositoryV4` :
    list_all / get / create / update / delete — toutes fail-closed.

    `_scope_column` reste "organisation_id" (défaut hérité — les V4 models
    nomment leur colonne org `organisation_id`, cohérent IS1).
    """

    model = ActionCenterItem
