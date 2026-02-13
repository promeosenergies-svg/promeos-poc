"""
PROMEOS - Action Hub Models (Sprint 10)
ActionItem: persisted unified action from all briques.
ActionSyncBatch: batch record for each sync run.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, Date, DateTime,
    ForeignKey, Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import ActionSourceType, ActionStatus


class ActionItem(Base, TimestampMixin):
    """
    A unified action persisted from any brique.
    Dedup: unique on (org_id, source_type, source_id, source_key).
    """
    __tablename__ = "action_items"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "source_type", "source_id", "source_key",
            name="uq_action_org_source",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer, ForeignKey("organisations.id"),
        nullable=False, index=True,
        comment="Organisation proprietaire",
    )
    site_id = Column(
        Integer, ForeignKey("sites.id"),
        nullable=True, index=True,
        comment="Site concerne (nullable for org-level actions)",
    )
    source_type = Column(
        SAEnum(ActionSourceType), nullable=False, index=True,
        comment="Brique source: compliance, consumption, billing, purchase",
    )
    source_id = Column(
        String(100), nullable=False,
        comment="ID de l'objet source (ex: finding_id, insight_id)",
    )
    source_key = Column(
        String(200), nullable=False,
        comment="Cle de dedup intra-source (ex: rule_id:0, type:0)",
    )
    title = Column(String(500), nullable=False, comment="Titre de l'action")
    rationale = Column(Text, nullable=True, comment="Justification detaillee")
    priority = Column(
        Integer, nullable=False, default=3,
        comment="Priorite 1 (critique) a 5 (faible)",
    )
    severity = Column(
        String(20), nullable=True,
        comment="Severite source: low, medium, high, critical",
    )
    estimated_gain_eur = Column(
        Float, nullable=True,
        comment="Gain financier estime en EUR",
    )
    due_date = Column(Date, nullable=True, comment="Echeance")
    status = Column(
        SAEnum(ActionStatus), default=ActionStatus.OPEN, nullable=False,
        comment="Statut workflow: open, in_progress, done, blocked, false_positive",
    )
    owner = Column(String(100), nullable=True, comment="Responsable assigne")
    notes = Column(Text, nullable=True, comment="Notes operateur")
    inputs_hash = Column(
        String(64), nullable=True,
        comment="SHA-256 du contenu source pour detecter les changements",
    )

    # Relations
    organisation = relationship("Organisation", backref="action_items")
    site = relationship("Site", backref="action_items")


class ActionSyncBatch(Base, TimestampMixin):
    """
    Enregistre un run de synchronisation Action Hub.
    Pattern: ComplianceRunBatch.
    """
    __tablename__ = "action_sync_batches"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer, ForeignKey("organisations.id"),
        nullable=True, index=True,
        comment="Organisation synchronisee",
    )
    triggered_by = Column(
        String(100), nullable=True,
        comment="Declencheur: api, seed, auto",
    )
    inputs_hash = Column(
        String(64), nullable=True,
        comment="Hash global des entrees pour idempotence",
    )
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    closed_count = Column(Integer, default=0, comment="Actions auto-fermees (source resolue)")
    warnings_json = Column(Text, nullable=True, comment="Warnings (JSON array)")

    # Relations
    organisation = relationship("Organisation", backref="action_sync_batches")
