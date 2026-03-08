"""
PROMEOS - Action Detail Models (Sprint V5.0)
ActionEvent: audit trail for every mutation on an ActionItem.
ActionComment: user comments on an action.
ActionEvidence: evidence/attachment references.
AnomalyActionLink: explicit anomaly-to-action link (V117).
AnomalyDismissal: anomaly dismissal with required reason (V117).
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base import Base, TimestampMixin
from .enums import DismissReason


class ActionEvent(Base, TimestampMixin):
    """Audit trail: every mutation on an ActionItem."""

    __tablename__ = "action_events"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(
        Integer,
        ForeignKey("action_items.id"),
        nullable=False,
        index=True,
        comment="Action concernee",
    )
    event_type = Column(
        String(50),
        nullable=False,
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
        Integer,
        ForeignKey("action_items.id"),
        nullable=False,
        index=True,
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
        Integer,
        ForeignKey("action_items.id"),
        nullable=False,
        index=True,
        comment="Action concernee",
    )
    label = Column(String(300), nullable=False, comment="Libelle de la piece")
    file_url = Column(String(1000), nullable=True, comment="URL ou chemin de reference")
    mime_type = Column(String(100), nullable=True, comment="Type MIME")
    uploaded_by = Column(String(200), nullable=True, comment="Utilisateur ayant ajoute la piece")

    # Relations
    action = relationship("ActionItem", backref="evidence_items")


# ── V117: Anomaly ↔ Action Link ─────────────────────────────────────────────


class AnomalyActionLink(Base):
    """Explicit link between an anomaly (any domain) and an ActionItem."""

    __tablename__ = "anomaly_action_links"
    __table_args__ = (
        UniqueConstraint(
            "anomaly_source",
            "anomaly_ref",
            "site_id",
            "action_id",
            name="uq_anomaly_action_link",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    anomaly_source = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Domain: patrimoine, billing, monitoring",
    )
    anomaly_ref = Column(
        String(200),
        nullable=False,
        comment="Anomaly code or insight ID",
    )
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)
    action_id = Column(
        Integer,
        ForeignKey("action_items.id"),
        nullable=False,
        index=True,
    )
    link_reason = Column(String(500), nullable=True, comment="Why linked")
    created_by = Column(String(200), nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relations
    action = relationship("ActionItem", backref="anomaly_links")


class AnomalyDismissal(Base):
    """Record of an anomaly being dismissed with a required reason."""

    __tablename__ = "anomaly_dismissals"
    __table_args__ = (
        UniqueConstraint(
            "anomaly_source",
            "anomaly_ref",
            "site_id",
            name="uq_anomaly_dismissal",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    anomaly_source = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Domain: patrimoine, billing, monitoring",
    )
    anomaly_ref = Column(
        String(200),
        nullable=False,
        comment="Anomaly code or insight ID",
    )
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)
    reason_code = Column(
        SAEnum(DismissReason),
        nullable=False,
        comment="Motif structure",
    )
    reason_text = Column(Text, nullable=True, comment="Commentaire libre")
    dismissed_by = Column(String(200), nullable=True)
    dismissed_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
