"""
PROMEOS - Modele JobOutbox
File d'attente asynchrone pour recompute, sync, watchers, agents IA.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from .base import Base
from .enums import JobType, JobStatus
from datetime import datetime


class JobOutbox(Base):
    __tablename__ = "job_outbox"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(Enum(JobType), nullable=False, index=True)
    payload_json = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
