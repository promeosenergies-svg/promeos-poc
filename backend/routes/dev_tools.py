"""
PROMEOS - Dev Tools Routes (development only)
POST /api/dev/reset_db - Backup + recreate schema + reseed demo data.
"""
import logging
import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db, engine
from models import Base

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dev", tags=["Dev Tools"])


@router.post("/reset_db")
def reset_db(db: Session = Depends(get_db)):
    """
    POST /api/dev/reset_db

    1. Backup existing DB file (timestamped copy).
    2. Drop all tables + recreate schema from models.
    3. Run demo seed.
    Returns status + backup path.
    """
    db_path = engine.url.database
    backup_path = None

    # 1. Backup
    if db_path and os.path.exists(db_path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.bak_{ts}"
        try:
            db.close()
            shutil.copy2(db_path, backup_path)
            logger.info("DB backup: %s", backup_path)
        except Exception as exc:
            logger.warning("Backup failed: %s", exc)
            backup_path = None

    # 2. Drop + recreate
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Schema recreated")
    except Exception as exc:
        logger.error("Schema reset failed: %s", exc)
        return {
            "status": "error",
            "error_code": "RESET_FAILED",
            "message": str(exc),
        }

    # 3. Run migrations (idempotent column additions)
    try:
        from database import run_migrations
        run_migrations(engine)
    except Exception:
        pass  # migrations are best-effort

    # 4. Reseed: Groupe HELIOS (5 sites E2E) — demo canonique
    seed_result = None
    try:
        new_db = next(get_db())
        from services.demo_seed import SeedOrchestrator
        orch = SeedOrchestrator(new_db)
        seed_result = orch.seed(pack="helios", size="S", rng_seed=42)
    except Exception as exc:
        logger.warning("Helios seed after reset: %s", exc)
        seed_result = {"status": "seed_skipped", "reason": str(exc)}

    return {
        "status": "ok",
        "backup_path": backup_path,
        "schema": "recreated",
        "seed": seed_result,
    }
