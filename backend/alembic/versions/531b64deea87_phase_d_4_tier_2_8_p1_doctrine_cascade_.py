"""Phase D-4 Tier 2 — 8 P1 doctrine + cascade BACS active (ADR-D-04)

Revision ID: 531b64deea87
Revises: 7f318cc8fb86
Create Date: 2026-05-08

17e migration Alembic Phase C+, 0 destructive cumulée.

Anti-DROP discipline 17e épisode (autogenerate drops legacy retirés —
backups préservés .original-autogenerate).

Ajouts cardinaux Phase D-4 Tier 2 (8 P1 doctrine matrice v1) :

- P1-MATV1-011→016 : EJ adresse_siege + code_postal_siege + commune_siege +
  pays + effectif_etp + chiffre_affaires_eur (Sirène round-trip + Audit SMÉ co-déclencheurs)
- P1-MATV1-023 + 024 : Batiment usage_batiment (UsageBatimentEnum) + dpe_emissions_kgco2_m2
- P1-MATV1-028 : DeliveryPoint cdc_pas_temporel_minutes (Integer, range CDC_PAS_MIN/MAX_MINUTES)
- P1-MATV1-033 : DeliveryPoint pcs_kwh_par_nm3 (Float, range PCS_GAZ_MIN/MAX_KWH_NM3)
- P1-MATV1-038 : ContractPricing indice_reference (String 30 — IndiceReferenceEnum)

+ ADR-D-04 cascade BACS active : service compute_site_bacs_aggregate /
  recompute_site_bacs_aggregate (`backend/services/cascade_bacs_service.py`).

Cumul Phase C+ : 17 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "531b64deea87"
down_revision: Union[str, Sequence[str], None] = "7f318cc8fb86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — 11 colonnes ajoutées (6 EJ + 2 Batiment + 2 DP + 1 ContractPricing)."""

    # P1-MATV1-011→016 — EntiteJuridique 6 colonnes adresse + Audit SMÉ co-déclencheurs
    with op.batch_alter_table("entites_juridiques", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "adresse_siege", sa.String(length=500), nullable=True, comment="Adresse siège — matrice v1 §4.2#9"
            )
        )
        batch_op.add_column(
            sa.Column("code_postal_siege", sa.String(length=5), nullable=True, comment="Code postal siège")
        )
        batch_op.add_column(sa.Column("commune_siege", sa.String(length=100), nullable=True, comment="Commune siège"))
        batch_op.add_column(
            sa.Column(
                "pays",
                sa.String(length=2),
                nullable=True,
                server_default="FR",
                comment="Pays ISO 3166-1 alpha-2",
            )
        )
        batch_op.add_column(
            sa.Column(
                "effectif_etp",
                sa.Integer(),
                nullable=True,
                comment="Effectif ETP — co-déclencheur Audit SMÉ matrice v1 §4.2#16",
            )
        )
        batch_op.add_column(
            sa.Column(
                "chiffre_affaires_eur",
                sa.Float(),
                nullable=True,
                comment="CA annuel EUR — co-déclencheur Audit SMÉ matrice v1 §4.2#17",
            )
        )

    # P1-MATV1-023 + 024 — Batiment usage_batiment + dpe_emissions
    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "usage_batiment",
                sa.String(length=50),
                nullable=True,
                comment="Usage principal bâtiment (UsageBatimentEnum) — matrice v1 §4.5#9",
            )
        )
        batch_op.add_column(
            sa.Column(
                "dpe_emissions_kgco2_m2",
                sa.Float(),
                nullable=True,
                comment="Émissions DPE bâtiment (kgCO2e/m²/an) — matrice v1 §4.5#14",
            )
        )

    # P1-MATV1-028 + 033 — DeliveryPoint cdc_pas + pcs_kwh
    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "cdc_pas_temporel_minutes",
                sa.Integer(),
                nullable=True,
                comment="Pas temporel CDC Enedis (min, range 1-60) — matrice v1 §4.6.B#8",
            )
        )
        batch_op.add_column(
            sa.Column(
                "pcs_kwh_par_nm3",
                sa.Float(),
                nullable=True,
                comment="PCS gaz (kWh/Nm³, range 9.0-13.0) — matrice v1 §4.6.C#13",
            )
        )

    # P1-MATV1-038 — ContractPricing indice_reference (String(30) P1-A audit code-reviewer)
    with op.batch_alter_table("contract_pricing", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "indice_reference",
                sa.String(length=30),
                nullable=True,
                comment="Indice référence formule indexation (IndiceReferenceEnum) — matrice v1 §4.8.C#5",
            )
        )


def downgrade() -> None:
    """Downgrade schema — retrait 11 colonnes."""
    with op.batch_alter_table("contract_pricing", schema=None) as batch_op:
        batch_op.drop_column("indice_reference")

    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.drop_column("pcs_kwh_par_nm3")
        batch_op.drop_column("cdc_pas_temporel_minutes")

    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.drop_column("dpe_emissions_kgco2_m2")
        batch_op.drop_column("usage_batiment")

    with op.batch_alter_table("entites_juridiques", schema=None) as batch_op:
        batch_op.drop_column("chiffre_affaires_eur")
        batch_op.drop_column("effectif_etp")
        batch_op.drop_column("pays")
        batch_op.drop_column("commune_siege")
        batch_op.drop_column("code_postal_siege")
        batch_op.drop_column("adresse_siege")
