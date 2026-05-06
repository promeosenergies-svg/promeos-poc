"""
PROMEOS — BillAnomaly model (Sprint C-5 Phase 5.1, ADR-013).

Différenciateur produit cardinal Phase C : Bill Intelligence anomaly detection.

Détection rules-based pure :
- R19 : VNU dormant facturé (ligne TAX label "VNU" sur invoice sans usage attendu)
- R20 : Capacité variance > 5% (NETWORK kVA facturé vs PowerContract.ps_par_poste_kva[period_code])

Sémantique distincte du modèle Anomaly KB Phase 1-4 (consommation vs facturation) :
- Anomaly KB : meter_id + anomaly_code "ANOM_BASE_NUIT_ELEVEE" (consommation atypique)
- BillAnomaly : invoice_id + code R19/R20 (anomalie facturation, économie chiffrée potentielle)

Adaptations Phase 5.1.0 (post-diagnostic) :
- FK invoice_id → energy_invoices.id (modèle EnergyInvoice, pas Facture)
- Pas de relation directe DeliveryPoint (JOIN via Site → Meter pour R20)
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from .base import Base, SoftDeleteMixin, TimestampMixin


class BillAnomaly(Base, TimestampMixin, SoftDeleteMixin):
    """Anomalie détectée sur une facture énergie (Bill Intelligence Sprint C-5 Phase 5.1)."""

    __tablename__ = "bill_anomaly"
    __table_args__ = (
        Index("ix_bill_anomaly_code_severity", "code", "severity"),
        Index("ix_bill_anomaly_detected_at", "detected_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(
        Integer,
        ForeignKey("energy_invoices.id"),
        nullable=False,
        index=True,
        comment="Facture concernée (EnergyInvoice)",
    )
    code = Column(
        String(20),
        nullable=False,
        comment="Code anomalie : R19 (VNU dormant), R20 (capacité variance), R21+ futurs",
    )
    severity = Column(
        String(10),
        nullable=False,
        comment="Sévérité : critical / warning / info",
    )
    detected_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Date détection",
    )
    resolved_at = Column(
        DateTime,
        nullable=True,
        comment="Date résolution (NULL = ouverte)",
    )
    resolution_note = Column(
        Text,
        nullable=True,
        comment="Note résolution (correction fournisseur, justification, etc.)",
    )
    threshold_value = Column(
        Numeric(10, 4),
        nullable=True,
        comment="Seuil YAML appliqué (ex : 5.0 pour R20)",
    )
    actual_value = Column(
        Numeric(15, 4),
        nullable=True,
        comment="Valeur observée (ex : variance_pct = 8.3)",
    )
    details_json = Column(
        JSON,
        nullable=True,
        comment="Contexte détection (montants VNU, période, contrat, etc.)",
    )

    # Relation cardinale
    invoice = relationship("EnergyInvoice", backref="bill_anomalies")

    def __repr__(self) -> str:
        return (
            f"<BillAnomaly(id={self.id}, invoice_id={self.invoice_id}, code='{self.code}', severity='{self.severity}')>"
        )
