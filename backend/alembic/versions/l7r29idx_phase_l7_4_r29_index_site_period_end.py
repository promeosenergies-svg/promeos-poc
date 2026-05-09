"""Phase L7.4 — Index ix_energy_invoices_site_period_end pour R29 batch performance

R29 query (`detect_r29_period_overlap_or_gap`) filtre sur (site_id, period_start)
et trie ORDER BY period_end DESC. L'index existant `ix_energy_invoices_site_period`
couvre (site_id, period_start) mais le tri DESC sur period_end nécessite un sort
post-filter qui peut scanner plusieurs milliers de lignes par site sur portefeuilles
ETI 12-25 sites × 12-24 mois historique × 4 vecteurs énergie = ~4 000-12 000 invoices.

Ce nouvel index composite (site_id, period_end DESC) permet à PostgreSQL/SQLite de
servir directement la query `WHERE site_id=X AND period_start<Y ORDER BY period_end DESC`
en index-only scan (les 2 colonnes du WHERE + ORDER BY sont en cache index).

Pattern Phase D-4 anti-DROP discipline (idempotent NON-DESTRUCTIVE) :
- AUCUN DROP de table/index existant
- Création conditionnelle (skip si déjà présent)
- Compatible SQLite (DEMO_MODE) + PostgreSQL (pré-prod)

Source : code-reviewer audit Phase L7 finding efficiency #4 (P1).

Revision ID: l7r29idx
Revises: h3iso50001
Create Date: 2026-05-09

"""

from typing import Sequence, Union

from alembic import op


revision: str = "l7r29idx"
down_revision: Union[str, Sequence[str], None] = "h3iso50001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_NAME = "ix_energy_invoices_site_period_end"
_TABLE_NAME = "energy_invoices"


def upgrade() -> None:
    """Phase L7.4 — création index composite (site_id, period_end DESC)."""
    import sqlalchemy as sa

    inspector = sa.inspect(op.get_bind())
    existing = {idx["name"] for idx in inspector.get_indexes(_TABLE_NAME)}
    if _INDEX_NAME not in existing:
        op.create_index(
            _INDEX_NAME,
            _TABLE_NAME,
            ["site_id", "period_end"],
            unique=False,
        )


def downgrade() -> None:
    """Rollback : drop de l'index ajouté Phase L7.4."""
    import sqlalchemy as sa

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(_TABLE_NAME)}
    if _INDEX_NAME in existing:
        op.drop_index(_INDEX_NAME, table_name=_TABLE_NAME)
