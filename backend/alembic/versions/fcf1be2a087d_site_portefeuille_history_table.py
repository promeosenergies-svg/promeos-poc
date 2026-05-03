"""site_portefeuille_history_table

Revision ID: fcf1be2a087d
Revises: f415992b3d25
Create Date: 2026-05-03

Sprint C-2 Phase 2 — Création table site_portefeuille_history (matrice v1 §6.5,
GAP audit Phase B R4).

Note : autogenerate Alembic a initialement produit 17 op.drop_table() sur des
tables Enedis legacy (cf. D-Enedis-Legacy-001 + Sprint C-1 Phase 3 + Sprint C-2
Phase 1.2). Ces drops ont été RETIRÉS manuellement — pattern identique aux
migrations Sprint C-1 Phase 3 (c8f1246522f9) et Sprint C-2 Phase 1.2
(f415992b3d25).

Cette migration ne contient QUE :
- 1 op.create_table 'site_portefeuille_history' (10 colonnes, 3 FK)
- 2 op.create_index (ix_sph_site_id_valid_from, ix_sph_portefeuille_id_valid_from)

Permet :
- Analyses rétrospectives (KPI portefeuille à date donnée)
- Audit trail des bascules Site↔Portefeuille (qui, quand, pourquoi)
- Cohérence cross-EJ enforced par site_portefeuille_service
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fcf1be2a087d"
down_revision: Union[str, Sequence[str], None] = "f415992b3d25"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema : créer table site_portefeuille_history + 2 index."""
    op.create_table(
        "site_portefeuille_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "site_id",
            sa.Integer(),
            nullable=False,
            comment="Site qui appartient au portefeuille pendant la période",
        ),
        sa.Column(
            "portefeuille_id",
            sa.Integer(),
            nullable=False,
            comment="Portefeuille auquel le site est rattaché",
        ),
        sa.Column(
            "valid_from",
            sa.DateTime(),
            nullable=False,
            comment="Début de la période (inclusif)",
        ),
        sa.Column(
            "valid_to",
            sa.DateTime(),
            nullable=True,
            comment="Fin de la période (inclusif). None = période courante (active)",
        ),
        sa.Column(
            "transferred_by_user_id",
            sa.Integer(),
            nullable=True,
            comment="Utilisateur ayant déclenché la bascule (None si système/cron)",
        ),
        sa.Column(
            "raison",
            sa.String(length=500),
            nullable=True,
            comment="Raison textuelle de la bascule (saisie utilisateur)",
        ),
        sa.Column(
            "metadata_json",
            sa.Text(),
            nullable=True,
            comment="Payload contextuel optionnel (correlation_id, batch_id, etc.)",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="Date de creation"),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            comment="Date de derniere modification",
        ),
        sa.ForeignKeyConstraint(["portefeuille_id"], ["portefeuilles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transferred_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("site_portefeuille_history", schema=None) as batch_op:
        batch_op.create_index(
            "ix_sph_portefeuille_id_valid_from",
            ["portefeuille_id", "valid_from"],
            unique=False,
        )
        batch_op.create_index(
            "ix_sph_site_id_valid_from",
            ["site_id", "valid_from"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema : drop table site_portefeuille_history + 2 index."""
    with op.batch_alter_table("site_portefeuille_history", schema=None) as batch_op:
        batch_op.drop_index("ix_sph_site_id_valid_from")
        batch_op.drop_index("ix_sph_portefeuille_id_valid_from")
    op.drop_table("site_portefeuille_history")
