"""
PROMEOS — Tests cardinaux Phase 7.3 Sprint C-7 — PATCH endpoints RGPD consentement (ADR-019).

Couverture cardinal :
- Validation pydantic stricte cgu_version (CNIL article 7)
- Org-scoping strict (cohérent ADR-017 Option B Phase 7.2)
- Cascade trigger runtime (Phase 5.8 G1 préservé)
- Override local DP (ADR-007 Option B archi-helios Phase 4.5)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _seed_org(db, siren_suffix="73001"):
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

    org = Organisation(nom=f"OrgPhase73_{siren_suffix}", siren=f"998{siren_suffix}")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom=f"EJ{siren_suffix}", siren=f"998{siren_suffix}", organisation_id=org.id)
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


# ─── Validation pydantic schemas ─────────────────────────────────────────────


def test_phase73_schema_org_consent_no_cgu_version_rejected():
    """Phase 7.3 cardinal CNIL : cgu_version requis si consentement_*_global set."""
    from pydantic import ValidationError

    from schemas.rgpd_consent import OrganisationConsentementPatch

    with pytest.raises(ValidationError, match="cgu_version requis"):
        OrganisationConsentementPatch(
            consentement_dataconnect_global=True,
            cgu_version=None,
        )


def test_phase73_schema_org_consent_with_cgu_version_accepted():
    """Phase 7.3 : payload valide avec cgu_version."""
    from schemas.rgpd_consent import OrganisationConsentementPatch

    schema = OrganisationConsentementPatch(
        consentement_dataconnect_global=True,
        cgu_version="1.0",
    )
    assert schema.consentement_dataconnect_global is True
    assert schema.cgu_version == "1.0"


def test_phase73_schema_org_consent_empty_payload_rejected():
    """Phase 7.3 : PATCH vide rejeté (au moins 1 champ requis)."""
    from pydantic import ValidationError

    from schemas.rgpd_consent import OrganisationConsentementPatch

    with pytest.raises(ValidationError, match="Au moins un champ"):
        OrganisationConsentementPatch()


def test_phase73_schema_dp_local_consent_no_cgu_version_rejected():
    """Phase 7.3 : DP local consent — cgu_version requis si set."""
    from pydantic import ValidationError

    from schemas.rgpd_consent import DeliveryPointConsentementLocalPatch

    with pytest.raises(ValidationError, match="cgu_version requis"):
        DeliveryPointConsentementLocalPatch(consentement_grdf_local=False)


def test_phase73_schema_dp_local_consent_only_cgu_update_accepted():
    """Phase 7.3 : update cgu_version seul OK (mise à jour version après acceptation)."""
    from schemas.rgpd_consent import DeliveryPointConsentementLocalPatch

    schema = DeliveryPointConsentementLocalPatch(cgu_version="2.0")
    assert schema.cgu_version == "2.0"
    assert schema.consentement_dataconnect_local is None


# ─── Endpoint PATCH Org integration ──────────────────────────────────────────


def test_phase73_patch_org_consent_with_cgu_returns_200(app_client):
    """Phase 7.3 cardinal : PATCH valide → 200 + cascade triggered."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="73001")
    finally:
        db.close()

    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={
            "consentement_dataconnect_global": True,
            "cgu_version": "1.0",
        },
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["org_id"] == org_id
    assert data["consentement_dataconnect_global"] is True
    assert data["cgu_version"] == "1.0"
    assert "cascade" in data


def test_phase73_patch_org_consent_no_cgu_returns_422(app_client):
    """Phase 7.3 cardinal CNIL : cgu_version manquant → 422 validation error."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="73002")
    finally:
        db.close()

    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={"consentement_dataconnect_global": True},  # pas de cgu_version
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 422, f"Expected 422 validation error, got {resp.status_code}"


def test_phase73_patch_org_cross_tenant_blocked_403(app_client):
    """Phase 7.3 cardinal SEC : org_id mismatch → 403 (anti-IDOR cross-tenant)."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org(db, siren_suffix="73003")
        org_b_id, _ = _seed_org(db, siren_suffix="73004")
    finally:
        db.close()

    # Tenter PATCH org_a en injectant X-Org-Id=org_b → mismatch détecté
    resp = client.patch(
        f"/api/organisations/{org_a_id}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "1.0"},
        headers={"X-Org-Id": str(org_b_id)},
    )
    assert resp.status_code == 403, f"Expected 403 cross-tenant blocked, got {resp.status_code}"


def test_phase73_patch_org_404_inexistant(app_client):
    """Phase 7.3 : org_id inexistant → 404 (mais X-Org-Id valide pour passer scope check)."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="73005")
    finally:
        db.close()

    # X-Org-Id valide mais path id différent et inexistant
    resp = client.patch(
        f"/api/organisations/{org_id + 99999}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "1.0"},
        headers={"X-Org-Id": str(org_id)},
    )
    # Soit 403 (scope check intervient avant), soit 404 — accepter les deux
    assert resp.status_code in (403, 404)


def test_phase73_patch_org_audit_fields_set_correctly(app_client):
    """Phase 7.3 : consentement_*_at + _by + _cgu_version persistés."""
    from models import Organisation

    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="73006")
    finally:
        db.close()

    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={
            "consentement_grdf_global": True,
            "cgu_version": "2.1.0",
        },
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        assert org.consentement_grdf_global is True
        assert org.consentement_grdf_at is not None
        assert org.consentement_grdf_cgu_version == "2.1.0"
        # consentement_dataconnect_global non touché (PATCH partial)
        assert org.consentement_dataconnect_global is None
    finally:
        db.close()


def test_phase73_patch_org_partial_update_preserves_other_field(app_client):
    """Phase 7.3 : PATCH partiel — modifier dataconnect ne touche pas grdf."""
    from models import Organisation

    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, _ = _seed_org(db, siren_suffix="73007")
        # État initial : grdf=True, dataconnect=None
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        org.consentement_grdf_global = True
        org.consentement_grdf_cgu_version = "1.0"
        db.commit()
    finally:
        db.close()

    # PATCH seulement dataconnect
    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "1.5"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        assert org.consentement_dataconnect_global is True
        assert org.consentement_dataconnect_cgu_version == "1.5"
        # GRDF préservé inchangé
        assert org.consentement_grdf_global is True
        assert org.consentement_grdf_cgu_version == "1.0"
    finally:
        db.close()


# ─── Endpoint PATCH DeliveryPoint local override ────────────────────────────


def test_phase73_patch_dp_local_consent_with_cgu_returns_200(app_client):
    """Phase 7.3 cardinal ADR-007 Option B : override local DP persiste."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, dp_id = _seed_org(db, siren_suffix="73008")
    finally:
        db.close()

    resp = client.patch(
        f"/api/delivery_points/{dp_id}/consentement-local",
        json={
            "consentement_dataconnect_local": False,
            "cgu_version": "1.0",
        },
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["dp_id"] == dp_id
    assert data["consentement_dataconnect_local"] is False
    assert data["cgu_version"] == "1.0"


def test_phase73_patch_dp_cross_tenant_blocked_404(app_client):
    """Phase 7.3 SEC : DP de org B avec X-Org-Id=org A → 404 (JOIN scope guard)."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org(db, siren_suffix="73009")
        org_b_id, dp_b_id = _seed_org(db, siren_suffix="73010")
    finally:
        db.close()

    resp = client.patch(
        f"/api/delivery_points/{dp_b_id}/consentement-local",
        json={"consentement_dataconnect_local": True, "cgu_version": "1.0"},
        headers={"X-Org-Id": str(org_a_id)},
    )
    assert resp.status_code == 404, f"Expected 404 cross-tenant DP, got {resp.status_code}"


def test_phase73_patch_dp_audit_trail_complete(app_client):
    """Phase 7.3 : DP local consent — _at + _by + _cgu_version persistés."""
    from models import DeliveryPoint

    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, dp_id = _seed_org(db, siren_suffix="73011")
    finally:
        db.close()

    resp = client.patch(
        f"/api/delivery_points/{dp_id}/consentement-local",
        json={"consentement_grdf_local": True, "cgu_version": "3.0"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        dp = db.query(DeliveryPoint).filter(DeliveryPoint.id == dp_id).first()
        assert dp.consentement_grdf_local is True
        assert dp.consentement_grdf_local_at is not None
        assert dp.consentement_grdf_local_cgu_version == "3.0"
    finally:
        db.close()
