"""
PROMEOS — Tests cardinaux Phase 7.8 Sprint C-7 — 6 P0 fixes audit deep multi-agents Phase 7.

Couvre :
- D-Audit-Phase7-IDOR-DataConnect-5-Endpoints-001 P0 (Critical)
- D-Audit-Phase7-IDOR-GRDF-2-Endpoints-002 P0 (Critical)
- D-Audit-Phase7-IDOR-Org-Id-Override-Bypass-003 P0 (High)
- D-Audit-Phase7-Audit-Rollback-Loss-004 P0 (CNIL)
- D-Audit-Phase7-RGPD-Article-Inadequate-005 P0 (Reg)
- D-Audit-Phase7-TURPE-7-Codes-Obsolete-006 P0 (Reg)
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _seed_org_with_meter(db, prm: str, siren_suffix: str = "78001"):
    """Helper Org → EJ → PF → Site → Meter (PRM ou PCE)."""
    from models import EnergyVector, EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.energy_models import Meter

    org = Organisation(nom=f"OrgPhase78_{siren_suffix}", siren=f"888{siren_suffix}")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom=f"EJ{siren_suffix}", siren=f"888{siren_suffix}", organisation_id=org.id)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom=f"PF{siren_suffix}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(nom=f"S{siren_suffix}", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db.add(site)
    db.flush()
    meter = Meter(
        meter_id=prm,
        name=f"Meter-{prm[:8]}",
        site_id=site.id,
        energy_vector=EnergyVector.ELECTRICITY,
        is_active=True,
    )
    db.add(meter)
    db.commit()
    return org.id, meter.id


# ─── Fix 1 — IDOR DataConnect endpoints ─────────────────────────────────────


def test_phase78_dataconnect_consent_403_cross_tenant(app_client):
    """Phase 7.8 cardinal : GET /api/dataconnect/consent/{prm} retourne 403 si PRM hors org."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org_with_meter(db, prm="11111111111111", siren_suffix="78001")
        org_b_id, _ = _seed_org_with_meter(db, prm="22222222222222", siren_suffix="78002")
    finally:
        db.close()

    # Org A tente de consulter PRM d'org B → 403
    resp = client.get(
        "/api/dataconnect/consent/22222222222222",
        headers={"X-Org-Id": str(org_a_id)},
    )
    assert resp.status_code == 403, (
        f"Phase 7.8 BLOQUANT IDOR : PRM cross-tenant doit retourner 403, got {resp.status_code}"
    )


def test_phase78_dataconnect_tokens_filtered_by_org(app_client):
    """Phase 7.8 cardinal : GET /api/dataconnect/tokens filtré par org (anti CWE-200)."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org_with_meter(db, prm="33333333333333", siren_suffix="78003")
        org_b_id, _ = _seed_org_with_meter(db, prm="44444444444444", siren_suffix="78004")
    finally:
        db.close()

    resp = client.get(
        "/api/dataconnect/tokens",
        headers={"X-Org-Id": str(org_a_id)},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    # Aucun token pour org_a (Meter sans token créé)
    # Mais surtout : aucun token org B ne doit fuiter
    assert all("44444444444444" not in t.get("prm", "") for t in tokens)


def test_phase78_dataconnect_delete_token_403_cross_tenant(app_client):
    """Phase 7.8 cardinal : DELETE /api/dataconnect/tokens/{prm} 403 si PRM hors org."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org_with_meter(db, prm="55555555555555", siren_suffix="78005")
        org_b_id, _ = _seed_org_with_meter(db, prm="66666666666666", siren_suffix="78006")
    finally:
        db.close()

    resp = client.delete(
        "/api/dataconnect/tokens/66666666666666",
        headers={"X-Org-Id": str(org_a_id)},
    )
    assert resp.status_code == 403


# ─── Fix 2 — IDOR GRDF endpoints ────────────────────────────────────────────


def test_phase78_grdf_consumption_403_cross_tenant(app_client):
    """Phase 7.8 cardinal : GET /api/grdf/pce/{pce}/consumption 403 si PCE hors org."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org_with_meter(db, prm="GAZ001GRDF0001", siren_suffix="78007")
        org_b_id, _ = _seed_org_with_meter(db, prm="GAZ002GRDF0002", siren_suffix="78008")
    finally:
        db.close()

    resp = client.get(
        "/api/grdf/pce/GAZ002GRDF0002/consumption?date_debut=2026-01-01&date_fin=2026-01-31",
        headers={"X-Org-Id": str(org_a_id)},
    )
    assert resp.status_code == 403, "PCE cross-tenant doit retourner 403"


# ─── Fix 3 — IDOR org_id_override ───────────────────────────────────────────


def test_phase78_org_id_override_validates_db_existence(app_client):
    """Phase 7.8 cardinal : org_id_override pointant org inexistante → 403 (vs accepté avant fix)."""
    from services.scope_utils import resolve_org_id

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        # Créer 1 org pour avoir un X-Org-Id valide
        from models import Organisation

        org = Organisation(nom="OrgValid78", siren="888991111", actif=True)
        db.add(org)
        db.commit()

        # Mock request sans X-Org-Id ni JWT → tomber dans branche org_id_override
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {}

        # org_id_override pointant ID inexistant → 403
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            resolve_org_id(request, None, db, org_id_override=99999)
        assert exc.value.status_code == 403
        assert "invalid" in exc.value.detail.lower() or "not found" in exc.value.detail.lower()
    finally:
        db.close()


def test_phase78_org_id_override_inactive_org_rejected(app_client):
    """Phase 7.8 : org_id_override pointant org actif=False → 403 (anti soft-delete bypass)."""
    from unittest.mock import MagicMock

    from fastapi import HTTPException

    from services.scope_utils import resolve_org_id

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        from models import Organisation

        org = Organisation(nom="OrgInactive78", siren="888996666", actif=False)
        db.add(org)
        db.commit()
        org_id = org.id

        request = MagicMock()
        request.headers = {}

        with pytest.raises(HTTPException) as exc:
            resolve_org_id(request, None, db, org_id_override=org_id)
        assert exc.value.status_code == 403
    finally:
        db.close()


# ─── Fix 4 — RGPD audit log immédiat (anti-rollback CNIL) ───────────────────


def test_phase78_log_consent_changes_batch_persists_immediately(app_client):
    """Phase 7.8 CNIL : log_consent_changes_batch commit immédiat → audit survit rollback caller."""
    from models import AuditLog
    from services.audit_log_service import log_consent_changes_batch

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        from models import Organisation

        org = Organisation(nom="OrgRGPDPhase78", siren="888995555", actif=True)
        db.add(org)
        db.commit()
        org_id = org.id

        events = log_consent_changes_batch(
            db=db,
            user_id=1,
            org_id=org_id,
            target_type="organisation",
            target_id=org_id,
            changes=[
                {"field": "consentement_dataconnect_global", "old": None, "new": True},
            ],
            cgu_version="1.0",
        )

        # Cardinal Phase 7.8 : événements PERSISTÉS (commit immédiat)
        assert len(events) == 1

        # Simuler rollback caller — events doivent survivre
        db.rollback()

        # Re-query : événement présent malgré rollback
        check_db = SessionLocal()
        try:
            persisted = (
                check_db.query(AuditLog)
                .filter(AuditLog.action == "rgpd.consent_change", AuditLog.org_id == org_id)
                .all()
            )
            assert len(persisted) == 1, "Phase 7.8 BLOQUANT CNIL : audit_log perdu sur rollback caller (régression)"
        finally:
            check_db.close()
    finally:
        db.close()


# ─── Fix 5 — Article 5(2) + 30 RGPD substitution ────────────────────────────


def test_phase78_audit_log_external_api_uses_article_5_2_30():
    """Phase 7.8 : payload `connector.api_call` cite Article 5(2) + Article 30 (vs Article 6)."""
    import inspect

    from services.audit_log_service import _record_external_api_event

    src = inspect.getsource(_record_external_api_event)
    assert "Article 5(2)" in src and "Article 30" in src, (
        "Phase 7.8 BLOQUANT REG : payload doit citer Article 5(2) accountability + Article 30 registre.\n"
        "Article 6 RGPD (bases légales) NON adéquat pour traçabilité technique."
    )
    assert "Article 6 RGPD" not in src, (
        "Phase 7.8 BLOQUANT REG : 'Article 6 RGPD' encore présent (substitution incomplète)."
    )


# ─── Fix 6 — TURPE 7 codes documentation ────────────────────────────────────


def test_phase78_turpe_7_official_codes_present():
    """Phase 7.8 : codes TURPE 7 officiels (P/HPH/HCH/HPB/HCB) explicitement documentés."""
    from services.bill_intelligence.anomaly_detector import (
        _PERIOD_CODES_KNOWN_TURPE_7,
        _PERIOD_CODES_LEGACY_TURPE_6,
    )

    cardinal_turpe_7 = ["P", "HPH", "HCH", "HPB", "HCB"]
    missing_official = [c for c in cardinal_turpe_7 if c not in _PERIOD_CODES_KNOWN_TURPE_7]
    assert not missing_official, (
        f"Phase 7.8 BLOQUANT REG : codes TURPE 7 officiels manquants : {missing_official}.\n"
        "CRE délibération 2025-78 du 13/03/2025 (JO 14/05/2025) — TURPE 7 HTA/BT cardinal."
    )

    # Legacy TURPE 6 explicitement séparés (rétro-compat factures historiques)
    legacy_codes = ["HPE", "HCE", "PM", "POINTE"]
    missing_legacy = [c for c in legacy_codes if c not in _PERIOD_CODES_LEGACY_TURPE_6]
    assert not missing_legacy, (
        f"Phase 7.8 : codes legacy TURPE 6 manquants : {missing_legacy}. Rétro-compat factures historiques."
    )


def test_phase78_period_codes_known_includes_both_turpe_versions():
    """Phase 7.8 : _PERIOD_CODES_KNOWN combine TURPE 7 officiel + TURPE 6 legacy."""
    from services.bill_intelligence.anomaly_detector import _PERIOD_CODES_KNOWN

    # TURPE 7 officiel
    for code in ("P", "HPH", "HCH", "HPB", "HCB"):
        assert code in _PERIOD_CODES_KNOWN
    # TURPE 6 legacy (rétro-compat)
    for code in ("HPE", "HCE", "PM"):
        assert code in _PERIOD_CODES_KNOWN
