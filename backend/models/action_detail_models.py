"""
PROMEOS - Action Detail Models (Sprint V5.0)
ActionEvent: audit trail for every mutation on an ActionItem.
ActionComment: user comments on an action.
ActionEvidence: evidence/attachment references.
"""
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class ActionEvent(Base, TimestampMixin):
    """Audit trail: every mutation on an ActionItem."""
    __tablename__ = "action_events"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(
        Integer, ForeignKey("action_items.id"),
        nullable=False, index=True,
        comment="Action concernee",
    )
    event_type = Column(
        String(50), nullable=False,
        comment="Type: created, status_change, assigned, priority_change, commented, evidence_added, realized_updated, field_update",
    )
    actor = Column(String(200), nullable=True, comment="Utilisateur ayant declenche l'evenement")
    old_value = Column(String(500), nullable=True, comment="Ancienne valeur")
    new_value = Column(String(500), nullable=True, comment="Nouvelle valeur")
    metadata_json = Column(Text, nullable=True, comment="Contexte additionnel (JSON)")

    # Relations
    action = relationship("ActionItem", backref="events")


class ActionComment(Base, TimestampMixin):
    """User comments on an ActionItem."""
    __tablename__ = "action_comments"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(
        Integer, ForeignKey("action_items.id"),
        nullable=False, index=True,
        comment="Action concernee",
    )
    author = Column(String(200), nullable=False, comment="Auteur du commentaire")
    body = Column(Text, nullable=False, comment="Contenu du commentaire")

    # Relations
    action = relationship("ActionItem", backref="comments")


class ActionEvidence(Base, TimestampMixin):
    """Evidence/attachment references for an ActionItem."""
    __tablename__ = "action_evidence"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(
        Integer, ForeignKey("action_items.id"),
        nullable=False, index=True,
        comment="Action concernee",
    )
    label = Column(String(300), nullable=False, comment="Libelle de la piece")
    file_url = Column(String(1000), nullable=True, comment="URL ou chemin de reference")
    mime_type = Column(String(100), nullable=True, comment="Type MIME")
    uploaded_by = Column(String(200), nullable=True, comment="Utilisateur ayant ajoute la piece")

    # Relations
    action = relationship("ActionItem", backref="evidence_items")
