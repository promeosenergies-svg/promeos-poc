"""energy_contract_alerte_renouvellement

Revision ID: 2e78ecc6040c
Revises: c2c806d24cd9
Create Date: 2026-05-04

Sprint C-2 Phase 5.3 — Création colonne alerte_renouvellement_logged_at sur
table `energy_contracts`. Flag idempotence cascade `EnergyContract.end_date`
→ alerte 90j (MVP Cas B : log structuré + flag, modèle Alert dédié reporté
Sprint C-5).

Note : autogenerate Alembic a initialement produit ~17 op.drop_table() sur
des tables Enedis legacy + IAM (annotator_profiles, enedis_flux_mesure_r151,
enedis_flux_mesure_r4x, meter_energy_index, unmatched_prm, meter_power_peak,
enedis_ingestion_run, enedis_opendata_conso_inf36, etc.). Ces drops ont été
RETIRÉS manuellement — pattern identique aux migrations :
- c8f1246522f9 (Sprint C-1 Phase 3 — Site +18 OPERAT/APER/EFA fields)
- f415992b3d25 (Sprint C-2 Phase 1.2 — audit_logs +6 cols)
- fcf1be2a087d (Sprint C-2 Phase 2 — site_portefeuille_history table)
- c2c806d24cd9 (Sprint C-2 Phase 4.2 — Site intensity 2 cols)

6e épisode de discipline anti-DROP : backup `.original-autogenerate` conservé.
Cf. tracker dette D-Enedis-Legacy-001.

Cette migration ne contient QUE :
- 1 op.add_column() sur table `energy_contracts` (alerte_renouvellement_logged_at)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2e78ecc6040c"
down_revision: Union[str, Sequence[str], None] = "c2c806d24cd9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema : ajouter alerte_renouvellement_logged_at sur energy_contracts."""
    with op.batch_alter_table("energy_contracts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "alerte_renouvellement_logged_at",
                sa.DateTime(),
                nullable=True,
                comment="Timestamp dernière log alerte renouvellement 90j (MVP Sprint C-2 Phase 5.3, modèle Alert dédié reporté Sprint C-5)",
            )
        )


def downgrade() -> None:
    """Downgrade schema : drop alerte_renouvellement_logged_at sur energy_contracts."""
    with op.batch_alter_table("energy_contracts", schema=None) as batch_op:
        batch_op.drop_column("alerte_renouvellement_logged_at")
