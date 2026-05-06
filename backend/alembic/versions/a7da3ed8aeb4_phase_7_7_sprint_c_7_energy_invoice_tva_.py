"""Phase 7.7 Sprint C-7 Lot C — EnergyInvoice +1 col tva_rate (clôture D-Sprint-C7-EnergyInvoice-TVA-Rate-Field-001)

Revision ID: a7da3ed8aeb4
Revises: f5df8bc45f8b
Create Date: 2026-05-06 14:21:50.583667

12e migration Alembic Phase C+, 0 destructive cumulée.

Anti-DROP discipline 12e épisode : autogenerate proposait de drop ~13 legacy tables
(meter_energy_index, enedis_flux_*, promotion_*, unmatched_prm — backups préservés
.original-autogenerate). Tous ces drops ont été manuellement retirés, conservés en
tracker D-Enedis-Legacy-001 P2 jusqu'au audit data lineage Sprint C-7+.

Clôture dette D-Sprint-C7-EnergyInvoice-TVA-Rate-Field-001 P1 — colonne `tva_rate`
Numeric(5,4) cardinale pour règles R0X TVA futurs (R21+ Bill Intelligence).

Cumul Phase C+ : 12 migrations propres / 0 destructive.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7da3ed8aeb4"
down_revision: Union[str, Sequence[str], None] = "f5df8bc45f8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — EnergyInvoice +1 col tva_rate (Numeric(5,4))."""
    with op.batch_alter_table("energy_invoices", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tva_rate",
                sa.Numeric(precision=5, scale=4),
                nullable=True,
                comment="Taux TVA applicable (0.0550=5.5%, 0.1000=10%, 0.2000=20%) — Phase 7.7 Lot C",
            )
        )


def downgrade() -> None:
    """Downgrade schema — suppression défensive col tva_rate."""
    with op.batch_alter_table("energy_invoices", schema=None) as batch_op:
        batch_op.drop_column("tva_rate")
