"""ActionScenario — options decision / playbooks recommendation V4.

🛡️ D3 ENRICHISSEMENT L7 §2.4 → ADR-025 §4.3 détaillé :
- Colonnes scalaires : scenario_tag, label, capex_eur, gain_eur_per_year,
                       is_recommended, display_order, selected_at, selected_by
- JSONB payload pour métadonnées additionnelles
- 2 indexes : (org, item, display_order) + (org, item) WHERE is_recommended
- CHECK chk_scenario_selection_consistency : selected_at NULL ⇔ selected_by NULL

Cas d'usage : drawer M4 affiche options pour Kind ∈ {decision, recommendation}
avec ROI inline. Sélection trace selected_at + selected_by.
"""

from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from models.base import Base


class ActionScenario(Base):
    """Scénario / option pour decision ou recommendation (D3 enrichi)."""

    __tablename__ = "action_scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organisation_id = Column(UUID(as_uuid=True), nullable=False)  # IS1
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("action_center_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Identification scénario
    scenario_tag = Column(String(20), nullable=False)  # ex: 'option_a', 'baseline', 'reco'
    label = Column(Text, nullable=False)

    # ROI scalaires (D3 — extraction from payload pour SQL filter/sort)
    capex_eur = Column(Numeric(12, 2))
    gain_eur_per_year = Column(Numeric(12, 2))
    is_recommended = Column(Boolean, nullable=False, server_default=text("false"))

    # Affichage
    display_order = Column(Integer, nullable=False, server_default="0")

    # Selection (drawer M4)
    selected_at = Column(DateTime(timezone=True))
    selected_by = Column(UUID(as_uuid=True))

    # Métadonnées additionnelles (extensible)
    payload = Column(JSON)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        # D3 cardinal : cohérence selection
        CheckConstraint(
            "(selected_at IS NULL AND selected_by IS NULL) OR (selected_at IS NOT NULL AND selected_by IS NOT NULL)",
            name="chk_scenario_selection_consistency",
        ),
        # ─── Indexes (D3 : 2 indexes) ───
        Index("idx_scenarios_item_order", "organisation_id", "item_id", "display_order"),
        Index(
            "idx_scenarios_item_recommended",
            "organisation_id",
            "item_id",
            sqlite_where=text("is_recommended = 1"),
            postgresql_where=text("is_recommended = TRUE"),
        ),
    )
