"""Phase F1 — Fournisseur entité normalisée (ADR-F-01)

Crée la table `fournisseurs` (catalogue hybride canonique + tenant)
+ ajoute la FK `fournisseur_id` (nullable, NON-DESTRUCTIVE) sur
`energy_contracts` en miroir transitoire avec `supplier_name`.

Pattern Phase D-4 anti-DROP discipline (18 épisodes) :
- AUCUN DROP de colonne existante
- `supplier_name` conservé pour Phase F1 backfill
- Hard-cut prévu Phase F2 ADR-F-04 séparé après validation backfill 100%

Source : docs/adr/ADR-F-01-fournisseur-entite-normalisation.md (ACCEPTED 2026-05-08)

Revision ID: a1b2c3d4e5f6
Revises: 17c5ab8161bf
Create Date: 2026-05-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "17c5ab8161bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase F1 — création table fournisseurs + FK energy_contracts.fournisseur_id (nullable)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ─── 1. Table fournisseurs (idempotent) ──────────────────────────────────
    if "fournisseurs" not in existing_tables:
        op.create_table(
            "fournisseurs",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "organisation_id",
                sa.Integer(),
                sa.ForeignKey("organisations.id"),
                nullable=True,
                index=True,
                comment="NULL = catalogue canonique Promeos. NOT NULL = privé org.",
            ),
            sa.Column("nom", sa.String(200), nullable=False),
            sa.Column("siren", sa.String(9), nullable=True, index=True),
            sa.Column("tva_intra", sa.String(13), nullable=True),
            sa.Column("naf_code", sa.String(10), nullable=True),
            sa.Column(
                "type_fourniture",
                sa.Enum("ELEC", "GAZ", "MULTI", name="typefournitureenum"),
                nullable=False,
            ),
            sa.Column("contact_email", sa.String(320), nullable=True),
            sa.Column("contact_telephone", sa.String(30), nullable=True),
            sa.Column("site_web", sa.String(500), nullable=True),
            sa.Column("cgv_url", sa.String(500), nullable=True),
            sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("1"), index=True),
            sa.Column("signataire_nom", sa.String(200), nullable=True),
            sa.Column("signataire_email", sa.String(320), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("siren", "organisation_id", name="uq_fournisseur_siren_org"),
        )
        op.create_index(
            "ix_fournisseur_org_actif",
            "fournisseurs",
            ["organisation_id", "actif"],
        )
        # Partial unique index canoniques (SQLite + PostgreSQL supportent partial indexes).
        # Couvre le cas SQLite NULL distinct sur UniqueConstraint composite (cf. ADR-F-01 §Risques).
        op.create_index(
            "uq_fournisseur_canonique_siren",
            "fournisseurs",
            ["siren"],
            unique=True,
            sqlite_where=sa.text("organisation_id IS NULL"),
            postgresql_where=sa.text("organisation_id IS NULL"),
        )

    # ─── 2. FK fournisseur_id sur energy_contracts (idempotent NON-DESTRUCTIVE) ──
    contract_cols = {c["name"] for c in inspector.get_columns("energy_contracts")}
    if "fournisseur_id" not in contract_cols:
        # SQLite batch_alter_table requiert FK named pour copy-and-move
        with op.batch_alter_table("energy_contracts") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "fournisseur_id",
                    sa.Integer(),
                    sa.ForeignKey("fournisseurs.id", name="fk_energy_contracts_fournisseur_id"),
                    nullable=True,
                )
            )
        # Index séparé pour respecter naming convention PROMEOS
        op.create_index(
            "ix_energy_contracts_fournisseur_id",
            "energy_contracts",
            ["fournisseur_id"],
        )


def downgrade() -> None:
    """Rollback : SET fournisseur_id = NULL puis DROP FK + table.

    AUCUN DROP supplier_name (anti-DROP discipline Phase D-4).
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Drop FK column on energy_contracts
    contract_cols = {c["name"] for c in inspector.get_columns("energy_contracts")}
    if "fournisseur_id" in contract_cols:
        existing_indexes = {i["name"] for i in inspector.get_indexes("energy_contracts")}
        if "ix_energy_contracts_fournisseur_id" in existing_indexes:
            op.drop_index("ix_energy_contracts_fournisseur_id", table_name="energy_contracts")
        with op.batch_alter_table("energy_contracts") as batch_op:
            batch_op.drop_column("fournisseur_id")

    # 2. Drop table fournisseurs
    if "fournisseurs" in inspector.get_table_names():
        existing_indexes = {i["name"] for i in inspector.get_indexes("fournisseurs")}
        if "uq_fournisseur_canonique_siren" in existing_indexes:
            op.drop_index("uq_fournisseur_canonique_siren", table_name="fournisseurs")
        if "ix_fournisseur_org_actif" in existing_indexes:
            op.drop_index("ix_fournisseur_org_actif", table_name="fournisseurs")
        op.drop_table("fournisseurs")
