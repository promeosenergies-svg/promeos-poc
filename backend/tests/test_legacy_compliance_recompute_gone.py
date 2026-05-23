"""
PROMEOS — Conformité P0 2026-05-23 : route /api/compliance/recompute → HTTP 410.

Endpoint legacy supprimé, remplacé par /api/compliance/recompute-rules + cascade
automatique. Zéro consumer frontend (vérifié par grep avant suppression).
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import Base  # noqa: E402


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    def _override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_legacy_recompute_returns_410(client):
    """POST /api/compliance/recompute → 410 avec payload FR canonique."""
    response = client.post("/api/compliance/recompute?scope=site&id=1")
    assert response.status_code == 410
    detail = response.json().get("detail") or response.json()
    assert detail.get("code") == "CONFORMITE_ROUTE_GONE"
    assert "dépréciée" in detail.get("message", "")
    assert detail.get("replacement") == "POST /api/compliance/recompute-rules"


def test_replacement_endpoint_exists(client):
    """Le remplacement /api/compliance/recompute-rules doit exister (≠ 410)."""
    # On ne vérifie pas le status code business (org scoping etc.), juste qu'il n'est PAS 410
    response = client.post("/api/compliance/recompute-rules?org_id=1")
    assert response.status_code != 410, (
        f"L'endpoint de remplacement ne doit pas être lui-même 410, reçu {response.status_code}"
    )
