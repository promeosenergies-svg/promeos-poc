"""
PROMEOS - Notification Models (Sprint 10.2)
NotificationEvent: persisted alert from any brique.
NotificationBatch: batch record for each sync run.
NotificationPreference: org-level alert preferences.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Enum as SAEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import NotificationSeverity, NotificationStatus, NotificationSourceType


class NotificationEvent(Base, TimestampMixin):
    """
    A single alert/notification generated from any brique.
    Dedup: unique on (org_id, source_type, source_id, source_key, inputs_hash).
    Fallback uniqueness via inputs_hash.
    """

    __tablename__ = "notification_events"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "source_type",
            "source_id",
            "source_key",
            name="uq_notif_org_source",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        index=True,
        comment="Organisation proprietaire",
    )
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=True,
        index=True,
        comment="Site concerne (nullable for org-level alerts)",
    )
    source_type = Column(
        SAEnum(NotificationSourceType),
        nullable=False,
        index=True,
        comment="Brique source: compliance, billing, purchase, consumption, action_hub",
    )
    source_id = Column(
        String(100),
        nullable=True,
        comment="ID de l'objet source (ex: finding_id, insight_id)",
    )
    source_key = Column(
        String(200),
        nullable=True,
        comment="Cle de dedup intra-source",
    )
    severity = Column(
        SAEnum(NotificationSeverity),
        nullable=False,
        index=True,
        comment="Severite: info, warn, critical",
    )
    title = Column(String(500), nullable=False, comment="Titre de l'alerte")
    message = Column(Text, nullable=True, comment="Description detaillee")
    due_date = Column(Date, nullable=True, comment="Echeance associee")
    estimated_impact_eur = Column(
        Float,
        nullable=True,
        comment="Impact financier estime en EUR",
    )
    deeplink_path = Column(
        String(500),
        nullable=True,
        comment="Chemin deep-link vers la page concernee (ex: /conformite?site_id=1)",
    )
    evidence_json = Column(
        Text,
        nullable=True,
        comment="Inputs cles + seuils + justification (JSON)",
    )
    status = Column(
        SAEnum(NotificationStatus),
        default=NotificationStatus.NEW,
        nullable=False,
        index=True,
        comment="Statut: new, read, dismissed",
    )
    inputs_hash = Column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 du contenu source pour dedup",
    )

    # Relations
    organisation = relationship("Organisation", backref="notification_events")
    site = relationship("Site", backref="notification_events")


class NotificationBatch(Base, TimestampMixin):
    """Enregistre un run de synchronisation notifications."""

    __tablename__ = "notification_batches"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=True,
        index=True,
        comment="Organisation synchronisee",
    )
    triggered_by = Column(
        String(100),
        nullable=True,
        comment="Declencheur: api, seed, auto",
    )
    inputs_hash = Column(
        String(64),
        nullable=True,
        comment="Hash global des entrees pour idempotence",
    )
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    warnings_json = Column(Text, nullable=True, comment="Warnings (JSON array)")

    # Relations
    organisation = relationship("Organisation", backref="notification_batches")


class NotificationPreference(Base, TimestampMixin):
    """Org-level notification preferences (simple V1)."""

    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        unique=True,
        index=True,
        comment="Organisation (1:1)",
    )
    enable_badges = Column(Boolean, default=True, comment="Afficher badges NEW")
    snooze_days = Column(Integer, default=0, comment="Jours de snooze global")
    thresholds_json = Column(
        Text,
        nullable=True,
        comment='Seuils (JSON): {"critical_due_days":30,"warn_due_days":60}',
    )

    # Relations
    organisation = relationship("Organisation", backref="notification_preference")
