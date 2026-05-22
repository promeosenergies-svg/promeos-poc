"""M2-6.A.2 — purge_log : table audit RGPD article 30 (traçabilité purges PII).

Ajoute la table dédiée `purge_log` pour répondre à l'obligation CNIL article 30
(registre des traitements) : chaque purge PII RGPD article 17 doit être tracée
avec un journal historique non identifiant (hash SHA256 du user_id purgé).

Colonnes :
- `id` Integer PK
- `user_id_hash` String(64) — SHA256 hex du user_id purgé (jamais user_id en clair)
- `purged_at` DateTime tz — timestamp UTC, server default NOW()
- `purged_by_admin_id` Integer — id de l'admin auteur (pas de FK : l'admin
  lui-même peut être purgé plus tard, on garde l'id audit historique)
- `reason` String(500) — justification métier (demande RGPD, audit interne…)
- `report_json` Text — JSON compteurs (preuve d'exécution complète)
- `dry_run` Boolean — flag si purge simulée (preview) vs effective

Indexes :
- `ix_purge_log_purged_at` — recherche chronologique CNIL
- `ix_purge_log_user_id_hash` — recherche par user_id (forensique post-incident)

Additive only (Q13-B) : nouvelle table, aucune donnée existante impactée.
Cohérent avec ADR-029 §6 audit trail (mais journal séparé, pas event_log V4
qui est org-scopé — purge_log est plateforme-scoped).

Revision ID: m26a2purge
Revises: m2511e
"""

import sqlalchemy as sa
from alembic import op

revision = "m26a2purge"
down_revision = "m2511e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "purge_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id_hash",
            sa.String(64),
            nullable=False,
            comment="SHA256 hex du user_id purgé — traçabilité sans nominatif (CNIL art. 30)",
        ),
        sa.Column(
            "purged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "purged_by_admin_id",
            sa.Integer,
            nullable=False,
            comment="id users de l'admin auteur (PAS de FK — l'admin peut être purgé plus tard)",
        ),
        sa.Column(
            "reason",
            sa.String(500),
            nullable=False,
            comment="Justification métier (demande RGPD art. 17, audit interne, etc.)",
        ),
        sa.Column(
            "report_json",
            sa.Text,
            nullable=False,
            comment="JSON compteurs entités anonymisées/supprimées (preuve d'exécution)",
        ),
        sa.Column(
            "dry_run",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
            comment="True si purge simulée (preview) — purge réelle a dry_run=False",
        ),
    )
    op.create_index("ix_purge_log_purged_at", "purge_log", ["purged_at"])
    op.create_index("ix_purge_log_user_id_hash", "purge_log", ["user_id_hash"])


def downgrade():
    op.drop_index("ix_purge_log_user_id_hash", table_name="purge_log")
    op.drop_index("ix_purge_log_purged_at", table_name="purge_log")
    op.drop_table("purge_log")
