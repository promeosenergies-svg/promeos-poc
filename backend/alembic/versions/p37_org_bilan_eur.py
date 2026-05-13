"""Phase 3.7 — Organisation.bilan_eur (P0 audit regulatory-expert Phase 3.5)

Audit regulatory-expert (rapport Phase 3.5) :
  > P0 SME — Critère CA_BILAN partiel : `bilan_eur = getattr(organisation,
  > "bilan_eur", None)` toujours None (champ absent du modèle Organisation v1.0).
  > Conséquence concrète : une ETI 240 salariés + CA 80 M€ + bilan 50 M€
  > + conso 2,5 GWh est classée NOT_APPLICABLE.PME alors qu'elle est légalement
  > assujettie SMÉ.

Cette migration ajoute la colonne `bilan_eur` à `organisations` :
  - Type Float, nullable=True (rétro-compat sites historiques)
  - Pas de backfill automatique : un null = "inconnu" (statut data_missing
    sera renvoyé correctement par SMEEvaluator).

Discipline anti-DROP : la colonne reste sur downgrade (information perdue
sinon). On garde la nullabilité pour rollback safe.

Revision ID: p37bilan
Revises: p34bisisd
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "p37bilan"
down_revision: Union[str, Sequence[str], None] = "p34bisisd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajoute Organisation.bilan_eur si absent (idempotent)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"]: c for c in inspector.get_columns("organisations")}

    if "bilan_eur" in cols:
        return

    with op.batch_alter_table("organisations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "bilan_eur",
                sa.Float(),
                nullable=True,
                comment="Bilan total en € (Code énergie L233-1 critère SMÉ b) — P3.7",
            )
        )


def downgrade() -> None:
    """Anti-DROP discipline : la colonne reste (rollback nullabilité only)."""
    pass
