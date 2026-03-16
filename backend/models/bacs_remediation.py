"""
PROMEOS — BacsRemediationAction : action corrective BACS tracable.
Boucle : detection → action → preuve → revue.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey
from datetime import datetime, timezone
from .base import Base, TimestampMixin


class BacsRemediationAction(Base, TimestampMixin):
    """Action corrective BACS liee a un blocker."""

    __tablename__ = "bacs_remediation_actions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("bacs_assets.id", ondelete="CASCADE"), nullable=False, index=True)

    # Lien au blocker
    blocker_code = Column(String(100), nullable=False, comment="Code du blocker source")
    blocker_cause = Column(String(300), nullable=False)
    expected_action = Column(String(500), nullable=False)
    expected_proof_type = Column(String(100), nullable=True)

    # Statut workflow
    status = Column(String(20), nullable=False, default="open", comment="open, in_progress, ready_for_review, closed")
    priority = Column(String(20), nullable=False, default="high")

    # Ownership
    owner = Column(String(200), nullable=True)
    due_at = Column(Date, nullable=True)
    created_by = Column(String(200), nullable=False, default="system")

    # Preuve rattachee
    proof_id = Column(Integer, ForeignKey("bacs_proof_documents.id", ondelete="SET NULL"), nullable=True)
    proof_review_status = Column(String(20), nullable=True, comment="missing, uploaded, accepted, rejected")
    proof_reviewed_by = Column(String(200), nullable=True)
    proof_reviewed_at = Column(DateTime, nullable=True)

    # Resolution
    resolution_notes = Column(Text, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(200), nullable=True)
