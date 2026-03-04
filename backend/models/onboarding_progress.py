"""
PROMEOS — Onboarding Progress Model (Chantier 5)
Tracks which onboarding steps are completed per organisation.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey

from .base import Base, TimestampMixin


class OnboardingProgress(Base, TimestampMixin):
    """Onboarding step completion tracking per org."""

    __tablename__ = "onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)

    # Step statuses (6 steps)
    step_org_created = Column(Boolean, nullable=False, default=False)
    step_sites_added = Column(Boolean, nullable=False, default=False)
    step_meters_connected = Column(Boolean, nullable=False, default=False)
    step_invoices_imported = Column(Boolean, nullable=False, default=False)
    step_users_invited = Column(Boolean, nullable=False, default=False)
    step_first_action = Column(Boolean, nullable=False, default=False)

    # Completion timestamps
    completed_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # Analytics — Time to First Value (seconds from created_at to completed_at)
    ttfv_seconds = Column(Integer, nullable=True)
