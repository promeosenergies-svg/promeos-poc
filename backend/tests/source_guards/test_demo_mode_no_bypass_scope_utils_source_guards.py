"""
PROMEOS — Source guards anti-régression Phase 7.2 — DEMO_MODE bypass scope_utils (SEC-2026-012).

Anti-régression cardinal post-fix Sprint C-7 Phase 7.2 (ADR-017 Option B) :
- SG_DEMO_MODE_01 : `scope_utils.get_scope_org_id` valide X-Org-Id en DB (Organisation existence + actif + soft-delete)
- SG_DEMO_MODE_02 : signature `get_scope_org_id(request, auth, db=None)` préservée (backward-compat)
- SG_DEMO_MODE_03 : `_security_logger.warning("x_org_id_rejected_db_check")` présent (audit trail IDOR tentatives)
- SG_DEMO_MODE_04 : pas de pattern bypass DEMO_MODE early-return cross-modules

Si quelqu'un retire la validation DB ou ajoute un bypass DEMO_MODE caché, ces SG flaggent.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SCOPE_UTILS_PATH = _BACKEND_ROOT / "services" / "scope_utils.py"


def test_sg_demo_mode_01_db_validation_present_in_get_scope_org_id():
    """SG_DEMO_MODE_01 cardinal : `get_scope_org_id` valide X-Org-Id en DB (existence + actif + soft-delete).

    Anti-régression SEC-2026-012 : sans cette validation, X-Org-Id forgé permettait IDOR
    cross-tenant énumération en DEMO_MODE (~25 endpoints surface attaque).
    """
    content = _SCOPE_UTILS_PATH.read_text(encoding="utf-8")

    cardinal_patterns = [
        "Organisation, not_deleted",  # import requis
        "Organisation.id == org_id",  # check existence
        "Organisation.actif.is_(True)",  # check actif
        "not_deleted(Organisation)",  # check soft-delete
        "x_org_id_rejected_db_check",  # warning audit
    ]

    missing = [pattern for pattern in cardinal_patterns if pattern not in content]
    assert not missing, (
        f"SG_DEMO_MODE_01 BLOQUANT : patterns validation DB X-Org-Id manquants : {missing}.\n"
        "Sprint C-7 Phase 7.2 fix ADR-017 Option B (SEC-2026-012) requiert validation DB stricte.\n"
        "Régression : permet IDOR cross-tenant énumération en DEMO_MODE."
    )


def test_sg_demo_mode_02_signature_backward_compat():
    """SG_DEMO_MODE_02 : signature `get_scope_org_id(request, auth, db=None)` backward-compat préservée.

    Permet aux callers legacy Sprint C-1 → C-6 de continuer fonctionner sans migration immédiate.
    """
    content = _SCOPE_UTILS_PATH.read_text(encoding="utf-8")

    expected_signature_pattern = re.compile(
        r"def get_scope_org_id\(\s*request:\s*Request,\s*auth:\s*Optional\[AuthContext\],\s*db:\s*Optional\[Session\]\s*=\s*None,?\s*\)",
        re.MULTILINE,
    )

    assert expected_signature_pattern.search(content), (
        "SG_DEMO_MODE_02 BLOQUANT : signature `get_scope_org_id(request, auth, db=None)` "
        "modifiée. Backward-compat callers legacy cassée."
    )


def test_sg_demo_mode_03_resolve_org_id_passes_db():
    """SG_DEMO_MODE_03 : `resolve_org_id` propage `db` à `get_scope_org_id` (fix runtime cardinal)."""
    content = _SCOPE_UTILS_PATH.read_text(encoding="utf-8")

    # Pattern : resolve_org_id appelle get_scope_org_id(request, auth, db=db) ou similaire
    assert "get_scope_org_id(request, auth, db=db)" in content, (
        "SG_DEMO_MODE_03 BLOQUANT : `resolve_org_id` doit propager `db` à `get_scope_org_id`.\n"
        "Sans cette propagation, validation DB X-Org-Id non déclenchée → IDOR persiste.\n"
        "Pattern attendu : `org_id = get_scope_org_id(request, auth, db=db)`"
    )


def test_sg_demo_mode_04_no_early_return_demo_mode_bypass():
    """SG_DEMO_MODE_04 : pas de pattern `if DEMO_MODE: return raw_value_unvalidated` early.

    Anti-régression cardinal : empêcher la réintroduction d'un bypass DEMO_MODE
    sans validation DB (cause racine SEC-2026-012).
    """
    content = _SCOPE_UTILS_PATH.read_text(encoding="utf-8")

    # Pattern interdit : `if DEMO_MODE` suivi de `return X` sans `db` query
    forbidden_patterns = [
        r"if DEMO_MODE:\s*\n\s*return\s+\w+\s*$",  # bypass return early
        r"if DEMO_MODE\s+and\s+raw:\s*\n\s*return",  # condition shortcut bypass
    ]

    for pattern in forbidden_patterns:
        match = re.search(pattern, content, re.MULTILINE)
        assert not match, (
            f"SG_DEMO_MODE_04 BLOQUANT : pattern bypass DEMO_MODE détecté : {pattern}.\n"
            f"Match : {match.group(0) if match else '?'}\n"
            "Régression SEC-2026-012 : permet IDOR cross-tenant en DEMO_MODE."
        )

    # Vérifier qu'il y a une référence à ADR-017 Option B (documentation traçable)
    assert "ADR-017" in content or "SEC-2026-012" in content, (
        "SG_DEMO_MODE_04 : référence ADR-017 ou SEC-2026-012 manquante dans scope_utils.py "
        "(traçabilité audit + onboarding nouveaux devs)."
    )
