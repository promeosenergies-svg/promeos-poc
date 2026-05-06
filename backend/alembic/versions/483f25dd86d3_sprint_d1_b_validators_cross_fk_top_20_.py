"""Sprint D1-B Validators cross-FK Top 20 contraintes matrice v1 §8.3 (Phase D-1bis)

Revision ID: 483f25dd86d3
Revises: c554f6299e9c
Create Date: 2026-05-07

15e migration Alembic Phase C+, 0 destructive cumulée.

Anti-DROP discipline 15e épisode : 17 drops autogenerate retirés (legacy
annotations, meter_*, enedis_flux_*, promotion_*, unmatched_prm, opendata_*,
backups préservés .original-autogenerate).

Ajouts cardinaux :
- C50 matrice v1 §8.3 : UniqueConstraint batiments (site_id, nom).
- C60+C85 matrice v1 §8.3 : delivery_points.code unique=True (PRM/PCE
  cardinal cross-energy_type — pré-audit DB confirmé 0 doublon avant).
- C108 matrice v1 §8.3 : CheckConstraint contract_pricing
  (effective_to > effective_from quand les deux dates renseignées).

Pré-audit cardinal pré-migration (script `scripts/audit_pre_d1b_uniqueness.py`) :
- DP code doublons : 0
- Batiment (site_id, nom) doublons : 0
- ContractPricing dates inversées : 0

Cumul Phase C+ : 15 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "483f25dd86d3"
down_revision: Union[str, Sequence[str], None] = "c554f6299e9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — 3 contraintes ajoutées (1 UC + 1 index UNIQUE + 1 CC)."""

    # ─── C50 — batiments (site_id, nom) UniqueConstraint ────────────────────
    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_batiment_nom_per_site", ["site_id", "nom"])

    # ─── C60+C85 — delivery_points.code unique active (partial index) ───────
    # Pattern existant `uq_delivery_point_code_active` (database/migrations.py)
    # déjà actif via initialisation runtime — partial index `WHERE deleted_at IS NULL`
    # autorisant ré-attribution post-soft-delete (cas légitime PRM/PCE recyclé).
    # On ajoute IDEMPOTENT le partial index pour les déploiements alembic-only.
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "uq_delivery_point_code_active" '
        'ON "delivery_points" ("code") '
        'WHERE "code" IS NOT NULL AND "deleted_at" IS NULL'
    )

    # ─── C108 — contract_pricing CheckConstraint (effective_to > effective_from) ─
    # NULL-friendly : si l'une des dates est NULL, contrainte tolérée.
    with op.batch_alter_table("contract_pricing", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_pricing_dates_order",
            "(effective_from IS NULL OR effective_to IS NULL OR effective_to > effective_from)",
        )


def downgrade() -> None:
    """Downgrade schema — retrait des 3 contraintes."""
    with op.batch_alter_table("contract_pricing", schema=None) as batch_op:
        batch_op.drop_constraint("ck_pricing_dates_order", type_="check")

    op.execute('DROP INDEX IF EXISTS "uq_delivery_point_code_active"')

    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.drop_constraint("uq_batiment_nom_per_site", type_="unique")
