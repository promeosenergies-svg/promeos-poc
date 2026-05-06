"""
PROMEOS — Tests cardinaux Phase 7.5 Sprint C-7 — `audit_external_api_call` décorateur (ADR-018).

DERNIER P0 résiduel CNIL Sprint C-7. Couvre :
- Décorateur AuditLog `connector.api_call` sur succès + exception
- Sanitisation secrets (Authorization/Bearer/client_secret/token/code_verifier)
- Hashing identifiants (PRM/PCE/SIREN/SIRET/usage_point_id/code)
- Préservation `functools.wraps` (__name__, __doc__)
- duration_ms ≥ 0, request_hash/response_hash stables
- Découplage transactionnel (audit DB séparée — exception caller préservée)
- Wiring 4 connecteurs cardinaux (DataConnect / GRDF / Sirene)
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def audit_db(monkeypatch):
    """In-memory SQLite + monkeypatch `database.SessionLocal` pour isoler audit trail."""
    from models import Base

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    import database
    import services.audit_log_service as svc

    monkeypatch.setattr(database, "SessionLocal", TestSession)
    monkeypatch.setattr(svc, "SessionLocal", TestSession, raising=False)

    yield TestSession


# ─── Helper resolver d'événements AuditLog connector.api_call ─────────────


def _events(session_factory, provider: str | None = None):
    from models import AuditLog

    db = session_factory()
    try:
        q = db.query(AuditLog).filter(AuditLog.action == "connector.api_call")
        if provider:
            q = q.filter(AuditLog.resource_type == provider)
        return q.all()
    finally:
        db.close()


# ─── Décorateur cardinal : succès ─────────────────────────────────────────


def test_phase75_decorator_creates_audit_log_on_success(audit_db):
    """Phase 7.5 cardinal : décorateur crée AuditLog action='connector.api_call' sur succès."""
    from services.audit_log_service import audit_external_api_call

    @audit_external_api_call(provider="test_provider", endpoint="/foo", method="GET")
    def fake_call(prm: str):
        return {"data": "ok"}

    result = fake_call(prm="12345678901234")

    assert result == {"data": "ok"}
    events = _events(audit_db, "test_provider")
    assert len(events) == 1
    payload = json.loads(events[0].detail_json)
    assert payload["success"] is True
    assert payload["provider"] == "test_provider"
    assert payload["endpoint"] == "/foo"
    assert payload["method"] == "GET"
    assert payload["duration_ms"] >= 0
    assert payload["error_class"] is None


def test_phase75_decorator_creates_audit_log_on_exception(audit_db):
    """Phase 7.5 cardinal : exception loguée success=False + error_class + reraise."""
    from services.audit_log_service import audit_external_api_call

    @audit_external_api_call(provider="test_provider", endpoint="/fail")
    def fake_fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        fake_fail()

    events = _events(audit_db, "test_provider")
    assert len(events) == 1
    payload = json.loads(events[0].detail_json)
    assert payload["success"] is False
    assert payload["error_class"] == "ValueError"
    assert "boom" in payload["error_message"]


# ─── Sanitisation secrets ──────────────────────────────────────────────────


def test_phase75_decorator_redacts_authorization_token(audit_db):
    """Phase 7.5 sécu : Authorization/Bearer/token/client_secret redacted dans detail_json."""
    from services.audit_log_service import audit_external_api_call

    @audit_external_api_call(provider="test_provider", endpoint="/auth")
    def fake_auth(token: str, client_secret: str, payload: dict):
        return {"ok": True}

    fake_auth(
        token="super-secret-token-xxx",
        client_secret="xyz-789",
        payload={"Authorization": "Bearer abcdef"},
    )

    events = _events(audit_db, "test_provider")
    assert len(events) == 1
    raw = events[0].detail_json
    assert "super-secret-token-xxx" not in raw
    assert "xyz-789" not in raw
    assert "abcdef" not in raw
    payload = json.loads(raw)
    assert payload["args_summary"]["kwargs"]["token"] == "<redacted>"
    assert payload["args_summary"]["kwargs"]["client_secret"] == "<redacted>"
    assert payload["args_summary"]["kwargs"]["payload"]["Authorization"] == "<redacted>"


def test_phase75_decorator_hashes_prm_pce_siren(audit_db):
    """Phase 7.5 RGPD : identifiants (PRM/PCE/SIREN/SIRET) hashés sha256[:16] (pas raw)."""
    from services.audit_log_service import audit_external_api_call

    @audit_external_api_call(provider="test_provider", endpoint="/data")
    def fake_data(prm: str, pce: str, siren: str):
        return {}

    raw_prm = "12345678901234"
    raw_pce = "GI999999999"
    raw_siren = "123456789"
    fake_data(prm=raw_prm, pce=raw_pce, siren=raw_siren)

    events = _events(audit_db, "test_provider")
    raw = events[0].detail_json
    assert raw_prm not in raw
    assert raw_pce not in raw
    assert raw_siren not in raw
    payload = json.loads(raw)
    assert payload["args_summary"]["kwargs"]["prm"].startswith("sha256:")
    assert payload["args_summary"]["kwargs"]["pce"].startswith("sha256:")
    assert payload["args_summary"]["kwargs"]["siren"].startswith("sha256:")


def test_phase75_decorator_session_kwarg_not_serialized(audit_db):
    """Phase 7.5 : SQLAlchemy Session injectée en kwargs n'est PAS sérialisée (non-pertinent + non-serializable)."""
    from services.audit_log_service import audit_external_api_call

    @audit_external_api_call(provider="test_provider", endpoint="/with_db")
    def fake_call_with_db(db, prm: str):
        return {"ok": True}

    db_obj = audit_db()
    try:
        fake_call_with_db(db=db_obj, prm="X")
    finally:
        db_obj.close()

    events = _events(audit_db, "test_provider")
    payload = json.loads(events[0].detail_json)
    # Session ne doit pas figurer dans args_summary.kwargs
    assert "db" not in payload["args_summary"]["kwargs"]


# ─── Décorateur preserves wraps ────────────────────────────────────────────


def test_phase75_decorator_preserves_function_metadata(audit_db):
    """Phase 7.5 : functools.wraps preserve __name__/__doc__ — anti-régression introspection."""
    from services.audit_log_service import audit_external_api_call

    @audit_external_api_call(provider="test_provider", endpoint="/x")
    def my_named_function():
        """My docstring."""
        return 1

    assert my_named_function.__name__ == "my_named_function"
    assert my_named_function.__doc__ == "My docstring."


# ─── Endpoint dynamique ────────────────────────────────────────────────────


def test_phase75_decorator_supports_dynamic_endpoint_callable(audit_db):
    """Phase 7.5 : endpoint=callable(*args, **kwargs) résout dynamiquement (cohérent _api_get path)."""
    from services.audit_log_service import audit_external_api_call

    @audit_external_api_call(
        provider="test_provider",
        endpoint=lambda *a, **kw: kw.get("path", "?"),
    )
    def dynamic_call(path: str):
        return {"ok": True}

    dynamic_call(path="/dynamic/route/xyz")
    events = _events(audit_db, "test_provider")
    assert events[0].resource_id == "/dynamic/route/xyz"
    payload = json.loads(events[0].detail_json)
    assert payload["endpoint"] == "/dynamic/route/xyz"


# ─── Hash stable ───────────────────────────────────────────────────────────


def test_phase75_request_hash_stable_for_same_input(audit_db):
    """Phase 7.5 : request_hash deterministic — même input → même hash (audit reproductible)."""
    from services.audit_log_service import audit_external_api_call

    @audit_external_api_call(provider="test_provider", endpoint="/h")
    def fake(x: int):
        return None

    fake(x=42)
    fake(x=42)
    fake(x=99)
    events = _events(audit_db, "test_provider")
    hashes = [json.loads(e.detail_json)["request_hash"] for e in events]
    assert hashes[0] == hashes[1]
    assert hashes[0] != hashes[2]


# ─── Découplage transactionnel ─────────────────────────────────────────────


def test_phase75_audit_uses_separate_session(audit_db, monkeypatch):
    """Phase 7.5 : exception dans audit_db ne casse PAS le caller (résilience)."""
    from services.audit_log_service import audit_external_api_call

    # Forcer SessionLocal à raise — le caller doit néanmoins terminer normalement
    import services.audit_log_service as svc

    def broken_session():
        raise RuntimeError("DB down")

    monkeypatch.setattr(svc, "SessionLocal", broken_session, raising=False)

    @audit_external_api_call(provider="test_provider", endpoint="/resilient")
    def caller():
        return {"ok": True}

    # Ne doit PAS lever
    result = caller()
    assert result == {"ok": True}


# ─── Wiring connecteurs cardinaux ──────────────────────────────────────────


def test_phase75_enedis_dataconnect_api_get_decorated():
    """SG-style : EnedisDataConnectConnector._api_get wiré décorateur."""
    from connectors.enedis_dataconnect import EnedisDataConnectConnector

    # functools.wraps préserve __wrapped__ — vérifier décoration
    assert hasattr(EnedisDataConnectConnector._api_get, "__wrapped__"), (
        "EnedisDataConnectConnector._api_get doit être décoré audit_external_api_call (Phase 7.5)"
    )


def test_phase75_enedis_dataconnect_exchange_code_decorated():
    """SG-style : exchange_code wiré (OAuth2 token endpoint — preuve d'extraction)."""
    from connectors.enedis_dataconnect import EnedisDataConnectConnector

    assert hasattr(EnedisDataConnectConnector.exchange_code, "__wrapped__"), (
        "EnedisDataConnectConnector.exchange_code doit être décoré audit_external_api_call (Phase 7.5)"
    )


def test_phase75_grdf_adict_api_get_decorated():
    """SG-style : GrdfAdictConnector._api_get wiré."""
    from connectors.grdf_adict import GrdfAdictConnector

    assert hasattr(GrdfAdictConnector._api_get, "__wrapped__"), (
        "GrdfAdictConnector._api_get doit être décoré audit_external_api_call (Phase 7.5)"
    )


def test_phase75_sirene_hydrate_decorated():
    """SG-style : sirene_hydrate.hydrate_siren_from_api wiré."""
    from services.sirene_hydrate import hydrate_siren_from_api

    assert hasattr(hydrate_siren_from_api, "__wrapped__"), (
        "hydrate_siren_from_api doit être décoré audit_external_api_call (Phase 7.5)"
    )
