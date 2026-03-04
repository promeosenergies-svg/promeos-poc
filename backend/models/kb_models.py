"""
PROMEOS KB Models - Knowledge Base with Provenance
KB system tables for usages, archetypes, rules, recommendations
"""

from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import Base


class KBConfidence(str, enum.Enum):
    """KB item confidence levels"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KBStatus(str, enum.Enum):
    """KB item lifecycle status"""

    DRAFT = "draft"
    VALIDATED = "validated"
    DEPRECATED = "deprecated"


class KBVersion(Base):
    """KB version tracking for source documents"""

    __tablename__ = "kb_version"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(100), nullable=False, unique=True, index=True)
    version = Column(String(20), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    source_path = Column(String(500), nullable=False)
    source_sha256 = Column(String(64), nullable=False, unique=True, index=True)
    author = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(KBStatus), nullable=False, default=KBStatus.VALIDATED)
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    archetypes = relationship("KBArchetype", back_populates="kb_version_ref")
    anomaly_rules = relationship("KBAnomalyRule", back_populates="kb_version_ref")
    recommendations = relationship("KBRecommendation", back_populates="kb_version_ref")

    def __repr__(self):
        return f"<KBVersion(doc_id='{self.doc_id}', version='{self.version}', sha256='{self.source_sha256[:16]}...')>"


class KBArchetype(Base):
    """Usage archetypes extracted from KB source"""

    __tablename__ = "kb_archetype"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Consumption profile
    kwh_m2_min = Column(Integer, nullable=True)
    kwh_m2_max = Column(Integer, nullable=True)
    kwh_m2_avg = Column(Integer, nullable=True)

    # Usage breakdown (JSON: {usage_type: percentage})
    usage_breakdown_json = Column(JSON, nullable=True)

    # Temporal signature (JSON: {period: characteristics})
    temporal_signature_json = Column(JSON, nullable=True)

    # Applicable sectors
    segment_tags = Column(JSON, nullable=True)  # List of segment tags

    # Full KB item reference
    kb_item_id = Column(String(200), nullable=True)  # Reference to YAML item ID

    # Provenance
    kb_version_id = Column(Integer, ForeignKey("kb_version.id"), nullable=True)
    source_section = Column(String(200), nullable=True)
    confidence = Column(SQLEnum(KBConfidence), nullable=False, default=KBConfidence.MEDIUM)
    status = Column(SQLEnum(KBStatus), nullable=False, default=KBStatus.VALIDATED)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kb_version_ref = relationship("KBVersion", back_populates="archetypes")
    naf_mappings = relationship("KBMappingCode", back_populates="archetype")

    def __repr__(self):
        return f"<KBArchetype(code='{self.code}', kwh_m2='{self.kwh_m2_min}-{self.kwh_m2_max}')>"


class KBMappingCode(Base):
    """NAF code to archetype mappings"""

    __tablename__ = "kb_mapping_code"

    id = Column(Integer, primary_key=True, autoincrement=True)
    naf_code = Column(String(10), nullable=False, index=True)
    archetype_id = Column(Integer, ForeignKey("kb_archetype.id"), nullable=False)

    # Mapping metadata
    confidence = Column(SQLEnum(KBConfidence), nullable=False, default=KBConfidence.HIGH)
    priority = Column(Integer, nullable=False, default=1)  # For multi-match scenarios

    # Provenance
    kb_version_id = Column(Integer, ForeignKey("kb_version.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    archetype = relationship("KBArchetype", back_populates="naf_mappings")

    def __repr__(self):
        return f"<KBMappingCode(naf='{self.naf_code}', archetype_id={self.archetype_id})>"


class KBAnomalyRule(Base):
    """Anomaly detection rules from KB"""

    __tablename__ = "kb_anomaly_rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Rule definition
    rule_type = Column(String(50), nullable=False)  # base_nuit, weekend, puissance, etc.
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical

    # Thresholds (JSON: sector-specific or global)
    thresholds_json = Column(JSON, nullable=True)

    # Conditions (JSON: KB logic format)
    conditions_json = Column(JSON, nullable=True)

    # Applicable archetypes
    archetype_codes = Column(JSON, nullable=True)  # List of archetype codes or ["*"] for all

    # Full KB item reference
    kb_item_id = Column(String(200), nullable=True)

    # Provenance
    kb_version_id = Column(Integer, ForeignKey("kb_version.id"), nullable=True)
    source_section = Column(String(200), nullable=True)
    confidence = Column(SQLEnum(KBConfidence), nullable=False, default=KBConfidence.HIGH)
    status = Column(SQLEnum(KBStatus), nullable=False, default=KBStatus.VALIDATED)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kb_version_ref = relationship("KBVersion", back_populates="anomaly_rules")

    def __repr__(self):
        return f"<KBAnomalyRule(code='{self.code}', severity='{self.severity}')>"


class KBRecommendation(Base):
    """Recommendation playbooks from KB"""

    __tablename__ = "kb_recommendation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Action details
    action_type = Column(String(50), nullable=False)  # regulation, equipment, behavior, etc.
    target_asset = Column(String(50), nullable=True)  # hvac, eclairage, froid, etc.

    # Impact estimation
    savings_min_pct = Column(Float, nullable=True)  # Minimum savings percentage
    savings_max_pct = Column(Float, nullable=True)  # Maximum savings percentage

    # ICE scoring components (1-10 scale)
    impact_score = Column(Integer, nullable=True)  # Impact potential
    confidence_score = Column(Integer, nullable=True)  # Confidence in savings
    ease_score = Column(Integer, nullable=True)  # Implementation ease (Facilité)
    ice_score = Column(Float, nullable=True)  # Computed: (I * C * E) / 1000

    # Implementation details (JSON)
    implementation_steps_json = Column(JSON, nullable=True)
    prerequisites_json = Column(JSON, nullable=True)

    # Applicable contexts
    archetype_codes = Column(JSON, nullable=True)  # Applicable archetypes
    anomaly_codes = Column(JSON, nullable=True)  # Triggered by anomalies

    # Full KB item reference
    kb_item_id = Column(String(200), nullable=True)

    # Provenance
    kb_version_id = Column(Integer, ForeignKey("kb_version.id"), nullable=True)
    source_section = Column(String(200), nullable=True)
    confidence = Column(SQLEnum(KBConfidence), nullable=False, default=KBConfidence.MEDIUM)
    status = Column(SQLEnum(KBStatus), nullable=False, default=KBStatus.VALIDATED)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kb_version_ref = relationship("KBVersion", back_populates="recommendations")

    def __repr__(self):
        return f"<KBRecommendation(code='{self.code}', savings='{self.savings_min_pct}-{self.savings_max_pct}%')>"


class KBTaxonomy(Base):
    """Taxonomy validation - allowed values for tags"""

    __tablename__ = "kb_taxonomy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True)  # type, domain, energy, etc.
    value = Column(String(100), nullable=False)
    label = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    # Hierarchy (for nested taxonomies)
    parent_value = Column(String(100), nullable=True)

    # Validation
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<KBTaxonomy(category='{self.category}', value='{self.value}')>"
