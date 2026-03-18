"""Actionable notifications for the action center."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from models.base import Base


class ActionNotification(Base):
    __tablename__ = "action_notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("action_plan_items.id"), nullable=False, index=True)
    notification_type = Column(
        String(50), nullable=False, comment="assigned|due_soon|overdue|evidence_missing|reopened"
    )
    recipient = Column(String(255), nullable=True, comment="Owner email or role")
    message = Column(String(500), nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
