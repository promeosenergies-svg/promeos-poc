"""Phase 3.9 — BillAnomalyEvidence (Bill Intelligence P1 C2)

Audit Bill Intelligence Phase 0-bis (2026-05-24, chantier C2) :
  > P0 §3 Règle 2 — Aucune FK Evidence formelle sur BillAnomaly. Les preuves
  > vivent dans `details_json` (semi-structuré, non opposable). Aucun endpoint
  > download authentifié. Conséquence : DAF ne peut pas opposer la preuve
  > documentaire devant le fournisseur.

Cette migration crée la table `bill_anomaly_evidence` :
  - FK anomaly_id (BillAnomaly), invoice_id (EnergyInvoice dénormalisé),
    org_id (Organisation, IDOR-safe)
  - file_hash_sha256 obligatoire (intégrité)
  - workflow verified_at / verified_by (preuve produite ≠ validée)
  - SoftDeleteMixin + TimestampMixin (mixin standard PROMEOS)

Pattern inspiré de Evidence V4 conformité C6 P1 (mergé 2026-05-23).

Discipline anti-DROP : la table n'est pas supprimée au downgrade
(les preuves d'audit ne peuvent pas être perdues).

Revision ID: p39evid
Revises: p38anmon
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "p39evid"
down_revision: Union[str, Sequence[str], None] = "p38anmon"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crée la table bill_anomaly_evidence si absente (idempotent)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "bill_anomaly_evidence" in existing_tables:
        return

    op.create_table(
        "bill_anomaly_evidence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "anomaly_id",
            sa.Integer(),
            sa.ForeignKey("bill_anomaly.id"),
            nullable=False,
            comment="Anomalie concernée (FK BillAnomaly)",
        ),
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organisations.id"),
            nullable=False,
            comment="Organisation propriétaire (org-scoping cardinal)",
        ),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("energy_invoices.id"),
            nullable=False,
            comment="Facture concernée (dénormalisée pour requêtes rapides)",
        ),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default="manual_upload",
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("verified_by", sa.Integer(), nullable=True),
        # TimestampMixin + SoftDeleteMixin
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("delete_reason", sa.String(length=255), nullable=True),
    )

    op.create_index(
        "ix_bill_anomaly_evidence_anomaly",
        "bill_anomaly_evidence",
        ["anomaly_id"],
    )
    op.create_index(
        "ix_bill_anomaly_evidence_invoice",
        "bill_anomaly_evidence",
        ["invoice_id"],
    )
    op.create_index(
        "ix_bill_anomaly_evidence_org",
        "bill_anomaly_evidence",
        ["org_id"],
    )
    op.create_index(
        "ix_bill_anomaly_evidence_hash",
        "bill_anomaly_evidence",
        ["file_hash_sha256"],
    )


def downgrade() -> None:
    """Anti-DROP : les preuves d'audit ne peuvent pas être perdues."""
    pass
