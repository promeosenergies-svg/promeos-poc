"""User preferences — Sprint Refonte Narrative dynamique Phase 1.4 + 13.B.

Table dédiée `user_preferences`. Permet à un user de surcharger des
paramètres dérivés automatiquement, sans polluer la table `users`.

## Phase 1.4 — typology_override (1 ligne / user, design global)

Première utilisation : permettre à un CFO d'une org mixte (ex: HELIOS
scope org → GRAND_GROUPE auto-détecté) de forcer une autre typologie
pour ses narratives.

## Phase 13.B — BL-7 cross-org typology_override (audit final P1)

Migration `(user_id) UNIQUE` → `(user_id, org_id) UNIQUE` composite
pour permettre des overrides différents selon l'org active. Cas d'usage :
DAF de holding multi-secteurs qui veut "patrimoine" pour HELIOS Tertiaire
et "groupe industriel" pour HELIOS Manufacturing.

Convention V2 : `org_id IS NULL` reste autorisé (override global user
si défini), `org_id != NULL` priorise sur global. Le résolveur lookup :

  1. (user_id, current_org_id) → si présent, utiliser
  2. (user_id, NULL) → si présent (override global), utiliser
  3. Sinon → auto-détection NAF typology_resolver

Si `typology_override IS NULL` → auto-détection NAF reprend la main.

Migration safe : `org_id` colonne nullable ajoutée sans casser les
override globaux existants (qui passent en `org_id=NULL`).

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.4 + audit final BL-7 Phase 13.B.
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
    """Préférences personnelles d'un user (Phase 13.B : 1 ligne / (user, org)).

    Extensible : à terme contiendra `narrative_style`, `push_threshold`,
    `email_digest_frequency`, etc. Phase 1.4 : `typology_override` ;
    Phase 13.B : ajout `org_id` nullable pour scope cross-org.
    """

    __tablename__ = "user_preferences"
    # Phase 13.B — UniqueConstraint composite (user_id, org_id).
    # Note : SQLite tolère plusieurs (user_id, NULL) car NULL ≠ NULL en SQL standard.
    # PostgreSQL idem. Pour empêcher 2 overrides globaux pour le même user, ajout
    # d'un index partiel WHERE org_id IS NULL en migration ad-hoc V3 si nécessaire.
    # MVP Phase 13.B : on accepte la contrainte composite simple.
    __table_args__ = (UniqueConstraint("user_id", "org_id", name="uq_user_preferences_user_org"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Phase 13.B — org_id NULL = override global user (rétrocompat Phase 1.4)
    # org_id != NULL = override scopé à cette org (priorité dans le résolveur)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True, index=True)

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
    organisation = relationship("Organisation")

    def __repr__(self):
        scope = f"org_id={self.org_id}" if self.org_id else "global"
        return f"<UserPreference user_id={self.user_id} {scope} typology_override={self.typology_override}>"
