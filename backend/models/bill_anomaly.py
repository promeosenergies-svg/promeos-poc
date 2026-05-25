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

Audit Bill Intelligence Phase 0-bis (2026-05-24, chantier C1) :
- Ajout `is_monetizable` (Boolean, default True) + `non_monetizable_reason` (Text)
- Validation runtime via SQLAlchemy event listener `before_insert` / `before_update` :
  une anomalie valorisable (`is_monetizable=True`) doit avoir `actual_value` non NULL.
- Migration `p38_bill_anomaly_monetizable.py` (anti-DROP, idempotent).
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import relationship

from .base import Base, SoftDeleteMixin, TimestampMixin


class BillAnomaly(Base, TimestampMixin, SoftDeleteMixin):
    """Anomalie détectée sur une facture énergie (Bill Intelligence Sprint C-5 Phase 5.1)."""

    __tablename__ = "bill_anomaly"
    __table_args__ = (
        Index("ix_bill_anomaly_code_severity", "code", "severity"),
        Index("ix_bill_anomaly_detected_at", "detected_at"),
        # Sprint C-5 Phase 5.8 fix G3 (audit transversal AXE 2 F4) : anti-doublons R19/R20
        # sur même invoice (replays ingestion concurrente). Note : avec SoftDeleteMixin,
        # un soft-delete ne libère pas la contrainte (PostgreSQL nécessitera index partiel
        # WHERE deleted_at IS NULL Sprint C-7 polish — MVP SQLite simple suffit).
        UniqueConstraint("invoice_id", "code", name="uq_bill_anomaly_invoice_code"),
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

    # Phase 0-bis Bill Intelligence — chantier C1 (2026-05-24)
    is_monetizable = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="True → impact financier chiffrable, actual_value requis. "
        "False → anomalie informative (R017 PDL manquant, etc.), actual_value libre.",
    )
    non_monetizable_reason = Column(
        Text,
        nullable=True,
        comment="Justification obligatoire si is_monetizable=False (FR clair).",
    )

    # Relation cardinale
    invoice = relationship("EnergyInvoice", backref="bill_anomalies")

    def __repr__(self) -> str:
        return (
            f"<BillAnomaly(id={self.id}, invoice_id={self.invoice_id}, "
            f"code='{self.code}', severity='{self.severity}', monetizable={self.is_monetizable})>"
        )


class BillAnomalyValidationError(ValueError):
    """Levée si une anomalie viole l'invariant doctrinal (cf. C1 Phase 0-bis).

    Une anomalie valorisable DOIT avoir `actual_value` non NULL.
    Une anomalie non valorisable DOIT avoir `non_monetizable_reason` non NULL.
    """


def _validate_bill_anomaly_invariant(mapper, connection, target: "BillAnomaly") -> None:
    """Listener SQLAlchemy : empêche les anomalies incomplètes côté financier.

    Doctrine Bill Intelligence P1 C1 (2026-05-24) :
    > Aucune anomalie facture sans : source, montant ou justification "non
    > valorisable", période, facture, site, PDL/contrat, preuve ou preuve
    > attendue, action possible ou statut non actionnable explicite.

    Bloque l'INSERT/UPDATE si :
    - `is_monetizable=True` (default) ET `actual_value IS NULL` → anomalie
      valorisable sans montant fiable, refusée (sinon KPI loss faux silencieusement).
    - `is_monetizable=False` ET `non_monetizable_reason` vide → on exige une
      raison explicite pour pouvoir l'auditer / l'afficher au DAF.

    Note défense : au moment de `before_insert`, le default Python n'est pas
    forcément appliqué sur le target → on traite `None` comme `True` (le default).
    """
    # `None` au moment de l'insert = sera défaulté à True par le serveur — on traite comme valorisable
    monetizable = True if target.is_monetizable is None else bool(target.is_monetizable)

    if monetizable and target.actual_value is None:
        raise BillAnomalyValidationError(
            f"BillAnomaly code={target.code!r} : is_monetizable=True (défaut) exige "
            f"`actual_value` non NULL. Si l'impact n'est pas chiffrable, "
            f"marquer is_monetizable=False + renseigner non_monetizable_reason."
        )
    if not monetizable and not (target.non_monetizable_reason or "").strip():
        raise BillAnomalyValidationError(
            f"BillAnomaly code={target.code!r} : is_monetizable=False exige "
            f"`non_monetizable_reason` (FR clair, ex : 'Données contractuelles "
            f"manquantes pour chiffrer l'impact')."
        )


event.listen(BillAnomaly, "before_insert", _validate_bill_anomaly_invariant)
event.listen(BillAnomaly, "before_update", _validate_bill_anomaly_invariant)
