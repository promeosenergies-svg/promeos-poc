"""M2-5.11.E — action_center_items : colonne snapshot `owner_display_name`.

Ajoute :
- `owner_display_name` (String 120, nullable) — snapshot du libellé pilote
  écrit au moment du PATCH /assign (pattern identique à `actor_name` sur
  `action_event_log`). Évite une jointure runtime sur la table legacy
  `users` (Integer id) depuis la table V4 `action_center_items` (UUID
  `owner_id`).

Additive only (Q13-B) : colonne nullable, aucune donnée existante
impactée. Cohérent avec le pattern V4 « UUID isolé + snapshot label »
documenté ADR-029 §3.4.

Revision ID: m2511e
Revises: m242idem
"""

import sqlalchemy as sa
from alembic import op

revision = "m2511e"
down_revision = "m242idem"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "action_center_items",
        sa.Column("owner_display_name", sa.String(120), nullable=True),
    )


def downgrade():
    op.drop_column("action_center_items", "owner_display_name")
