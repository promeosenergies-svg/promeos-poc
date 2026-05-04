"""site_intensity_kwh_m2_2cols

Revision ID: c2c806d24cd9
Revises: fcf1be2a087d
Create Date: 2026-05-04

Sprint C-2 Phase 4.2 — Création 2 colonnes intensity sur table `sites`
(matrice v1 §4.4.F #56) :

- intensity_kwh_m2_total      : annual_kwh_total / surface_m2          (UI legacy)
- intensity_kwh_m2_tertiaire  : annual_kwh_total / tertiaire_area_m2   (doctrine OPERAT/DT)

Note : autogenerate Alembic a initialement produit ~17 op.drop_table() sur
des tables Enedis legacy + IAM (annotator_profiles, enedis_flux_mesure_r151,
enedis_flux_mesure_r4x, meter_energy_index, unmatched_prm, meter_power_peak,
enedis_ingestion_run, enedis_opendata_conso_inf36, etc.). Ces drops ont été
RETIRÉS manuellement — pattern identique aux migrations :
- c8f1246522f9 (Sprint C-1 Phase 3 — Site +18 OPERAT/APER/EFA fields)
- f415992b3d25 (Sprint C-2 Phase 1.2 — audit_logs +6 cols)
- fcf1be2a087d (Sprint C-2 Phase 2 — site_portefeuille_history table)

5e épisode de discipline anti-DROP : backup `.original-autogenerate` conservé.
Cf. tracker dette D-Enedis-Legacy-001.

Cette migration ne contient QUE :
- 2 op.add_column() sur table `sites` (intensity_kwh_m2_total + tertiaire)

Permet :
- Persistance intensité énergétique par site (cascade depuis annual_kwh_total /
  surface_m2 / tertiaire_area_m2 via cascade_recompute_service)
- Élimination calculs kWh/m² inline frontend Patrimoine.jsx (Phase 4.3)
- Doctrine PROMEOS : zero business logic frontend
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2c806d24cd9"
down_revision: Union[str, Sequence[str], None] = "fcf1be2a087d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema : ajouter 2 colonnes intensity sur `sites`."""
    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "intensity_kwh_m2_total",
                sa.Float(),
                nullable=True,
                comment="Intensité énergétique = annual_kwh_total / surface_m2 (UI legacy, compat L825/L1528 Patrimoine.jsx)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "intensity_kwh_m2_tertiaire",
                sa.Float(),
                nullable=True,
                comment="Intensité énergétique = annual_kwh_total / tertiaire_area_m2 (doctrine OPERAT/DT)",
            )
        )


def downgrade() -> None:
    """Downgrade schema : drop 2 colonnes intensity sur `sites`."""
    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.drop_column("intensity_kwh_m2_tertiaire")
        batch_op.drop_column("intensity_kwh_m2_total")
