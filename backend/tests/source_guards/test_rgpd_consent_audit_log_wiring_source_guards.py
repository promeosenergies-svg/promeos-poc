"""
PROMEOS — Source guards Phase 7.4 — RGPD consent_change AuditLog wiring (CNIL).

Anti-régression cardinal post-Phase 7.4 — clôture pattern doctrinal "Déclaration sans
enforcement runtime" 5/5 Phase C+ :

- SG_RGPD_AUDIT_01 : Helper `log_consent_change` + `log_consent_changes_batch` présents dans audit_log_service.py
- SG_RGPD_AUDIT_02 : 2 endpoints PATCH RGPD Phase 7.3 incluent appel `log_consent_changes_batch` (anti-régression wiring)
- SG_RGPD_AUDIT_03 : action="rgpd.consent_change" présent (cohérent convention dot-snake AuditLog)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_AUDIT_SERVICE_PATH = _BACKEND_ROOT / "services" / "audit_log_service.py"
_RGPD_ROUTE_PATH = _BACKEND_ROOT / "routes" / "rgpd_consent.py"


def test_sg_rgpd_audit_01_helpers_present():
    """SG_RGPD_AUDIT_01 cardinal : `log_consent_change` + `log_consent_changes_batch` présents."""
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    cardinal_helpers = [
        "def log_consent_change(",
        "def log_consent_changes_batch(",
        'action="rgpd.consent_change"',
    ]
    missing = [h for h in cardinal_helpers if h not in content]
    assert not missing, (
        f"SG_RGPD_AUDIT_01 BLOQUANT : helpers manquants dans audit_log_service.py : {missing}.\n"
        "Phase 7.4 cardinal : clôture pattern doctrinal 'Déclaration sans enforcement runtime' 5/5.\n"
        "Sans ces helpers, CNIL article 7 'preuve d'origine forte' impossible à tracer."
    )


def test_sg_rgpd_audit_02_endpoints_wire_batch_helper():
    """SG_RGPD_AUDIT_02 cardinal : 2 endpoints Phase 7.3 wirés sur `log_consent_changes_batch`.

    Anti-régression : empêche la suppression silencieuse du wiring AuditLog
    (qui invaliderait audit RGPD CNIL).
    """
    content = _RGPD_ROUTE_PATH.read_text(encoding="utf-8")

    # Import obligatoire
    assert "from services.audit_log_service import log_consent_changes_batch" in content, (
        "SG_RGPD_AUDIT_02 : import log_consent_changes_batch manquant dans rgpd_consent.py."
    )

    # Au moins 2 appels (1 par endpoint Phase 7.3 — org + dp local)
    call_count = content.count("log_consent_changes_batch(")
    assert call_count >= 2, (
        f"SG_RGPD_AUDIT_02 BLOQUANT : appels log_consent_changes_batch insuffisants ({call_count}/2).\n"
        "Phase 7.3 a livré 2 endpoints PATCH (org + dp local). Phase 7.4 doit wirer chacun.\n"
        "Sans wiring sur les 2, mutation consentement non tracée AuditLog → CNIL preuve cassée."
    )

    # Vérifier scope distinct (organisation vs delivery_point)
    assert 'target_type="organisation"' in content, (
        "SG_RGPD_AUDIT_02 : target_type='organisation' manquant (endpoint Org)."
    )
    assert 'target_type="delivery_point"' in content, (
        "SG_RGPD_AUDIT_02 : target_type='delivery_point' manquant (endpoint DP local)."
    )


def test_sg_rgpd_audit_03_action_naming_convention():
    """SG_RGPD_AUDIT_03 : action='rgpd.consent_change' suit convention dot-snake AuditLog.

    Cohérent avec autres event types existants : 'patrimoine.update', 'site.archive',
    'cascade.recompute' (vs SHOUTING_CASE non-uniforme).
    """
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    assert 'action="rgpd.consent_change"' in content, (
        "SG_RGPD_AUDIT_03 : action='rgpd.consent_change' manquant.\n"
        "Convention dot-snake cohérente avec 'patrimoine.update' / 'cascade.recompute' / etc."
    )

    # Anti-pattern : SHOUTING_CASE incohérent
    assert "RGPD_CONSENT_CHANGE" not in content, (
        "SG_RGPD_AUDIT_03 : SHOUTING_CASE 'RGPD_CONSENT_CHANGE' détecté.\n"
        "Convention PROMEOS = dot-snake : 'rgpd.consent_change'."
    )
