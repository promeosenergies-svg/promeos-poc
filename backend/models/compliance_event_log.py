"""
PROMEOS — ComplianceEventLog : audit-trail pour conformite reglementaire.
Trace toutes les mutations sur les donnees de conformite (consommations, exports, trajectoire).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from .base import Base


class ComplianceEventLog(Base):
    """Journal des evenements de conformite — audit-trail immuable."""

    __tablename__ = "compliance_event_log"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(
        String(100), nullable=False, index=True, comment="Ex: TertiaireEfaConsumption, TertiaireDeclaration"
    )
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(
        String(50), nullable=False, comment="create, update, delete, export_generate, status_change, trajectory_compute"
    )
    before_json = Column(Text, nullable=True, comment="Etat avant modification (JSON)")
    after_json = Column(Text, nullable=True, comment="Etat apres modification (JSON)")
    actor = Column(String(200), nullable=False, default="system", comment="Identifiant utilisateur ou systeme")
    source_context = Column(String(200), nullable=True, comment="Ex: api_endpoint, seed, import_csv, manual")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
