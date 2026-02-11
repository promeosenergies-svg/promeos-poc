"""
PROMEOS - Modele ComplianceFinding
Resultat persistant d'une evaluation de conformite par regle.
"""
from sqlalchemy import Column, Integer, String, Float, Text, Date, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


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

    # Relation
    site = relationship("Site", backref="compliance_findings")
