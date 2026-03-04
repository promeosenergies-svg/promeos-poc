"""
PROMEOS — Achat Energie SQLAlchemy models
PurchaseAssumptionSet, PurchasePreference, PurchaseScenarioResult.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import BillingEnergyType, PurchaseStrategy, PurchaseRecoStatus


class PurchaseAssumptionSet(Base, TimestampMixin):
    """
    Hypotheses de simulation d'achat energie pour un site.
    Volume, profil, horizon, parametres libres.
    """

    __tablename__ = "purchase_assumption_sets"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        index=True,
        comment="Site concerne",
    )
    energy_type = Column(
        Enum(BillingEnergyType),
        nullable=False,
        default=BillingEnergyType.ELEC,
        comment="Type d'energie (elec/gaz)",
    )
    volume_kwh_an = Column(
        Float,
        nullable=False,
        default=0,
        comment="Consommation annuelle estimee (kWh)",
    )
    profile_factor = Column(
        Float,
        nullable=False,
        default=1.0,
        comment="Facteur de profil (P/Pmoy). >1 = profil pointe, <1 = profil plat",
    )
    horizon_months = Column(
        Integer,
        nullable=False,
        default=24,
        comment="Duree du contrat simule (mois)",
    )
    assumptions_json = Column(
        Text,
        nullable=True,
        comment="Hypotheses libres (JSON): inflation, ARENH, etc.",
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    site = relationship("Site", backref="purchase_assumptions")
    scenario_results = relationship(
        "PurchaseScenarioResult",
        back_populates="assumption_set",
        cascade="all, delete-orphan",
    )


class PurchasePreference(Base, TimestampMixin):
    """
    Preferences utilisateur pour le scoring des scenarios d'achat.
    Une preference par organisation.
    """

    __tablename__ = "purchase_preferences"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="Organisation (None si single-tenant)",
    )
    risk_tolerance = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="Tolerance au risque: low, medium, high",
    )
    budget_priority = Column(
        Float,
        nullable=False,
        default=0.5,
        comment="Poids prix vs risque (0=risque, 1=prix)",
    )
    green_preference = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Preference offre verte",
    )
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PurchaseScenarioResult(Base, TimestampMixin):
    """
    Resultat d'une simulation de scenario d'achat.
    Un PurchaseAssumptionSet peut avoir N resultats (1 par strategie).
    """

    __tablename__ = "purchase_scenario_results"
    __table_args__ = (UniqueConstraint("run_id", "strategy", name="uq_run_strategy"),)

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        String(36),
        nullable=True,
        index=True,
        comment="UUID unique du run de calcul",
    )
    batch_id = Column(
        String(36),
        nullable=True,
        index=True,
        comment="UUID du batch portfolio (multi-site)",
    )
    inputs_hash = Column(
        String(64),
        nullable=True,
        comment="SHA-256 des hypotheses pour comparaison inter-runs",
    )
    assumption_set_id = Column(
        Integer,
        ForeignKey("purchase_assumption_sets.id"),
        nullable=False,
        index=True,
        comment="Jeu d'hypotheses parent",
    )
    strategy = Column(
        Enum(PurchaseStrategy),
        nullable=False,
        comment="Strategie: fixe, indexe, spot",
    )
    price_eur_per_kwh = Column(
        Float,
        nullable=False,
        comment="Prix moyen EUR HT/kWh",
    )
    total_annual_eur = Column(
        Float,
        nullable=False,
        comment="Cout annuel total EUR HT",
    )
    risk_score = Column(
        Float,
        nullable=False,
        default=50,
        comment="Score de risque 0-100 (100 = max risque)",
    )
    savings_vs_current_pct = Column(
        Float,
        nullable=True,
        comment="Economies vs prix actuel (%)",
    )
    p10_eur = Column(
        Float,
        nullable=True,
        comment="Borne basse P10 du cout annuel EUR",
    )
    p90_eur = Column(
        Float,
        nullable=True,
        comment="Borne haute P90 du cout annuel EUR",
    )
    detail_json = Column(
        Text,
        nullable=True,
        comment="Breakdown mensuel (JSON)",
    )
    is_recommended = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Scenario recommande par l'algo",
    )
    reco_status = Column(
        Enum(PurchaseRecoStatus),
        default=PurchaseRecoStatus.DRAFT,
        nullable=False,
        comment="Statut de la recommandation: draft, accepted, rejected",
    )
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    assumption_set = relationship("PurchaseAssumptionSet", back_populates="scenario_results")
