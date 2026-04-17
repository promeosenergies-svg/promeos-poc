"""
PROMEOS — CSAT Response model (CX Gap #7)
Stocke les réponses de satisfaction in-app (J+14 + déclencheurs manuels).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from .base import Base


class CsatResponse(Base):
    __tablename__ = "csat_responses"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    score = Column(Integer, nullable=False, comment="Score 1-5")
    verbatim = Column(Text, nullable=True, comment="Commentaire libre (<=500 chars)")
    trigger_type = Column(
        String(50),
        default="j14_auto",
        nullable=False,
        comment="j14_auto | post_export | manual",
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<CsatResponse org={self.org_id} score={self.score}>"
