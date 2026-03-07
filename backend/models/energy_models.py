"""
PROMEOS Energy Models - Consumption Data & Analytics
Time series data, usage profiles, anomalies, recommendations
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    JSON,
    DateTime,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, backref
from datetime import datetime
import enum

from .base import Base
from .enums import EnergyVector


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

    # Champs unifiés depuis Compteur (Step 25)
    numero_serie = Column(String(100), nullable=True, index=True)
    type_compteur = Column(String(50), nullable=True)  # "electricite", "gaz", "eau"
    marque = Column(String(100), nullable=True)
    modele = Column(String(100), nullable=True)
    date_derniere_releve = Column(DateTime, nullable=True)

    # Lien DeliveryPoint (unifié depuis Compteur)
    delivery_point_id = Column(
        Integer,
        ForeignKey("delivery_points.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Support sous-compteur (préparation Step 26)
    parent_meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = relationship("Site", back_populates="meters")
    delivery_point = relationship("DeliveryPoint", foreign_keys=[delivery_point_id])
    sub_meters = relationship("Meter", backref=backref("parent_meter", remote_side="Meter.id"), foreign_keys=[parent_meter_id])
    readings = relationship("MeterReading", back_populates="meter", cascade="all, delete-orphan")
    profiles = relationship("UsageProfile", back_populates="meter", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="meter", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="meter", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Meter(meter_id='{self.meter_id}', energy='{self.energy_vector.value}', site_id={self.site_id})>"


class MeterReading(Base):
    """Time series consumption data"""

    __tablename__ = "meter_reading"
    __table_args__ = (UniqueConstraint("meter_id", "timestamp", name="uq_meter_reading_meter_ts"),)

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
    job_type = Column(
        String(50), nullable=False, default="consumption_import"
    )  # consumption_import, manual_entry, api_sync
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
        return (
            f"<DataImportJob(id={self.id}, status='{self.status.value}', rows={self.rows_imported}/{self.rows_total})>"
        )


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


# ========================================
# Monitoring Models (Electric Consumption Mastery)
# ========================================


class AlertStatus(str, enum.Enum):
    """Monitoring alert lifecycle"""

    OPEN = "open"
    ACKNOWLEDGED = "ack"
    RESOLVED = "resolved"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class MonitoringSnapshot(Base):
    """Periodic monitoring snapshot with KPIs for a site/meter"""

    __tablename__ = "monitoring_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Scope
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True, index=True)

    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # KPIs (JSON blob for flexibility)
    kpis_json = Column(JSON, nullable=True)
    # Expected keys:
    # pmax_kw, p95_kw, p99_kw, pmean_kw, pbase_kw, pbase_night_kw,
    # load_factor, peak_to_average, weekend_ratio, night_ratio,
    # total_kwh, readings_count, interval_minutes,
    # ramp_rate_max_kw_h, weekday_profile_kw[], weekend_profile_kw[],
    # monthly_kwh{}

    # Scores
    data_quality_score = Column(Float, nullable=True)  # 0-100
    risk_power_score = Column(Float, nullable=True)  # 0-100
    data_quality_details_json = Column(JSON, nullable=True)
    risk_power_details_json = Column(JSON, nullable=True)

    # Metadata
    engine_version = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    site = relationship("Site")
    meter = relationship("Meter")

    def __repr__(self):
        return (
            f"<MonitoringSnapshot(site_id={self.site_id}, period={self.period_start.date()}-{self.period_end.date()})>"
        )


class MonitoringAlert(Base):
    """Monitoring alert instance with lifecycle (open/ack/resolved)"""

    __tablename__ = "monitoring_alert"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Scope
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True, index=True)

    # Alert type & severity
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)

    # Time window
    start_ts = Column(DateTime, nullable=True)
    end_ts = Column(DateTime, nullable=True)

    # Evidence
    evidence_json = Column(JSON, nullable=True)
    # Expected: {measured, threshold, deviation_pct, context, ...}

    # Explanation & action
    explanation = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)
    estimated_impact_kwh = Column(Float, nullable=True)
    estimated_impact_eur = Column(Float, nullable=True)

    # KB linkage
    kb_link_json = Column(JSON, nullable=True)
    # Expected: {kb_rule_id, kb_rec_id, provenance, confidence}

    # Lifecycle
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.OPEN, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(200), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(200), nullable=True)
    resolution_note = Column(Text, nullable=True)

    # Snapshot reference
    snapshot_id = Column(Integer, ForeignKey("monitoring_snapshot.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = relationship("Site")
    meter = relationship("Meter")
    snapshot = relationship("MonitoringSnapshot")

    def __repr__(self):
        return f"<MonitoringAlert(id={self.id}, type='{self.alert_type}', severity='{self.severity.value}', status='{self.status.value}')>"
