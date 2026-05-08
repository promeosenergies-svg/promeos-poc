"""Phase H3 — ISO 50001 exemption Audit SMÉ (Marie DAF différenciant ROI)

Ajoute deux colonnes sur `entites_juridiques` pour tracker la certification
ISO 50001 (SMÉ) qui exempte de l'obligation Audit SMÉ (Loi DDADUE 2025-391
art. 8) les EJ entre 2,75 et 23,6 GWh.

Pattern Phase D-4 anti-DROP discipline (19e épisode anti-DROP) :
- AUCUN DROP de colonne existante
- 2 colonnes ajoutées nullable, idempotent

Source : docs/audits/persona_marie_daf_phase_g_audit.md (économie ~60 k€/audit × 4 ans)

Revision ID: h3iso50001
Revises: a1b2c3d4e5f6
Create Date: 2026-05-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "h3iso50001"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase H3 — ajout iso_50001_actif + iso_50001_date_validite (idempotent NON-DESTRUCTIVE)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("entites_juridiques")}

    if "iso_50001_actif" not in existing_cols:
        with op.batch_alter_table("entites_juridiques") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "iso_50001_actif",
                    sa.Boolean(),
                    nullable=True,
                    server_default=sa.text("0"),
                )
            )
    if "iso_50001_date_validite" not in existing_cols:
        with op.batch_alter_table("entites_juridiques") as batch_op:
            batch_op.add_column(sa.Column("iso_50001_date_validite", sa.Date(), nullable=True))


def downgrade() -> None:
    """Rollback : drop des 2 colonnes ajoutées Phase H3."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("entites_juridiques")}

    if "iso_50001_date_validite" in existing_cols:
        with op.batch_alter_table("entites_juridiques") as batch_op:
            batch_op.drop_column("iso_50001_date_validite")
    if "iso_50001_actif" in existing_cols:
        with op.batch_alter_table("entites_juridiques") as batch_op:
            batch_op.drop_column("iso_50001_actif")
