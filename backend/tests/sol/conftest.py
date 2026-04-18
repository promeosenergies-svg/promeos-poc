"""
Fixtures partagées pour tests Sol V1.

Fournit une DB SQLite en mémoire isolée par test, avec les 4 tables Sol +
tables FK dependencies (organisations, users) créées.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
import models.sol  # noqa: F401 — enregistre les tables Sol dans metadata
from models.iam import User
from models.organisation import Organisation


@pytest.fixture
def sol_db():
    """DB SQLite en mémoire avec schéma minimal pour tests Sol."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def sol_org(sol_db):
    """Organisation minimale pour FK tests Sol."""
    org = Organisation(nom="Test Org Sol", actif=True)
    sol_db.add(org)
    sol_db.commit()
    sol_db.refresh(org)
    return org


@pytest.fixture
def sol_user(sol_db, sol_org):
    """User minimal pour FK tests Sol."""
    user = User(
        email=f"sol-test-{uuid.uuid4().hex[:8]}@test.local",
        hashed_password="bcrypt_stub",
        nom="TestSol",
        prenom="User",
        actif=True,
    )
    sol_db.add(user)
    sol_db.commit()
    sol_db.refresh(user)
    return user


@pytest.fixture
def sol_correlation_id():
    """Correlation ID déterministe par test."""
    return str(uuid.uuid4())


@pytest.fixture
def now_utc():
    """Helper : datetime UTC-aware à l'instant du test."""
    return datetime.now(timezone.utc)
