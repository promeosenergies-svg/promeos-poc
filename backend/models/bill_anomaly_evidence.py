"""
PROMEOS — BillAnomalyEvidence model (Bill Intelligence P1 C2, 2026-05-24).

Doctrine produit (audit Bill Intelligence P0 §3 + Phase 0-bis §7.1) :
> Une anomalie facture doit toujours avoir : source, montant ou justification
> "non valorisable", période, facture, site, point de livraison ou contrat,
> **preuve ou preuve attendue**, action possible ou statut non actionnable.

Avant P1 : les "preuves" vivaient dans `BillAnomaly.details_json` (champ JSON
semi-structuré). Aucun document opposable n'était attachable, aucun téléchargement
authentifié n'était possible.

P1 livre :
- table `bill_anomaly_evidence` (FK anomaly + invoice + org)
- hash SHA-256 obligatoire (intégrité opposable)
- workflow `verified_at` / `verified_by` (preuve produite ≠ preuve validée)
- migration `p39_bill_anomaly_evidence.py` (idempotent, anti-DROP)

Pattern inspiré de Evidence V4 conformité C6 (livré P1 conformité 2026-05-23).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base, SoftDeleteMixin, TimestampMixin


class BillAnomalyEvidence(Base, TimestampMixin, SoftDeleteMixin):
    """Preuve documentaire rattachée à une anomalie de facture."""

    __tablename__ = "bill_anomaly_evidence"
    __table_args__ = (
        Index("ix_bill_anomaly_evidence_anomaly", "anomaly_id"),
        Index("ix_bill_anomaly_evidence_invoice", "invoice_id"),
        Index("ix_bill_anomaly_evidence_org", "org_id"),
        Index("ix_bill_anomaly_evidence_hash", "file_hash_sha256"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    anomaly_id = Column(
        Integer,
        ForeignKey("bill_anomaly.id"),
        nullable=False,
        comment="Anomalie concernée (FK BillAnomaly)",
    )
    org_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        comment="Organisation propriétaire (org-scoping cardinal — IDOR-safe)",
    )
    invoice_id = Column(
        Integer,
        ForeignKey("energy_invoices.id"),
        nullable=False,
        comment="Facture concernée (dénormalisée pour requêtes rapides + audit)",
    )
    evidence_type = Column(
        String(50),
        nullable=False,
        comment=(
            "Type de preuve : 'invoice_pdf', 'contract_pdf', 'meter_index_photo', "
            "'energy_supplier_response', 'manual_calculation', 'audit_report'"
        ),
    )
    filename = Column(
        String(255),
        nullable=False,
        comment="Nom de fichier d'origine (sanitized, sans path)",
    )
    mime_type = Column(
        String(100),
        nullable=False,
        comment="Type MIME validé côté backend (whitelist : pdf/png/jpeg/csv)",
    )
    file_hash_sha256 = Column(
        String(64),
        nullable=False,
        comment="Hash SHA-256 (intégrité opposable — chaîne de signature)",
    )
    storage_uri = Column(
        Text,
        nullable=False,
        comment=(
            "URI de stockage (fs://path | s3://bucket/key) — jamais exposé en clair "
            "côté FE, accédé uniquement via endpoint download org-scopé"
        ),
    )
    source = Column(
        String(50),
        nullable=False,
        default="manual_upload",
        comment="Source : 'manual_upload' (DAF) / 'auto_ingestion' / 'system_generated'",
    )
    created_by = Column(
        Integer,
        nullable=True,
        comment="user_id de l'uploader (NULL si système)",
    )
    verified_at = Column(
        DateTime,
        nullable=True,
        comment="Date de vérification par un opérateur (NULL = preuve déposée mais pas validée)",
    )
    verified_by = Column(
        Integer,
        nullable=True,
        comment="user_id du vérificateur",
    )

    # Relations
    anomaly = relationship("BillAnomaly", backref="evidences")

    def __repr__(self) -> str:
        return (
            f"<BillAnomalyEvidence(id={self.id}, anomaly_id={self.anomaly_id}, "
            f"type={self.evidence_type!r}, verified={self.verified_at is not None})>"
        )
