"""
PROMEOS - Modele ComplianceFinding
Resultat persistant d'une evaluation de conformite par regle.
"""

from sqlalchemy import Column, Integer, String, Float, Text, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import InsightStatus


class ComplianceFinding(Base, TimestampMixin):
    """
    Un finding = une regle evaluee pour un site.
    Status: OK / NOK / UNKNOWN / OUT_OF_SCOPE
    """

    __tablename__ = "compliance_findings"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        index=True,
        comment="Site evalue",
    )
    regulation = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Pack reglementaire (decret_tertiaire_operat, bacs, aper)",
    )
    rule_id = Column(
        String(100),
        nullable=False,
        comment="Identifiant unique de la regle (ex: DT_SCOPE, BACS_POWER)",
    )
    status = Column(
        String(20),
        nullable=False,
        comment="OK, NOK, UNKNOWN, OUT_OF_SCOPE",
    )
    severity = Column(
        String(20),
        nullable=True,
        comment="low, medium, high, critical",
    )
    deadline = Column(
        Date,
        nullable=True,
        comment="Echeance reglementaire",
    )
    evidence = Column(
        String(500),
        nullable=True,
        comment="Explication humaine du finding",
    )
    recommended_actions_json = Column(
        Text,
        nullable=True,
        comment="Actions recommandees (JSON array de strings)",
    )

    # OPS workflow (pattern BillingInsight — Sprint 9)
    insight_status = Column(
        SAEnum(InsightStatus),
        default=InsightStatus.OPEN,
        nullable=False,
        comment="Statut workflow: open, ack, resolved, false_positive",
    )
    owner = Column(
        String(100),
        nullable=True,
        comment="Responsable assigne (email ou nom)",
    )
    notes = Column(
        Text,
        nullable=True,
        comment="Notes operateur (motif de resolution, etc.)",
    )
    run_batch_id = Column(
        Integer,
        ForeignKey("compliance_run_batches.id"),
        nullable=True,
        index=True,
        comment="Batch d'evaluation parent",
    )

    # Penalty fields (Step 14)
    estimated_penalty_eur = Column(Float, nullable=True, comment="Penalite estimee en EUR")
    penalty_source = Column(String(100), nullable=True, comment="Source: regs.yaml, estimation, etc.")
    penalty_basis = Column(String(200), nullable=True, comment="Base de calcul de la penalite")

    # Audit fields (inputs/params/evidence used for this finding)
    inputs_json = Column(Text, nullable=True, default="{}", comment="JSON: input data used")
    params_json = Column(Text, nullable=True, default="{}", comment="JSON: thresholds/params applied")
    evidence_json = Column(Text, nullable=True, default="{}", comment="JSON: evidence references")
    engine_version = Column(String(64), nullable=True, comment="Config version hash")

    # Relations
    site = relationship("Site", backref="compliance_findings")
    run_batch = relationship("ComplianceRunBatch", backref="findings")
