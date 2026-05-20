"""M2-4.2 — action_center_items : colonnes idempotency (POST /items replay-safe).

Ajoute :
- idempotency_key (String 36)        — UUID v4 du header Idempotency-Key
- idempotency_payload_hash (String 64) — SHA256 du body (détecte rejeu clé+payload≠)
- index UNIQUE partiel (organisation_id, idempotency_key) WHERE key IS NOT NULL
  → unicité PAR org ; les lignes sans clé ne sont pas indexées.

Additive only (Q13-B) : colonnes nullable, aucune donnée existante impactée.

Revision ID: m242idem
Revises: m2s2v4
"""

import sqlalchemy as sa
from alembic import op

revision = "m242idem"
down_revision = "m2s2v4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "action_center_items",
        sa.Column("idempotency_key", sa.String(36), nullable=True),
    )
    op.add_column(
        "action_center_items",
        sa.Column("idempotency_payload_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "idx_aci_idempotency_key",
        "action_center_items",
        ["organisation_id", "idempotency_key"],
        unique=True,
        sqlite_where=sa.text("idempotency_key IS NOT NULL"),
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade():
    op.drop_index("idx_aci_idempotency_key", table_name="action_center_items")
    op.drop_column("action_center_items", "idempotency_payload_hash")
    op.drop_column("action_center_items", "idempotency_key")
