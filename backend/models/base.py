"""
PROMEOS - Base SQLAlchemy
Configuration de base pour tous les modeles de donnees
"""
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime, String
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
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date de creation"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date de derniere modification"
    )


class SoftDeleteMixin:
    """
    Mixin pour suppression logique (soft delete).
    Les objets ne sont jamais physiquement supprimes -- deleted_at est set.
    """
    deleted_at = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="Date de suppression logique (NULL = actif)"
    )
    deleted_by = Column(
        String(200),
        nullable=True,
        comment="Identifiant utilisateur ayant supprime"
    )
    delete_reason = Column(
        String(500),
        nullable=True,
        comment="Raison de la suppression"
    )

    @property
    def is_deleted(self):
        """True si l'objet a ete soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self, by=None, reason=None):
        """Marque l'objet comme supprime."""
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = by
        self.delete_reason = reason

    def restore(self):
        """Restaure un objet soft-deleted."""
        self.deleted_at = None
        self.deleted_by = None
        self.delete_reason = None


def not_deleted(query, model):
    """Filtre les objets soft-deleted d'une query SQLAlchemy.
    Si le model n'a pas SoftDeleteMixin, retourne la query inchangee.
    """
    if hasattr(model, 'deleted_at'):
        return query.filter(model.deleted_at.is_(None))
    return query
