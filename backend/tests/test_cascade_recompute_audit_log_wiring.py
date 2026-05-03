"""
PROMEOS — Sprint C-2 Phase 1.3 : Tests wiring cascade_recompute → log_cascade.

Vérifie l'intégration du service audit_log_service.log_cascade() dans
cascade_recompute_service :
- Cascade persist=True crée 1 AuditLog avec action='cascade.recompute'
- Payload detail_json structuré (type, trigger_field, actions, ...)
- Résilience : un échec log_cascade NE BLOQUE PAS la cascade
- Preview SAVEPOINT : 0 AuditLog persisté après dry-run
- Query audit trail org-scoped retrouve les logs cascade
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def site_with_data():
    """Site HELIOS avec champs Phase 3 minimaux pour cascade."""
    from database import SessionLocal
    from models import Site, not_deleted

    db = SessionLocal()
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if not site:
            pytest.skip("Aucun site HELIOS dans la DB")
        if site.altitude_m is None:
            site.altitude_m = 35
        if not site.operat_sous_categorie_id:
            site.operat_sous_categorie_id = "Bureaux - Bureaux Standards (cloisonnés - attribués)"
        db.commit()
        yield site, db
    finally:
        db.close()


# ─── Test 1 : cascade persist=True crée un AuditLog ─────────────────────────


def test_cascade_recompute_creates_audit_log(site_with_data):
    """cascade_recompute_on_change(persist=True) → 1 AuditLog action='cascade.recompute'."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change
    from services.audit_log_service import query_audit_trail

    site, db = site_with_data
    org_id = 999_001  # org test isolée

    # Pré-condition : aucun log cascade pour cette org
    pre_logs = query_audit_trail(db, org_id=org_id, action="cascade.recompute")
    pre_count = len(pre_logs)

    # Cascade altitude (champ simple, ne change pas réellement la DB)
    cascade_recompute_on_change(
        db,
        site,
        "Site.altitude_m",
        old_value=site.altitude_m,
        new_value=site.altitude_m,  # idempotent
        persist=True,
        user_id=None,
        org_id=org_id,
        correlation_id="test-cascade-create-001",
    )
    db.commit()

    # Post-condition : 1 nouveau log cascade
    post_logs = query_audit_trail(db, org_id=org_id, action="cascade.recompute")
    assert len(post_logs) == pre_count + 1
    log = post_logs[0]
    assert log.action == "cascade.recompute"
    assert log.field_modified == "Site.altitude_m"
    assert log.org_id == org_id
    assert log.correlation_id == "test-cascade-create-001"


# ─── Test 2 : payload detail_json structuré ─────────────────────────────────


def test_cascade_audit_log_contains_correct_payload(site_with_data):
    """detail_json de l'AuditLog cascade contient le payload structuré attendu."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change
    from services.audit_log_service import query_audit_trail

    site, db = site_with_data
    org_id = 999_002

    cascade_recompute_on_change(
        db,
        site,
        "Site.altitude_m",
        old_value=35,
        new_value=35,
        persist=True,
        org_id=org_id,
        correlation_id="test-payload-002",
    )
    db.commit()

    logs = query_audit_trail(db, org_id=org_id, correlation_id="test-payload-002")
    assert len(logs) >= 1
    payload = json.loads(logs[0].detail_json)
    assert payload["type"] == "cascade_recompute"
    assert payload["trigger_field"] == "Site.altitude_m"
    assert "actions" in payload
    assert "errors_count" in payload
    assert "successes_count" in payload
    assert "persisted" in payload


# ─── Test 3 : résilience — échec log_cascade ne bloque pas la cascade ────────


def test_cascade_audit_log_failure_does_not_break_cascade(site_with_data):
    """Si log_cascade raise, cascade renvoie quand même CascadeResult valide."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    site, db = site_with_data

    # Mock log_cascade pour qu'il raise systématiquement
    with patch(
        "services.audit_log_service.log_cascade",
        side_effect=RuntimeError("simulated audit failure"),
    ):
        # La cascade NE DOIT PAS lever l'exception — elle doit catch et continuer
        result = cascade_recompute_on_change(
            db,
            site,
            "Site.altitude_m",
            old_value=site.altitude_m,
            new_value=site.altitude_m,
            persist=True,
            org_id=999_003,
        )

    # Cascade returns valid result even if audit failed
    assert result is not None
    assert result.field_modified == "Site.altitude_m"
    assert result.persisted is True
    # Les actions cascade ont bien été exécutées
    assert isinstance(result.actions, list)


# ─── Test 4 : preview SAVEPOINT — 0 AuditLog persisté après rollback ────────


def test_cascade_preview_no_audit_log_persisted(site_with_data):
    """cascade_impact_preview rollback SAVEPOINT → 0 AuditLog créé."""
    from database import SessionLocal
    from regops.services.cascade_recompute_service import cascade_impact_preview
    from services.audit_log_service import query_audit_trail

    site, db = site_with_data
    org_id = 999_004
    cid = "test-preview-no-persist-004"

    # Pré-condition : 0 log avec ce correlation_id
    pre = query_audit_trail(db, org_id=org_id, correlation_id=cid)
    assert len(pre) == 0

    # Preview cascade — ne doit PAS persister d'audit log
    cascade_impact_preview(
        db,
        site,
        "Site.altitude_m",
        500,
        org_id=org_id,
        correlation_id=cid,
    )

    # Vérifier dans une nouvelle session pour bypasser la session courante
    db2 = SessionLocal()
    try:
        post = query_audit_trail(db2, org_id=org_id, correlation_id=cid)
        assert len(post) == 0, f"Preview a créé {len(post)} AuditLog (dry-run violation)"
    finally:
        db2.close()


# ─── Test 5 : query audit trail org-scoped pour cascade ─────────────────────


def test_cascade_audit_log_org_scoped_query(site_with_data):
    """query_audit_trail org_id=X retrouve les logs cascade créés pour X."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change
    from services.audit_log_service import query_audit_trail

    site, db = site_with_data
    cid = "test-cascade-orgscope-005"

    # Cascade pour org A
    cascade_recompute_on_change(
        db,
        site,
        "Site.altitude_m",
        old_value=35,
        new_value=35,
        persist=True,
        org_id=999_005,
        correlation_id=cid,
    )
    # Cascade pour org B (correlation_id différent)
    cascade_recompute_on_change(
        db,
        site,
        "Site.altitude_m",
        old_value=35,
        new_value=35,
        persist=True,
        org_id=999_006,
        correlation_id="other-cid",
    )
    db.commit()

    # Org A ne voit que ses logs
    logs_a = query_audit_trail(db, org_id=999_005, action="cascade.recompute")
    assert any(l.correlation_id == cid for l in logs_a)
    assert not any(l.correlation_id == "other-cid" for l in logs_a)
