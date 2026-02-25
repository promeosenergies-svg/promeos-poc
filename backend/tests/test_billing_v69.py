"""
PROMEOS — V69 Meta Version Tests
Couvre: GET /api/meta/version — sha + branch.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models import Base
from database import get_db
from main import app


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ========================================
# Tests GET /api/meta/version
# ========================================

def test_meta_version_returns_sha(client):
    """GET /api/meta/version retourne sha + branch + build_time."""
    r = client.get("/api/meta/version")
    assert r.status_code == 200
    data = r.json()
    assert "sha" in data
    assert "branch" in data
    assert "build_time" in data
    assert "version" in data
    assert data["version"] == "1.0.0"


def test_meta_version_sha_nonempty(client):
    """sha et branch doivent être non-vides (git disponible en dev)."""
    r = client.get("/api/meta/version")
    data = r.json()
    # Si git est absent, sha = 'unknown' — on accepte les deux cas
    assert isinstance(data["sha"], str)
    assert len(data["sha"]) > 0
