"""
PROMEOS — Sprint C-2 Phase 1.2 : Tests audit_log_service.

Vérifie API publique :
- log_patrimoine_change : audit modification champ patrimoine
- log_cascade : audit cascade recompute (Phase 6 Sprint C-1)
- query_audit_trail : récupération filtrée + org-scopée
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_session():
    """Session DB SQLAlchemy avec rollback en fin de test."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


# ─── log_patrimoine_change ──────────────────────────────────────────────────


def test_log_patrimoine_change_basic(db_session):
    """Création log patrimoine basique."""
    from services.audit_log_service import log_patrimoine_change

    log = log_patrimoine_change(
        db_session,
        user_id=1,
        org_id=1,
        entity_type="site",
        entity_id=42,
        action="site.update",
    )
    assert log.id is not None
    assert log.action == "site.update"
    assert log.resource_type == "site"
    assert log.resource_id == "42"
    assert log.user_id == 1
    assert log.org_id == 1


def test_log_patrimoine_change_with_diff(db_session):
    """old_value + new_value sérialisés en JSON."""
    from services.audit_log_service import log_patrimoine_change

    log = log_patrimoine_change(
        db_session,
        user_id=1,
        org_id=1,
        entity_type="site",
        entity_id=42,
        action="site.update",
        field_modified="code_postal",
        old_value="75001",
        new_value="13001",
    )
    assert log.field_modified == "code_postal"
    assert json.loads(log.old_value) == "75001"
    assert json.loads(log.new_value) == "13001"


def test_log_patrimoine_change_with_correlation_id(db_session):
    """correlation_id stocké pour traçage cross-services."""
    from services.audit_log_service import log_patrimoine_change

    log = log_patrimoine_change(
        db_session,
        user_id=1,
        org_id=1,
        entity_type="site",
        entity_id=42,
        action="site.update",
        correlation_id="req-abc-123",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
    )
    assert log.correlation_id == "req-abc-123"
    assert log.ip_address == "192.168.1.1"
    assert log.user_agent == "Mozilla/5.0"


def test_log_patrimoine_change_dict_value_serialized(db_session):
    """old_value/new_value en dict sérialisés JSON correctement."""
    from services.audit_log_service import log_patrimoine_change

    log = log_patrimoine_change(
        db_session,
        user_id=1,
        org_id=1,
        entity_type="site",
        entity_id=42,
        action="site.update",
        old_value={"a": 1, "b": "test"},
        new_value={"a": 2, "b": "modified"},
    )
    assert json.loads(log.old_value) == {"a": 1, "b": "test"}
    assert json.loads(log.new_value) == {"a": 2, "b": "modified"}


# ─── log_cascade ────────────────────────────────────────────────────────────


def test_log_cascade_basic(db_session):
    """Cascade result enveloppé en payload structuré."""
    from regops.services.cascade_recompute_service import CascadeAction, CascadeResult
    from services.audit_log_service import log_cascade

    cascade_result = CascadeResult(
        entity_type="Site",
        entity_id=42,
        field_modified="Site.code_postal",
        old_value="75001",
        new_value="13001",
        actions=[
            CascadeAction(output_field="operat_zone_climatique", new_value="H3"),
            CascadeAction(output_field="cabs_kwh_m2_an", new_value=90.0),
        ],
        persisted=True,
        computed_at=datetime.utcnow().isoformat(),
    )

    log = log_cascade(
        db_session,
        user_id=1,
        org_id=1,
        cascade_result=cascade_result,
    )
    assert log.action == "cascade.recompute"
    assert log.resource_type == "Site"
    assert log.resource_id == "42"
    payload = json.loads(log.detail_json)
    assert payload["type"] == "cascade_recompute"
    assert payload["trigger_field"] == "Site.code_postal"
    assert len(payload["actions"]) == 2
    assert payload["successes_count"] == 2
    assert payload["errors_count"] == 0
    assert payload["persisted"] is True


def test_log_cascade_with_errors(db_session):
    """Actions avec erreurs comptées dans payload."""
    from regops.services.cascade_recompute_service import CascadeAction, CascadeResult
    from services.audit_log_service import log_cascade

    cascade_result = CascadeResult(
        entity_type="Site",
        entity_id=42,
        field_modified="Site.altitude_m",
        old_value=35,
        new_value=2500,
        actions=[
            CascadeAction(output_field="operat_palier_altitude", new_value="alt_gte_1600"),
            CascadeAction(output_field="cabs_kwh_m2_an", error="Sous-cat introuvable"),
        ],
        persisted=False,
        computed_at=datetime.utcnow().isoformat(),
    )

    log = log_cascade(db_session, user_id=1, org_id=1, cascade_result=cascade_result)
    payload = json.loads(log.detail_json)
    assert payload["successes_count"] == 1
    assert payload["errors_count"] == 1
    assert payload["persisted"] is False


# ─── query_audit_trail ──────────────────────────────────────────────────────


def test_query_audit_trail_org_scoped(db_session):
    """query filtre strictement par org_id."""
    from services.audit_log_service import log_patrimoine_change, query_audit_trail

    log_patrimoine_change(db_session, user_id=1, org_id=100, entity_type="site", entity_id=1, action="test.org_a")
    log_patrimoine_change(db_session, user_id=2, org_id=200, entity_type="site", entity_id=2, action="test.org_b")
    db_session.flush()

    logs_a = query_audit_trail(db_session, org_id=100)
    actions_a = {l.action for l in logs_a}
    assert "test.org_a" in actions_a
    assert "test.org_b" not in actions_a, "Org A ne doit pas voir les logs de Org B (sécurité)"


def test_query_audit_trail_filter_entity_type(db_session):
    """Filtre par entity_type."""
    from services.audit_log_service import log_patrimoine_change, query_audit_trail

    log_patrimoine_change(db_session, user_id=1, org_id=300, entity_type="site", entity_id=1, action="site.test")
    log_patrimoine_change(
        db_session, user_id=1, org_id=300, entity_type="batiment", entity_id=1, action="batiment.test"
    )
    db_session.flush()

    logs_site = query_audit_trail(db_session, org_id=300, entity_type="site")
    assert all(l.resource_type == "site" for l in logs_site)


def test_query_audit_trail_filter_correlation_id(db_session):
    """Filtre par correlation_id pour tracer un workflow cross-services."""
    from services.audit_log_service import log_patrimoine_change, query_audit_trail

    cid = "test-corr-xyz-789"
    log_patrimoine_change(
        db_session,
        user_id=1,
        org_id=400,
        entity_type="site",
        entity_id=1,
        action="step.1",
        correlation_id=cid,
    )
    log_patrimoine_change(
        db_session,
        user_id=1,
        org_id=400,
        entity_type="site",
        entity_id=1,
        action="step.2",
        correlation_id=cid,
    )
    log_patrimoine_change(
        db_session,
        user_id=1,
        org_id=400,
        entity_type="site",
        entity_id=1,
        action="other",
        correlation_id="different",
    )
    db_session.flush()

    logs = query_audit_trail(db_session, org_id=400, correlation_id=cid)
    assert len(logs) == 2
    assert all(l.correlation_id == cid for l in logs)


def test_query_audit_trail_pagination_limit(db_session):
    """limit pagination respectée."""
    from services.audit_log_service import log_patrimoine_change, query_audit_trail

    for i in range(15):
        log_patrimoine_change(db_session, user_id=1, org_id=500, entity_type="site", entity_id=i, action="test")
    db_session.flush()

    logs = query_audit_trail(db_session, org_id=500, limit=10)
    assert len(logs) <= 10


def test_query_audit_trail_time_range(db_session):
    """Filtre since + until."""
    from services.audit_log_service import log_patrimoine_change, query_audit_trail

    log = log_patrimoine_change(db_session, user_id=1, org_id=600, entity_type="site", entity_id=1, action="recent")
    db_session.flush()

    cutoff = log.created_at - timedelta(hours=1)
    logs = query_audit_trail(db_session, org_id=600, since=cutoff)
    assert any(l.action == "recent" for l in logs)

    future = log.created_at + timedelta(hours=1)
    logs_future = query_audit_trail(db_session, org_id=600, since=future)
    assert all(l.action != "recent" for l in logs_future)
