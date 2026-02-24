"""
PROMEOS — Bill Intelligence SQLAlchemy models
Persisted: EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight.
Complement the dataclass-based domain model in app/bill_intelligence/domain.py.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, Date, DateTime, Enum, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import BillingEnergyType, InvoiceLineType, BillingInvoiceStatus, InsightStatus


class EnergyContract(Base, TimestampMixin):
    """
    Contrat d'energie lie a un site.
    Un site peut avoir plusieurs contrats (elec + gaz, ou succession).
    """
    __tablename__ = "energy_contracts"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer, ForeignKey("sites.id"), nullable=False, index=True,
        comment="Site concerne",
    )
    energy_type = Column(
        Enum(BillingEnergyType), nullable=False,
        comment="Type d'energie (elec/gaz)",
    )
    supplier_name = Column(
        String(200), nullable=False,
        comment="Nom du fournisseur (EDF, Engie, TotalEnergies...)",
    )
    start_date = Column(Date, nullable=True, comment="Debut du contrat")
    end_date = Column(Date, nullable=True, comment="Fin du contrat")
    price_ref_eur_per_kwh = Column(
        Float, nullable=True,
        comment="Prix de reference EUR HT/kWh",
    )
    fixed_fee_eur_per_month = Column(
        Float, nullable=True,
        comment="Abonnement mensuel EUR HT",
    )
    metadata_json = Column(Text, nullable=True, comment="Metadata libre (JSON)")
    notice_period_days = Column(
        Integer, nullable=False, default=90,
        comment="Preavis de resiliation en jours",
    )
    auto_renew = Column(
        Boolean, nullable=False, default=False,
        comment="Reconduction tacite",
    )

    # Relations
    site = relationship("Site", backref="energy_contracts")
    invoices = relationship(
        "EnergyInvoice", back_populates="contract",
        cascade="all, delete-orphan",
    )


class EnergyInvoice(Base, TimestampMixin):
    """
    Facture d'energie importee (CSV, JSON, PDF ou saisie manuelle).
    Chaque facture peut porter N lignes (EnergyInvoiceLine).
    """
    __tablename__ = "energy_invoices"
    __table_args__ = (
        UniqueConstraint(
            "site_id", "invoice_number", "period_start", "period_end",
            name="uq_invoice_site_number_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer, ForeignKey("sites.id"), nullable=False, index=True,
        comment="Site concerne",
    )
    contract_id = Column(
        Integer, ForeignKey("energy_contracts.id"), nullable=True, index=True,
        comment="Contrat rattache (optionnel)",
    )
    invoice_number = Column(
        String(100), nullable=False, index=True,
        comment="Numero de facture",
    )
    period_start = Column(Date, nullable=True, comment="Debut de periode facturee")
    period_end = Column(Date, nullable=True, comment="Fin de periode facturee")
    issue_date = Column(Date, nullable=True, comment="Date d'emission")
    total_eur = Column(Float, nullable=True, comment="Montant total EUR TTC")
    energy_kwh = Column(Float, nullable=True, comment="Consommation en kWh")
    status = Column(
        Enum(BillingInvoiceStatus), default=BillingInvoiceStatus.IMPORTED,
        nullable=False, comment="Statut de la facture",
    )
    source = Column(
        String(50), nullable=True,
        comment="Source d'import: csv, json, pdf, manual",
    )
    raw_json = Column(Text, nullable=True, comment="Donnees brutes (JSON)")

    # Relations
    site = relationship("Site", backref="energy_invoices")
    contract = relationship("EnergyContract", back_populates="invoices")
    lines = relationship(
        "EnergyInvoiceLine", back_populates="invoice",
        cascade="all, delete-orphan",
    )


# V67 — Indexes sur les champs période pour les range queries de couverture
_idx_period_start = Index("ix_energy_invoices_period_start", EnergyInvoice.period_start)
_idx_period_end = Index("ix_energy_invoices_period_end", EnergyInvoice.period_end)
_idx_issue_date = Index("ix_energy_invoices_issue_date", EnergyInvoice.issue_date)
_idx_site_period = Index("ix_energy_invoices_site_period", EnergyInvoice.site_id, EnergyInvoice.period_start)


class EnergyInvoiceLine(Base, TimestampMixin):
    """
    Ligne de detail d'une facture energie.
    Categorisee: ENERGY, NETWORK, TAX, OTHER.
    """
    __tablename__ = "energy_invoice_lines"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(
        Integer, ForeignKey("energy_invoices.id"), nullable=False, index=True,
        comment="Facture parente",
    )
    line_type = Column(
        Enum(InvoiceLineType), nullable=False,
        comment="Type de ligne (energy/network/tax/other)",
    )
    label = Column(String(300), nullable=False, comment="Libelle de la ligne")
    qty = Column(Float, nullable=True, comment="Quantite")
    unit = Column(String(20), nullable=True, comment="Unite (kWh, kVA, mois...)")
    unit_price = Column(Float, nullable=True, comment="Prix unitaire EUR")
    amount_eur = Column(Float, nullable=True, comment="Montant EUR")
    meta_json = Column(Text, nullable=True, comment="Metadata libre (JSON)")

    # Relations
    invoice = relationship("EnergyInvoice", back_populates="lines")


class BillingInsight(Base, TimestampMixin):
    """
    Insight de facturation detecte par l'anomaly engine.
    Ex: surfacturation, derive de prix, ecart shadow billing, doublon...
    """
    __tablename__ = "billing_insights"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer, ForeignKey("sites.id"), nullable=False, index=True,
        comment="Site concerne",
    )
    invoice_id = Column(
        Integer, ForeignKey("energy_invoices.id"), nullable=True, index=True,
        comment="Facture liee (optionnel, pour insights globaux)",
    )
    type = Column(
        String(50), nullable=False, index=True,
        comment="Type d'insight: overcharge, price_drift, shadow_gap, duplicate, missing_period...",
    )
    severity = Column(
        String(20), nullable=False, default="medium",
        comment="low, medium, high, critical",
    )
    message = Column(String(500), nullable=False, comment="Description humaine")
    metrics_json = Column(Text, nullable=True, comment="Metriques detaillees (JSON)")
    estimated_loss_eur = Column(
        Float, nullable=True,
        comment="Perte estimee en EUR",
    )
    recommended_actions_json = Column(
        Text, nullable=True,
        comment="Actions recommandees (JSON array)",
    )
    insight_status = Column(
        Enum(InsightStatus), default=InsightStatus.OPEN, nullable=False,
        comment="Statut workflow: open, ack, resolved, false_positive",
    )
    owner = Column(
        String(100), nullable=True,
        comment="Responsable assigne (email ou nom)",
    )
    notes = Column(
        Text, nullable=True,
        comment="Notes operateur (motif de resolution, etc.)",
    )

    # Relations
    site = relationship("Site", backref="billing_insights")
    invoice = relationship("EnergyInvoice", backref="billing_insights")


class ConceptAllocation(Base, TimestampMixin):
    """
    Allocation d'une ligne de facture a un concept de facturation.
    Chaque EnergyInvoiceLine peut avoir 1 ConceptAllocation.
    concept_id mappe vers BillingConcept (fourniture, acheminement, taxes, tva, ...).
    """
    __tablename__ = "concept_allocations"

    id = Column(Integer, primary_key=True, index=True)
    invoice_line_id = Column(
        Integer, ForeignKey("energy_invoice_lines.id"), nullable=False, index=True,
        comment="Ligne de facture allouee",
    )
    concept_id = Column(
        String(50), nullable=False, index=True,
        comment="Concept de facturation (fourniture, acheminement, taxes, tva, abonnement...)",
    )
    confidence = Column(
        Float, nullable=False, default=1.0,
        comment="Confiance de l'allocation (0.0-1.0)",
    )
    matched_rules_json = Column(
        Text, nullable=True,
        comment="Regles ayant contribue a l'allocation (JSON array)",
    )

    # Relations
    line = relationship("EnergyInvoiceLine", backref="allocations")


class BillingImportBatch(Base, TimestampMixin):
    """
    Batch d'import CSV avec hash de contenu pour idempotence.
    Un re-upload du meme fichier (meme org + meme hash) est rejete.
    """
    __tablename__ = "billing_import_batches"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer, nullable=True, index=True,
        comment="Organisation d'import (None si single-tenant)",
    )
    filename = Column(String(500), nullable=True, comment="Nom du fichier uploade")
    content_hash = Column(
        String(64), nullable=False, index=True,
        comment="SHA-256 du contenu CSV brut",
    )
    imported_at = Column(
        DateTime, default=datetime.utcnow, nullable=False,
        comment="Date d'import",
    )
    rows_total = Column(Integer, nullable=False, default=0)
    rows_inserted = Column(Integer, nullable=False, default=0)
    rows_skipped = Column(Integer, nullable=False, default=0)
    errors_json = Column(Text, nullable=True, comment="Erreurs d'import (JSON array)")
