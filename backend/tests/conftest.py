"""
PROMEOS - Test conftest: ensure DB state is consistent between test files.

Re-seeds HELIOS demo data when the real DB has fewer than 5 sites.
Runs as an autouse module-scoped fixture so that destructive tests
(reset_db, reset-pack hard) don't break subsequent test modules.
"""

import pytest


def _ensure_seeded():
    """Seed HELIOS S if the real DB has < 5 sites. Always set DemoState."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        from models import Site, Organisation
        from services.demo_state import DemoState

        if db.query(Site).count() < 5:
            from services.demo_seed import SeedOrchestrator

            orch = SeedOrchestrator(db)
            orch.reset(mode="hard")
            orch.seed("helios", "S", rng_seed=42)
            db.commit()

        # Toujours set DemoState même si déjà seedé
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


def seed_org_hierarchy(db):
    """Seed minimal Org→EJ→PF hierarchy in an in-memory test DB.

    Returns (org, ej, pf). Also sets DemoState so scope_utils resolves correctly.
    Usage: org, ej, pf = seed_org_hierarchy(session); site.portefeuille_id = pf.id
    """
    from models import Organisation, EntiteJuridique, Portefeuille
    from services.demo_state import DemoState

    org = Organisation(nom="Test Org", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(nom="Test EJ", organisation_id=org.id, siren="000000001")
    db.add(ej)
    db.flush()

    pf = Portefeuille(nom="Test PF", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()

    DemoState.set_demo_org(org_id=org.id, org_nom=org.nom)
    return org, ej, pf


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


@pytest.fixture
def app_client_with_org(app_client):
    """Variante app_client avec org/EJ/PF pré-seedés pour tests scope-required."""
    client, SessionLocal = app_client
    db_seed = SessionLocal()
    seed_org_hierarchy(db_seed)
    db_seed.commit()
    db_seed.close()
    yield client, SessionLocal
