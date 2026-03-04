"""
PROMEOS - Modele ComplianceRunBatch
Batch d'evaluation de conformite (Sprint 9).
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class ComplianceRunBatch(Base, TimestampMixin):
    """
    Enregistre un run d'evaluation de conformite (recompute-rules).
    Permet le suivi historique des evaluations.
    """

    __tablename__ = "compliance_run_batches"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=True,
        index=True,
        comment="Organisation evaluee",
    )
    triggered_by = Column(
        String(100),
        nullable=True,
        comment="Declencheur: api, auto, manual",
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    sites_count = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    nok_count = Column(Integer, default=0)
    unknown_count = Column(Integer, default=0)

    # Relations
    organisation = relationship("Organisation", backref="compliance_batches")
