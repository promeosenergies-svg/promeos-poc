"""
PROMEOS — Tests cardinaux Phase 8.4 Sprint C-8 Lot 2 — P1 SEC + REG fixés.

Couvre :
- D-Audit-C8-Address-Substring-Match-005 P1 SEC (ip_address allowlist non-redacted)
- D-Audit-C8-CGU-Cache-Reload-Auth-004 P1 SEC (reload_cgu_referentiel doc admin-only)
- D-Audit-C8-CGU-Pdf-Hash-007 P1 REG (contenu_sha256 field ajouté YAML)
- D-Audit-C8-CGU-Dates-Versionning-008 P1 REG (statut archive_test_only clarifié)
"""

from __future__ import annotations

from pathlib import Path


# ─── Fix P1-SEC-005 — address allowlist ip_address ──────────────────────────


def test_phase84_lot2_ip_address_not_redacted():
    """Phase 8.4 P1 SEC : `ip_address` (technique non-PII) NON redacted (allowlist)."""
    from services.audit_log_service import _is_sensitive_key

    # Allowlist non-sensitive (techniques)
    assert _is_sensitive_key("ip_address") is False, (
        "Phase 8.4 BLOQUANT SEC : ip_address sur-redacted (perte traçabilité CNIL article 5(2))"
    )
    assert _is_sensitive_key("mac_address") is False
    assert _is_sensitive_key("url_address") is False
    assert _is_sensitive_key("user_agent") is False


def test_phase84_lot2_real_pii_address_still_redacted():
    """Phase 8.4 : vrais PII address keys restent redacted (billing/shipping/home/email)."""
    from services.audit_log_service import _is_sensitive_key

    # Vrais PII : redacted
    assert _is_sensitive_key("billing_address") is True
    assert _is_sensitive_key("shipping_address") is True
    assert _is_sensitive_key("street_address") is True
    assert _is_sensitive_key("user_email") is True
    assert _is_sensitive_key("contact_phone") is True


# ─── Fix P1-SEC-004 — LRU cache reload doc admin-only ───────────────────────


def test_phase84_lot2_reload_cgu_referentiel_admin_only_doc():
    """Phase 8.4 P1 SEC : `reload_cgu_referentiel()` documenté admin-only (caller responsable)."""
    import inspect

    from services.cgu_service import reload_cgu_referentiel

    src = inspect.getsource(reload_cgu_referentiel)
    assert "D-Audit-C8-CGU-Cache-Reload-Auth-004" in src, "Phase 8.4 : marqueur dette absent"
    assert "admin" in src.lower(), "Phase 8.4 : doctrine admin-only manquante docstring"
    assert "require_role" in src or "ADMIN" in src, "Phase 8.4 : guard auth recommandation manquante"


# ─── Fix P1-REG-007 — CGU contenu_sha256 field ──────────────────────────────


def test_phase84_lot2_cgu_yaml_includes_contenu_sha256_field():
    """Phase 8.4 P1 REG cardinal CNIL : YAML CGU inclut champ `contenu_sha256` (preuve d'origine forte)."""
    yaml_path = Path(__file__).parent.parent / "config" / "cgu_referentiel.yaml"
    content = yaml_path.read_text(encoding="utf-8")

    # Champ contenu_sha256 présent (au moins 1 occurrence)
    assert "contenu_sha256" in content, (
        "Phase 8.4 BLOQUANT REG : champ contenu_sha256 absent YAML CGU (preuve d'origine forte CNIL)"
    )

    # Marqueur dette Phase 8.4 fix
    assert "D-Audit-C8-CGU-Pdf-Hash-007" in content


def test_phase84_lot2_cgu_versions_archive_test_only_explicit():
    """Phase 8.4 P1 REG : versions tests fixtures clarifiées `statut: archive_test_only`."""
    from services.cgu_service import _load_cgu_referentiel, reload_cgu_referentiel

    reload_cgu_referentiel()
    config = _load_cgu_referentiel()

    versions = config.get("versions", [])
    # Au moins une version actuel + au moins une archive_test_only
    actuel = [v for v in versions if v.get("statut") == "actuel"]
    archive_test = [v for v in versions if v.get("statut") == "archive_test_only"]

    assert len(actuel) >= 1
    assert len(archive_test) >= 1, (
        "Phase 8.4 P1 REG : fixtures tests clarifiées 'archive_test_only' (vs 'archive' ambigu)"
    )


def test_phase84_lot2_runtime_patch_rejects_archive_test_only(app_client):
    """Phase 8.4 cardinal : runtime PATCH refuse `statut='archive_test_only'` (idem `archive`)."""
    from models import Organisation

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhase84Lot2", siren="887840004", actif=True)
        db.add(org)
        db.commit()
        org_id = org.id
    finally:
        db.close()

    # Version archive_test_only "0.9" rejetée par runtime PATCH
    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "0.9"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 422, "Phase 8.4 : 0.9 archive_test_only doit être rejeté runtime"

    # Version actuel "1.0" acceptée
    resp_ok = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "1.0"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp_ok.status_code == 200
