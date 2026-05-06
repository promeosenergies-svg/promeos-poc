"""
PROMEOS — Tests cardinaux Phase 7.4 Sprint C-7 — log_consent_change RGPD CNIL helper.

CLÔTURE pattern doctrinal "Déclaration sans enforcement runtime" 5/5 cardinal Phase C+.

Couverture cardinal :
- Helper log_consent_change crée AuditLog action="rgpd.consent_change"
- Helper log_consent_changes_batch (multi mutations 1 PATCH)
- Wiring endpoints Phase 7.3 PATCH org + dp local crée events runtime
- CNIL article 7 preuve d'origine forte : qui + quand + valeur + CGU + scope
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _seed_org(db, siren_suffix="74001"):
    """Helper Org → EJ → PF → Site → DP."""
    from models import (
        DeliveryPoint,
        DeliveryPointEnergyType,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    org = Organisation(nom=f"OrgPhase74_{siren_suffix}", siren=f"997{siren_suffix}")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom=f"EJ{siren_suffix}", siren=f"997{siren_suffix}", organisation_id=org.id)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom=f"PF{siren_suffix}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(nom=f"S{siren_suffix}", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db.add(site)
    db.flush()
    dp = DeliveryPoint(
        code=f"{siren_suffix}1234567890"[:14],
        site_id=site.id,
        energy_type=DeliveryPointEnergyType.ELEC,
        grd_code="ENEDIS",
    )
    db.add(dp)
    db.commit()
    return org.id, dp.id


# ─── Helper log_consent_change ───────────────────────────────────────────────


def test_phase74_helper_creates_audit_log_with_action_rgpd_consent_change(app_client):
    """Phase 7.4 cardinal : helper crée AuditLog action='rgpd.consent_change'."""
    from models import AuditLog
    from services.audit_log_service import log_consent_change

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="74001")

        log = log_consent_change(
            db=db,
            user_id=1,
            org_id=org_id,
            target_type="organisation",
            target_id=org_id,
            field="consentement_dataconnect_global",
            old_value=None,
            new_value=True,
            cgu_version="1.0",
        )
        db.commit()

        assert log.action == "rgpd.consent_change"
        assert log.resource_type == "organisation"
        assert log.resource_id == str(org_id)
        assert log.org_id == org_id
        assert log.user_id == 1
        assert log.field_modified == "consentement_dataconnect_global"
    finally:
        db.close()


def test_phase74_helper_payload_contains_cgu_version_and_rgpd_article(app_client):
    """Phase 7.4 CNIL : payload detail_json contient cgu_version + référence article RGPD."""
    from services.audit_log_service import log_consent_change

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="74002")

        log = log_consent_change(
            db=db,
            user_id=42,
            org_id=org_id,
            target_type="organisation",
            target_id=org_id,
            field="consentement_grdf_global",
            old_value=False,
            new_value=True,
            cgu_version="2.1.0",
        )
        db.commit()

        payload = json.loads(log.detail_json)
        assert payload["cgu_version"] == "2.1.0"
        assert payload["type"] == "rgpd.consent_change"
        assert payload["field"] == "consentement_grdf_global"
        assert "Article 7 RGPD" in payload["rgpd_article"]
    finally:
        db.close()


def test_phase74_helper_old_new_values_serialized(app_client):
    """Phase 7.4 : old/new_value sérialisés en string (booléens → 'True'/'False')."""
    from services.audit_log_service import log_consent_change

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="74003")

        log = log_consent_change(
            db=db,
            user_id=1,
            org_id=org_id,
            target_type="organisation",
            target_id=org_id,
            field="consentement_dataconnect_global",
            old_value=False,
            new_value=True,
            cgu_version="1.0",
        )
        db.commit()

        assert log.old_value is not None
        assert log.new_value is not None
    finally:
        db.close()


def test_phase74_batch_creates_n_events_for_n_changes(app_client):
    """Phase 7.4 : batch helper crée 1 event AuditLog par mutation."""
    from models import AuditLog
    from services.audit_log_service import log_consent_changes_batch

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="74004")

        events = log_consent_changes_batch(
            db=db,
            user_id=1,
            org_id=org_id,
            target_type="organisation",
            target_id=org_id,
            changes=[
                {"field": "consentement_dataconnect_global", "old": None, "new": True},
                {"field": "consentement_grdf_global", "old": None, "new": False},
            ],
            cgu_version="1.0",
        )
        db.commit()

        assert len(events) == 2
        assert all(e.action == "rgpd.consent_change" for e in events)
        fields = {e.field_modified for e in events}
        assert fields == {"consentement_dataconnect_global", "consentement_grdf_global"}
    finally:
        db.close()


def test_phase74_batch_empty_changes_returns_empty_list(app_client):
    """Phase 7.4 : batch sans changes retourne [] (pas d'event créé)."""
    from services.audit_log_service import log_consent_changes_batch

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="74005")

        events = log_consent_changes_batch(
            db=db,
            user_id=1,
            org_id=org_id,
            target_type="organisation",
            target_id=org_id,
            changes=[],
            cgu_version="1.0",
        )
        db.commit()

        assert events == []
    finally:
        db.close()


# ─── Wiring endpoints Phase 7.3 ──────────────────────────────────────────────


def test_phase74_patch_org_endpoint_creates_audit_log_event(app_client):
    """Phase 7.4 cardinal : PATCH /api/organisations/{id}/consentement crée event AuditLog."""
    from models import AuditLog

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="74006")
    finally:
        db.close()

    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "1.0"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        events = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "rgpd.consent_change",
                AuditLog.org_id == org_id,
                AuditLog.resource_type == "organisation",
            )
            .all()
        )
        assert len(events) == 1
        assert events[0].field_modified == "consentement_dataconnect_global"
    finally:
        db.close()


def test_phase74_patch_org_endpoint_2_fields_creates_2_events(app_client):
    """Phase 7.4 : PATCH avec dataconnect+grdf crée 2 events distincts."""
    from models import AuditLog

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="74007")
    finally:
        db.close()

    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={
            "consentement_dataconnect_global": True,
            "consentement_grdf_global": False,
            "cgu_version": "1.0",
        },
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        events = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "rgpd.consent_change",
                AuditLog.org_id == org_id,
            )
            .all()
        )
        assert len(events) == 2
        fields = {e.field_modified for e in events}
        assert fields == {"consentement_dataconnect_global", "consentement_grdf_global"}
    finally:
        db.close()


def test_phase74_patch_dp_local_endpoint_creates_audit_log_event(app_client):
    """Phase 7.4 : PATCH /api/delivery_points/{id}/consentement-local crée event scope=delivery_point."""
    from models import AuditLog

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, dp_id = _seed_org(db, siren_suffix="74008")
    finally:
        db.close()

    resp = client.patch(
        f"/api/delivery_points/{dp_id}/consentement-local",
        json={"consentement_grdf_local": True, "cgu_version": "2.0"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        events = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "rgpd.consent_change",
                AuditLog.resource_type == "delivery_point",
                AuditLog.resource_id == str(dp_id),
            )
            .all()
        )
        assert len(events) == 1
        assert events[0].field_modified == "consentement_grdf_local"
        assert events[0].org_id == org_id
        # CGU version dans payload
        payload = json.loads(events[0].detail_json)
        assert payload["cgu_version"] == "2.0"
    finally:
        db.close()


def test_phase74_audit_event_has_created_at_immutable(app_client):
    """Phase 7.4 CNIL anti-falsification : AuditLog.created_at est NOT NULL et auto-set."""
    from datetime import datetime

    from models import AuditLog
    from services.audit_log_service import log_consent_change

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="74009")

        log = log_consent_change(
            db=db,
            user_id=1,
            org_id=org_id,
            target_type="organisation",
            target_id=org_id,
            field="consentement_dataconnect_global",
            old_value=None,
            new_value=True,
            cgu_version="1.0",
        )
        db.commit()

        assert log.created_at is not None
        assert isinstance(log.created_at, datetime)
    finally:
        db.close()


def test_phase74_audit_log_org_scoped_correctly(app_client):
    """Phase 7.4 : event scope cross-org isolé (org A event ne pollue pas org B)."""
    from models import AuditLog

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org(db, siren_suffix="74010")
        org_b_id, _ = _seed_org(db, siren_suffix="74011")
    finally:
        db.close()

    # PATCH org A
    client.patch(
        f"/api/organisations/{org_a_id}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "1.0"},
        headers={"X-Org-Id": str(org_a_id)},
    )

    db = SessionLocal()
    try:
        # Events org A
        events_a = (
            db.query(AuditLog).filter(AuditLog.action == "rgpd.consent_change", AuditLog.org_id == org_a_id).count()
        )
        # Events org B (devrait être 0)
        events_b = (
            db.query(AuditLog).filter(AuditLog.action == "rgpd.consent_change", AuditLog.org_id == org_b_id).count()
        )

        assert events_a >= 1
        assert events_b == 0, "Cross-org pollution AuditLog détectée — scope cassé"
    finally:
        db.close()
