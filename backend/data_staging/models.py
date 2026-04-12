"""
SF5 — Modèles des tables fonctionnelles de promotion.

Tables créées :
- meter_load_curve      : CDC puissance (R4x, R50 → kW, kVAr, V)
- meter_energy_index    : Index énergie cumulative par classe tarifaire (R171, R151 → Wh)
- meter_power_peak      : Puissance max appelée (R151 PMAX → VA)
- promotion_run         : Exécution de promotion (audit)
- promotion_event       : Événements par ligne (audit trail)
- unmatched_prm         : PRM non résolus (backlog)
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Date,
    Float,
    Integer,
    String,
    Boolean,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from models.base import Base, TimestampMixin


# ── Tables fonctionnelles ─────────────────────────────────────────────────


class MeterLoadCurve(Base, TimestampMixin):
    """CDC puissance — un point par (meter, timestamp, pas)."""

    __tablename__ = "meter_load_curve"
    __table_args__ = (
        UniqueConstraint("meter_id", "timestamp", "pas_minutes", name="uq_mlc_meter_ts_pas"),
        Index("ix_mlc_meter_ts", "meter_id", "timestamp"),
        Index("ix_mlc_run", "promotion_run_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, comment="Début intervalle UTC")
    pas_minutes = Column(Integer, nullable=False, comment="5, 10 ou 30")

    active_power_kw = Column(Float, nullable=True)
    reactive_inductive_kvar = Column(Float, nullable=True)
    reactive_capacitive_kvar = Column(Float, nullable=True)
    voltage_v = Column(Float, nullable=True)

    quality_score = Column(Float, nullable=False, default=0.5, comment="0=inconnu, 1=réel")
    is_estimated = Column(Boolean, nullable=False, default=False)
    source_flux_type = Column(String(10), nullable=False, comment="R4H/R4M/R4Q/R50")

    promotion_run_id = Column(Integer, ForeignKey("promotion_run.id"), nullable=True)


class MeterEnergyIndex(Base, TimestampMixin):
    """Index énergie cumulative par classe tarifaire."""

    __tablename__ = "meter_energy_index"
    __table_args__ = (
        UniqueConstraint(
            "meter_id",
            "date_releve",
            "tariff_class_code",
            "tariff_grid",
            name="uq_mei_meter_date_class_grid",
        ),
        Index("ix_mei_meter_date", "meter_id", "date_releve"),
        Index("ix_mei_run", "promotion_run_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)
    date_releve = Column(Date, nullable=False)
    tariff_class_code = Column(String(20), nullable=False, comment="HCE/HCH/HPE/HPH/P/BASE/etc")
    tariff_class_label = Column(String(100), nullable=True)
    tariff_grid = Column(String(10), nullable=False, comment="CT ou CT_DIST")
    value_wh = Column(Float, nullable=False)

    quality_score = Column(Float, nullable=False, default=0.9)
    is_estimated = Column(Boolean, nullable=False, default=False)
    source_flux_type = Column(String(10), nullable=False, comment="R171/R151")

    promotion_run_id = Column(Integer, ForeignKey("promotion_run.id"), nullable=True)


class MeterPowerPeak(Base, TimestampMixin):
    """Puissance max appelée (PMAX)."""

    __tablename__ = "meter_power_peak"
    __table_args__ = (
        UniqueConstraint("meter_id", "date_releve", name="uq_mpp_meter_date"),
        Index("ix_mpp_meter_date", "meter_id", "date_releve"),
        Index("ix_mpp_run", "promotion_run_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False, index=True)
    date_releve = Column(Date, nullable=False)
    value_va = Column(Float, nullable=False)

    quality_score = Column(Float, nullable=False, default=0.9)
    is_estimated = Column(Boolean, nullable=False, default=False)
    source_flux_type = Column(String(10), nullable=False, default="R151")

    promotion_run_id = Column(Integer, ForeignKey("promotion_run.id"), nullable=True)


# ── Tables opérationnelles (audit) ���───────────────────────────────────────


class PromotionRun(Base, TimestampMixin):
    """Une exécution du pipeline de promotion."""

    __tablename__ = "promotion_run"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running", comment="running/completed/failed")
    triggered_by = Column(String(20), nullable=False, default="api", comment="cli/api")
    mode = Column(String(20), nullable=False, default="incremental", comment="incremental/full")
    scope_flux_types = Column(String(100), nullable=True, comment="R4H,R50,R171,R151")

    high_water_mark_before = Column(Text, nullable=True, comment="JSON {table: max_id}")
    high_water_mark_after = Column(Text, nullable=True, comment="JSON {table: max_id}")

    prms_total = Column(Integer, default=0)
    prms_matched = Column(Integer, default=0)
    prms_unmatched = Column(Integer, default=0)
    prms_promoted = Column(Integer, default=0)
    prms_failed = Column(Integer, default=0)

    rows_load_curve = Column(Integer, default=0)
    rows_energy_index = Column(Integer, default=0)
    rows_power_peak = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    rows_flagged = Column(Integer, default=0)

    error_message = Column(Text, nullable=True)


class PromotionEvent(Base):
    """Événement d'audit par ligne promue/ignorée/bloquée."""

    __tablename__ = "promotion_event"
    __table_args__ = (Index("ix_pe_run", "promotion_run_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    promotion_run_id = Column(Integer, ForeignKey("promotion_run.id"), nullable=False)
    target_table = Column(String(30), nullable=False)
    target_row_id = Column(Integer, nullable=True)
    action = Column(String(20), nullable=False, comment="created/updated/skipped/flagged")
    source_table = Column(String(50), nullable=False)
    source_row_id = Column(Integer, nullable=False)
    source_flux_file_id = Column(Integer, nullable=True)
    previous_quality_score = Column(Float, nullable=True)
    new_quality_score = Column(Float, nullable=True)
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class UnmatchedPrm(Base, TimestampMixin):
    """PRM non résolus ��� backlog de matching."""

    __tablename__ = "unmatched_prm"
    __table_args__ = (Index("ix_uprm_status", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    point_id = Column(String(14), nullable=False, index=True, comment="PRM 14 chiffres")
    first_seen_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    flux_types = Column(String(100), nullable=True, comment="R4H,R50,R171 (comma-sep)")
    measures_count = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="pending", comment="pending/resolved/ignored")
    block_reason = Column(String(50), nullable=True, comment="no_delivery_point/no_active_meter/multiple_active_meters")
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True)
    notes = Column(Text, nullable=True)


# Liste pour migration
SF5_TABLES = (
    "promotion_run",
    "promotion_event",
    "unmatched_prm",
    "meter_load_curve",
    "meter_energy_index",
    "meter_power_peak",
)
