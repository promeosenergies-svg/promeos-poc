"""
PROMEOS — Annotation model + AnnotatorProfile.
Table d'annotation polymorphique pour tous les objets annotables.
Org-scopee obligatoirement.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from .base import Base, TimestampMixin


class Annotation(TimestampMixin, Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True)

    # Cible polymorphique
    object_type = Column(String(50), nullable=False, index=True)
    # Valeurs: meter_reading | monitoring_alert | billing_insight
    #          ai_insight | kb_item | anomaly | compliance_finding
    object_id = Column(Integer, nullable=False, index=True)

    # Signal d'annotation
    label = Column(String(100), nullable=False)
    # Valeurs: confirmed_anomaly | false_positive | correct_archetype
    #          wrong_threshold | missing_context | validated_constant
    #          validated_regulation | ground_truth

    confidence = Column(Float, nullable=False, default=0.5)
    # 0.0-1.0 : user expert=0.9, agent IA=0.65, consensus=calcule, seed=1.0

    # Feedback qualitatif
    correction = Column(Text, nullable=True)
    note = Column(Text, nullable=True)

    # Provenance
    annotator_type = Column(String(20), nullable=False)
    # Valeurs: user | ai_agent | rule_engine | import | seed
    annotator_id = Column(String(100), nullable=False)
    # Valeurs: "user:42" | "agent:data_quality_agent" | "seed:helios_v1"
    org_id = Column(Integer, nullable=False, index=True)

    # Lien KB (optionnel)
    kb_item_id = Column(String(200), nullable=True)
    rule_id = Column(String(200), nullable=True)

    # Meta
    needs_review = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_annotations_object", "object_type", "object_id"),
        Index("ix_annotations_annotator", "annotator_type", "annotator_id"),
        Index("ix_annotations_rule", "rule_id"),
    )


class AnnotatorProfile(TimestampMixin, Base):
    __tablename__ = "annotator_profiles"

    id = Column(Integer, primary_key=True)
    annotator_id = Column(String(100), nullable=False, unique=True, index=True)
    annotator_type = Column(String(20), nullable=False)  # human | ai_agent | rule_engine
    org_id = Column(Integer, nullable=False, index=True)

    # Scores par domaine (JSON : {billing: {accuracy, count, fp_rate}, ...})
    domain_scores_json = Column(Text, nullable=True, default="{}")

    # Biais detectes (JSON)
    bias_flags_json = Column(Text, nullable=True, default="{}")

    trust_weight = Column(Float, nullable=False, default=0.5)  # 0.0-1.0 global
    annotation_count = Column(Integer, nullable=False, default=0)
    last_active_at = Column(DateTime, nullable=True)
    computed_at = Column(DateTime, nullable=True)
    computed_by = Column(String(100), nullable=True)
