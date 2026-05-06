"""
PROMEOS — Source guards Phase 8.3 Sprint C-8 — Lot CR+REG polish anti-régression.

3 SG cardinaux :
- SG_PHASE83_01 : rgpd_consent.py sans commentaire "Phase 7.4 préparation" obsolète
- SG_PHASE83_02 : Organisation.actif.is_(True) idiomatique (main.py + routes/sites.py)
- SG_PHASE83_03 : VNU terminologie YAML "Versement pour Non-Usage" + L.336-2
"""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_RGPD_CONSENT_PATH = _BACKEND_ROOT / "routes" / "rgpd_consent.py"
_MAIN_PATH = _BACKEND_ROOT / "main.py"
_SITES_PATH = _BACKEND_ROOT / "routes" / "sites.py"
_TARIFS_YAML_PATH = _BACKEND_ROOT / "config" / "tarifs_reglementaires.yaml"
_AUDIT_SERVICE_PATH = _BACKEND_ROOT / "services" / "audit_log_service.py"


def test_sg_phase83_01_rgpd_consent_no_dead_comments():
    """SG_PHASE83_01 : rgpd_consent.py sans commentaire 'Phase 7.4 préparation' obsolète."""
    content = _RGPD_CONSENT_PATH.read_text(encoding="utf-8")
    assert "Phase 7.4 préparation : wiring AuditLog log_consent_change" not in content, (
        "SG_PHASE83_01 BLOQUANT : commentaire 'Phase 7.4 préparation' encore présent (dead-code)"
    )
    assert "D-Audit-Phase7-RGPD-Consent-Dead-Comments-001" in content


def test_sg_phase83_02_organisation_actif_idiomatic():
    """SG_PHASE83_02 : aucun 'Organisation.actif == True' runtime dans main.py + routes/sites.py."""
    for path in (_MAIN_PATH, _SITES_PATH):
        content = path.read_text(encoding="utf-8")
        runtime_lines = [
            line
            for line in content.split("\n")
            if "Organisation.actif == True" in line and not line.strip().startswith("#")
        ]
        assert not runtime_lines, (
            f"SG_PHASE83_02 BLOQUANT : 'Organisation.actif == True' runtime dans {path.name} :\n"
            + "\n".join(runtime_lines)
        )

    # Marqueur Phase 8.3 fix présent au moins dans 1 fichier
    main_content = _MAIN_PATH.read_text(encoding="utf-8")
    sites_content = _SITES_PATH.read_text(encoding="utf-8")
    assert "D-Audit-Phase7-Org-Actif-Idiomatic-001" in (main_content + sites_content)


def test_sg_phase83_03_vnu_yaml_terminologie_cardinal():
    """SG_PHASE83_03 : tarifs YAML utilise 'Versement pour Non-Usage' + L.336-2."""
    content = _TARIFS_YAML_PATH.read_text(encoding="utf-8")

    # Header VNU utilise terminologie cardinale
    assert "Versement pour Non-Usage" in content, (
        "SG_PHASE83_03 BLOQUANT REG : 'Versement pour Non-Usage' absent tarifs YAML"
    )
    assert "L.336-2" in content

    # Anti-pattern : "VNU (Versement Nucléaire Universel)" header obsolète
    assert "VNU (Versement Nucléaire Universel)" not in content


def test_sg_phase83_04_is_hash_key_code_word_boundary_fix():
    """SG_PHASE83_04 : _is_hash_key('code') word-boundary fix (P1-SEC-006)."""
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    # Marqueur fix Phase 8.3
    assert "D-Audit-Phase7-Hash-Key-Code-Overmatch-001" in content, (
        "SG_PHASE83_04 BLOQUANT SEC : référence dette overmatch absente"
    )
    # Pattern exact match strict pour "code" (la key OAuth2)
    assert 'lk == "code"' in content, 'SG_PHASE83_04 : exact match `lk == "code"` manquant (P1-SEC-006 fix)'
