"""
PROMEOS - Modele SegmentationProfile + SegmentationAnswer
Stocke le profil de segmentation detecte pour une organisation
et les reponses individuelles au questionnaire.
"""
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin


class SegmentationProfile(Base, TimestampMixin):
    """
    Profil de segmentation B2B d'une organisation.
    Detecte automatiquement (NAF, heuristiques) ou affine par questionnaire.
    V100: portfolio_id nullable + derived_from + segment_label.
    """
    __tablename__ = "segmentation_profiles"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        index=True,
        comment="Organisation rattachee",
    )
    portfolio_id = Column(
        Integer,
        ForeignKey("portefeuilles.id"),
        nullable=True,
        index=True,
        comment="Portefeuille (nullable = profil org-level)",
    )
    typologie = Column(
        String(50),
        nullable=False,
        comment="Segment detecte (enum Typologie key)",
    )
    segment_label = Column(
        String(100),
        nullable=True,
        comment="Label humain du segment (ex: Tertiaire Prive)",
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
    derived_from = Column(
        String(30),
        nullable=True,
        default="mix",
        comment="Source de detection: naf|questionnaire|patrimoine|mix",
    )
    answers_json = Column(
        Text,
        nullable=True,
        comment="Reponses au questionnaire (JSON serialise) — legacy, prefer SegmentationAnswer",
    )
    reasons_json = Column(
        Text,
        nullable=True,
        comment="Raisons de la detection (JSON serialise)",
    )

    # Relations
    organisation = relationship("Organisation", backref="segmentation_profile")
    answers = relationship("SegmentationAnswer", back_populates="profile", cascade="all, delete-orphan")


class SegmentationAnswer(Base, TimestampMixin):
    """
    V100: Reponse individuelle au questionnaire de segmentation.
    Remplace progressivement answers_json dans SegmentationProfile.
    """
    __tablename__ = "segmentation_answers"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(
        Integer,
        ForeignKey("segmentation_profiles.id"),
        nullable=False,
        index=True,
        comment="Profil de segmentation rattache",
    )
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        index=True,
        comment="Organisation (denormalise pour requetes rapides)",
    )
    portfolio_id = Column(
        Integer,
        ForeignKey("portefeuilles.id"),
        nullable=True,
        index=True,
        comment="Portefeuille (nullable = org-level)",
    )
    question_id = Column(
        String(50),
        nullable=False,
        comment="ID de la question (ex: q_travaux, q_gtb)",
    )
    answer_value = Column(
        String(100),
        nullable=False,
        comment="Valeur de la reponse",
    )

    # Relations
    profile = relationship("SegmentationProfile", back_populates="answers")
