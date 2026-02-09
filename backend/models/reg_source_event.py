"""
PROMEOS - Modele RegSourceEvent
Evenements de veille reglementaire detectes par les watchers.
Stockage minimal : hash + snippet uniquement (pas de copie massive).
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from .base import Base
from datetime import datetime


class RegSourceEvent(Base):
    __tablename__ = "reg_source_events"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=True)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    snippet = Column(String(500), nullable=True)
    tags = Column(String(200), nullable=True)
    published_at = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed = Column(Boolean, default=False)
    review_note = Column(String(500), nullable=True)
