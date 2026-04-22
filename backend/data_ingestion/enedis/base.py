"""Dedicated SQLAlchemy base for Enedis raw-ingestion storage."""

from sqlalchemy.orm import declarative_base


FluxDataBase = declarative_base()
