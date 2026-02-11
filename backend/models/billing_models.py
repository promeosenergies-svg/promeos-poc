"""
PROMEOS — Bill Intelligence SQLAlchemy models
Persisted: EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight.
Complement the dataclass-based domain model in app/bill_intelligence/domain.py.
"""
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import BillingEnergyType, InvoiceLineType, BillingInvoiceStatus


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

    # Relations
    site = relationship("Site", backref="billing_insights")
    invoice = relationship("EnergyInvoice", backref="billing_insights")
