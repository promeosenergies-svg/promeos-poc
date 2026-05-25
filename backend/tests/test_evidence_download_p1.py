"""
PROMEOS — Conformité P1 2026-05-23 : tests endpoint download Evidence.

`GET /api/v4/action-center/evidences/{evidence_id}/download` — permet à
l'utilisateur de re-télécharger une preuve qu'il a uploadée. Gap audit P0
critique (UX audit) corrigé.

Vérifie :
- Download d'une evidence existante de l'org courante → 200 + contenu binaire
- Download cross-org → 404 (anti-énumération)
- Evidence inexistante → 404
- Storage_uri non-fs (S3 future) → 501 documenté
- Path traversal → 403
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import Base  # noqa: E402
from models.v4.action_center_items import ActionCenterItem  # noqa: E402
from models.v4.evidences import Evidence  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db):
    """TestClient avec bypass JWT (lit X-Org-Id du header)."""
    from middleware.org_context import (
        populate_org_context,
        reset_org_context,
        set_org_context,
    )

    async def _override_populate_org_context(request: Request):
        org_id_header = request.headers.get("X-Org-Id")
        token = None
        if org_id_header:
            try:
                token = set_org_context(int(org_id_header))
            except (TypeError, ValueError):
                pass
        try:
            yield
        finally:
            if token is not None:
                reset_org_context(token)

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[populate_org_context] = _override_populate_org_context

    for route in app.routes:
        if not hasattr(route, "dependant") or route.dependant is None:
            continue
        for dep in route.dependant.dependencies:
            if dep.call and getattr(dep.call, "__name__", "") == "_role_checker":
                app.dependency_overrides[dep.call] = lambda: {"sub": 1, "role": "user"}

    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_item_and_evidence(
    db, *, org_id: int = 1, file_content: bytes = b"PDF content here", original_filename: str = "preuve.pdf"
):
    """Crée un ActionCenterItem + Evidence avec un fichier temporaire sur disque."""
    item = ActionCenterItem(
        id=uuid.uuid4(),
        organisation_id=org_id,
        kind="evidence_request",
        title="Test item",
        domain="conformite",
        lifecycle_state="new",
        priority_bracket="P1",
        priority_score=60.0,
    )
    db.add(item)
    db.flush()

    # Écrit le fichier dans un répertoire temporaire
    tmp_dir = tempfile.mkdtemp(prefix="evidence_p1_test_")
    fs_path = os.path.join(tmp_dir, original_filename)
    with open(fs_path, "wb") as f:
        f.write(file_content)

    evidence = Evidence(
        id=uuid.uuid4(),
        organisation_id=org_id,
        action_item_id=item.id,
        mime_type="application/pdf",
        file_size_bytes=len(file_content),
        storage_uri=f"fs://{fs_path}",
        original_filename=original_filename,
        uploaded_by=uuid.uuid4(),
    )
    db.add(evidence)
    db.commit()
    return item, evidence, fs_path


# ─── Cas nominal ─────────────────────────────────────────────────────────


def test_download_existing_evidence_returns_200_and_content(client, db):
    """GET /evidences/{id}/download retourne le binaire avec mime + filename."""
    content = b"PDF binary content placeholder"
    _, evidence, _ = _create_item_and_evidence(db, file_content=content, original_filename="rapport.pdf")
    response = client.get(
        f"/api/v4/action-center/evidences/{evidence.id}/download",
        headers={"X-Org-Id": "1"},
    )
    assert response.status_code == 200, response.text
    assert response.content == content
    assert response.headers["content-type"].startswith("application/pdf")
    assert 'filename="rapport.pdf"' in response.headers.get("content-disposition", "")


# ─── Cross-org : 404 anti-énumération ────────────────────────────────────


def test_download_cross_org_returns_404(client, db):
    """Org 2 essayant de télécharger evidence de org 1 → 404 (pas 403)."""
    _, evidence, _ = _create_item_and_evidence(db, org_id=1)
    response = client.get(
        f"/api/v4/action-center/evidences/{evidence.id}/download",
        headers={"X-Org-Id": "2"},
    )
    assert response.status_code == 404, response.text
    assert (response.json().get("detail") or {}).get("code") == "EVIDENCE_NOT_FOUND"


# ─── Evidence inexistante ────────────────────────────────────────────────


def test_download_unknown_evidence_returns_404(client, db):
    """ID inexistant → 404."""
    response = client.get(
        f"/api/v4/action-center/evidences/{uuid.uuid4()}/download",
        headers={"X-Org-Id": "1"},
    )
    assert response.status_code == 404


# ─── Storage S3 future (501) ─────────────────────────────────────────────


def test_download_s3_storage_returns_501(client, db):
    """Storage `s3://` non implémenté en P1 → 501 documenté."""
    item = ActionCenterItem(
        id=uuid.uuid4(),
        organisation_id=1,
        kind="evidence_request",
        title="Test",
        domain="conformite",
        lifecycle_state="new",
        priority_bracket="P1",
        priority_score=60.0,
    )
    db.add(item)
    db.flush()
    evidence = Evidence(
        id=uuid.uuid4(),
        organisation_id=1,
        action_item_id=item.id,
        mime_type="application/pdf",
        file_size_bytes=100,
        storage_uri="s3://bucket/evidences/file.pdf",
        original_filename="file.pdf",
        uploaded_by=uuid.uuid4(),
    )
    db.add(evidence)
    db.commit()

    response = client.get(
        f"/api/v4/action-center/evidences/{evidence.id}/download",
        headers={"X-Org-Id": "1"},
    )
    assert response.status_code == 501
    assert (response.json().get("detail") or {}).get("code") == "EVIDENCE_STORAGE_NOT_SUPPORTED"


# ─── Fichier disparu du disque (404 FILE_MISSING) ────────────────────────


def test_download_file_missing_on_disk_returns_404(client, db):
    """Fichier supprimé du disque → 404 EVIDENCE_FILE_MISSING + message FR."""
    _, evidence, fs_path = _create_item_and_evidence(db)
    os.remove(fs_path)  # simule fichier disparu

    response = client.get(
        f"/api/v4/action-center/evidences/{evidence.id}/download",
        headers={"X-Org-Id": "1"},
    )
    assert response.status_code == 404
    detail = response.json().get("detail") or {}
    assert detail.get("code") == "EVIDENCE_FILE_MISSING"
    assert "introuvable" in detail.get("message", "")


# ─── Path traversal (403) ────────────────────────────────────────────────


def test_download_path_traversal_returns_403(client, db):
    """storage_uri avec `..` → 403 EVIDENCE_PATH_INVALID."""
    item = ActionCenterItem(
        id=uuid.uuid4(),
        organisation_id=1,
        kind="evidence_request",
        title="Test",
        domain="conformite",
        lifecycle_state="new",
        priority_bracket="P1",
        priority_score=60.0,
    )
    db.add(item)
    db.flush()
    evidence = Evidence(
        id=uuid.uuid4(),
        organisation_id=1,
        action_item_id=item.id,
        mime_type="application/pdf",
        file_size_bytes=100,
        storage_uri="fs:///tmp/../../etc/passwd",
        original_filename="hack.pdf",
        uploaded_by=uuid.uuid4(),
    )
    db.add(evidence)
    db.commit()

    response = client.get(
        f"/api/v4/action-center/evidences/{evidence.id}/download",
        headers={"X-Org-Id": "1"},
    )
    assert response.status_code == 403
    assert (response.json().get("detail") or {}).get("code") == "EVIDENCE_PATH_INVALID"
