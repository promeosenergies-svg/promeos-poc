"""site_operat_aper_efa_fields_18cols

Revision ID: c8f1246522f9
Revises: 2f83c6bebc57
Create Date: 2026-05-03 19:42:20.062733

Phase 3 — Sprint C-1 — Matrice v1 §4.4.C/D/G

Note : autogenerate Alembic a initialement produit 17 op.drop_table() sur des
tables Enedis legacy (annotations, meter_load_curve, meter_energy_index,
meter_power_peak, enedis_opendata_conso_inf36/sup36, enedis_flux_mesure_r151/
r171/r4x/r50, enedis_flux_file, enedis_flux_file_error, enedis_ingestion_run,
unmatched_prm, promotion_run, promotion_event, annotator_profiles) sans
modèle SQLAlchemy actif. Ces drops ont été retirés manuellement — leur
traitement est reporté en sprint séparé "Audit data lineage Enedis legacy"
(hors scope C-1, cf. docs/audits/DETTE_TECHNIQUE_TRACKER.md ligne D-Enedis-Legacy-001).

Cette migration ne contient QUE les 18 ajouts de colonnes Site OPERAT/APER/EFA
demandés par la matrice v1 §4.4.C (13 OPERAT) + §4.4.D (5 APER) + §4.4.G
(efa_id partagé OPERAT/EFA).

Convention SQLAlchemy : sa.Enum(<EnumClass>, native_enum=False) sur SQLite
→ CHECK constraint listant les valeurs ; sur PostgreSQL (cible roadmap) →
type ENUM natif sans cassure.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8f1246522f9"
down_revision: Union[str, Sequence[str], None] = "2f83c6bebc57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema : ajouter 18 colonnes OPERAT/APER/EFA sur table sites."""
    with op.batch_alter_table("sites", schema=None) as batch_op:
        # ─── OPERAT — matrice v1 §4.4.C (13 champs) ───
        batch_op.add_column(
            sa.Column(
                "operat_zone_climatique",
                sa.Enum(
                    "H1A",
                    "H1B",
                    "H1C",
                    "H2A",
                    "H2B",
                    "H2C",
                    "H2D",
                    "H3",
                    "GUADELOUPE",
                    "MARTINIQUE",
                    "GUYANE",
                    "REUNION",
                    "MAYOTTE",
                    name="operatzoneclimatiqueenum",
                    native_enum=False,
                ),
                nullable=True,
                comment="Matrice v1 §4.4.C #25 — Zone climatique OPERAT (résolue depuis code_postal/altitude)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "operat_palier_altitude",
                sa.Enum(
                    "LT_400",
                    "BETW_400_800",
                    "BETW_800_1200",
                    "BETW_1200_1600",
                    "GTE_1600",
                    name="operatpalieraltitudeenum",
                    native_enum=False,
                ),
                nullable=True,
                comment="Matrice v1 §4.4.C #26 — Palier altitude OPERAT (5 paliers stricts Annexe I)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "altitude_m",
                sa.Integer(),
                nullable=True,
                comment="Matrice v1 §4.4.C #27 — Altitude en mètres (input pour résoudre operat_palier_altitude)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "operat_sous_categorie_id",
                sa.String(length=50),
                nullable=True,
                comment="Matrice v1 §4.4.C #28 — Identifiant sous-catégorie OPERAT (parmi 426 Annexe I)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "operat_iiu_temporels",
                sa.JSON(),
                nullable=True,
                comment="Matrice v1 §4.4.C #29 — Indicateurs Intensité Usage temporels (heures/jours)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "operat_iiu_surfaciques",
                sa.JSON(),
                nullable=True,
                comment="Matrice v1 §4.4.C #30 — Indicateurs Intensité Usage surfaciques (m²)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "cabs_kwh_m2_an",
                sa.Float(),
                nullable=True,
                comment="Matrice v1 §4.4.C #31 — Cabs 2030 calculé via OperatValeursAbsoluesService (kWh/m²/an)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "crelat_kwh_m2_an",
                sa.Float(),
                nullable=True,
                comment="Matrice v1 §4.4.C — Crelat (objectif relatif) calculé alternativement à Cabs (kWh/m²/an)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "usage_principal",
                sa.Enum(
                    "BUREAUX",
                    "COMMERCES",
                    "ENSEIGNEMENT",
                    "HOTELLERIE",
                    "RESTAURATION",
                    "SANTE",
                    "SPORT_LOISIRS",
                    "LOGISTIQUE",
                    "MIXTE",
                    name="operatusageprincipalenum",
                    native_enum=False,
                ),
                nullable=True,
                comment="Matrice v1 §4.4.C #32 — Usage principal du site (catégorie macro OPERAT)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "efa_id",
                sa.String(length=50),
                nullable=True,
                comment="Matrice v1 §4.4.G — Identifiant EFA (Entité Fonctionnelle Assujettie OPERAT)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "annee_reference_operat",
                sa.Integer(),
                nullable=True,
                comment="Matrice v1 §4.4.C #33 — Année de référence OPERAT (entre 2010 et 2022)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "methode_modulation_dt",
                sa.Enum(
                    "COUT_DISPROPORTIONNE",
                    "CONSEQUENCES_NEGATIVES",
                    "PATRIMOINE_INCOMPATIBILITE",
                    "CHANGEMENT_ACTIVITE",
                    name="operatmodulationmotifenum",
                    native_enum=False,
                ),
                nullable=True,
                comment="Matrice v1 §4.4.C #34 — Motif de modulation DT (4 motifs officiels art. 12)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "dossier_modulation_id",
                sa.String(length=50),
                nullable=True,
                comment="Matrice v1 §4.4.C #35 — ID dossier de modulation déposé (avant 30/09/2026)",
            )
        )

        # ─── APER — matrice v1 §4.4.D (5 champs) ───
        batch_op.add_column(
            sa.Column(
                "aper_assujetti",
                sa.Boolean(),
                nullable=True,
                comment="Matrice v1 §4.4.D #37 — Site assujetti APER (calculé via parking_area_m2 ≥ 1500, cascade Phase 6)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "aper_categorie_taille",
                sa.Enum(
                    "SMALL",
                    "LARGE",
                    name="apercategorietailleenum",
                    native_enum=False,
                ),
                nullable=True,
                comment="Matrice v1 §4.4.D #38 — SMALL (1500-10000) ou LARGE (>10000) m²",
            )
        )
        batch_op.add_column(
            sa.Column(
                "aper_deadline",
                sa.Date(),
                nullable=True,
                comment="Matrice v1 §4.4.D #39 — Échéance APER (01/07/2026 LARGE, 01/07/2028 SMALL)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "parking_solar_pct_engaged",
                sa.Float(),
                nullable=True,
                comment="Matrice v1 §4.4.D #40 — Pourcentage parking engagé en solarisation (0-100)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "aper_exemption_motif",
                sa.Enum(
                    "CONTRAINTES_TECHNIQUES",
                    "CONTRAINTES_PATRIMONIALES",
                    "CONTRAINTES_ECONOMIQUES",
                    "CONTRAINTES_OPERATIONNELLES",
                    name="aperexemptionmotifenum",
                    native_enum=False,
                ),
                nullable=True,
                comment="Matrice v1 §4.4.D #41 — Motif d'exemption APER si applicable",
            )
        )

        # Index sur efa_id pour lookup rapide (matrice v1 §4.4.G)
        batch_op.create_index(batch_op.f("ix_sites_efa_id"), ["efa_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema : retirer 18 colonnes OPERAT/APER/EFA de table sites.

    Ordre de drop inverse de l'add (cosmétique pour SQLite, mais respecté pour
    cohérence et lisibilité).
    """
    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sites_efa_id"))

        # APER (5)
        batch_op.drop_column("aper_exemption_motif")
        batch_op.drop_column("parking_solar_pct_engaged")
        batch_op.drop_column("aper_deadline")
        batch_op.drop_column("aper_categorie_taille")
        batch_op.drop_column("aper_assujetti")

        # OPERAT (13)
        batch_op.drop_column("dossier_modulation_id")
        batch_op.drop_column("methode_modulation_dt")
        batch_op.drop_column("annee_reference_operat")
        batch_op.drop_column("efa_id")
        batch_op.drop_column("usage_principal")
        batch_op.drop_column("crelat_kwh_m2_an")
        batch_op.drop_column("cabs_kwh_m2_an")
        batch_op.drop_column("operat_iiu_surfaciques")
        batch_op.drop_column("operat_iiu_temporels")
        batch_op.drop_column("operat_sous_categorie_id")
        batch_op.drop_column("altitude_m")
        batch_op.drop_column("operat_palier_altitude")
        batch_op.drop_column("operat_zone_climatique")
