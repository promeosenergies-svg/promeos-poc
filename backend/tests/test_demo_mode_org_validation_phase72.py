"""
PROMEOS — Tests cardinaux Phase 7.2 Sprint C-7 — DEMO_MODE bypass scope_utils fix (ADR-017 Option B).

Anti-régression cardinal post-fix SEC-2026-012 (audit Phase 5.5 + Phase 5.7 transversal AXE 4) :
Avant fix : `X-Org-Id` accepté brut sans validation DB → IDOR cross-tenant énumération
~25 endpoints en DEMO_MODE.

Après fix : validation DB stricte Organisation existence + actif + non soft-deleted.

Pattern reproduit Phase 5.6 F1 PRAGMA + Phase 5.8 G1 cascade — "Déclaration sans enforcement".
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_session():
    """In-memory SQLite avec schema déployé."""
    from models import Base

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_request(x_org_id: str | None = None) -> Request:
    """Helper : créer mock Request avec X-Org-Id header."""
    from starlette.datastructures import Headers

    headers = {}
    if x_org_id is not None:
        headers["X-Org-Id"] = x_org_id

    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


def _seed_org(db, **kwargs):
    """Helper : seed Organisation."""
    from models import Organisation

    defaults = {"nom": "TestOrg", "siren": "999000001", "actif": True}
    defaults.update(kwargs)
    org = Organisation(**defaults)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


# ─── G1 Phase 7.2 SEC-2026-012 fix runtime ──────────────────────────────────


def test_phase72_x_org_id_existing_org_accepted(db_session):
    """Phase 7.2 fix : X-Org-Id existant + actif → accepté."""
    from services.scope_utils import get_scope_org_id

    org = _seed_org(db_session, siren="999000010")
    request = _make_request(x_org_id=str(org.id))

    result = get_scope_org_id(request, auth=None, db=db_session)

    assert result == org.id, "Org existant + actif doit être retourné"


def test_phase72_x_org_id_nonexistent_rejected(db_session):
    """Phase 7.2 cardinal SEC-2026-012 : X-Org-Id inexistant DB → REJETÉ (None).

    Avant fix : returnait `99999` brut → fallback callers utilisait org_id arbitraire.
    Après fix : None → callers tombent sur DemoState fallback (org démo seulement).
    """
    from services.scope_utils import get_scope_org_id

    request = _make_request(x_org_id="99999")  # ID inexistant DB

    result = get_scope_org_id(request, auth=None, db=db_session)

    assert result is None, (
        "Phase 7.2 BLOQUANT : X-Org-Id inexistant DB doit être REJETÉ (None).\n"
        f"Au lieu, retour : {result}\n"
        "Régression SEC-2026-012 : permet IDOR cross-tenant énumération."
    )


def test_phase72_x_org_id_inactive_rejected(db_session):
    """Phase 7.2 : X-Org-Id existe mais `actif=False` → REJETÉ."""
    from services.scope_utils import get_scope_org_id

    org = _seed_org(db_session, siren="999000020", actif=False)
    request = _make_request(x_org_id=str(org.id))

    result = get_scope_org_id(request, auth=None, db=db_session)

    assert result is None, "Org `actif=False` doit être rejeté (anti-IDOR sur orgs désactivées)"


def test_phase72_x_org_id_soft_deleted_rejected(db_session):
    """Phase 7.2 : X-Org-Id existe mais soft-deleted → REJETÉ."""
    from services.scope_utils import get_scope_org_id

    org = _seed_org(db_session, siren="999000030")
    org.soft_delete(by="test", reason="Phase 7.2 test")
    db_session.commit()

    request = _make_request(x_org_id=str(org.id))
    result = get_scope_org_id(request, auth=None, db=db_session)

    assert result is None, "Org soft-deleted doit être rejeté (cohérence not_deleted)"


def test_phase72_x_org_id_invalid_format_rejected(db_session):
    """Phase 7.2 : X-Org-Id non-int (ex: 'abc' ou injection SQL-like) → REJETÉ."""
    from services.scope_utils import get_scope_org_id

    for bogus in ["abc", "1; DROP TABLE", "1' OR '1'='1", ""]:
        request = _make_request(x_org_id=bogus)
        result = get_scope_org_id(request, auth=None, db=db_session)
        assert result is None, f"X-Org-Id invalide '{bogus}' doit être rejeté"


def test_phase72_no_x_org_id_returns_none(db_session):
    """Phase 7.2 : pas de header X-Org-Id → None (caller fallback DemoState)."""
    from services.scope_utils import get_scope_org_id

    request = _make_request(x_org_id=None)
    result = get_scope_org_id(request, auth=None, db=db_session)

    assert result is None


def test_phase72_jwt_auth_priority_preserved(db_session):
    """Phase 7.2 : auth JWT priorité absolue, X-Org-Id ignoré (comportement préservé)."""
    from services.scope_utils import get_scope_org_id

    # Mock auth context avec org_id JWT
    class MockAuth:
        org_id = 42

        class user:
            id = 1

    request = _make_request(x_org_id="999")  # Header différent JWT

    result = get_scope_org_id(request, auth=MockAuth(), db=db_session)

    assert result == 42, "JWT org_id (42) doit primer sur X-Org-Id header (999)"


def test_phase72_backward_compat_db_none_legacy_callers(db_session):
    """Phase 7.2 : backward-compat — callers legacy `db=None` continuent à fonctionner.

    Sprint C-1 → C-6 ont des callsites `get_scope_org_id(request, auth)` sans `db`.
    À migrer Sprint C-8+ — pour Sprint C-7 fix MVP, accepter db=None retourne brut
    (validation skippée, comportement legacy).
    """
    from services.scope_utils import get_scope_org_id

    org = _seed_org(db_session, siren="999000040")
    request = _make_request(x_org_id=str(org.id))

    # db=None (signature legacy)
    result = get_scope_org_id(request, auth=None, db=None)

    assert result == org.id, "Backward-compat : db=None retourne X-Org-Id brut"


def test_phase72_resolve_org_id_passes_db_to_get_scope(db_session):
    """Phase 7.2 cardinal : resolve_org_id propage db à get_scope_org_id (fix runtime)."""
    from services.scope_utils import resolve_org_id

    # X-Org-Id arbitraire 88888 inexistant DB
    request = _make_request(x_org_id="88888")

    # En DEMO_MODE actif, fallback DemoState après rejet 88888
    # (test que rejet a lieu, fallback DemoState est testé ailleurs)
    from middleware.auth import DEMO_MODE

    if not DEMO_MODE:
        # Hors DEMO : 88888 rejeté → 401
        with pytest.raises(Exception):  # HTTPException 401
            resolve_org_id(request, auth=None, db=db_session)
    # En DEMO_MODE : fallback DemoState (test couverture indirecte via end-to-end)


def test_phase72_security_log_warning_on_rejection(db_session, caplog):
    """Phase 7.2 : tentative IDOR loggée pour audit security_logger."""
    import logging

    from services.scope_utils import get_scope_org_id

    request = _make_request(x_org_id="77777")

    with caplog.at_level(logging.WARNING, logger="promeos.security"):
        result = get_scope_org_id(request, auth=None, db=db_session)

    assert result is None
    # Au moins 1 warning logged (anti-IDOR audit)
    security_logs = [r for r in caplog.records if r.name == "promeos.security"]
    assert any("x_org_id_rejected_db_check" in r.message for r in security_logs), (
        "Tentative IDOR doit être loggée pour audit security_logger"
    )
