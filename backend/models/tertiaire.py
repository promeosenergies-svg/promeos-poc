"""
PROMEOS V39 - Modeles Tertiaire / OPERAT (Decret tertiaire)
EFA = Entite Fonctionnelle Assujettie
"""

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Text,
    ForeignKey,
    Enum,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import (
    EfaStatut,
    EfaRole,
    DeclarationStatus,
    PerimeterEventType,
    DataQualityIssueSeverity,
    DataQualityIssueStatus,
)


class TertiaireEfa(Base, TimestampMixin, SoftDeleteMixin):
    """Entite Fonctionnelle Assujettie au Decret tertiaire."""

    __tablename__ = "tertiaire_efa"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)
    nom = Column(String(300), nullable=False)
    statut = Column(Enum(EfaStatut), default=EfaStatut.DRAFT, nullable=False)
    role_assujetti = Column(Enum(EfaRole), default=EfaRole.PROPRIETAIRE, nullable=False)
    reporting_start = Column(Date, nullable=True)
    reporting_end = Column(Date, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Trajectoire OPERAT
    reference_year = Column(Integer, nullable=True, comment="Annee de reference (ex: 2010)")
    reference_year_kwh = Column(Float, nullable=True, comment="Conso reference verrouillée (kWh)")
    trajectory_status = Column(String(20), nullable=True, comment="on_track / off_track / not_evaluable")
    trajectory_last_calculated_at = Column(DateTime, nullable=True)

    # Relations
    consumptions = relationship("TertiaireEfaConsumption", back_populates="efa", cascade="all, delete-orphan")
    buildings = relationship("TertiaireEfaBuilding", back_populates="efa", cascade="all, delete-orphan")
    responsibilities = relationship("TertiaireResponsibility", back_populates="efa", cascade="all, delete-orphan")
    events = relationship("TertiairePerimeterEvent", back_populates="efa", cascade="all, delete-orphan")
    declarations = relationship("TertiaireDeclaration", back_populates="efa", cascade="all, delete-orphan")
    proof_artifacts = relationship("TertiaireProofArtifact", back_populates="efa", cascade="all, delete-orphan")
    quality_issues = relationship("TertiaireDataQualityIssue", back_populates="efa", cascade="all, delete-orphan")


class TertiaireEfaLink(Base, TimestampMixin):
    """Lien entre EFA (turnover, scission, fusion)."""

    __tablename__ = "tertiaire_efa_link"

    id = Column(Integer, primary_key=True, index=True)
    child_efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    parent_efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    reason = Column(String(100), nullable=False)


class TertiaireEfaBuilding(Base, TimestampMixin):
    """Association EFA <-> Batiment avec usage et surface."""

    __tablename__ = "tertiaire_efa_building"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    building_id = Column(Integer, ForeignKey("batiments.id"), nullable=True, index=True)
    usage_label = Column(String(200), nullable=True)
    surface_m2 = Column(Float, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="buildings")


class TertiaireResponsibility(Base, TimestampMixin):
    """Responsabilite d'un acteur sur une EFA."""

    __tablename__ = "tertiaire_responsibility"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    role = Column(Enum(EfaRole), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_value = Column(String(300), nullable=True)
    contact_email = Column(String(300), nullable=True)
    scope_json = Column(Text, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="responsibilities")


class TertiairePerimeterEvent(Base, TimestampMixin):
    """Evenement de perimetre EFA (changement occupant, vacance, renovation, etc.)."""

    __tablename__ = "tertiaire_perimeter_event"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    type = Column(Enum(PerimeterEventType), nullable=False)
    effective_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    justification = Column(Text, nullable=True)
    attachments_json = Column(Text, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="events")


class TertiaireDeclaration(Base, TimestampMixin):
    """Declaration annuelle OPERAT pour une EFA."""

    __tablename__ = "tertiaire_declaration"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    status = Column(Enum(DeclarationStatus), default=DeclarationStatus.DRAFT, nullable=False)
    checklist_json = Column(Text, nullable=True)
    exported_pack_path = Column(String(500), nullable=True)

    efa = relationship("TertiaireEfa", back_populates="declarations")


class TertiaireProofArtifact(Base, TimestampMixin):
    """Preuve documentaire liee a une EFA (pont vers Memobox via kb_doc_id)."""

    __tablename__ = "tertiaire_proof_artifact"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=True)
    kb_doc_id = Column(String(200), nullable=True)
    owner_role = Column(Enum(EfaRole), nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    tags_json = Column(Text, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="proof_artifacts")


class TertiaireDataQualityIssue(Base, TimestampMixin):
    """Issue de qualite de donnees pour une EFA / annee."""

    __tablename__ = "tertiaire_data_quality_issue"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    year = Column(Integer, nullable=True)
    code = Column(String(100), nullable=False)
    severity = Column(Enum(DataQualityIssueSeverity), nullable=False)
    message_fr = Column(Text, nullable=False)
    impact_fr = Column(Text, nullable=True)
    action_fr = Column(Text, nullable=True)
    status = Column(Enum(DataQualityIssueStatus), default=DataQualityIssueStatus.OPEN, nullable=False)
    proof_required_json = Column(Text, nullable=True)
    proof_owner_role = Column(String(100), nullable=True)

    efa = relationship("TertiaireEfa", back_populates="quality_issues")


class TertiaireEfaConsumption(Base, TimestampMixin):
    """Consommation energetique annuelle d'une EFA — base de la trajectoire OPERAT."""

    __tablename__ = "tertiaire_efa_consumption"
    __table_args__ = (UniqueConstraint("efa_id", "year", name="uq_efa_consumption_year"),)

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False, comment="Annee de la consommation")
    kwh_total = Column(Float, nullable=False, comment="Consommation totale (kWh)")
    kwh_elec = Column(Float, nullable=True, comment="Part electricite (kWh)")
    kwh_gaz = Column(Float, nullable=True, comment="Part gaz (kWh)")
    kwh_reseau = Column(Float, nullable=True, comment="Part reseau chaleur/froid (kWh)")
    is_reference = Column(Boolean, default=False, nullable=False, comment="True si annee de reference")
    is_normalized = Column(Boolean, default=False, nullable=False, comment="True si normalise climatiquement")
    source = Column(
        String(50), nullable=True, comment="declared_manual, import_invoice, site_fallback, inferred, unknown"
    )
    reliability = Column(String(20), nullable=True, default="unverified", comment="high, medium, low, unverified")

    # Normalisation climatique
    normalized_kwh_total = Column(Float, nullable=True, comment="Conso normalisee climatiquement (kWh)")
    normalization_method = Column(String(50), nullable=True, comment="dju_ratio, none")
    normalization_confidence = Column(String(20), nullable=True, comment="high, medium, low, none")
    dju_heating = Column(Float, nullable=True, comment="Degres-jours unifies chauffage")
    dju_cooling = Column(Float, nullable=True, comment="Degres-jours unifies climatisation")
    dju_reference = Column(Float, nullable=True, comment="DJU reference (moyenne 30 ans)")
    weather_data_source = Column(String(100), nullable=True, comment="meteo_france, manual, estimated")
    normalized_at = Column(DateTime, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="consumptions")
