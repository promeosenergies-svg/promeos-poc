"""Phase D-4 Tier 1 — 10 P0 cardinaux matrice v1 (audit écarts AUDIT_ECARTS_MATRICE_V1_2026_05_07)

Revision ID: 7f318cc8fb86
Revises: 483f25dd86d3
Create Date: 2026-05-08

16e migration Alembic Phase C+, 0 destructive cumulée.

Anti-DROP discipline 16e épisode : 17 drops autogenerate retirés (legacy
annotations, meter_*, enedis_flux_*, promotion_*, unmatched_prm, opendata_*,
backups préservés .original-autogenerate).

Ajouts cardinaux 10 P0 matrice v1 (post audit AUDIT_ECARTS_MATRICE_V1_2026_05_07.md) :

- P0-MATV1-001 : `entites_juridiques.consommation_annuelle_moyenne_3y_gwh`
  (Float — déclencheur Audit SMÉ deadline 11/10/2026, seuils 2.75/23.6 GWh)

- P0-MATV1-002 + 003 : `delivery_points.accise_categorie_gaz/elec`
  (String CIBS — ADR-D-05, bloque billing CIBS L.312-24/36/37)

- P0-MATV1-004 : `sites.consentement_site_overrides`
  (JSON — cascade RGPD §6.1 herite_entite/accepte_local/refuse_local)

- P0-MATV1-005 : `sites.bacs_assujetti` + `sites.bacs_puissance_cvc_totale_kw`
  (Boolean + Float — ADR-D-04 cascade Σ Batiment.cvc_power_kw, score BACS §8.4)

- P0-MATV1-006 + 007 + 008 : `delivery_points.pce_format/type_reseau/referentiel_tarifaire/est_profile/mode_releve_gaz`
  (5 String matérialisés — ADR-D-02, traçabilité audit + perf billing gaz)

- P0-MATV1-009 : `batiments.categorie_operat_batiment`
  (String — contrainte A9 cardinale Cabs Site MIXTE multi-bâtiments)

- P0-MATV1-010 : `compteurs.batiment_id` FK → batiments.id (ondelete=SET NULL)
  (ADR-D-03 — différenciateur agrégation conso par bâtiment)

Cumul Phase C+ : 16 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7f318cc8fb86"
down_revision: Union[str, Sequence[str], None] = "483f25dd86d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — 11 colonnes + 1 FK + 1 index ajoutés."""

    # P0-MATV1-001 — EntiteJuridique.consommation_annuelle_moyenne_3y_gwh
    with op.batch_alter_table("entites_juridiques", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "consommation_annuelle_moyenne_3y_gwh",
                sa.Float(),
                nullable=True,
                comment="Consommation annuelle moyenne 3 ans (GWh) — déclencheur Audit SMÉ matrice v1 §4.2#18",
            )
        )

    # P0-MATV1-002 + 003 + 006 + 007 + 008 — DeliveryPoint 7 colonnes (DP gaz + accise CIBS)
    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "pce_format",
                sa.String(length=20),
                nullable=True,
                comment="Format PCE/PRM gaz (DISTRIBUTION_14/DISTRIBUTION_GI/TRANSPORT_PIR) — ADR-D-02",
            )
        )
        batch_op.add_column(
            sa.Column(
                "type_reseau",
                sa.String(length=20),
                nullable=True,
                comment="Type réseau gaz (DISTRIBUTION/TRANSPORT) — ADR-D-02",
            )
        )
        batch_op.add_column(
            sa.Column(
                "referentiel_tarifaire",
                sa.String(length=10),
                nullable=True,
                comment="Référentiel tarifaire gaz (ATRD/ATRT) — ADR-D-02",
            )
        )
        batch_op.add_column(
            sa.Column(
                "est_profile",
                sa.Boolean(),
                nullable=True,
                comment="True si DP gaz profilé (T1/T2/T3) — ADR-D-02",
            )
        )
        batch_op.add_column(
            sa.Column(
                "mode_releve_gaz",
                sa.String(length=10),
                nullable=True,
                comment="Mode relevé gaz (MM/MJ/JJ/MH) — ADR-D-02",
            )
        )
        batch_op.add_column(
            sa.Column(
                "accise_categorie_elec",
                sa.String(length=30),
                nullable=True,
                comment="Catégorie accise CIBS élec (MENAGES_ASSIMILES/PME/HAUTE_PUISSANCE) — ADR-D-05",
            )
        )
        batch_op.add_column(
            sa.Column(
                "accise_categorie_gaz",
                sa.String(length=20),
                nullable=True,
                comment="Catégorie accise CIBS gaz (NATUREL/GPL/GNL) — ADR-D-05",
            )
        )

    # P0-MATV1-004 + 005 — Site cascade RGPD + BACS agrégé
    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "consentement_site_overrides",
                sa.JSON(),
                nullable=True,
                comment="JSON cascade RGPD Org→Site override (herite_entite/accepte_local/refuse_local)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "bacs_assujetti",
                sa.Boolean(),
                nullable=True,
                comment="Site assujetti BACS (puissance_cvc_totale_kw ≥ 70 kW) — ADR-D-04",
            )
        )
        batch_op.add_column(
            sa.Column(
                "bacs_puissance_cvc_totale_kw",
                sa.Float(),
                nullable=True,
                comment="Puissance CVC totale Site (Σ Batiment.cvc_power_kw cascade ADR-D-04)",
            )
        )

    # P0-MATV1-009 — Batiment.categorie_operat_batiment
    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "categorie_operat_batiment",
                sa.String(length=50),
                nullable=True,
                comment="Catégorie OPERAT bâtiment (héritée Site override possible) — A9 contrainte cardinale",
            )
        )

    # P0-MATV1-010 — Compteur.batiment_id FK ondelete=SET NULL (ADR-D-03)
    with op.batch_alter_table("compteurs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "batiment_id",
                sa.Integer(),
                nullable=True,
                comment="Bâtiment de rattachement (matrice v1 §4.6.A#12 — agrégation conso par bâtiment)",
            )
        )
        batch_op.create_index("ix_compteurs_batiment_id", ["batiment_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_compteurs_batiment_id",
            "batiments",
            ["batiment_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema — retrait 11 colonnes + 1 FK + 1 index ajoutés."""
    with op.batch_alter_table("compteurs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_compteurs_batiment_id", type_="foreignkey")
        batch_op.drop_index("ix_compteurs_batiment_id")
        batch_op.drop_column("batiment_id")

    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.drop_column("categorie_operat_batiment")

    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.drop_column("bacs_puissance_cvc_totale_kw")
        batch_op.drop_column("bacs_assujetti")
        batch_op.drop_column("consentement_site_overrides")

    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.drop_column("accise_categorie_gaz")
        batch_op.drop_column("accise_categorie_elec")
        batch_op.drop_column("mode_releve_gaz")
        batch_op.drop_column("est_profile")
        batch_op.drop_column("referentiel_tarifaire")
        batch_op.drop_column("type_reseau")
        batch_op.drop_column("pce_format")

    with op.batch_alter_table("entites_juridiques", schema=None) as batch_op:
        batch_op.drop_column("consommation_annuelle_moyenne_3y_gwh")
