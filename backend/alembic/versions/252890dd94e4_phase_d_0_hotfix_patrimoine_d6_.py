"""Phase D-0 hotfix Patrimoine — D6 SousCompteur self-FK + Bâtiment RNB/DPE + Site categorie_operat (audit Sprint Patrimoine v1)

Revision ID: 252890dd94e4
Revises: a7da3ed8aeb4
Create Date: 2026-05-07

13e migration Alembic Phase C+, 0 destructive cumulée.

Anti-DROP discipline 13e épisode : 75 drops autogenerate retirés (legacy enedis_*,
meter_*, promotion_*, annotations, unmatched_prm — backups préservés
.original-autogenerate cumul Phase C+).

Clôture 3 P0 audit Sprint Patrimoine v1 (commit f738f1d0) :

D-Audit-PARAM-D6-SousCompteur-Self-FK-002 P0 :
- compteurs.sub_meter_of_id self-FK (D6 décision matrice v1 §3 honorée)
- compteurs.sub_meter_usage (CVC/IT/ECLAIRAGE/AUTRES)
- Différenciateur Mid-market premium pilotage par sous-compteur

D-Audit-PARAM-Bati-Champs-Manquants-001 P0 :
- batiments.rnb_id (Référentiel National Bâtiments V9.0 — obligatoire OPERAT 2026)
- batiments.dpe_class (A-G Décret 2020-1610 modifié 2024)
- batiments.dpe_score_kwhep_m2_an (énergie primaire)
- batiments.dpe_date_validite (Date)
- batiments.annee_renovation_lourde (base ajustée OPERAT post-rénovation)

D-Audit-PARAM-Site-Cat-Operat-Mode-Propriete-005 P0 :
- sites.categorie_operat_principale (catégorie macro OPERAT P0 Section 9.1)
- sites.mode_propriete (proprietaire/locataire/syndic — trace assujettissement DT)

Cumul Phase C+ : 13 migrations propres / 0 destructive (anti-DROP discipline 13e épisode).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "252890dd94e4"
down_revision: Union[str, Sequence[str], None] = "a7da3ed8aeb4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — 9 colonnes ajoutées (D6 SousCompteur + Bâtiment RNB/DPE + Site categorie_operat)."""

    # ─── D6 SousCompteur self-FK + sub_meter_usage (Compteur) ───────────────
    with op.batch_alter_table("compteurs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "sub_meter_of_id",
                sa.Integer(),
                nullable=True,
                comment="Compteur parent self-FK (D6) — sous-compteur pilotage CVC/IT/éclairage",
            )
        )
        batch_op.add_column(
            sa.Column(
                "sub_meter_usage",
                sa.String(length=50),
                nullable=True,
                comment="Usage sous-compteur si sub_meter_of_id non NULL (CVC, IT, ECLAIRAGE, AUTRES)",
            )
        )
        batch_op.create_index("ix_compteurs_sub_meter_of_id", ["sub_meter_of_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_compteurs_sub_meter_of_id_compteurs",
            "compteurs",
            ["sub_meter_of_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # ─── Bâtiment 5 champs cardinaux RNB/DPE/rénovation ─────────────────────
    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "rnb_id",
                sa.String(length=20),
                nullable=True,
                comment="Référentiel National Bâtiments V9.0 (matrice v1 §4.5 — obligatoire OPERAT 2026)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "dpe_class",
                sa.String(length=1),
                nullable=True,
                comment="Classe DPE A-G (matrice v1 §4.5 — Décret n° 2020-1610 modifié 2024)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "dpe_score_kwhep_m2_an",
                sa.Float(),
                nullable=True,
                comment="Score DPE en énergie primaire (kWhep/m²/an) — différenciateur intensité énergétique",
            )
        )
        batch_op.add_column(
            sa.Column(
                "dpe_date_validite",
                sa.Date(),
                nullable=True,
                comment="Date validité DPE (10 ans depuis émission) — alerte renouvellement",
            )
        )
        batch_op.add_column(
            sa.Column(
                "annee_renovation_lourde",
                sa.Integer(),
                nullable=True,
                comment="Année rénovation lourde (matrice v1 §4.5) — base ajustée OPERAT post-rénovation",
            )
        )
        batch_op.create_index("ix_batiments_rnb_id", ["rnb_id"], unique=False)

    # ─── Site categorie_operat_principale + mode_propriete ──────────────────
    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "categorie_operat_principale",
                sa.String(length=50),
                nullable=True,
                comment="Matrice v1 §4.4 — Catégorie OPERAT macro (Bureaux/Commerce/Enseignement/Santé/etc.)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "mode_propriete",
                sa.String(length=20),
                nullable=True,
                comment="Matrice v1 §4.4 — Mode propriété (proprietaire/locataire/syndic)",
            )
        )


def downgrade() -> None:
    """Downgrade schema — retire les 9 colonnes ajoutées."""
    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.drop_column("mode_propriete")
        batch_op.drop_column("categorie_operat_principale")

    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.drop_index("ix_batiments_rnb_id")
        batch_op.drop_column("annee_renovation_lourde")
        batch_op.drop_column("dpe_date_validite")
        batch_op.drop_column("dpe_score_kwhep_m2_an")
        batch_op.drop_column("dpe_class")
        batch_op.drop_column("rnb_id")

    with op.batch_alter_table("compteurs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_compteurs_sub_meter_of_id_compteurs", type_="foreignkey")
        batch_op.drop_index("ix_compteurs_sub_meter_of_id")
        batch_op.drop_column("sub_meter_usage")
        batch_op.drop_column("sub_meter_of_id")
