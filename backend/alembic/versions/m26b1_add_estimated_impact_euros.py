"""m26b1_add_estimated_impact_euros — action_center_items: champ impact € CFO.

M2-6.B.backend — Champ `estimated_impact_euros NUMERIC(12,2) NULL` posé sur
`action_center_items` pour le mode CFO (NarrativeBar v3 sommes € + colonne €
ItemsTable + export PDF COMEX en M2-6.B.frontend/M2-6.B.pdf).

Distinct de :
  - `impact_current_period_eur` (mesure réelle période — billing)
  - `impact_cumulative_eur` (cumul historique mesuré)
  - `impact_payload` JSON (drill-down 4 quadrants estimated/at_risk/secured/foregone)

Sémantique : valeur estimée simple (€/an) exposée directement au CFO sans
drill-down. NULL strict si pas de source documentée (discipline « pas de
chiffre menteur » §6.6).

Index partiel : majorité des items NULL en MV3 → l'index ne grossit qu'avec
les items qui portent une valeur (efficient sur agrégat SUM).

Additive only (Q13-B) : colonne nullable, aucune donnée existante impactée.

Revision ID: m26b1impact
Revises: m26a2purge
"""

import sqlalchemy as sa
from alembic import op

revision = "m26b1impact"
down_revision = "m26a2purge"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "action_center_items",
        sa.Column(
            "estimated_impact_euros",
            sa.Numeric(12, 2),
            nullable=True,
            comment="Impact financier estimé EUR/an (mode CFO). NULL si non documenté.",
        ),
    )
    # Index partiel: majorité NULL en MV3, l'index ne grossit qu'avec les items
    # portant une valeur (agrégat SUM + tri DESC plus rapide post-pilote).
    op.create_index(
        "ix_action_center_items_estimated_impact_euros",
        "action_center_items",
        ["estimated_impact_euros"],
        postgresql_where=sa.text("estimated_impact_euros IS NOT NULL"),
        sqlite_where=sa.text("estimated_impact_euros IS NOT NULL"),
    )


def downgrade():
    op.drop_index(
        "ix_action_center_items_estimated_impact_euros",
        table_name="action_center_items",
    )
    op.drop_column("action_center_items", "estimated_impact_euros")
