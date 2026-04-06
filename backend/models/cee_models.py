"""
PROMEOS - V69 CEE Pipeline + M&V Models
WorkPackage: lot de travaux S/M/L par site.
CeeDossier: dossier CEE (statut + étapes kanban) lié aux actions.
CeeDossierEvidence: preuves auto-créées pour un dossier CEE.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    Boolean,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import (
    WorkPackageSize,
    CeeDossierStep,
    CeeStatus,
    StatutEvidence,
    MVAlertType,
)


class WorkPackage(Base, TimestampMixin):
    """
    Lot de travaux (S/M/L) pour un site.
    Chaque package peut mener à un dossier CEE.
    """

    __tablename__ = "work_packages"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        index=True,
    )
    label = Column(String(300), nullable=False, comment="Nom du lot")
    size = Column(
        SAEnum(WorkPackageSize),
        nullable=False,
        default=WorkPackageSize.M,
        comment="Taille: S, M, L",
    )
    capex_eur = Column(Float, nullable=True, comment="CAPEX estimé EUR")
    savings_eur_year = Column(Float, nullable=True, comment="Économies annuelles estimées EUR")
    payback_years = Column(Float, nullable=True, comment="Payback en années")
    complexity = Column(
        String(20),
        nullable=True,
        default="medium",
        comment="Complexité: low, medium, high",
    )
    cee_status = Column(
        SAEnum(CeeStatus),
        nullable=False,
        default=CeeStatus.A_QUALIFIER,
        comment="Statut CEE: a_qualifier, ok, non",
    )
    fiche_ref = Column(
        String(20),
        nullable=True,
        comment="Code fiche CEE (ex: BAT-EN-101)",
    )
    description = Column(Text, nullable=True)

    # Relations
    site = relationship("Site", backref="work_packages")
    cee_dossier = relationship("CeeDossier", back_populates="work_package", uselist=False)


class CeeDossier(Base, TimestampMixin):
    """
    Dossier CEE associé à un work package.
    Kanban steps: devis → engagement → travaux → pv_photos → mv → versement.
    Lié à des actions Action Center via action_ids.
    """

    __tablename__ = "cee_dossiers"

    id = Column(Integer, primary_key=True, index=True)
    work_package_id = Column(
        Integer,
        ForeignKey("work_packages.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        index=True,
    )
    current_step = Column(
        SAEnum(CeeDossierStep),
        nullable=False,
        default=CeeDossierStep.DEVIS,
        comment="Étape kanban courante",
    )
    amount_cee_kwh = Column(Float, nullable=True, comment="Volume CEE estimé en kWh cumac")
    amount_cee_eur = Column(Float, nullable=True, comment="Prime CEE estimée en EUR")
    obliged_party = Column(String(200), nullable=True, comment="Obligé choisi")
    action_ids_json = Column(
        Text,
        nullable=True,
        comment="JSON array of action_item IDs linked to this dossier",
    )

    # Relations
    work_package = relationship("WorkPackage", back_populates="cee_dossier")
    site = relationship("Site", backref="cee_dossiers")
    evidence_items = relationship("CeeDossierEvidence", back_populates="dossier")


class CeeDossierEvidence(Base, TimestampMixin):
    """
    Pièce justificative auto-créée lors de la création du dossier CEE.
    Alimente le coffre de preuves du site.
    """

    __tablename__ = "cee_dossier_evidences"

    id = Column(Integer, primary_key=True, index=True)
    dossier_id = Column(
        Integer,
        ForeignKey("cee_dossiers.id"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        index=True,
    )
    label = Column(String(300), nullable=False, comment="Nom de la pièce")
    type_key = Column(
        String(50),
        nullable=False,
        comment="Type: devis, pv_reception, photos_chantier, rapport_mv, attestation_fin, facture_travaux",
    )
    statut = Column(
        SAEnum(StatutEvidence),
        nullable=False,
        default=StatutEvidence.MANQUANT,
    )
    owner = Column(String(100), nullable=True, comment="Responsable de la pièce")
    due_date = Column(Date, nullable=True, comment="Date limite")
    file_url = Column(String(1000), nullable=True)
    evidence_id = Column(
        Integer,
        ForeignKey("evidences.id"),
        nullable=True,
        comment="Lien vers Evidence du coffre site (auto-créé)",
    )

    # Relations
    dossier = relationship("CeeDossier", back_populates="evidence_items")
    site = relationship("Site")
