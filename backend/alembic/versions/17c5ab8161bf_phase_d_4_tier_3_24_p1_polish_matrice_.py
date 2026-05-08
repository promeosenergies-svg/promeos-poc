"""Phase D-4 Tier 3 — 24 P1 polish matrice v1 (Portefeuille + Batiment + DP + EJ)

Revision ID: 17c5ab8161bf
Revises: 531b64deea87
Create Date: 2026-05-08

18e migration Alembic Phase C+, 0 destructive cumulée.

Anti-DROP discipline 18e épisode (autogenerate drops legacy retirés —
backups préservés .original-autogenerate).

24 P1 polish matrice v1 résiduels (Phase D-4 Tier 3 — couverture matrice ~90% → ~100%) :

- §4.3 Portefeuille (6 colonnes) : responsable_id (FK User SET NULL) + actif (NOT NULL default=1)
  + couleur_ui (validator hex) + tags (JSON) + code_interne (indexé) + notes
- §4.5 Batiment (4 colonnes) : siret_batiment (validator 14 chiffres) + etage_count
  (range -5/200) + efa_operat_id + parties_communes_pct (range 0-100)
- §4.6.B DP élec (4 colonnes) : puissances_souscrites_par_plage (JSON LU) + tan_phi_mesure
  + dataconnect_token_expires_at + dataconnect_scopes (JSON 4 scopes)
- §4.6.C DP gaz (3 colonnes) : zone_implantation + pitd_code + adict_token_expires_at
- §4.2 EJ (7 colonnes) : telephone + email_contact (PII SoT pii_sanitizer) + site_web
  (normalisation https://) + type_societe + date_creation_societe + capital_social_eur
  + representant_legal_nom

Cumul Phase C+ : 18 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "17c5ab8161bf"
down_revision: Union[str, Sequence[str], None] = "531b64deea87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — 24 colonnes ajoutées + 1 FK + 2 index."""

    # §4.3 Portefeuille — 6 P1 polish
    with op.batch_alter_table("portefeuilles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("responsable_id", sa.Integer(), nullable=True, comment="Responsable portefeuille (FK User)")
        )
        batch_op.add_column(
            sa.Column(
                "actif",
                sa.Boolean(),
                nullable=False,
                server_default="1",
                comment="Portefeuille actif (cohérent SoftDeleteMixin)",
            )
        )
        batch_op.add_column(
            sa.Column("couleur_ui", sa.String(length=7), nullable=True, comment="Couleur UI hex #RRGGBB")
        )
        batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=True, comment="Tags JSON libres"))
        batch_op.add_column(sa.Column("code_interne", sa.String(length=50), nullable=True, comment="Code interne"))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True, comment="Notes libres"))
        batch_op.create_index("ix_portefeuilles_responsable_id", ["responsable_id"], unique=False)
        batch_op.create_index("ix_portefeuilles_code_interne", ["code_interne"], unique=False)
        batch_op.create_foreign_key(
            "fk_portefeuilles_responsable_id",
            "users",
            ["responsable_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # §4.5 Batiment — 4 P1 polish
    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("siret_batiment", sa.String(length=14), nullable=True, comment="SIRET bâtiment"))
        batch_op.add_column(sa.Column("etage_count", sa.Integer(), nullable=True, comment="Nombre d'étages (-5 à 200)"))
        batch_op.add_column(
            sa.Column("efa_operat_id", sa.String(length=50), nullable=True, comment="EFA OPERAT bâtiment")
        )
        batch_op.add_column(
            sa.Column("parties_communes_pct", sa.Float(), nullable=True, comment="Parties communes % (0-100)")
        )

    # §4.6.B DP élec + §4.6.C DP gaz — 7 P1 polish
    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("puissances_souscrites_par_plage", sa.JSON(), nullable=True, comment="Puissances par plage (LU)")
        )
        batch_op.add_column(sa.Column("tan_phi_mesure", sa.Float(), nullable=True, comment="Tan(phi) HTA"))
        batch_op.add_column(
            sa.Column(
                "dataconnect_token_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Expiration token DataConnect OAuth2",
            )
        )
        batch_op.add_column(
            sa.Column("dataconnect_scopes", sa.JSON(), nullable=True, comment="Scopes DataConnect actifs")
        )
        batch_op.add_column(
            sa.Column("zone_implantation", sa.String(length=50), nullable=True, comment="Zone implantation gaz")
        )
        batch_op.add_column(sa.Column("pitd_code", sa.String(length=20), nullable=True, comment="PITD code"))
        batch_op.add_column(
            sa.Column(
                "adict_token_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Expiration token ADICT GRDF",
            )
        )

    # §4.2 EJ — 7 P1 polish
    with op.batch_alter_table("entites_juridiques", schema=None) as batch_op:
        batch_op.add_column(sa.Column("telephone", sa.String(length=30), nullable=True, comment="Téléphone"))
        batch_op.add_column(sa.Column("email_contact", sa.String(length=255), nullable=True, comment="Email contact"))
        batch_op.add_column(sa.Column("site_web", sa.String(length=500), nullable=True, comment="Site web HTTPS"))
        batch_op.add_column(
            sa.Column("type_societe", sa.String(length=50), nullable=True, comment="Type société (SA/SAS/SARL)")
        )
        batch_op.add_column(
            sa.Column("date_creation_societe", sa.Date(), nullable=True, comment="Date création société")
        )
        batch_op.add_column(sa.Column("capital_social_eur", sa.Float(), nullable=True, comment="Capital social EUR"))
        batch_op.add_column(
            sa.Column("representant_legal_nom", sa.String(length=255), nullable=True, comment="Représentant légal")
        )


def downgrade() -> None:
    """Downgrade schema — retrait 24 colonnes + 1 FK + 2 index."""
    with op.batch_alter_table("entites_juridiques", schema=None) as batch_op:
        batch_op.drop_column("representant_legal_nom")
        batch_op.drop_column("capital_social_eur")
        batch_op.drop_column("date_creation_societe")
        batch_op.drop_column("type_societe")
        batch_op.drop_column("site_web")
        batch_op.drop_column("email_contact")
        batch_op.drop_column("telephone")

    with op.batch_alter_table("delivery_points", schema=None) as batch_op:
        batch_op.drop_column("adict_token_expires_at")
        batch_op.drop_column("pitd_code")
        batch_op.drop_column("zone_implantation")
        batch_op.drop_column("dataconnect_scopes")
        batch_op.drop_column("dataconnect_token_expires_at")
        batch_op.drop_column("tan_phi_mesure")
        batch_op.drop_column("puissances_souscrites_par_plage")

    with op.batch_alter_table("batiments", schema=None) as batch_op:
        batch_op.drop_column("parties_communes_pct")
        batch_op.drop_column("efa_operat_id")
        batch_op.drop_column("etage_count")
        batch_op.drop_column("siret_batiment")

    with op.batch_alter_table("portefeuilles", schema=None) as batch_op:
        batch_op.drop_constraint("fk_portefeuilles_responsable_id", type_="foreignkey")
        batch_op.drop_index("ix_portefeuilles_code_interne")
        batch_op.drop_index("ix_portefeuilles_responsable_id")
        batch_op.drop_column("notes")
        batch_op.drop_column("code_interne")
        batch_op.drop_column("tags")
        batch_op.drop_column("couleur_ui")
        batch_op.drop_column("actif")
        batch_op.drop_column("responsable_id")
