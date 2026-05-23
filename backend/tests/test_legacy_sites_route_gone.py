"""
PROMEOS — P0-A 2026-05-23 : routes /api/sites/* legacy retournent HTTP 410 Gone.

Ces routes ont été relocalisées sous /api/patrimoine/* (canonique). Le frontend
a été migré (api/patrimoine.js). Toute tentative d'appel sur l'ancien préfixe
doit retourner 410 avec un message FR + un pointeur de remplacement.

Référence : docs/dev/patrimoine_routes_canonical.md
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


@pytest.mark.parametrize(
    "method,path,expected_replacement",
    [
        ("POST", "/api/sites/quick-create", "POST /api/patrimoine/crud/sites/quick-create"),
        ("POST", "/api/sites", "POST /api/patrimoine/crud/sites"),
        ("GET", "/api/sites", "GET /api/patrimoine/sites"),
    ],
)
def test_legacy_route_returns_410(client, method, path, expected_replacement):
    """Chaque route legacy doit retourner HTTP 410 + message FR + pointeur canonique."""
    response = client.request(method, path, json={} if method == "POST" else None)
    assert response.status_code == 410, f"{method} {path} attendu 410 Gone, reçu {response.status_code}"
    body = response.json()
    detail = body.get("detail") or body
    assert detail.get("code") == "PATRIMOINE_ROUTE_GONE"
    assert "dépréciée" in detail.get("message", "")
    assert detail.get("replacement") == expected_replacement
    assert detail.get("doc", "").startswith("docs/dev/patrimoine_routes_canonical")


def test_410_message_is_french(client):
    """Le message d'erreur doit être en français (pas d'anglais résiduel)."""
    response = client.post("/api/sites/quick-create", json={})
    detail = response.json().get("detail", {})
    msg = detail.get("message", "")
    assert "déprécié" in msg.lower() or "dépréciée" in msg.lower()
    # Aucun anglais courant
    for english_word in ("deprecated", "use ", "gone", "removed"):
        assert english_word.lower() not in msg.lower(), f"Message contient anglais résiduel : {msg!r}"
