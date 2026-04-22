import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base
from database import (
    DATABASE_URL,
    FLUX_DATA_DATABASE_URL,
    engine,
    flux_data_engine,
    run_migrations,
)
from data_ingestion.enedis.migrations import run_flux_data_migrations


def init_database():
    print("[INIT] PROMEOS - Initialisation de la base de donnees")
    print(f"[DB] Base principale : {DATABASE_URL}")
    print(f"[DB] Base flux bruts : {FLUX_DATA_DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    run_flux_data_migrations(flux_data_engine)
    print("[OK] Tables principales creees :", list(Base.metadata.tables.keys()))
    print("[OK] Base flux_data initialisee")


if __name__ == "__main__":
    init_database()
