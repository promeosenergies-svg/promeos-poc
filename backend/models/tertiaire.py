"""
PROMEOS V39 - Modeles Tertiaire / OPERAT (Decret tertiaire)
EFA = Entite Fonctionnelle Assujettie
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Text,
    ForeignKey,
    Enum,
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

    # Relations
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
