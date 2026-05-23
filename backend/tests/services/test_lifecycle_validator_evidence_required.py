"""
PROMEOS — Conformité P0 2026-05-23 : `validate_evidence_required_for_closure`.

Vérifie qu'un ActionCenterItem preuve-dépendant (kind=EVIDENCE_REQUEST OU
domain=CONFORMITE) ne peut pas être clôturé en RESOLVED sans au moins une
Evidence vérifiée (verified_at ≠ NULL).
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import Base  # noqa: E402
from models.v4.enums import ClosureReason, Domain, Kind  # noqa: E402
from models.v4.evidences import Evidence  # noqa: E402
from services.v4.lifecycle_validator import (  # noqa: E402
    validate_evidence_required_for_closure,
)


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


def _fake_item(*, kind: str, domain: str, item_id: uuid.UUID | None = None):
    """Construit un mock léger d'ActionCenterItem (pas besoin de la table SQLite)."""
    return SimpleNamespace(id=item_id or uuid.uuid4(), kind=kind, domain=domain)


def _seed_verified_evidence(db, item_id: uuid.UUID, org_id: int = 1) -> Evidence:
    """Crée une Evidence vérifiée (verified_at ≠ NULL) liée à l'item."""
    now = datetime.now(timezone.utc)
    ev = Evidence(
        id=uuid.uuid4(),
        organisation_id=org_id,
        action_item_id=item_id,
        mime_type="application/pdf",
        file_size_bytes=1024,
        storage_uri=f"fs://test/{item_id}/evidence.pdf",
        original_filename="evidence.pdf",
        verified_at=now,
        verified_by=uuid.uuid4(),
        expires_at=now,
        uploaded_by=uuid.uuid4(),
    )
    db.add(ev)
    db.commit()
    return ev


def _seed_unverified_evidence(db, item_id: uuid.UUID, org_id: int = 1) -> Evidence:
    """Crée une Evidence NON vérifiée (verified_at = NULL)."""
    ev = Evidence(
        id=uuid.uuid4(),
        organisation_id=org_id,
        action_item_id=item_id,
        mime_type="application/pdf",
        file_size_bytes=1024,
        storage_uri=f"fs://test/{item_id}/draft.pdf",
        original_filename="draft.pdf",
        uploaded_by=uuid.uuid4(),
    )
    db.add(ev)
    db.commit()
    return ev


# ─── Cas qui doivent PASSER (no-op) ────────────────────────────────────────


def test_dismissed_always_ok_for_any_item(db):
    """closure_reason=DISMISSED → check skip même sur item preuve-dépendant."""
    item = _fake_item(kind=Kind.EVIDENCE_REQUEST.value, domain=Domain.CONFORMITE.value)
    # Aucune evidence → mais DISMISSED ne déclenche pas le check
    validate_evidence_required_for_closure(db, item, ClosureReason.DISMISSED)


def test_not_applicable_always_ok(db):
    """closure_reason=NOT_APPLICABLE → check skip."""
    item = _fake_item(kind=Kind.EVIDENCE_REQUEST.value, domain=Domain.CONFORMITE.value)
    validate_evidence_required_for_closure(db, item, ClosureReason.NOT_APPLICABLE)


def test_none_closure_reason_ok(db):
    """closure_reason=None (transition non-fermante) → check skip."""
    item = _fake_item(kind=Kind.EVIDENCE_REQUEST.value, domain=Domain.CONFORMITE.value)
    validate_evidence_required_for_closure(db, item, None)


def test_resolved_anomaly_outside_conformite_ok(db):
    """Item kind=ANOMALY + domain=MAINTENANCE → pas preuve-dépendant → RESOLVED OK."""
    item = _fake_item(kind=Kind.ANOMALY.value, domain="maintenance")
    validate_evidence_required_for_closure(db, item, ClosureReason.RESOLVED)


def test_resolved_evidence_request_with_verified_evidence_ok(db):
    """Item EVIDENCE_REQUEST avec evidence vérifiée → RESOLVED autorisé."""
    item = _fake_item(kind=Kind.EVIDENCE_REQUEST.value, domain="maintenance")
    _seed_verified_evidence(db, item.id)
    validate_evidence_required_for_closure(db, item, ClosureReason.RESOLVED)


def test_resolved_conformite_with_verified_evidence_ok(db):
    """Item domain=CONFORMITE avec evidence vérifiée → RESOLVED autorisé."""
    item = _fake_item(kind=Kind.ACTION.value, domain=Domain.CONFORMITE.value)
    _seed_verified_evidence(db, item.id)
    validate_evidence_required_for_closure(db, item, ClosureReason.RESOLVED)


# ─── Cas qui doivent ÉCHOUER (HTTP 422) ────────────────────────────────────


def test_resolved_evidence_request_without_evidence_raises_422(db):
    """Item EVIDENCE_REQUEST sans aucune evidence → 422 CLOSURE_REQUIRES_EVIDENCE."""
    item = _fake_item(kind=Kind.EVIDENCE_REQUEST.value, domain="maintenance")
    with pytest.raises(HTTPException) as exc_info:
        validate_evidence_required_for_closure(db, item, ClosureReason.RESOLVED)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "CLOSURE_REQUIRES_EVIDENCE"
    assert "résolu" in exc_info.value.detail["message"]
    assert "preuve" in exc_info.value.detail["message"]
    assert exc_info.value.detail["blocking"] is True


def test_resolved_conformite_without_evidence_raises_422(db):
    """Item domain=CONFORMITE sans evidence → 422."""
    item = _fake_item(kind=Kind.ACTION.value, domain=Domain.CONFORMITE.value)
    with pytest.raises(HTTPException) as exc_info:
        validate_evidence_required_for_closure(db, item, ClosureReason.RESOLVED)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "CLOSURE_REQUIRES_EVIDENCE"


def test_resolved_with_only_unverified_evidence_raises_422(db):
    """Evidence existe MAIS verified_at=NULL → 422 (preuve pas encore vérifiée)."""
    item = _fake_item(kind=Kind.EVIDENCE_REQUEST.value, domain=Domain.CONFORMITE.value)
    _seed_unverified_evidence(db, item.id)
    with pytest.raises(HTTPException) as exc_info:
        validate_evidence_required_for_closure(db, item, ClosureReason.RESOLVED)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "CLOSURE_REQUIRES_EVIDENCE"


def test_evidence_attached_to_other_item_does_not_count(db):
    """Evidence vérifiée mais sur un AUTRE item → 422 (pas applicable à cet item)."""
    item_target = _fake_item(kind=Kind.EVIDENCE_REQUEST.value, domain=Domain.CONFORMITE.value)
    other_item_id = uuid.uuid4()
    _seed_verified_evidence(db, other_item_id)  # evidence vérifiée mais sur autre item
    with pytest.raises(HTTPException) as exc_info:
        validate_evidence_required_for_closure(db, item_target, ClosureReason.RESOLVED)
    assert exc_info.value.status_code == 422


# ─── FR strict — pas d'anglais dans le message utilisateur ─────────────────


def test_error_message_french_only(db):
    """Le message d'erreur P0 doit être en français sans anglais résiduel."""
    item = _fake_item(kind=Kind.EVIDENCE_REQUEST.value, domain=Domain.CONFORMITE.value)
    with pytest.raises(HTTPException) as exc_info:
        validate_evidence_required_for_closure(db, item, ClosureReason.RESOLVED)
    msg = exc_info.value.detail["message"]
    for english in ("evidence", "resolve", "closure", "required", "missing"):
        assert english.lower() not in msg.lower(), f"Anglais résiduel : {msg!r}"
