"""
PROMEOS - Base SQLAlchemy
Configuration de base pour tous les modeles de donnees
"""

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime, String, and_, literal
from datetime import datetime, timezone

# Base commune pour tous les modeles
Base = declarative_base()


class TimestampMixin:
    """
    Mixin pour ajouter automatiquement les timestamps
    a tous les modeles PROMEOS

    Attributs:
        created_at: Date de creation (auto)
        updated_at: Date de derniere modification (auto)
    """

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="Date de creation"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date de derniere modification",
    )


class CreatedAtOnlyMixin:
    """
    Mixin pour tables append-only : created_at seul, pas d'updated_at.

    Utilisé pour les journaux d'audit immuables (ex: sol_action_log) où
    toute modification doit être rejetée. Ne fournit PAS updated_at car
    l'append-only implique qu'une ligne n'est jamais modifiée après insert.

    Voir aussi : event listener SQLAlchemy `before_update` sur le modèle
    concret pour bloquer les UPDATE au runtime (cf models/sol.py).
    """

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date de creation (append-only, jamais modifie)",
    )


class SoftDeleteMixin:
    """
    Mixin pour suppression logique (soft delete).
    Les objets ne sont jamais physiquement supprimes -- deleted_at est set.
    """

    deleted_at = Column(DateTime, nullable=True, index=True, comment="Date de suppression logique (NULL = actif)")
    deleted_by = Column(String(200), nullable=True, comment="Identifiant utilisateur ayant supprime")
    delete_reason = Column(String(500), nullable=True, comment="Raison de la suppression")

    @property
    def is_deleted(self):
        """True si l'objet a ete soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self, by=None, reason=None):
        """Marque l'objet comme supprime.

        Synchronise actif=False si le champ existe (Organisation, Site, Compteur).
        """
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = by
        self.delete_reason = reason
        # Sync: keep actif coherent with deleted_at
        if hasattr(self, "actif"):
            self.actif = False

    def restore(self):
        """Restaure un objet soft-deleted.

        Synchronise actif=True si le champ existe.
        """
        self.deleted_at = None
        self.deleted_by = None
        self.delete_reason = None
        # Sync: keep actif coherent with deleted_at
        if hasattr(self, "actif"):
            self.actif = True


def not_deleted(query_or_model, model=None):
    """Filtre les objets soft-deleted.

    Deux modes :
      not_deleted(query, Model) → retourne la query filtrée
      not_deleted(Model)        → retourne un critère pour .filter()

    Checks deleted_at IS NULL AND actif=True (if field exists).
    """
    if model is None:
        # Mode expression : retourne un critère SQLAlchemy
        m = query_or_model
        conditions = []
        if hasattr(m, "deleted_at"):
            conditions.append(m.deleted_at.is_(None))
        if hasattr(m, "actif"):
            conditions.append(m.actif == True)  # noqa: E712
        return and_(*conditions) if conditions else literal(True)
    # Mode query : retourne la query filtrée
    query = query_or_model
    if hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))
    if hasattr(model, "actif"):
        query = query.filter(model.actif == True)  # noqa: E712
    return query
