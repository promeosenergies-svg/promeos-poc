"""
PROMEOS - Test conftest: ensure DB state is consistent between test files.

Re-seeds HELIOS demo data when the real DB has fewer than 5 sites.
Runs as an autouse module-scoped fixture so that destructive tests
(reset_db, reset-pack hard) don't break subsequent test modules.
"""

import os

import pytest

# M2-4.6 : rate limiting désactivé en test. Le limiter slowapi lit cette env à
# l'import de `main_limiter` → `enabled=False`. Sans ça, les centaines d'appels
# rapides des suites V4 (même user → même bucket) déclencheraient des 429.
os.environ.setdefault("PROMEOS_RATE_LIMIT_ENABLED", "false")

# JWT secret test-safe — requis par services.iam_service à l'import. Posé ici
# (conftest racine) pour couvrir tous les dossiers de tests (api/middleware/...).
os.environ.setdefault("PROMEOS_JWT_SECRET", "m2_3_b_test_secret_do_not_use_prod")


def _ensure_seeded():
    """Seed HELIOS S if the real DB has < 5 sites.

    Sprint C-4 Phase 4.7 (clôture D-Sprint-C2-Conftest-Reseed-Reset-001 P2) :
    le reset hard via SeedOrchestrator écrase les tables PROMEOS mais peut laisser
    `alembic_version` désynchronisé entre tests modules consécutifs (race condition
    si le seed précède une nouvelle migration tested). Reset explicite ajouté pour
    cohérence baseline alembic post-reseed (idempotent — pas d'effet si table
    déjà à head).
    """
    from database import SessionLocal

    db = SessionLocal()
    try:
        from models import Site

        if db.query(Site).count() < 5:
            from services.demo_seed import SeedOrchestrator

            orch = SeedOrchestrator(db)
            orch.reset(mode="hard")
            result = orch.seed("helios", "S", rng_seed=42)
            db.commit()

            # Sprint C-4 Phase 4.7 — reset alembic_version pour cohérence baseline
            # post-reseed (anti-désync entre test modules consécutifs).
            try:
                from sqlalchemy import text

                db.execute(text("DELETE FROM alembic_version"))
                # Re-stamp head courant (lecture migration max via Alembic config)
                # Defensive : si Alembic command unavailable in test env, log + skip.
                from alembic import command
                from alembic.config import Config

                alembic_cfg = Config("alembic.ini")
                command.stamp(alembic_cfg, "head")
                db.commit()
            except Exception:
                # Defensive : alembic_version reset n'est pas critique pour les
                # tests qui n'utilisent pas de migration runtime. Best-effort.
                db.rollback()

            # Réactiver DemoState pour les tests qui en dépendent
            from services.demo_state import DemoState
            from models import Organisation

            org = db.query(Organisation).first()
            if org:
                DemoState.set_demo_org(org_id=org.id, org_nom=org.nom)
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def ensure_demo_data():
    """Re-seed before each test module if the DB was wiped by a prior module."""
    _ensure_seeded()


@pytest.fixture
def app_client():
    """
    TestClient FastAPI avec DB in-memory SQLite.
    Partage par tous les fichiers de test qui ont besoin d'un client HTTP isole.
    """
    import os
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from models import Base

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    from main import app
    from database import get_db

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    os.environ["DEMO_MODE"] = "true"
    client = TestClient(app, raise_server_exceptions=False)
    yield client, SessionLocal
    app.dependency_overrides.clear()
