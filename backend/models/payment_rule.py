"""
PROMEOS — V96 PaymentRule model
Matrice Facturé / Payeur / Centre de coûts.
3-level hierarchy: portefeuille > site > contrat.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import PaymentRuleLevel


class PaymentRule(Base, TimestampMixin):
    """
    Règle de paiement à 3 niveaux (portefeuille, site, contrat).
    Résolution en cascade : contrat > site > portefeuille.
    """

    __tablename__ = "payment_rules"
    __table_args__ = (
        UniqueConstraint(
            "level",
            "portefeuille_id",
            "site_id",
            "contract_id",
            name="uq_payment_rule_scope",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    level = Column(
        Enum(PaymentRuleLevel),
        nullable=False,
        comment="Niveau d'application (portefeuille/site/contrat)",
    )
    portefeuille_id = Column(
        Integer,
        ForeignKey("portefeuilles.id"),
        nullable=True,
        index=True,
        comment="Portefeuille cible (si level=portefeuille)",
    )
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=True,
        index=True,
        comment="Site cible (si level=site)",
    )
    contract_id = Column(
        Integer,
        ForeignKey("energy_contracts.id"),
        nullable=True,
        index=True,
        comment="Contrat cible (si level=contrat)",
    )
    invoice_entity_id = Column(
        Integer,
        ForeignKey("entites_juridiques.id"),
        nullable=False,
        comment="Entité juridique facturée (qui reçoit la facture)",
    )
    payer_entity_id = Column(
        Integer,
        ForeignKey("entites_juridiques.id"),
        nullable=True,
        comment="Entité juridique payeuse (si différente du facturé)",
    )
    cost_center = Column(
        String(100),
        nullable=True,
        comment="Centre de coûts / imputation analytique",
    )

    # Relations
    portefeuille = relationship("Portefeuille", foreign_keys=[portefeuille_id])
    site = relationship("Site", foreign_keys=[site_id])
    contract = relationship("EnergyContract", foreign_keys=[contract_id])
    invoice_entity = relationship("EntiteJuridique", foreign_keys=[invoice_entity_id])
    payer_entity = relationship("EntiteJuridique", foreign_keys=[payer_entity_id])
