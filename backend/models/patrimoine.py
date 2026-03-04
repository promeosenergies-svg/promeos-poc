"""
PROMEOS — Patrimoine models (DIAMANT)
N-N link tables + Staging pipeline + Quality findings + DeliveryPoint.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import (
    StagingStatus,
    ImportSourceType,
    QualityRuleSeverity,
    ActivationLogStatus,
    DeliveryPointStatus,
    DeliveryPointEnergyType,
)


# ========================================
# N-N Link Tables
# ========================================


class OrgEntiteLink(Base, TimestampMixin):
    """N-N: une organisation peut avoir N entites juridiques, et inversement."""

    __tablename__ = "org_entite_links"
    __table_args__ = (UniqueConstraint("organisation_id", "entite_juridique_id", name="uq_org_entite"),)

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    entite_juridique_id = Column(Integer, ForeignKey("entites_juridiques.id"), nullable=False, index=True)
    role = Column(String(50), nullable=True, comment="proprietaire, gestionnaire, locataire")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    confidence = Column(Float, default=1.0, comment="Confiance du lien 0-1")
    source_ref = Column(String(200), nullable=True, comment="Reference source (facture, contrat)")


class PortfolioEntiteLink(Base, TimestampMixin):
    """N-N: un portefeuille peut etre lie a N entites juridiques."""

    __tablename__ = "portfolio_entite_links"
    __table_args__ = (UniqueConstraint("portefeuille_id", "entite_juridique_id", name="uq_portfolio_entite"),)

    id = Column(Integer, primary_key=True)
    portefeuille_id = Column(Integer, ForeignKey("portefeuilles.id"), nullable=False, index=True)
    entite_juridique_id = Column(Integer, ForeignKey("entites_juridiques.id"), nullable=False, index=True)
    role = Column(String(50), nullable=True)


# ========================================
# Staging Pipeline
# ========================================


class StagingBatch(Base, TimestampMixin):
    """Un batch d'import patrimoine (CSV, Excel, factures, manuel)."""

    __tablename__ = "staging_batches"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(StagingStatus), default=StagingStatus.DRAFT, nullable=False)
    source_type = Column(Enum(ImportSourceType), nullable=False)
    filename = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    mode = Column(String(20), nullable=True, comment="express, import, assiste, demo")
    stats_json = Column(Text, nullable=True)
    error_json = Column(Text, nullable=True)

    # Relations
    sites = relationship("StagingSite", back_populates="batch", cascade="all, delete-orphan")
    compteurs = relationship("StagingCompteur", back_populates="batch", cascade="all, delete-orphan")
    findings = relationship("QualityFinding", back_populates="batch", cascade="all, delete-orphan")


class StagingSite(Base, TimestampMixin):
    """Site en staging (pas encore active en base finale)."""

    __tablename__ = "staging_sites"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("staging_batches.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=True, comment="Ligne dans le fichier source")
    nom = Column(String(200), nullable=False)
    type_site = Column(String(50), nullable=True)
    adresse = Column(String(300), nullable=True)
    code_postal = Column(String(10), nullable=True)
    ville = Column(String(100), nullable=True)
    surface_m2 = Column(Float, nullable=True)
    siret = Column(String(14), nullable=True)
    naf_code = Column(String(5), nullable=True)
    # Lineage
    source_type = Column(String(20), nullable=True)
    source_ref = Column(String(200), nullable=True)
    # Mapping (set during correction step)
    target_site_id = Column(Integer, nullable=True, comment="Merge avec un site existant")
    target_portefeuille_id = Column(Integer, nullable=True)
    skip = Column(Boolean, default=False, comment="Ignore par l'utilisateur")

    # Relations
    batch = relationship("StagingBatch", back_populates="sites")
    compteurs = relationship("StagingCompteur", back_populates="staging_site")


class StagingCompteur(Base, TimestampMixin):
    """Compteur en staging."""

    __tablename__ = "staging_compteurs"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("staging_batches.id"), nullable=False, index=True)
    staging_site_id = Column(Integer, ForeignKey("staging_sites.id"), nullable=True)
    row_number = Column(Integer, nullable=True)
    numero_serie = Column(String(50), nullable=True)
    meter_id = Column(String(14), nullable=True, comment="PRM/PDL/PCE")
    type_compteur = Column(String(20), nullable=True, comment="electricite, gaz, eau")
    puissance_kw = Column(Float, nullable=True)
    # Mapping
    target_site_id = Column(Integer, nullable=True)
    target_compteur_id = Column(Integer, nullable=True, comment="Merge avec compteur existant")
    skip = Column(Boolean, default=False)

    # Relations
    batch = relationship("StagingBatch", back_populates="compteurs")
    staging_site = relationship("StagingSite", back_populates="compteurs")


class QualityFinding(Base, TimestampMixin):
    """Resultat d'une regle de qualite sur un batch staging."""

    __tablename__ = "quality_findings"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("staging_batches.id"), nullable=False, index=True)
    rule_id = Column(String(50), nullable=False, comment="dup_site, dup_meter, orphan_meter, etc.")
    severity = Column(Enum(QualityRuleSeverity), nullable=False)
    staging_site_id = Column(Integer, nullable=True)
    staging_compteur_id = Column(Integer, nullable=True)
    evidence_json = Column(Text, nullable=True)
    suggested_action = Column(String(200), nullable=True, comment="merge, skip, fix_address")
    resolved = Column(Boolean, default=False)
    resolution = Column(String(200), nullable=True)

    # Relations
    batch = relationship("StagingBatch", back_populates="findings")


# ========================================
# Activation audit log
# ========================================


class ActivationLog(Base, TimestampMixin):
    """Audit trail for batch activation attempts."""

    __tablename__ = "activation_logs"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("staging_batches.id"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(Enum(ActivationLogStatus), nullable=False)
    error_message = Column(Text, nullable=True)
    sites_created = Column(Integer, default=0)
    compteurs_created = Column(Integer, default=0)
    activation_hash = Column(String(64), nullable=True, index=True)
    user_id = Column(Integer, nullable=True)


# ========================================
# Delivery Point (PRM/PCE)
# ========================================


class DeliveryPoint(Base, TimestampMixin, SoftDeleteMixin):
    """Point de livraison energie (PRM elec / PCE gaz).

    Entite autonome representant un contrat de raccordement reseau.
    Un DeliveryPoint est lie a un Site et peut etre associe a N Compteurs.
    """

    __tablename__ = "delivery_points"

    id = Column(Integer, primary_key=True)
    code = Column(String(14), nullable=False, index=True, comment="PRM ou PCE (14 digits)")
    energy_type = Column(
        Enum(DeliveryPointEnergyType),
        nullable=True,
        comment="elec (PRM) ou gaz (PCE)",
    )
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    status = Column(
        Enum(DeliveryPointStatus),
        default=DeliveryPointStatus.ACTIVE,
        nullable=False,
    )

    # Data lineage (coherent with Site/Compteur)
    data_source = Column(String(20), nullable=True, comment="csv, manual, demo, api")
    data_source_ref = Column(String(200), nullable=True, comment="Batch ID or filename")
    imported_at = Column(DateTime, nullable=True)
    imported_by = Column(Integer, nullable=True)

    # Relations
    site = relationship("Site", back_populates="delivery_points")
    compteurs = relationship("Compteur", back_populates="delivery_point")
