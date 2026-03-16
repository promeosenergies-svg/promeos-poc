"""
PROMEOS — OperatExportManifest : chaine de preuve pour chaque export preparatoire OPERAT.
Chaque generation d'export cree un manifest immuable reconstituable.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime, timezone
from .base import Base


class OperatExportManifest(Base):
    """Manifest d'un export OPERAT preparatoire — preuve de ce qui a ete genere."""

    __tablename__ = "operat_export_manifest"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, nullable=True, index=True, comment="EFA concerne (null si multi-EFA)")
    org_id = Column(Integer, nullable=False, index=True)
    generated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    actor = Column(String(200), nullable=False, default="system", comment="Qui a genere l'export")
    file_name = Column(String(500), nullable=False)
    checksum_sha256 = Column(String(64), nullable=False, comment="SHA-256 du contenu CSV")
    observation_year = Column(Integer, nullable=False)
    baseline_year = Column(Integer, nullable=True)
    baseline_kwh = Column(Float, nullable=True)
    current_kwh = Column(Float, nullable=True)
    baseline_source = Column(String(50), nullable=True)
    current_source = Column(String(50), nullable=True)
    baseline_reliability = Column(String(20), nullable=True)
    current_reliability = Column(String(20), nullable=True)
    trajectory_status = Column(String(20), nullable=True)
    efa_count = Column(Integer, nullable=True)
    evidence_warnings_json = Column(Text, nullable=True)
    export_version = Column(String(20), nullable=False, default="1.0")
