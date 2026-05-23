"""
PROMEOS — Conformité P1 2026-05-23 : cleanup legacy (CEE V69 + doublons regops/bacs).

Vérifie que les 6 endpoints CEE Pipeline V69 et les 2 doublons regops/bacs
score_explain + data_quality retournent HTTP 410 avec payload FR canonique.

Tous ces endpoints étaient identifiés morts par l'audit Conformité P0
(`docs/audits/audit_brique_conformite_deep_readonly_2026_05_23.md` §10).
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


# ─── CEE Pipeline V69 (6 endpoints morts) ──────────────────────────────────


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/compliance/sites/1/packages"),
        ("POST", "/api/compliance/sites/1/packages"),
        ("POST", "/api/compliance/sites/1/cee/dossier?work_package_id=1"),
        ("PATCH", "/api/compliance/cee/dossier/1/step"),
        ("GET", "/api/compliance/sites/1/mv/summary"),
        ("POST", "/api/compliance/cee/dossier/1/compute"),
    ],
)
def test_cee_pipeline_v69_returns_410(client, method, path):
    """Chaque endpoint CEE Pipeline V69 retourne 410 + payload FR canonique."""
    response = client.request(method, path, json={} if method != "GET" else None)
    assert response.status_code == 410, f"{method} {path} attendu 410, reçu {response.status_code}"
    detail = response.json().get("detail") or response.json()
    assert detail.get("code") == "CONFORMITE_CEE_PIPELINE_GONE"
    assert "dépréciée" in detail.get("message", "")
    assert "jamais été livré" in detail.get("message", "")


# ─── Doublons regops/bacs (2 endpoints) ────────────────────────────────────


def test_bacs_score_explain_returns_410(client):
    """GET /api/regops/bacs/score_explain/{id} → 410 + pointe vers regops générique."""
    response = client.get("/api/regops/bacs/score_explain/1")
    assert response.status_code == 410
    detail = response.json().get("detail") or response.json()
    assert detail.get("code") == "CONFORMITE_BACS_DUPLICATE_GONE"
    assert "regops" in detail.get("replacement", "").lower()
    assert "score_explain" in detail.get("replacement", "")


def test_bacs_data_quality_returns_410(client):
    """GET /api/regops/bacs/data_quality/{id} → 410 + pointe vers regops générique."""
    response = client.get("/api/regops/bacs/data_quality/1")
    assert response.status_code == 410
    detail = response.json().get("detail") or response.json()
    assert detail.get("code") == "CONFORMITE_BACS_DUPLICATE_GONE"
    assert "regops" in detail.get("replacement", "").lower()
    assert "data_quality" in detail.get("replacement", "")


# ─── FR strict ─────────────────────────────────────────────────────────────


def test_410_messages_french_only(client):
    """Tous les messages d'erreur 410 sont en FR (pas d'anglais résiduel)."""
    response = client.get("/api/compliance/sites/1/packages")
    msg = (response.json().get("detail") or {}).get("message", "")
    # "pipeline" toléré (fait partie du nom propre "CEE Pipeline V69")
    for english in ("deprecated", "please use", "removed", "missing"):
        assert english.lower() not in msg.lower(), f"Anglais résiduel dans le message 410 : {msg!r}"
