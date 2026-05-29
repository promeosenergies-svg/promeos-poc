"""s4_mutu_validation_token — Sprint S4 mutualisation advanced (2026-05-29).

Migration additive : ajoute `validation_token_hash` (String 64) à
`tertiaire_groupe_structures_membre` pour rendre la validation RL
opposable (Art. 14 §1 al.2 — solidarité).

Le hash SHA256 est calculé applicativement au moment où le service
`set_representant_legal_status(new_status='validated')` valide la RL.
Il signe le payload (group_id, efa_id, validator_user_id, timestamp UTC)
et peut être recalculé ultérieurement par un auditeur ADEME pour
vérifier l'absence d'altération.

Revision ID: s4_mutu_tok
Revises: s3_mutu_gs
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "s4_mutu_tok"
down_revision: Union[str, Sequence[str], None] = "s3_mutu_gs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tertiaire_groupe_structures_membre") as batch:
        batch.add_column(sa.Column("validation_token_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tertiaire_groupe_structures_membre") as batch:
        batch.drop_column("validation_token_hash")
