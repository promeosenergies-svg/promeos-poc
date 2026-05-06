"""Phase 7.1 Sprint C-7 — Site +1 col s_ce_m2 Surface CE Décret Tertiaire (clôture D-Phase4-2-Operat-Surfaces-3-Distinct)

Revision ID: f5df8bc45f8b
Revises: 86dec8e5cb26
Create Date: 2026-05-06 11:57:19.434997

11e migration Alembic Phase C+, 0 destructive cumulée.

Anti-DROP discipline 11e épisode : 63 drop_table/drop_index autogenerate retirés
(annotator_profiles, enedis_*, meter_*, promotion_*, unmatched_prm, annotations).

Clôture dette historique D-Phase4-2-Operat-Surfaces-3-Distinct-001 (P0 Sprint C-2).

Source légale : Arrêté 10/04/2020 art. 2-j (NOR LOGL2005904A version 15/03/2024) :
"La surface de consommations énergétiques [S_CE], la surface sur laquelle l'ensemble
des consommations énergétiques sont prises en compte, intégrant notamment les surfaces
de stationnement intérieur et de locaux techniques de l'entité fonctionnelle, au
contraire de la surface de plancher [SDP]".

3 surfaces distinctes Site cardinal post-Phase 7.1 :
- `surface_m2` = SDP (Surface De Plancher) — Code construction art. R111-22
- `tertiaire_area_m2` = surface tertiaire assujettie OPERAT (sous-périmètre SDP)
- `s_ce_m2` = Surface CE OPERAT (Arrêté 10/04/2020 art. 2-j, typiquement > SDP)

Cumul Phase C+ : 11 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f5df8bc45f8b"
down_revision: Union[str, Sequence[str], None] = "86dec8e5cb26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — Site +1 col s_ce_m2 (Surface CE OPERAT)."""
    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "s_ce_m2",
                sa.Float(),
                nullable=True,
                comment="Surface CE OPERAT (Arrêté 10/04/2020 art. 2-j) — distincte SDP/tertiaire",
            )
        )


def downgrade() -> None:
    """Downgrade schema — suppression défensive col s_ce_m2."""
    with op.batch_alter_table("sites", schema=None) as batch_op:
        batch_op.drop_column("s_ce_m2")
