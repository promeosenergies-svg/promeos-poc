"""initial_schema — baseline

Revision ID: 2f83c6bebc57
Revises:
Create Date: 2026-03-05 18:18:18.331990

This is a no-op baseline migration.
The existing database was created via Base.metadata.create_all() and
manual migrations in database/migrations.py.  Alembic starts tracking
from this point forward.
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "2f83c6bebc57"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — existing schema is the baseline."""
    pass


def downgrade() -> None:
    """No-op — cannot downgrade past baseline."""
    pass
