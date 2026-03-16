"""
PROMEOS - Modeles BACS Expert (Decret n°2020-887)
4 modeles: BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import (
    CvcSystemType,
    CvcArchitecture,
    BacsTriggerReason,
    InspectionStatus,
)


class BacsAsset(Base, TimestampMixin, SoftDeleteMixin):
    """
    Actif BACS lie a un site.
    Porte les donnees d'eligibilite: tertiaire, date PC, renouvellement, responsable.
    """

    __tablename__ = "bacs_assets"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        index=True,
        comment="Site rattache",
    )
    building_id = Column(
        Integer,
        ForeignKey("batiments.id"),
        nullable=True,
        index=True,
        comment="Batiment specifique (optionnel)",
    )
    is_tertiary_non_residential = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Batiment tertiaire non-residentiel (critere d'eligibilite)",
    )
    pc_date = Column(
        Date,
        nullable=True,
        comment="Date du permis de construire",
    )
    renewal_events_json = Column(
        Text,
        nullable=True,
        default="[]",
        comment='JSON: [{"date":"2024-01-15","system":"heating","kw":200}]',
    )
    responsible_party_json = Column(
        Text,
        nullable=True,
        default="{}",
        comment='JSON: {"type":"owner","name":"...","siren":"..."}',
    )

    # Statut perimetre BACS
    bacs_scope_status = Column(
        String(30),
        nullable=True,
        comment="not_applicable, potentially_in_scope, in_scope_incomplete, review_required, ready_for_internal_review",
    )
    bacs_scope_reason = Column(String(200), nullable=True)

    # Relations
    site = relationship("Site", backref="bacs_assets")
    building = relationship("Batiment", backref="bacs_assets")
    cvc_systems = relationship(
        "BacsCvcSystem",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    assessments = relationship(
        "BacsAssessment",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    inspections = relationship(
        "BacsInspection",
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class BacsCvcSystem(Base, TimestampMixin):
    """
    Systeme CVC inventorie pour un actif BACS.
    Type (chauffage/clim/ventilation) + architecture (cascade/reseau/independant)
    + unites kW → sert au calcul Putile.
    """

    __tablename__ = "bacs_cvc_systems"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer,
        ForeignKey("bacs_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Actif BACS parent",
    )
    system_type = Column(
        SAEnum(CvcSystemType),
        nullable=False,
        comment="Type CVC: heating, cooling, ventilation",
    )
    architecture = Column(
        SAEnum(CvcArchitecture),
        nullable=False,
        comment="Architecture: cascade, network, independent",
    )
    units_json = Column(
        Text,
        nullable=False,
        default="[]",
        comment='JSON: [{"label":"PAC 1","kw":150},{"label":"PAC 2","kw":100}]',
    )
    putile_kw_computed = Column(
        Float,
        nullable=True,
        comment="Puissance utile calculee (kW)",
    )

    # Classe systeme (EN 15232)
    system_class = Column(
        String(1),
        nullable=True,
        comment="Classe GTB : A, B, C, D ou null (inconnue)",
    )
    system_class_source = Column(
        String(50),
        nullable=True,
        comment="Source : declaratif, inspection, import_doc, unknown",
    )
    system_class_verified = Column(
        Boolean,
        nullable=True,
        default=False,
        comment="Classe verifiee par inspection ou preuve externe",
    )

    # Performance baseline
    performance_baseline_kwh = Column(Float, nullable=True, comment="Conso reference pour detection perte efficacite")
    efficiency_loss_threshold_pct = Column(Float, nullable=True, default=10.0, comment="Seuil perte efficacite (%)")

    # V1.1 Usage — Lien systeme CVC → usage energetique
    usage_id = Column(
        Integer,
        ForeignKey("usages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Usage energetique couvert par ce systeme CVC",
    )
    putile_calc_trace_json = Column(
        Text,
        nullable=True,
        comment="JSON: trace audit du calcul Putile",
    )

    # Audit fields
    inputs_json = Column(Text, nullable=True, default="{}", comment="JSON: input data used")
    params_json = Column(Text, nullable=True, default="{}", comment="JSON: params applied")
    engine_version = Column(String(64), nullable=True, comment="Engine version hash")

    # Relations
    asset = relationship("BacsAsset", back_populates="cvc_systems")


class BacsAssessment(Base, TimestampMixin):
    """
    Evaluation BACS cachee pour un actif.
    Resultat du moteur: obligation, seuil, echeance, TRI, score.
    """

    __tablename__ = "bacs_assessments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer,
        ForeignKey("bacs_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Actif BACS evalue",
    )
    assessed_at = Column(
        DateTime,
        nullable=False,
        comment="Date/heure de l'evaluation",
    )
    threshold_applied = Column(
        Integer,
        nullable=True,
        comment="Seuil applique: 70 ou 290 kW",
    )
    is_obligated = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Le site est-il assujetti au decret BACS?",
    )
    deadline_date = Column(
        Date,
        nullable=True,
        comment="Echeance reglementaire",
    )
    trigger_reason = Column(
        SAEnum(BacsTriggerReason),
        nullable=True,
        comment="Raison declenchante de l'obligation",
    )
    tri_exemption_possible = Column(
        Boolean,
        nullable=True,
        comment="Exemption TRI > 10 ans possible?",
    )
    tri_years = Column(
        Float,
        nullable=True,
        comment="Temps de retour sur investissement (annees)",
    )
    confidence_score = Column(
        Float,
        nullable=True,
        comment="Score de confiance de l'evaluation (0-1)",
    )
    compliance_score = Column(
        Float,
        nullable=True,
        comment="Score de conformite global (0-100)",
    )
    findings_json = Column(
        Text,
        nullable=True,
        comment="JSON: liste des findings detailles",
    )

    # Audit fields
    rule_id = Column(String(100), nullable=True, comment="Rule ID (BACS_V2_*)")
    inputs_json = Column(Text, nullable=True, default="{}", comment="JSON: input data used")
    params_json = Column(Text, nullable=True, default="{}", comment="JSON: params applied")
    evidence_json = Column(Text, nullable=True, default="{}", comment="JSON: evidence references")
    engine_version = Column(String(64), nullable=True, comment="Engine version hash")

    # Relations
    asset = relationship("BacsAsset", back_populates="assessments")


class BacsInspection(Base, TimestampMixin):
    """
    Suivi des inspections quinquennales BACS.
    Periodicite max 5 ans, tracking statut + rapport.
    """

    __tablename__ = "bacs_inspections"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer,
        ForeignKey("bacs_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Actif BACS inspecte",
    )
    inspection_date = Column(
        Date,
        nullable=True,
        comment="Date de l'inspection",
    )
    due_next_date = Column(
        Date,
        nullable=True,
        comment="Date de la prochaine inspection (periodicite 5 ans)",
    )
    report_ref = Column(
        String(255),
        nullable=True,
        comment="Reference du rapport d'inspection",
    )
    status = Column(
        SAEnum(InspectionStatus),
        nullable=False,
        default=InspectionStatus.SCHEDULED,
        comment="Statut: scheduled, completed, overdue",
    )

    # Enrichissement inspection
    inspector_name = Column(String(200), nullable=True)
    inspector_qualification = Column(String(100), nullable=True)
    findings_json = Column(Text, nullable=True, comment="JSON: [{code, severity, description, corrective_action}]")
    findings_count = Column(Integer, nullable=True, default=0)
    critical_findings_count = Column(Integer, nullable=True, default=0)
    system_class_observed = Column(String(1), nullable=True, comment="Classe observee lors de l'inspection")

    # Exigences inspection reglementaire R.175-5-1
    inspection_type = Column(String(20), nullable=True, comment="initial, periodic")
    report_delivered_at = Column(Date, nullable=True)
    report_retention_until = Column(Date, nullable=True)
    settings_evaluated = Column(Boolean, nullable=True, default=False, comment="Parametrage evalue")
    functional_analysis_done = Column(Boolean, nullable=True, default=False, comment="Analyse fonctionnelle realisee")
    recommendations_json = Column(Text, nullable=True, comment="JSON: recommandations structurees")
    report_compliant = Column(Boolean, nullable=True, comment="Rapport conforme aux exigences")

    # Relations
    asset = relationship("BacsAsset", back_populates="inspections")
