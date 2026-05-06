"""Phase 5.1 Sprint C-5 — bill_anomaly table (ADR-013)

Revision ID: 478ee4a61ebb
Revises: d4a59f7c8e21
Create Date: 2026-05-06 09:03:03.951027

8e migration Alembic Phase C, 0 destructive cumulée.

Anti-DROP discipline 8e épisode : 14 drop_table autogenerate retirés manuellement
(annotator_profiles, enedis_opendata_conso_inf36/sup36, enedis_flux_mesure_r4x/r50/r151/r171,
enedis_flux_file/_error, enedis_ingestion_run, meter_load_curve/energy_index/power_peak,
promotion_run/_event, unmatched_prm, annotations).

Adaptations Phase 5.1.0 (post-diagnostic mini-audit) :
- FK invoice_id → energy_invoices.id (modèle EnergyInvoice, pas Facture)
- 4 index : invoice_id (FK), code+severity, detected_at, deleted_at (SoftDeleteMixin)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "478ee4a61ebb"
down_revision: Union[str, Sequence[str], None] = "d4a59f7c8e21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — création table bill_anomaly + 4 index."""
    op.create_table(
        "bill_anomaly",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False, comment="Facture concernée (EnergyInvoice)"),
        sa.Column(
            "code",
            sa.String(length=20),
            nullable=False,
            comment="Code anomalie : R19 (VNU dormant), R20 (capacité variance), R21+ futurs",
        ),
        sa.Column("severity", sa.String(length=10), nullable=False, comment="Sévérité : critical / warning / info"),
        sa.Column("detected_at", sa.DateTime(), nullable=False, comment="Date détection"),
        sa.Column("resolved_at", sa.DateTime(), nullable=True, comment="Date résolution (NULL = ouverte)"),
        sa.Column(
            "resolution_note",
            sa.Text(),
            nullable=True,
            comment="Note résolution (correction fournisseur, justification, etc.)",
        ),
        sa.Column(
            "threshold_value",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="Seuil YAML appliqué (ex : 5.0 pour R20)",
        ),
        sa.Column(
            "actual_value",
            sa.Numeric(precision=15, scale=4),
            nullable=True,
            comment="Valeur observée (ex : variance_pct = 8.3)",
        ),
        sa.Column(
            "details_json",
            sa.JSON(),
            nullable=True,
            comment="Contexte détection (montants VNU, période, contrat, etc.)",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="Date de creation"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="Date de derniere modification"),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Date de suppression logique (NULL = actif)"),
        sa.Column("deleted_by", sa.String(length=200), nullable=True, comment="Identifiant utilisateur ayant supprime"),
        sa.Column("delete_reason", sa.String(length=500), nullable=True, comment="Raison de la suppression"),
        sa.ForeignKeyConstraint(["invoice_id"], ["energy_invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("bill_anomaly", schema=None) as batch_op:
        batch_op.create_index("ix_bill_anomaly_code_severity", ["code", "severity"], unique=False)
        batch_op.create_index(batch_op.f("ix_bill_anomaly_deleted_at"), ["deleted_at"], unique=False)
        batch_op.create_index("ix_bill_anomaly_detected_at", ["detected_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_bill_anomaly_invoice_id"), ["invoice_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema — suppression défensive table bill_anomaly + 4 index."""
    with op.batch_alter_table("bill_anomaly", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_bill_anomaly_invoice_id"))
        batch_op.drop_index("ix_bill_anomaly_detected_at")
        batch_op.drop_index(batch_op.f("ix_bill_anomaly_deleted_at"))
        batch_op.drop_index("ix_bill_anomaly_code_severity")

    op.drop_table("bill_anomaly")
