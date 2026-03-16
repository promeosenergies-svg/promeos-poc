"""
PROMEOS — Modeles reglementaires BACS complementaires.
Exigences fonctionnelles R.175-3, exploitation/maintenance R.175-4/5, preuves.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Date, ForeignKey
from datetime import datetime, timezone
from .base import Base, TimestampMixin


class BacsFunctionalRequirement(Base, TimestampMixin):
    """Exigence fonctionnelle BACS (R.175-3) evaluee pour un actif."""

    __tablename__ = "bacs_functional_requirements"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("bacs_assets.id", ondelete="CASCADE"), nullable=False, index=True)

    # Exigences R.175-3
    continuous_monitoring = Column(String(20), default="not_demonstrated", comment="ok/partial/absent/not_demonstrated")
    hourly_timestep = Column(String(20), default="not_demonstrated")
    functional_zones = Column(String(20), default="not_demonstrated")
    monthly_retention_5y = Column(String(20), default="not_demonstrated")
    reference_values = Column(String(20), default="not_demonstrated")
    efficiency_loss_detection = Column(String(20), default="not_demonstrated")
    interoperability = Column(String(20), default="not_demonstrated")
    manual_override = Column(String(20), default="not_demonstrated")
    autonomous_management = Column(String(20), default="not_demonstrated")
    data_ownership = Column(String(20), default="not_demonstrated")

    # Meta
    assessed_at = Column(DateTime, nullable=True)
    assessed_by = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)


class BacsExploitationStatus(Base, TimestampMixin):
    """Statut exploitation/maintenance BACS (R.175-4 / R.175-5)."""

    __tablename__ = "bacs_exploitation_status"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("bacs_assets.id", ondelete="CASCADE"), nullable=False, index=True)

    # Consignes et procedures
    written_procedures = Column(String(20), default="absent", comment="ok/partial/absent")
    verification_periodicity = Column(String(50), nullable=True, comment="Ex: mensuelle, trimestrielle")
    control_points_defined = Column(Boolean, default=False)
    repair_process_defined = Column(Boolean, default=False)

    # Formation
    operator_trained = Column(Boolean, default=False)
    training_date = Column(Date, nullable=True)
    training_provider = Column(String(200), nullable=True)
    training_certificate_ref = Column(String(200), nullable=True)

    # Meta
    last_review_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)


class BacsProofDocument(Base, TimestampMixin):
    """Preuve documentaire BACS — coffre minimal."""

    __tablename__ = "bacs_proof_documents"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("bacs_assets.id", ondelete="CASCADE"), nullable=False, index=True)

    document_type = Column(
        String(50),
        nullable=False,
        comment="attestation_bacs, rapport_inspection, formation, consignes, derogation_tri, interop_certificat",
    )
    label = Column(String(300), nullable=True)
    source = Column(String(100), nullable=True, comment="upload, manual, api, inspection")
    actor = Column(String(200), nullable=False, default="system")
    file_ref = Column(String(500), nullable=True, comment="URL ou reference fichier")
    valid_until = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    # Lien generique
    linked_entity_type = Column(String(50), nullable=True, comment="BacsInspection, BacsCvcSystem, etc.")
    linked_entity_id = Column(Integer, nullable=True)
