"""
PROMEOS — Tests cardinaux Phase 8.3 Sprint C-8 — Lot CR+REG polish (4 P1 fixes).

Couvre :
- D-Audit-Phase7-RGPD-Consent-Dead-Comments-001 P1 CR (rgpd_consent.py:147 + :250 cleanup)
- D-Audit-Phase7-Org-Actif-Idiomatic-001 P1 CR (Organisation.actif.is_(True) idiomatique)
- D-Sprint-C7-VNU-Terminologie-Cleanup-002 P1 REG (tarifs_reglementaires.yaml:546 art. L.336-2)
- D-Audit-Phase7-Hash-Key-Code-Overmatch-001 P1 SEC (_is_hash_key('code') word-boundary)
"""

from __future__ import annotations

from pathlib import Path


# ─── Fix 1 — Dead-code comments rgpd_consent.py ─────────────────────────────


def test_phase83_rgpd_consent_no_dead_phase74_preparation_comments():
    """Phase 8.3 cardinal CR : commentaires 'Phase 7.4 préparation' obsolètes supprimés."""
    rgpd_path = Path(__file__).parent.parent / "routes" / "rgpd_consent.py"
    content = rgpd_path.read_text(encoding="utf-8")

    # Commentaires obsolètes "Phase 7.4 préparation" éliminés (déjà fait Phase 7.4)
    assert "Phase 7.4 préparation : wiring AuditLog log_consent_change automatique" not in content
    assert "Phase 7.4 préparation : wiring AuditLog log_consent_change scope" not in content

    # Marqueur Phase 8.3 fix présent
    assert "D-Audit-Phase7-RGPD-Consent-Dead-Comments-001" in content


# ─── Fix 2 — Organisation.actif idiomatique ────────────────────────────────


def test_phase83_main_py_uses_organisation_actif_idiomatic():
    """Phase 8.3 : main.py utilise Organisation.actif.is_(True) (vs == True)."""
    main_path = Path(__file__).parent.parent / "main.py"
    content = main_path.read_text(encoding="utf-8")

    # Anti-pattern == True éliminé sur Organisation.actif
    assert "Organisation.actif == True" not in content, (
        "Phase 8.3 BLOQUANT : 'Organisation.actif == True' encore dans main.py (idiomatique .is_(True))"
    )
    # Pattern idiomatique présent
    assert "Organisation.actif.is_(True)" in content


def test_phase83_routes_sites_uses_actif_idiomatic():
    """Phase 8.3 : routes/sites.py idem (Organisation.actif.is_(True))."""
    sites_path = Path(__file__).parent.parent / "routes" / "sites.py"
    content = sites_path.read_text(encoding="utf-8")

    # noqa E712 supprimé car plus nécessaire post-fix
    assert "Organisation.actif == True" not in content
    assert "Organisation.actif.is_(True)" in content


# ─── Fix 3 — VNU YAML terminologie cleanup ──────────────────────────────────


def test_phase83_tarifs_yaml_vnu_terminologie_cardinal():
    """Phase 8.3 : tarifs_reglementaires.yaml VNU = 'Versement pour Non-Usage' art. L.336-2."""
    yaml_path = Path(__file__).parent.parent / "config" / "tarifs_reglementaires.yaml"
    content = yaml_path.read_text(encoding="utf-8")

    # Section VNU header utilise terminologie cardinale (PAS "Nucléaire Universel")
    assert "Versement pour Non-Usage" in content, (
        "Phase 8.3 BLOQUANT REG : 'Versement pour Non-Usage' absent du header VNU YAML"
    )
    assert "L.336-2" in content, "Phase 8.3 : référence art. L.336-2 manquante (cohérence Phase 7.7 Lot C)"

    # Anti-pattern : header obsolète
    assert "VNU (Versement Nucléaire Universel)" not in content, (
        "Phase 8.3 BLOQUANT REG : header obsolète 'Versement Nucléaire Universel' encore présent"
    )


# ─── Fix 4 — _is_hash_key('code') word-boundary ─────────────────────────────


def test_phase83_is_hash_key_code_exact_match_only():
    """Phase 8.3 cardinal SEC : _is_hash_key('code') exact match strict (vs substring overmatch)."""
    from services.audit_log_service import _is_hash_key

    # Vrai positif : key OAuth2 cardinale "code" exact
    assert _is_hash_key("code") is True
    # PRM/PCE/SIREN substring conservé (cardinal Phase 7.5 anti-régression — patterns spécifiques)
    assert _is_hash_key("usage_point_id") is True
    assert _is_hash_key("user_prm") is True


def test_phase83_is_hash_key_code_no_overmatch_period_error():
    """Phase 8.3 cardinal SEC anti sur-redaction : period_code/error_code/region_code NON matchés."""
    from services.audit_log_service import _is_hash_key

    # Faux positifs Phase 7.5 maintenant éliminés
    assert _is_hash_key("period_code") is False, (
        "Phase 8.3 BLOQUANT SEC : 'period_code' était sur-redacted (substring match) — fix word-boundary"
    )
    assert _is_hash_key("error_code") is False
    assert _is_hash_key("region_code") is False
    assert _is_hash_key("status_code") is False
    assert _is_hash_key("zip_code") is False
    assert _is_hash_key("country_code") is False
