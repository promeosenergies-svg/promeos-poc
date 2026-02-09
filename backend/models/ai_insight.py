"""
PROMEOS - Modele AiInsight
Stockage des sorties IA (explications, suggestions, analyses).
IA ne modifie JAMAIS le statut/score deterministe.
"""
from sqlalchemy import Column, Integer, String, Text, Enum
from .base import Base, TimestampMixin
from .enums import InsightType


class AiInsight(Base, TimestampMixin):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    object_type = Column(String(20), nullable=False, index=True)
    object_id = Column(Integer, nullable=False, index=True)
    insight_type = Column(Enum(InsightType), nullable=False, index=True)
    content_json = Column(Text, nullable=False)
    ai_version = Column(String(64), nullable=False)
    sources_used_json = Column(Text, nullable=True)
