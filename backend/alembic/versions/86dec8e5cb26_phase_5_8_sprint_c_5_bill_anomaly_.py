"""Phase 5.8 Sprint C-5 — bill_anomaly UNIQUE(invoice_id, code) audit transversal G3

Revision ID: 86dec8e5cb26
Revises: b86d01f19001
Create Date: 2026-05-06 11:15:42.317662

10e migration Alembic Phase C, 0 destructive cumulée.

Anti-DROP discipline 10e épisode : 63 drop_table/drop_index autogenerate retirés
(record cumul Phase C 9 → 10 migrations propres).

Audit transversal Phase C 6 AXES (Phase 5.7) AXE 2 F4 — BillAnomaly UNIQUE absent :

- Avant : doublons R19/R20 possibles sur même invoice (replays ingestion concurrente)
- Après : UNIQUE(invoice_id, code) anti-doublons enforced runtime

⚠️ Note SoftDeleteMixin : avec un soft-delete (deleted_at SET), la contrainte UNIQUE
n'est pas libérée. Pour PostgreSQL prod, index partiel `WHERE deleted_at IS NULL`
recommandé Sprint C-7 polish (D-Sprint-C7-BillAnomaly-Partial-Index-001 P2).

Cleanup pré-migration : DELETE doublons existants éventuels (gardé MIN(id) par
groupe (invoice_id, code)) — défensif si seed produit doublons.

Cumul Phase C : 10 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "86dec8e5cb26"
down_revision: Union[str, Sequence[str], None] = "b86d01f19001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — UNIQUE constraint anti-doublons R19/R20."""

    # Cleanup défensif : DELETE doublons existants (gardé MIN(id) par (invoice_id, code))
    op.execute(
        """
        DELETE FROM bill_anomaly
        WHERE id NOT IN (
            SELECT MIN(id) FROM bill_anomaly
            GROUP BY invoice_id, code
        )
        """
    )

    # UNIQUE constraint
    with op.batch_alter_table("bill_anomaly", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_bill_anomaly_invoice_code",
            ["invoice_id", "code"],
        )


def downgrade() -> None:
    """Downgrade schema — suppression UNIQUE constraint."""
    with op.batch_alter_table("bill_anomaly", schema=None) as batch_op:
        batch_op.drop_constraint("uq_bill_anomaly_invoice_code", type_="unique")
