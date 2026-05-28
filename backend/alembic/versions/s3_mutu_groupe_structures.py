"""s3_mutu_groupe_structures — Sprint S3 Mutualisation P0 juridique (2026-05-28).

Crée les 3 tables nécessaires à la mutualisation des résultats au sens
de l'Article 14 de l'arrêté du 10 avril 2020 modifié (en application de
L.174-1 + R.174-31 CCH) :

  - tertiaire_groupe_structures           (entité « groupe de structures »)
  - tertiaire_groupe_structures_membre    (appartenance EFA + état validation RL)
  - tertiaire_mutualisation_ledger        (journal redistribution unique)

Cross-check Légifrance : voir
docs/audits/crosscheck_legifrance_mutualisation_art14_2026_05_28.md

Invariants juridiques posés DB-side :
  - I3 : `UNIQUE PARTIAL (efa_id) WHERE deleted_at IS NULL` sur la
    table membre — une EFA active ne peut appartenir qu'à un seul
    groupe.
  - I4 : `UNIQUE (group_id, donneuse_efa_id, jalon_annee)` sur le ledger
    — une EFA donneuse ne peut redistribuer qu'une fois par jalon.
  - I2 : `CHECK (representant_legal_status IN (...))` whitelist stricte.
  - I1 : `CHECK (status IN (...))` whitelist stricte sur le groupe.

Merge des 2 heads alembic préexistantes (`p0fix_acref` + `p39evid`) —
dette branching alembic résorbée au passage en branchant cette
migration sur les deux.

Revision ID: s3_mutu_gs
Revises: p0fix_acref, p39evid
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "s3_mutu_gs"
down_revision: Union[str, Sequence[str], None] = ("p0fix_acref", "p39evid")
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1. Table « groupe de structures » (entité Art. 14 §1 al.1)
    op.create_table(
        "tertiaire_groupe_structures",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "organisation_id",
            sa.Integer,
            sa.ForeignKey("organisations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_by", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("deleted_at", sa.DateTime, nullable=True, index=True),
        sa.Column("deleted_by", sa.String(length=200), nullable=True),
        sa.Column("delete_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_validation', 'validated', 'archived')",
            name="chk_groupe_status",
        ),
    )
    where_groupe_active = "deleted_at IS NULL AND status != 'archived'"
    if dialect == "postgresql":
        op.execute(
            "CREATE INDEX idx_groupe_org_active ON tertiaire_groupe_structures "
            "(organisation_id, status) WHERE " + where_groupe_active
        )
    else:
        op.execute(
            "CREATE INDEX idx_groupe_org_active ON tertiaire_groupe_structures "
            "(organisation_id, status) WHERE " + where_groupe_active
        )

    # 2. Table membre (appartenance EFA + état validation RL)
    op.create_table(
        "tertiaire_groupe_structures_membre",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer,
            sa.ForeignKey("tertiaire_groupe_structures.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "efa_id",
            sa.Integer,
            sa.ForeignKey("tertiaire_efa.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "representant_legal_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("representant_legal_validated_at", sa.DateTime, nullable=True),
        sa.Column("validator_user_id", sa.String(length=200), nullable=True),
        sa.Column("validation_note", sa.Text, nullable=True),
        sa.Column("deleted_at", sa.DateTime, nullable=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint(
            "representant_legal_status IN ('pending', 'validated', 'rejected')",
            name="chk_membre_rl_status",
        ),
        sa.UniqueConstraint("group_id", "efa_id", name="uq_membre_group_efa"),
    )
    # I3 cardinale — UNIQUE PARTIEL : une EFA active dans un seul groupe.
    if dialect == "postgresql":
        op.execute(
            "CREATE UNIQUE INDEX uq_membre_efa_active "
            "ON tertiaire_groupe_structures_membre (efa_id) "
            "WHERE deleted_at IS NULL"
        )
    else:
        op.execute(
            "CREATE UNIQUE INDEX uq_membre_efa_active "
            "ON tertiaire_groupe_structures_membre (efa_id) "
            "WHERE deleted_at IS NULL"
        )

    # 3. Table ledger (I4 — redistribution unique par jalon)
    op.create_table(
        "tertiaire_mutualisation_ledger",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer,
            sa.ForeignKey("tertiaire_groupe_structures.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("jalon_annee", sa.Integer, nullable=False),
        sa.Column(
            "donneuse_efa_id",
            sa.Integer,
            sa.ForeignKey("tertiaire_efa.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("kwh_redistribues", sa.Float, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint("kwh_redistribues >= 0", name="chk_ledger_kwh_positive"),
        sa.UniqueConstraint(
            "group_id",
            "donneuse_efa_id",
            "jalon_annee",
            name="uq_ledger_donneuse_jalon",
        ),
    )


def downgrade() -> None:
    op.drop_table("tertiaire_mutualisation_ledger")
    op.execute("DROP INDEX IF EXISTS uq_membre_efa_active")
    op.drop_table("tertiaire_groupe_structures_membre")
    op.execute("DROP INDEX IF EXISTS idx_groupe_org_active")
    op.drop_table("tertiaire_groupe_structures")
