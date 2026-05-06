"""Phase 5.3 Sprint C-5 — Org/DP consentement_by + cgu_version (ADR-007 ext)

Revision ID: b86d01f19001
Revises: 478ee4a61ebb
Create Date: 2026-05-06 09:31:26.392184

9e migration Alembic Phase C, 0 destructive cumulée.

Anti-DROP discipline 9e épisode : 63 drop_table/drop_index autogenerate retirés
(annotator_profiles, enedis_opendata_conso_inf36/sup36, enedis_flux_mesure_r4x/r50/r151/r171,
enedis_flux_file/_error, enedis_ingestion_run, meter_load_curve/energy_index/power_peak,
promotion_run/_event, unmatched_prm, annotations).

Extension Sprint C-4 P4.4 (8 cols cardinaux) avec audit trail RGPD complet (ADR-007 ext) :

- organisations +4 cols :
  * consentement_dataconnect_by (Integer FK users.id ondelete=SET NULL)
  * consentement_dataconnect_cgu_version (String 20)
  * consentement_grdf_by (Integer FK users.id ondelete=SET NULL)
  * consentement_grdf_cgu_version (String 20)
- delivery_points +4 cols (override local audit RGPD) :
  * consentement_dataconnect_local_by (Integer FK users.id ondelete=SET NULL)
  * consentement_dataconnect_local_cgu_version (String 20)
  * consentement_grdf_local_by (Integer FK users.id ondelete=SET NULL)
  * consentement_grdf_local_cgu_version (String 20)

ondelete=SET NULL CARDINAL : suppression user (RGPD droit oubli) préserve l'historique
de consentement (la trace persiste, la référence personnelle disparaît). Cohérent
doctrine "preuve d'origine + valeur" — un consentement est traçable jusqu'au dernier
détail (qui, quand, sur quelle CGU).

Cumul Phase C : 9 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b86d01f19001"
down_revision: Union[str, Sequence[str], None] = "478ee4a61ebb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — 4 cols audit RGPD sur organisations + 4 sur delivery_points."""

    # ─── Organisation +4 cols (audit RGPD) ────────────────────────────────
    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "consentement_dataconnect_by",
                sa.Integer(),
                nullable=True,
                comment="User ayant donné le consentement DataConnect (RGPD audit, NULL si user supprimé)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "consentement_dataconnect_cgu_version",
                sa.String(length=20),
                nullable=True,
                comment="Version CGU au moment du consentement DataConnect (ex: '1.0', '2.1.0')",
            )
        )
        batch_op.add_column(
            sa.Column(
                "consentement_grdf_by",
                sa.Integer(),
                nullable=True,
                comment="User ayant donné le consentement GRDF (RGPD audit, NULL si user supprimé)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "consentement_grdf_cgu_version",
                sa.String(length=20),
                nullable=True,
                comment="Version CGU au moment du consentement GRDF",
            )
        )
        batch_op.create_foreign_key(
            "fk_organisations_consent_dataconnect_by_users",
            "users",
            ["consentement_dataconnect_by"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_organisations_consent_grdf_by_users",
            "users",
            ["consentement_grdf_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # ─── DeliveryPoint +4 cols (override local audit RGPD) ────────────────
    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "consentement_dataconnect_local_by",
                sa.Integer(),
                nullable=True,
                comment="User ayant donné l'override local DataConnect (RGPD audit, NULL si user supprimé)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "consentement_dataconnect_local_cgu_version",
                sa.String(length=20),
                nullable=True,
                comment="Version CGU au moment de l'override local DataConnect",
            )
        )
        batch_op.add_column(
            sa.Column(
                "consentement_grdf_local_by",
                sa.Integer(),
                nullable=True,
                comment="User ayant donné l'override local GRDF (RGPD audit, NULL si user supprimé)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "consentement_grdf_local_cgu_version",
                sa.String(length=20),
                nullable=True,
                comment="Version CGU au moment de l'override local GRDF",
            )
        )
        batch_op.create_foreign_key(
            "fk_delivery_points_consent_dataconnect_local_by_users",
            "users",
            ["consentement_dataconnect_local_by"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_delivery_points_consent_grdf_local_by_users",
            "users",
            ["consentement_grdf_local_by"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema — suppression défensive des 8 cols audit RGPD."""

    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.drop_constraint("fk_delivery_points_consent_grdf_local_by_users", type_="foreignkey")
        batch_op.drop_constraint("fk_delivery_points_consent_dataconnect_local_by_users", type_="foreignkey")
        batch_op.drop_column("consentement_grdf_local_cgu_version")
        batch_op.drop_column("consentement_grdf_local_by")
        batch_op.drop_column("consentement_dataconnect_local_cgu_version")
        batch_op.drop_column("consentement_dataconnect_local_by")

    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.drop_constraint("fk_organisations_consent_grdf_by_users", type_="foreignkey")
        batch_op.drop_constraint("fk_organisations_consent_dataconnect_by_users", type_="foreignkey")
        batch_op.drop_column("consentement_grdf_cgu_version")
        batch_op.drop_column("consentement_grdf_by")
        batch_op.drop_column("consentement_dataconnect_cgu_version")
        batch_op.drop_column("consentement_dataconnect_by")
