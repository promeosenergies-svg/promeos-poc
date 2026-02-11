"""
PROMEOS - Modele SegmentationProfile
Stocke le profil de segmentation detecte pour une organisation.
"""
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin


class SegmentationProfile(Base, TimestampMixin):
    """
    Profil de segmentation B2B d'une organisation.
    Detecte automatiquement (NAF, heuristiques) ou affine par questionnaire.
    """
    __tablename__ = "segmentation_profiles"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        unique=True,
        index=True,
        comment="Organisation rattachee (1:1)",
    )
    typologie = Column(
        String(50),
        nullable=False,
        comment="Segment detecte (enum Typologie)",
    )
    naf_code = Column(
        String(10),
        nullable=True,
        comment="Code NAF principal si connu",
    )
    confidence_score = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="Score de confiance 0-100",
    )
    answers_json = Column(
        Text,
        nullable=True,
        comment="Reponses au questionnaire (JSON serialise)",
    )
    reasons_json = Column(
        Text,
        nullable=True,
        comment="Raisons de la detection (JSON serialise)",
    )

    # Relation
    organisation = relationship("Organisation", backref="segmentation_profile")
