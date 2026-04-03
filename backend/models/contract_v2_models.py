"""
PROMEOS — Contrats V2 : Cadre + Annexes Site
Tables : contract_annexes, contract_pricing, volume_commitments, contract_events.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    ForeignKey,
    Date,
    Enum,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import ContractStatus, TariffOptionEnum


class ContractAnnexe(Base, TimestampMixin, SoftDeleteMixin):
    """Annexe site = conditions specifiques par site/PDL rattachees a un contrat cadre."""

    __tablename__ = "contract_annexes"
    __table_args__ = (UniqueConstraint("contrat_cadre_id", "site_id", name="uq_annexe_cadre_site"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    contrat_cadre_id = Column(
        Integer,
        ForeignKey("energy_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Contrat cadre parent",
    )
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        index=True,
        comment="Site concerne par cette annexe",
    )
    delivery_point_id = Column(
        Integer,
        ForeignKey("delivery_points.id"),
        nullable=True,
        comment="PDL specifique (optionnel)",
    )
    annexe_ref = Column(String(100), nullable=True, comment="Reference annexe (ex: ANX-Paris-001)")

    # Donnees specifiques site (peuvent differer du cadre)
    tariff_option = Column(
        Enum(TariffOptionEnum),
        nullable=True,
        comment="Option tarifaire: base/hp_hc/cu/mu/lu",
    )
    subscribed_power_kva = Column(Float, nullable=True, comment="Puissance souscrite kVA")
    segment_enedis = Column(String(10), nullable=True, comment="Segment: C5/C4/C3/C2/C1")

    # Override prix (null = herite du cadre)
    has_price_override = Column(Boolean, default=False, comment="True si prix differents du cadre")
    override_pricing_model = Column(String(30), nullable=True, comment="Modele prix override (null = herite)")

    # Dates specifiques (null = herite du cadre)
    start_date_override = Column(Date, nullable=True, comment="Date debut override")
    end_date_override = Column(Date, nullable=True, comment="Date fin override")

    # Status annexe
    status = Column(
        Enum(ContractStatus),
        nullable=True,
        default="active",
        comment="Statut lifecycle annexe",
    )

    # Relations
    contrat_cadre = relationship("EnergyContract", back_populates="annexes")
    site = relationship("Site")
    delivery_point = relationship("DeliveryPoint")
    volume_commitment = relationship(
        "VolumeCommitment",
        back_populates="annexe",
        uselist=False,
        cascade="all, delete-orphan",
    )
    pricing_overrides = relationship(
        "ContractPricing",
        back_populates="annexe",
        cascade="all, delete-orphan",
        foreign_keys="ContractPricing.annexe_id",
    )


class ContractPricing(Base, TimestampMixin):
    """Grille tarifaire structuree — rattachee au cadre (base) OU a une annexe (override)."""

    __tablename__ = "contract_pricing"
    __table_args__ = (
        CheckConstraint(
            "(contract_id IS NOT NULL AND annexe_id IS NULL) OR (contract_id IS NULL AND annexe_id IS NOT NULL)",
            name="ck_pricing_one_parent",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(
        Integer,
        ForeignKey("energy_contracts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Contrat cadre (tarifs de base)",
    )
    annexe_id = Column(
        Integer,
        ForeignKey("contract_annexes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Annexe (tarifs override)",
    )

    period_code = Column(
        String(10),
        nullable=False,
        comment="BASE/HP/HC/HPH/HCH/HPB/HCB/POINTE",
    )
    season = Column(String(10), default="ANNUEL", comment="ANNUEL/HIVER/ETE")
    unit_price_eur_kwh = Column(Float, nullable=True, comment="Prix unitaire EUR HT/kWh")
    subscription_eur_month = Column(Float, nullable=True, comment="Abonnement EUR HT/mois")
    effective_from = Column(Date, nullable=True, comment="Date debut validite")
    effective_to = Column(Date, nullable=True, comment="Date fin validite")

    # Relations
    contract = relationship(
        "EnergyContract",
        back_populates="pricing_lines",
        foreign_keys=[contract_id],
    )
    annexe = relationship(
        "ContractAnnexe",
        back_populates="pricing_overrides",
        foreign_keys=[annexe_id],
    )


class VolumeCommitment(Base, TimestampMixin):
    """Engagement de volume par annexe site."""

    __tablename__ = "volume_commitments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annexe_id = Column(
        Integer,
        ForeignKey("contract_annexes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Annexe concernee",
    )

    annual_kwh = Column(Float, nullable=False, comment="Volume engage MWh/an (en kWh)")
    tolerance_pct_up = Column(Float, default=10.0, comment="Tolerance haute %")
    tolerance_pct_down = Column(Float, default=10.0, comment="Tolerance basse %")
    penalty_eur_kwh_above = Column(Float, nullable=True, comment="Penalite depassement EUR/kWh")
    penalty_eur_kwh_below = Column(Float, nullable=True, comment="Penalite sous-conso EUR/kWh")

    # Relations
    annexe = relationship("ContractAnnexe", back_populates="volume_commitment")


class ContractEvent(Base, TimestampMixin):
    """Evenement lifecycle d'un contrat cadre."""

    __tablename__ = "contract_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(
        Integer,
        ForeignKey("energy_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Contrat cadre concerne",
    )
    event_type = Column(
        String(30),
        nullable=False,
        comment="CREATION/AVENANT/REVISION/RESILIATION/CESSION/TRANSFER/RENOUVELLEMENT",
    )
    event_date = Column(Date, nullable=False, comment="Date de l'evenement")
    description = Column(String(500), nullable=True, comment="Description libre")
    meta_json = Column(Text, nullable=True, comment="Metadata JSON supplementaire")

    # Relations
    contract = relationship("EnergyContract", back_populates="events")
