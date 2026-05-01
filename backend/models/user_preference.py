"""User preferences — Sprint Refonte Narrative dynamique Phase 1.4.

Table dédiée `user_preferences` (1 ligne par user, unique). Permet à un user
de surcharger des paramètres dérivés automatiquement, sans polluer la table
`users` (qui reste minimale auth-only).

## Phase 1.4 — typology_override

Première utilisation : permettre à un CFO d'une org mixte (ex: HELIOS scope
org → GRAND_GROUPE auto-détecté) de forcer une autre typologie pour ses
narratives (ex: si l'org pivote sur un nouveau métier, ou si l'auto-détection
NAF est jugée non représentative).

Si `typology_override IS NULL` → l'auto-détection NAF (`typology_resolver`)
prend le relais.

## Design choice cross-org (Amine 2026-05-01)

L'override est **global par user** : la table porte une UniqueConstraint
sur `user_id` seul, **pas** `(user_id, org_id)`. Conséquence : un user
multi-org partage son override entre toutes ses orgs.

Justification produit : la typologie est une perception personnelle du
user (« mes briefings, mon registre lexical »), pas une caractéristique
de l'org. Si V2 multi-org révèle un besoin d'override scopé à l'org
active (ex : DAF d'un groupe holding multi-secteurs), migrer vers
`(user_id, org_id)` unique composite — ADR P1-1 Phase 2 dans
`docs/maquettes/narrative-sol2/`.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.4.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from doctrine.naf_to_typology import OrganizationTypology

from .base import Base, TimestampMixin


class UserPreference(Base, TimestampMixin):
    """Préférences personnelles d'un user (1 ligne / user).

    Extensible : à terme contiendra `narrative_style`, `push_threshold`,
    `email_digest_frequency`, etc. Pour l'instant uniquement
    `typology_override` (Phase 1.4).
    """

    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_preferences_user"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Phase 1.4 — override typologie auto-détectée (None = auto-détection NAF)
    typology_override = Column(
        SAEnum(OrganizationTypology),
        nullable=True,
        doc=(
            "Si défini, surcharge la typologie auto-détectée par "
            "naf_to_typology.resolve_typology / typology_resolver. "
            "None = auto-détection (défaut)."
        ),
    )

    # Relations
    user = relationship("User")

    def __repr__(self):
        return f"<UserPreference user_id={self.user_id} typology_override={self.typology_override}>"
