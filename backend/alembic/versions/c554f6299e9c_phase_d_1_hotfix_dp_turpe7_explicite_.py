"""Phase D-1 hotfix Patrimoine — DP TURPE 7 explicite + Org enrichi entreprise (audit Sprint Patrimoine v1)

Revision ID: c554f6299e9c
Revises: 252890dd94e4
Create Date: 2026-05-07

14e migration Alembic Phase C+, 0 destructive cumulée.

Anti-DROP discipline 14e épisode : 75 drops autogenerate retirés (legacy enedis_*,
meter_*, promotion_*, annotations, unmatched_prm — backups préservés
.original-autogenerate cumul Phase C+ 14 épisodes systémiques).

Clôture 2 P1 audit Sprint Patrimoine v1 (commit f738f1d0) :

D-Audit-PARAM-DP-TURPE7-Explicite-006 P1 :
- delivery_points.categorie_turpe (C5/C4/C3/C2/C1) — matrice v1 §4.6
- delivery_points.domaine_tension (BT≤36kVA/BT>36kVA/HTA/HTB)
- delivery_points.code_fta (Formule Tarifaire d'Acheminement)
- delivery_points.version_turpe (TURPE_6/TURPE_7)
- delivery_points.mode_traitement (smart/traditionnel/telereleve/manuel)
- Cohérent CRE délibération 2025-78 du 13/03/2025 TURPE 7 HTA-BT

D-Audit-PARAM-Org-Champs-004 P1 :
- organisations.tva_intra (FR + 11 chars)
- organisations.code_naf_principal (ex: 6201Z, indexé)
- organisations.pays (ISO 3166-1 alpha-2, défaut FR)
- organisations.secteur (industrie/tertiaire_bureaux/etc.)
- organisations.effectif_total (TPE/PME/ETI/GE)
- organisations.chiffre_affaires_eur (segmentation Audit SMÉ)

Cumul Phase C+ : 14 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c554f6299e9c"
down_revision: Union[str, Sequence[str], None] = "252890dd94e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — 11 colonnes ajoutées (5 DP TURPE 7 + 6 Org enrichi)."""

    # ─── DP TURPE 7 explicite (5 colonnes matrice v1 §4.6) ──────────────────
    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "categorie_turpe",
                sa.String(length=20),
                nullable=True,
                comment="Catégorie TURPE explicite (C5, C4, C3, C2, C1) — matrice v1 §4.6",
            )
        )
        batch_op.add_column(
            sa.Column(
                "domaine_tension",
                sa.String(length=20),
                nullable=True,
                comment="Domaine tension (BT≤36kVA, BT>36kVA, HTA, HTB) — matrice v1 §4.6",
            )
        )
        batch_op.add_column(
            sa.Column(
                "code_fta",
                sa.String(length=50),
                nullable=True,
                comment="Formule Tarifaire d'Acheminement — matrice v1 §4.6",
            )
        )
        batch_op.add_column(
            sa.Column(
                "version_turpe",
                sa.String(length=10),
                nullable=True,
                comment="Version TURPE active (TURPE_6, TURPE_7)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "mode_traitement",
                sa.String(length=20),
                nullable=True,
                comment="Mode traitement compteur (smart, traditionnel, telereleve, manuel)",
            )
        )

    # ─── Org enrichi entreprise (6 colonnes matrice v1 §4.1) ────────────────
    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tva_intra",
                sa.String(length=20),
                nullable=True,
                comment="N° TVA intracommunautaire — matrice v1 §4.1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "code_naf_principal",
                sa.String(length=10),
                nullable=True,
                comment="Code NAF principal entreprise — matrice v1 §4.1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "pays",
                sa.String(length=2),
                nullable=True,
                server_default="FR",
                comment="Pays (ISO 3166-1 alpha-2) — matrice v1 §4.1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "secteur",
                sa.String(length=50),
                nullable=True,
                comment="Secteur d'activité — matrice v1 §4.1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "effectif_total",
                sa.Integer(),
                nullable=True,
                comment="Effectif total entreprise — matrice v1 §4.1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "chiffre_affaires_eur",
                sa.Float(),
                nullable=True,
                comment="Chiffre d'affaires annuel EUR — matrice v1 §4.1",
            )
        )
        batch_op.create_index("ix_organisations_code_naf_principal", ["code_naf_principal"], unique=False)


def downgrade() -> None:
    """Downgrade schema — retire les 11 colonnes ajoutées."""
    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.drop_index("ix_organisations_code_naf_principal")
        batch_op.drop_column("chiffre_affaires_eur")
        batch_op.drop_column("effectif_total")
        batch_op.drop_column("secteur")
        batch_op.drop_column("pays")
        batch_op.drop_column("code_naf_principal")
        batch_op.drop_column("tva_intra")

    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.drop_column("mode_traitement")
        batch_op.drop_column("version_turpe")
        batch_op.drop_column("code_fta")
        batch_op.drop_column("domaine_tension")
        batch_op.drop_column("categorie_turpe")
