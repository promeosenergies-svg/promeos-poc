"""
PROMEOS - Dev Tools Routes (development only)
POST /api/dev/reset_db - Backup + recreate schema + reseed demo data.
"""

import logging
import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db, engine
from models import Base
from middleware.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

DEMO_MODE = os.environ.get("PROMEOS_DEMO_MODE", "false").lower() == "true"

router = APIRouter(prefix="/api/dev", tags=["Dev Tools"])


@router.post("/reset_db")
def reset_db(request: Request, db: Session = Depends(get_db)):
    """
    POST /api/dev/reset_db

    1. Backup existing DB file (timestamped copy).
    2. Drop all tables + recreate schema from models.
    3. Run demo seed.
    Returns status + backup path.
    Only available in DEMO_MODE.
    """
    check_rate_limit(request, key_prefix="reset_db", max_requests=2, window_seconds=60)
    if not DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="reset_db is only available in DEMO_MODE",
        )

    db_path = engine.url.database
    backup_path = None

    # 1. Backup (close session first to release file lock)
    if db_path and os.path.exists(db_path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.bak_{ts}"
        try:
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
