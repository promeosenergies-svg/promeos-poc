"""
PROMEOS Energy Models - Consumption Data & Analytics
Time series data, usage profiles, anomalies, recommendations
"""
from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import Base


class EnergyVector(str, enum.Enum):
    """Energy type"""
    ELECTRICITY = "electricity"
    GAS = "gas"
    HEAT = "heat"
    WATER = "water"
    OTHER = "other"


class FrequencyType(str, enum.Enum):
    """Time series frequency"""
    MIN_15 = "15min"
    MIN_30 = "30min"
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"


class ImportStatus(str, enum.Enum):
    """Import job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class AnomalySeverity(str, enum.Enum):
    """Anomaly severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationStatus(str, enum.Enum):
    """Recommendation lifecycle status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class Meter(Base):
    """Energy meter with enhanced metadata"""
    __tablename__ = "meter"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Meter identification
    meter_id = Column(String(50), nullable=False, unique=True, index=True)  # PRM, PDL, etc.
    name = Column(String(200), nullable=False)

    # Energy type
    energy_vector = Column(SQLEnum(EnergyVector), nullable=False, default=EnergyVector.ELECTRICITY)

    # Site association
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)

    # Subscription details
    subscribed_power_kva = Column(Float, nullable=True)
    tariff_type = Column(String(50), nullable=True)  # C5, TURPE, etc.

    # Metadata
    installation_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = relationship("Site", back_populates="meters")
    readings = relationship("MeterReading", back_populates="meter", cascade="all, delete-orphan")
    profiles = relationship("UsageProfile", back_populates="meter", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="meter", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="meter", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Meter(meter_id='{self.meter_id}', energy='{self.energy_vector.value}', site_id={self.site_id})>"


class MeterReading(Base):
    """Time series consumption data"""
    __tablename__ = "meter_reading"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Meter reference
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)

    # Time dimension
    timestamp = Column(DateTime, nullable=False, index=True)
    frequency = Column(SQLEnum(FrequencyType), nullable=False, default=FrequencyType.HOURLY)

    # Value
    value_kwh = Column(Float, nullable=False)

    # Quality metadata
    is_estimated = Column(Boolean, nullable=False, default=False)
    quality_score = Column(Float, nullable=True)  # 0-1 confidence score

    # Import tracking
    import_job_id = Column(Integer, ForeignKey("data_import_job.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    meter = relationship("Meter", back_populates="readings")
    import_job = relationship("DataImportJob", back_populates="readings")

    def __repr__(self):
        return f"<MeterReading(meter_id={self.meter_id}, timestamp='{self.timestamp}', kwh={self.value_kwh})>"


class DataImportJob(Base):
    """Track data import operations"""
    __tablename__ = "data_import_job"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Job metadata
    job_type = Column(String(50), nullable=False, default="consumption_import")  # consumption_import, manual_entry, api_sync
    status = Column(SQLEnum(ImportStatus), nullable=False, default=ImportStatus.PENDING)

    # File reference
    filename = Column(String(500), nullable=True)
    file_format = Column(String(20), nullable=True)  # csv, xlsx, json
    file_size_bytes = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA256 for deduplication

    # Scope
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True)

    # Results
    rows_total = Column(Integer, nullable=True)
    rows_imported = Column(Integer, nullable=True)
    rows_skipped = Column(Integer, nullable=True)
    rows_errored = Column(Integer, nullable=True)

    # Time range imported
    date_start = Column(DateTime, nullable=True)
    date_end = Column(DateTime, nullable=True)

    # Error details
    error_message = Column(Text, nullable=True)
    error_details_json = Column(JSON, nullable=True)  # Detailed error log

    # Audit
    created_by = Column(String(200), nullable=True)  # User or system
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    site = relationship("Site")
    meter = relationship("Meter")
    readings = relationship("MeterReading", back_populates="import_job")

    def __repr__(self):
        return f"<DataImportJob(id={self.id}, status='{self.status.value}', rows={self.rows_imported}/{self.rows_total})>"


class UsageProfile(Base):
    """Analyzed usage profile for a meter"""
    __tablename__ = "usage_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Meter reference
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)

    # Analysis period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Matched archetype
    archetype_id = Column(Integer, ForeignKey("kb_archetype.id"), nullable=True)
    archetype_code = Column(String(100), nullable=True)
    archetype_match_score = Column(Float, nullable=True)  # 0-1 confidence

    # Computed features (JSON: detailed metrics)
    features_json = Column(JSON, nullable=True)
    # Example: {
    #   "kwh_total": 50000,
    #   "kwh_m2_year": 185.2,
    #   "base_nuit_ratio": 0.15,
    #   "weekend_ratio": 0.12,
    #   "load_factor": 0.42,
    #   "peak_power_kw": 125,
    #   "seasonality_cv": 0.18,
    #   ...
    # }

    # Temporal patterns (JSON)
    temporal_patterns_json = Column(JSON, nullable=True)
    # Example: {
    #   "hourly_profile": [...],
    #   "day_type_profile": {"weekday": ..., "weekend": ...},
    #   "monthly_profile": [...]
    # }

    # KB provenance
    kb_version_id = Column(Integer, ForeignKey("kb_version.id"), nullable=True)
    analysis_version = Column(String(50), nullable=True)  # Analytics engine version

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meter = relationship("Meter", back_populates="profiles")
    archetype = relationship("KBArchetype")
    kb_version = relationship("KBVersion")

    def __repr__(self):
        return f"<UsageProfile(meter_id={self.meter_id}, archetype='{self.archetype_code}', period='{self.period_start.date()}')>"


class Anomaly(Base):
    """Detected anomaly instance"""
    __tablename__ = "anomaly"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Meter reference
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)

    # Anomaly details
    anomaly_code = Column(String(100), nullable=False, index=True)  # ANOM_BASE_NUIT_ELEVEE, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Severity & confidence
    severity = Column(SQLEnum(AnomalySeverity), nullable=False, default=AnomalySeverity.MEDIUM)
    confidence = Column(Float, nullable=False, default=0.8)  # 0-1

    # Detection details
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    # Measured values
    measured_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    deviation_pct = Column(Float, nullable=True)

    # KB provenance
    kb_rule_id = Column(Integer, ForeignKey("kb_anomaly_rule.id"), nullable=True)
    kb_version_id = Column(Integer, ForeignKey("kb_version.id"), nullable=True)

    # Explanation (JSON: detailed breakdown)
    explanation_json = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(200), nullable=True)
    review_note = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meter = relationship("Meter", back_populates="anomalies")
    kb_rule = relationship("KBAnomalyRule")
    kb_version = relationship("KBVersion")

    def __repr__(self):
        return f"<Anomaly(id={self.id}, code='{self.anomaly_code}', severity='{self.severity.value}', meter_id={self.meter_id})>"


class Recommendation(Base):
    """Generated recommendation instance"""
    __tablename__ = "recommendation"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Meter reference
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)

    # Recommendation details
    recommendation_code = Column(String(100), nullable=False, index=True)  # RECO_BASE_NUIT, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Trigger (what caused this recommendation)
    triggered_by_anomaly_id = Column(Integer, ForeignKey("anomaly.id"), nullable=True)

    # Impact estimation
    estimated_savings_kwh_year = Column(Float, nullable=True)
    estimated_savings_eur_year = Column(Float, nullable=True)
    estimated_savings_pct = Column(Float, nullable=True)

    # ICE scoring
    impact_score = Column(Integer, nullable=True)  # 1-10
    confidence_score = Column(Integer, nullable=True)  # 1-10
    ease_score = Column(Integer, nullable=True)  # 1-10 (Facilité)
    ice_score = Column(Float, nullable=True)  # Computed
    priority_rank = Column(Integer, nullable=True)  # For sorting

    # KB provenance
    kb_recommendation_id = Column(Integer, ForeignKey("kb_recommendation.id"), nullable=True)
    kb_version_id = Column(Integer, ForeignKey("kb_version.id"), nullable=True)

    # Implementation details (JSON)
    action_plan_json = Column(JSON, nullable=True)

    # Status
    status = Column(SQLEnum(RecommendationStatus), nullable=False, default=RecommendationStatus.PENDING)
    is_reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(200), nullable=True)
    review_note = Column(Text, nullable=True)

    # Completion tracking
    implementation_started_at = Column(DateTime, nullable=True)
    implementation_completed_at = Column(DateTime, nullable=True)
    actual_savings_kwh_year = Column(Float, nullable=True)  # Post-implementation measurement

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meter = relationship("Meter", back_populates="recommendations")
    triggered_by_anomaly = relationship("Anomaly")
    kb_recommendation = relationship("KBRecommendation")
    kb_version = relationship("KBVersion")

    def __repr__(self):
        return f"<Recommendation(id={self.id}, code='{self.recommendation_code}', ice={self.ice_score}, meter_id={self.meter_id})>"
