"""
PROMEOS - Smart Intake Models (DIAMANT)
IntakeSession, IntakeAnswer, IntakeFieldOverride.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey,
    Enum as SAEnum, UniqueConstraint,
)
from datetime import datetime

from .base import Base, TimestampMixin
from .enums import IntakeSessionStatus, IntakeMode, IntakeSource


class IntakeSession(Base, TimestampMixin):
    """Session d'intake: collecte de donnees reglementaires pour un site."""
    __tablename__ = "intake_sessions"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    scope_type = Column(String(10), nullable=False, comment="site, entity, org")
    scope_id = Column(Integer, nullable=False)
    status = Column(SAEnum(IntakeSessionStatus), default=IntakeSessionStatus.DRAFT, nullable=False)
    mode = Column(SAEnum(IntakeMode), default=IntakeMode.WIZARD, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    score_before = Column(Float, nullable=True, comment="Compliance score avant intake")
    score_after = Column(Float, nullable=True, comment="Compliance score apres intake")
    questions_count = Column(Integer, default=0)
    answers_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<IntakeSession {self.id} site={self.site_id} status={self.status}>"


class IntakeAnswer(Base, TimestampMixin):
    """Reponse a une question d'intake: field_path + value + source."""
    __tablename__ = "intake_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("intake_sessions.id"), nullable=False, index=True)
    field_path = Column(String(100), nullable=False, comment="e.g. site.tertiaire_area_m2")
    value_json = Column(Text, nullable=False, comment="JSON-encoded answer value")
    source = Column(SAEnum(IntakeSource), default=IntakeSource.USER, nullable=False)
    confidence = Column(String(10), default="high", comment="high, medium, low")
    previous_value_json = Column(Text, nullable=True, comment="Previous value for diff")
    applied_at = Column(DateTime, nullable=True, comment="When written to final model")

    def __repr__(self):
        return f"<IntakeAnswer {self.id} field={self.field_path} source={self.source}>"


class IntakeFieldOverride(Base, TimestampMixin):
    """Override multi-scope: ORG > ENTITY > SITE pour heritage de valeurs."""
    __tablename__ = "intake_field_overrides"
    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", "field_path", name="uq_intake_override"),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String(10), nullable=False, comment="org, entity, site")
    scope_id = Column(Integer, nullable=False, index=True)
    field_path = Column(String(100), nullable=False)
    value_json = Column(Text, nullable=False)
    source = Column(String(20), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<IntakeFieldOverride {self.scope_type}={self.scope_id} {self.field_path}>"
