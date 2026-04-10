"""
PROMEOS — Contrats V2 : Cadre + Annexes Site
Tables : contrats_cadre, contract_annexes, contract_pricing,
         volume_commitments, contract_events.

Phase 1 (PRO-43): ContratCadre entity-level + AnnexeSite enrichi.
Backward-compatible: EnergyInvoice.contract_id FK preserved,
ContractAnnexe.contrat_cadre_id → energy_contracts preserved.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Numeric,
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
from .enums import ContractIndexation, ContractStatus, TariffOptionEnum, BillingEnergyType


# ---------------------------------------------------------------------------
# ContratCadre — contrat cadre entity-level (multi-sites)
# ---------------------------------------------------------------------------


class ContratCadre(Base, TimestampMixin, SoftDeleteMixin):
    """Contrat cadre au niveau entite juridique / organisation.

    Un ContratCadre couvre N sites via ses AnnexeSites.
    Prix par defaut HP/HC/base + poids + CEE + capacite.
    """

    __tablename__ = "contrats_cadre"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Rattachement hierarchique
    org_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        index=True,
        comment="Organisation signataire",
    )
    entite_juridique_id = Column(
        Integer,
        ForeignKey("entites_juridiques.id"),
        nullable=True,
        index=True,
        comment="Entite juridique signataire (si multi-entites)",
    )

    # Identification
    reference = Column(
        String(100),
        nullable=False,
        comment="Reference interne du contrat cadre (ex: CC-2025-001)",
    )
    reference_fournisseur = Column(
        String(100),
        nullable=True,
        comment="Reference chez le fournisseur",
    )
    fournisseur = Column(
        String(200),
        nullable=False,
        comment="Nom du fournisseur (EDF, Engie, TotalEnergies...)",
    )
    energie = Column(
        Enum(BillingEnergyType),
        nullable=False,
        comment="Type d'energie: elec / gaz",
    )

    # Dates
    date_signature = Column(Date, nullable=True, comment="Date de signature")
    date_debut = Column(Date, nullable=False, comment="Date debut de fourniture")
    date_fin = Column(Date, nullable=False, comment="Date fin de fourniture")
    date_preavis = Column(Date, nullable=True, comment="Date limite de preavis resiliation")
    notice_period_months = Column(Integer, nullable=True, comment="Preavis en mois")
    auto_renew = Column(Boolean, default=False, comment="Reconduction tacite")

    # Type de prix
    type_prix = Column(
        Enum(ContractIndexation),
        nullable=False,
        comment="Modele de prix: fixe/indexe/spot/tunnel/clic",
    )

    # Prix de reference (EUR HT/kWh) — defaut cadre, overridable par annexe
    # Numeric pour precision billing (eviter erreurs flottantes cumulees sur milliers kWh)
    prix_hp_eur_kwh = Column(Numeric(18, 6), nullable=True, comment="Prix HP EUR HT/kWh")
    prix_hc_eur_kwh = Column(Numeric(18, 6), nullable=True, comment="Prix HC EUR HT/kWh")
    prix_base_eur_kwh = Column(Numeric(18, 6), nullable=True, comment="Prix Base EUR HT/kWh (tarif unique)")

    # Poids HP/HC (repartition forfaitaire)
    poids_hp = Column(
        Float,
        nullable=True,
        default=62.0,
        comment="Poids HP en % (defaut 62% convention marche)",
    )
    poids_hc = Column(
        Float,
        nullable=True,
        default=38.0,
        comment="Poids HC en % (defaut 38% convention marche)",
    )

    # CEE (Certificats d'Economies d'Energie)
    cee_inclus = Column(
        Boolean,
        default=False,
        comment="True si CEE inclus dans le prix fourniture",
    )
    cee_eur_mwh = Column(
        Numeric(18, 6),
        nullable=True,
        comment="Prix CEE EUR/MWh (si facture separement)",
    )

    # Capacite (mecanisme de capacite)
    capacite_incluse = Column(
        Boolean,
        default=False,
        comment="True si capacite incluse dans le prix fourniture",
    )
    capacite_eur_mwh = Column(
        Numeric(18, 6),
        nullable=True,
        comment="Prix capacite EUR/MWh (si facture separement)",
    )

    # Indexation details (pour type tunnel/clic)
    indexation_reference = Column(
        String(100),
        nullable=True,
        comment="Index de reference (TRVE, EPEX_SPOT_FR, PEG_DA)",
    )
    indexation_spread_eur_mwh = Column(
        Numeric(18, 6),
        nullable=True,
        comment="Spread EUR/MWh par rapport a l'index",
    )
    prix_plancher_eur_mwh = Column(
        Numeric(18, 6),
        nullable=True,
        comment="Plancher prix EUR/MWh (tunnel)",
    )
    prix_plafond_eur_mwh = Column(
        Numeric(18, 6),
        nullable=True,
        comment="Plafond prix EUR/MWh (tunnel/cap)",
    )

    # Statut lifecycle
    statut = Column(
        Enum(ContractStatus),
        nullable=False,
        default=ContractStatus.DRAFT,
        comment="Statut lifecycle: draft/active/expiring/expired/terminated",
    )

    # Offre verte
    is_green = Column(Boolean, default=False, comment="Offre verte (GO)")
    green_percentage = Column(Float, nullable=True, comment="% couverture GO (0-100)")

    # Notes / metadata
    notes = Column(Text, nullable=True, comment="Notes libres")
    conditions_particulieres = Column(Text, nullable=True, comment="Conditions particulieres / derogations")
    document_url = Column(String(500), nullable=True, comment="Lien vers le PDF signe")

    # Relations
    organisation = relationship("Organisation")
    entite_juridique = relationship("EntiteJuridique")
    annexes = relationship(
        "ContractAnnexe",
        back_populates="cadre",
        cascade="all, delete-orphan",
        foreign_keys="ContractAnnexe.cadre_id",
    )


# ---------------------------------------------------------------------------
# ContractAnnexe — annexe site d'un contrat cadre
# ---------------------------------------------------------------------------


class ContractAnnexe(Base, TimestampMixin, SoftDeleteMixin):
    """Annexe site = conditions specifiques par site/PDL rattachees a un contrat cadre.

    Supporte deux FK parent:
    - cadre_id → contrats_cadre (nouveau, Phase 1)
    - contrat_cadre_id → energy_contracts (legacy, backward-compatible)
    """

    __tablename__ = "contract_annexes"
    __table_args__ = (
        UniqueConstraint("contrat_cadre_id", "site_id", name="uq_annexe_cadre_site"),
        UniqueConstraint("cadre_id", "site_id", name="uq_annexe_cadre_v2_site"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK vers ContratCadre (nouveau)
    cadre_id = Column(
        Integer,
        ForeignKey("contrats_cadre.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Contrat cadre parent (Phase 1)",
    )

    # FK legacy vers EnergyContract (backward-compatible, a deprecier)
    contrat_cadre_id = Column(
        Integer,
        ForeignKey("energy_contracts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Contrat cadre parent legacy (EnergyContract)",
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

    # Identifiants reseau (PRM / PCE)
    prm = Column(String(14), nullable=True, comment="PRM elec (14 chiffres)")
    pce = Column(String(14), nullable=True, comment="PCE gaz (14 chiffres)")

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

    # Prix override (si has_price_override=True) — Numeric pour precision billing
    prix_hp_override = Column(Numeric(18, 6), nullable=True, comment="Prix HP override EUR HT/kWh")
    prix_hc_override = Column(Numeric(18, 6), nullable=True, comment="Prix HC override EUR HT/kWh")
    prix_base_override = Column(Numeric(18, 6), nullable=True, comment="Prix Base override EUR HT/kWh")

    # Dates specifiques (null = herite du cadre)
    start_date_override = Column(Date, nullable=True, comment="Date debut override")
    end_date_override = Column(Date, nullable=True, comment="Date fin override")

    # Volume engage (au niveau annexe)
    volume_engage_kwh = Column(Numeric(20, 3), nullable=True, comment="Volume annuel engage kWh")

    # Status annexe
    status = Column(
        Enum(ContractStatus),
        nullable=True,
        default=ContractStatus.ACTIVE,
        comment="Statut lifecycle annexe",
    )

    # Relations
    cadre = relationship(
        "ContratCadre",
        back_populates="annexes",
        foreign_keys=[cadre_id],
    )
    contrat_cadre = relationship(
        "EnergyContract",
        back_populates="annexes",
        foreign_keys=[contrat_cadre_id],
    )
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


# ---------------------------------------------------------------------------
# ContractPricing — grille tarifaire structuree
# ---------------------------------------------------------------------------


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
    unit_price_eur_kwh = Column(Numeric(18, 6), nullable=True, comment="Prix unitaire EUR HT/kWh")
    subscription_eur_month = Column(Numeric(14, 2), nullable=True, comment="Abonnement EUR HT/mois")
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


# ---------------------------------------------------------------------------
# VolumeCommitment — engagement de volume par annexe
# ---------------------------------------------------------------------------


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

    annual_kwh = Column(Numeric(20, 3), nullable=False, comment="Volume engage MWh/an (en kWh)")
    tolerance_pct_up = Column(Float, default=10.0, comment="Tolerance haute %")
    tolerance_pct_down = Column(Float, default=10.0, comment="Tolerance basse %")
    penalty_eur_kwh_above = Column(Numeric(18, 6), nullable=True, comment="Penalite depassement EUR/kWh")
    penalty_eur_kwh_below = Column(Numeric(18, 6), nullable=True, comment="Penalite sous-conso EUR/kWh")

    # Relations
    annexe = relationship("ContractAnnexe", back_populates="volume_commitment")


# ---------------------------------------------------------------------------
# ContractEvent — evenement lifecycle
# ---------------------------------------------------------------------------


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
