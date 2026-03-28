"""
PROMEOS - Configuration de la base de données
Supports SQLite (default, dev) and PostgreSQL (production).
Reads DATABASE_URL from environment (.env or system env var).
"""

import logging
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_logger = logging.getLogger("promeos.db")

load_dotenv()  # Load .env file if present

# Database URL: env var > .env > SQLite fallback
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_SQLITE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'promeos.db')}"

DATABASE_URL = os.environ.get("DATABASE_URL", _DEFAULT_SQLITE_URL)

# Ensure data dir exists for SQLite
_is_sqlite = DATABASE_URL.startswith("sqlite")
if _is_sqlite:
    db_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

_logger.info("Base de donnees PROMEOS : %s://...", DATABASE_URL.split("://")[0])

# Engine configuration — database-specific
_engine_kwargs = {
    "echo": False,
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 10}
else:
    # PostgreSQL connection pool settings
    _engine_kwargs["pool_size"] = int(os.environ.get("DB_POOL_SIZE", "5"))
    _engine_kwargs["max_overflow"] = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **_engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency pour FastAPI
def get_db():
    """Générateur de session de base de données — dépendance FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
