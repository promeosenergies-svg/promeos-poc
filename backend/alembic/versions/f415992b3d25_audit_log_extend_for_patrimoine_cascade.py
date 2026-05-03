"""audit_log_extend_for_patrimoine_cascade

Revision ID: f415992b3d25
Revises: c8f1246522f9
Create Date: 2026-05-03 22:32:07.962055

Sprint C-2 Phase 1 — Extension iam.AuditLog pour patrimoine + cascade events.

Source : matrice v1 §6.10 + audit Phase B R9 (audit_log_service dédié).

Note : autogenerate Alembic a initialement produit 17 op.drop_table() sur des
tables Enedis legacy (annotations, meter_load_curve, meter_energy_index,
meter_power_peak, enedis_opendata_conso_inf36/sup36, enedis_flux_mesure_r151/
r171/r4x/r50, enedis_flux_file, enedis_flux_file_error, enedis_ingestion_run,
unmatched_prm, promotion_run, promotion_event, annotator_profiles) sans
modèle SQLAlchemy actif. Ces drops ont été RETIRÉS manuellement — leur
traitement est tracé sous D-Enedis-Legacy-001 (cf. DETTE_TECHNIQUE_TRACKER.md).
Pattern identique à Sprint C-1 Phase 3 (migration c8f1246522f9).

Cette migration ne contient QUE :
- 6 op.add_column sur audit_logs (correlation_id, org_id, field_modified,
  old_value, new_value, user_agent)
- 2 op.create_index (ix_audit_correlation_id, ix_audit_org_id_resource_type_created)

Toutes les nouvelles colonnes sont nullable=True → backward compat 9 callsites
legacy AuditLog (cx_logger, intake_service, operat_export_service, copilot_engine,
iam_service, routes/patrimoine/sites.py).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f415992b3d25"
down_revision: Union[str, Sequence[str], None] = "c8f1246522f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema : ajouter 6 colonnes + 2 index sur audit_logs."""
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        # 6 nouvelles colonnes nullable (backward compat 9 callsites legacy)
        batch_op.add_column(
            sa.Column(
                "correlation_id",
                sa.String(length=64),
                nullable=True,
                comment="Sprint C-2 Phase 1 — corrélation cross-services",
            )
        )
        batch_op.add_column(
            sa.Column(
                "org_id",
                sa.Integer(),
                nullable=True,
                comment="Sprint C-2 Phase 1 — scoping multi-tenant queries audit",
            )
        )
        batch_op.add_column(
            sa.Column(
                "field_modified",
                sa.String(length=100),
                nullable=True,
                comment="Sprint C-2 Phase 1 — champ modifié (cascade trigger ou PATCH event)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "old_value",
                sa.Text(),
                nullable=True,
                comment="Sprint C-2 Phase 1 — valeur avant modification (JSON serialized)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "new_value",
                sa.Text(),
                nullable=True,
                comment="Sprint C-2 Phase 1 — valeur après modification (JSON serialized)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "user_agent",
                sa.String(length=500),
                nullable=True,
                comment="Sprint C-2 Phase 1 — User-Agent HTTP du client",
            )
        )

        # 2 nouveaux index
        batch_op.create_index(
            "ix_audit_correlation_id",
            ["correlation_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_audit_org_id_resource_type_created",
            ["org_id", "resource_type", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema : retirer 6 colonnes + 2 index de audit_logs."""
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        # Drop index avant drop column
        batch_op.drop_index("ix_audit_org_id_resource_type_created")
        batch_op.drop_index("ix_audit_correlation_id")

        batch_op.drop_column("user_agent")
        batch_op.drop_column("new_value")
        batch_op.drop_column("old_value")
        batch_op.drop_column("field_modified")
        batch_op.drop_column("org_id")
        batch_op.drop_column("correlation_id")
