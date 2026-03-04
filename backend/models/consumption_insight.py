"""
PROMEOS - Modele ConsumptionInsight
Resultat d'un diagnostic de consommation (hors horaires, base load, pointe, derive).
"""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin
from .enums import InsightStatus


class ConsumptionInsight(Base, TimestampMixin):
    """
    Un insight = un diagnostic de consommation detecte pour un site.
    Types: hors_horaires, base_load, pointe, derive, data_gap
    """

    __tablename__ = "consumption_insights"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        index=True,
        comment="Site concerne",
    )
    meter_id = Column(
        Integer,
        ForeignKey("meter.id"),
        nullable=True,
        index=True,
        comment="Compteur concerne (optionnel)",
    )
    type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type de diagnostic: hors_horaires, base_load, pointe, derive, data_gap",
    )
    severity = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="low, medium, high, critical",
    )
    message = Column(
        String(500),
        nullable=False,
        comment="Description humaine du diagnostic",
    )
    metrics_json = Column(
        Text,
        nullable=True,
        comment="Metriques detaillees (JSON)",
    )
    estimated_loss_kwh = Column(
        Float,
        nullable=True,
        comment="Perte estimee en kWh/an",
    )
    estimated_loss_eur = Column(
        Float,
        nullable=True,
        comment="Perte estimee en EUR/an",
    )
    recommended_actions_json = Column(
        Text,
        nullable=True,
        comment="Actions recommandees (JSON array of {title, rationale, expected_gain_kwh, expected_gain_eur, effort, priority})",
    )
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    insight_status = Column(
        SAEnum(InsightStatus),
        default=InsightStatus.OPEN,
        nullable=False,
        server_default="open",
        comment="Statut workflow: open, ack, resolved, false_positive",
    )

    # Relations
    site = relationship("Site", backref="consumption_insights")
