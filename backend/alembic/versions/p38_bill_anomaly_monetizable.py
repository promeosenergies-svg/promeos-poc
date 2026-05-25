"""Phase 3.8 — BillAnomaly.is_monetizable + non_monetizable_reason

Audit Bill Intelligence Phase 0-bis (2026-05-24, chantier C1) :
  > P0 §3 Règle 2 — `BillAnomaly.actual_value` nullable autorise la création
  > d'anomalies financières sans montant. Tous les détecteurs (R19, R20, R21+)
  > peuplent `details_json` mais aucune CHECK constraint ni assertion runtime
  > ne garantit l'invariant. Conséquence live : `kpi_vnu_dormant_reclaim_eur=0,0 €`
  > observé sur DB démo malgré 52 anomalies présentes.

Cette migration ajoute 2 colonnes à `bill_anomaly` :
  - `is_monetizable` (Boolean, default True) : flag explicite
    * True  → l'anomalie a un impact financier chiffrable → `actual_value` requis
    * False → anomalie informative (ex : R017 PDL manquant) → `actual_value` peut être NULL
  - `non_monetizable_reason` (Text, nullable) : justification obligatoire si
    `is_monetizable=False` (ex : "Données contractuelles manquantes pour
    chiffrer l'impact", "Anomalie informative — vérification documentaire seule")

Discipline anti-DROP : colonnes restent sur downgrade (information perdue sinon).

Pas de migration NOT NULL d'`actual_value` à ce stade : la doctrine "ne pas
forcer NOT NULL sur les anomalies purement informatives si le modèle ne
distingue pas encore `is_monetizable`" est respectée. La validation est
appliquée par un listener SQLAlchemy `before_insert` (cf. models/bill_anomaly.py).

Une fois le scan DB validé propre (0 anomalie valorisable sans actual_value),
une migration P3.9 pourra ajouter une CHECK constraint :
    CHECK (is_monetizable = false OR actual_value IS NOT NULL)

Revision ID: p38anmon
Revises: p37bilan
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "p38anmon"
down_revision: Union[str, Sequence[str], None] = "p37bilan"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajoute BillAnomaly.is_monetizable + non_monetizable_reason si absent (idempotent)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("bill_anomaly")}

    with op.batch_alter_table("bill_anomaly") as batch_op:
        if "is_monetizable" not in cols:
            batch_op.add_column(
                sa.Column(
                    "is_monetizable",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                    comment="True → impact financier chiffrable, actual_value requis. "
                    "False → anomalie informative, actual_value peut être NULL "
                    "(doctrine Bill Intelligence P1 C1, 2026-05-24).",
                )
            )
        if "non_monetizable_reason" not in cols:
            batch_op.add_column(
                sa.Column(
                    "non_monetizable_reason",
                    sa.Text(),
                    nullable=True,
                    comment="Justification obligatoire si is_monetizable=False "
                    "(FR clair, ex : 'Données contractuelles manquantes pour chiffrer').",
                )
            )


def downgrade() -> None:
    """Anti-DROP : colonnes conservées (info perdue sinon)."""
    pass
