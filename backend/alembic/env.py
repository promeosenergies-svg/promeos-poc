"""
PROMEOS — Alembic environment configuration.
Reads DATABASE_URL from environment, uses PROMEOS models metadata.
Supports SQLite batch mode for ALTER TABLE operations.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure backend/ is on sys.path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from models.base import Base

# Import all models so Base.metadata is fully populated
import models  # noqa: F401

config = context.config

# Override sqlalchemy.url from environment if set, otherwise use alembic.ini value
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ── Legacy indexes ──────────────────────────────────────────────────
# These partial / conditional indexes were created by database/migrations.py
# (outside of SQLAlchemy model definitions).  We tell Alembic to ignore them
# so autogenerate does not try to drop them.
_LEGACY_INDEX_NAMES = frozenset(
    {
        "uq_batiment_site_nom_active",
        "uq_compteur_meter_id_active",
        "uq_delivery_point_code_active",
        "uq_org_siren_active",
        "uq_portefeuille_ej_nom_active",
        "uq_site_portefeuille_siret_active",
        "uq_tertiaire_declaration_efa_year",
        "ix_tertiaire_dq_issue_efa_id",
        "ix_tertiaire_efa_statut",
        "ix_meter_parent_meter_id",
    }
)


def include_object(obj, name, type_, reflected, compare_to):
    """Filter callback for autogenerate.

    Skip legacy indexes that exist in the DB but not in models.
    """
    if type_ == "index" and reflected and compare_to is None:
        # Index exists in DB but not in models — skip if it's a known legacy one
        if name in _LEGACY_INDEX_NAMES:
            return False
    return True


def _is_sqlite(url: str) -> bool:
    """Check if the database URL points to SQLite."""
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite(url),
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    Uses batch mode for SQLite to support ALTER TABLE operations.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    url = config.get_main_option("sqlalchemy.url")

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_is_sqlite(url),
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
