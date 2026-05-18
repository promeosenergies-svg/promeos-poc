"""Constantes figées du seed V4 minimal — Sprint M2-4.1.bis.

Aucune logique métier (contrainte C4) : specs littérales + un helper UUID5
purement déterministe. Toute évolution des valeurs se fait ici, en un point.
"""

from uuid import NAMESPACE_DNS, UUID, uuid5

# Organisation cible du seed V4 (décisions D1 / D5) : HELIOS, org démo canonique.
# Le seed NE crée PAS cette org — il exige qu'elle existe (cf. v4_seed._require_org).
# La création d'organisations appartient au seed HELIOS legacy. Choisir une autre
# org que celle portée par le JWT démo rendrait les items invisibles (org-scoping).
SEED_ORG_ID: int = 1

# 3 action_center_items minimaux, un par état de cycle de vie représentatif.
# lifecycle_state ∈ {new, triaged, planned, in_progress, closed} (chk_lifecycle_state).
# L'item 'closed' porte closed_at + closure_reason (chk_closure_consistency · IL10).
SEED_ACTION_SPECS: tuple[dict, ...] = (
    {
        "slug": "ouvert",
        "kind": "anomaly",
        "title": "Seed V4 — anomalie à traiter",
        "lifecycle_state": "new",
        "priority_bracket": "P1",
        "priority_score": 60.0,
        "closure_reason": None,
    },
    {
        "slug": "en-cours",
        "kind": "action",
        "title": "Seed V4 — action en cours",
        "lifecycle_state": "in_progress",
        "priority_bracket": "P2",
        "priority_score": 45.0,
        "closure_reason": None,
    },
    {
        "slug": "resolu",
        "kind": "action",
        "title": "Seed V4 — action résolue",
        "lifecycle_state": "closed",
        "priority_bracket": "P2",
        "priority_score": 30.0,
        "closure_reason": "resolved",
    },
)

# Namespace UUID5 dédié → PK action_center_items stables d'un run à l'autre.
# C'est le socle de l'idempotence (D3) : même slug ⇒ même PK ⇒ insert ignoré.
_SEED_UUID_NAMESPACE: UUID = uuid5(NAMESPACE_DNS, "promeos.seed.v4")


def seed_item_uuid(slug: str) -> UUID:
    """UUID5 déterministe d'un action_center_item seed (idempotence par PK stable)."""
    return uuid5(_SEED_UUID_NAMESPACE, f"action_center_item:{slug}")
