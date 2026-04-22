"""Dedicated database connection for raw flux ingestion storage."""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("promeos.fluxdb")

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_FLUX_DATA_PATH = os.path.join(DATA_DIR, "flux_data.db")
LEGACY_ENEDIS_PATH = os.path.join(DATA_DIR, "enedis.db")
_DEFAULT_FLUX_DATA_URL = f"sqlite:///{DEFAULT_FLUX_DATA_PATH}"


def _sqlite_path_from_url(url: str) -> str | None:
    if not url.startswith("sqlite:///"):
        return None
    return os.path.abspath(url.replace("sqlite:///", "", 1))


def _adopt_legacy_flux_db_files(target_path: str, legacy_path: str) -> bool:
    """Rename legacy enedis.db files to flux_data.db."""
    if os.path.exists(target_path) or not os.path.exists(legacy_path):
        return False

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    moved = False
    for suffix in ("", "-wal", "-shm"):
        src = f"{legacy_path}{suffix}"
        dst = f"{target_path}{suffix}"
        if not os.path.exists(src):
            continue
        os.replace(src, dst)
        moved = True
    return moved


def _maybe_adopt_legacy_flux_db(flux_data_url: str) -> None:
    if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if flux_data_url != _DEFAULT_FLUX_DATA_URL:
        return

    target_path = _sqlite_path_from_url(flux_data_url)
    if not target_path:
        return

    if _adopt_legacy_flux_db_files(target_path, LEGACY_ENEDIS_PATH):
        logger.info("Adopted legacy Enedis raw DB as flux_data.db")


def _build_engine(url: str, logger_name: str):
    is_sqlite = url.startswith("sqlite")
    engine_kwargs: dict[str, object] = {"echo": False}

    if is_sqlite:
        path = _sqlite_path_from_url(url)
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    else:
        engine_kwargs["pool_size"] = int(os.environ.get("DB_POOL_SIZE", "5"))
        engine_kwargs["max_overflow"] = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
        engine_kwargs["pool_pre_ping"] = True

    engine = create_engine(url, **engine_kwargs)

    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    logger.info("%s : %s://...", logger_name, url.split("://")[0])
    return engine, is_sqlite


FLUX_DATA_DATABASE_URL = os.environ.get("FLUX_DATA_DATABASE_URL", _DEFAULT_FLUX_DATA_URL)
_maybe_adopt_legacy_flux_db(FLUX_DATA_DATABASE_URL)

flux_data_engine, _is_flux_data_sqlite = _build_engine(FLUX_DATA_DATABASE_URL, "Base de donnees FLUX")
FluxDataSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=flux_data_engine)


def get_flux_data_db():
    """FastAPI dependency for the dedicated raw-flux database."""
    db = FluxDataSessionLocal()
    try:
        yield db
    finally:
        db.close()
