"""
PROMEOS — Source guards Phase 7.3 — RGPD consent endpoints structure (ADR-019).

Anti-régression cardinal post-livraison Phase 7.3 :
- SG_RGPD_CONSENT_01 : 2 endpoints PATCH dédiés présents (org + dp)
- SG_RGPD_CONSENT_02 : Schemas pydantic validation cgu_version requis si consentement_* set
- SG_RGPD_CONSENT_03 : Org-scoping via resolve_org_id (anti-IDOR cross-tenant)
- SG_RGPD_CONSENT_04 : Cascade trigger préservé (Phase 5.8 G1 réutilisé via cascade_recompute_on_change)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ROUTE_PATH = _BACKEND_ROOT / "routes" / "rgpd_consent.py"
_SCHEMA_PATH = _BACKEND_ROOT / "schemas" / "rgpd_consent.py"


def test_sg_rgpd_consent_01_two_patch_endpoints_present():
    """SG_RGPD_CONSENT_01 : 2 endpoints PATCH dédiés présents (ADR-019)."""
    content = _ROUTE_PATH.read_text(encoding="utf-8")

    cardinal_endpoints = [
        '@router.patch("/organisations/{org_id}/consentement")',
        '@router.patch("/delivery_points/{dp_id}/consentement-local")',
    ]
    missing = [ep for ep in cardinal_endpoints if ep not in content]
    assert not missing, (
        f"SG_RGPD_CONSENT_01 BLOQUANT : endpoints PATCH manquants : {missing}.\n"
        "Phase 7.3 (ADR-019) requiert 2 endpoints dédiés RGPD-compliant."
    )


def test_sg_rgpd_consent_02_pydantic_cgu_validation():
    """SG_RGPD_CONSENT_02 : Schemas pydantic validation cgu_version requis si consentement_* set."""
    content = _SCHEMA_PATH.read_text(encoding="utf-8")

    cardinal_patterns = [
        "OrganisationConsentementPatch",
        "DeliveryPointConsentementLocalPatch",
        "validate_cgu_required_if_consent_set",
        "cgu_version requis",
        "@model_validator",
    ]
    missing = [p for p in cardinal_patterns if p not in content]
    assert not missing, (
        f"SG_RGPD_CONSENT_02 BLOQUANT : patterns validation cgu_version manquants : {missing}.\n"
        "Phase 7.3 (ADR-019 + CNIL article 7) requiert validation pydantic stricte."
    )


def test_sg_rgpd_consent_03_org_scoping_resolve_org_id():
    """SG_RGPD_CONSENT_03 : Org-scoping via resolve_org_id (cohérent ADR-017 Phase 7.2)."""
    content = _ROUTE_PATH.read_text(encoding="utf-8")

    assert "from services.scope_utils import resolve_org_id" in content, (
        "SG_RGPD_CONSENT_03 : import resolve_org_id manquant.\n"
        "Anti-IDOR cross-tenant requis (cohérent ADR-017 Phase 7.2)."
    )

    assert "resolve_org_id(request, auth, db)" in content, (
        "SG_RGPD_CONSENT_03 : appel resolve_org_id(request, auth, db) manquant.\n"
        "Sans org-scoping, IDOR cross-tenant possible."
    )

    # Vérifier 403 cross-tenant explicite
    assert "org_id mismatch" in content or "403" in content, "SG_RGPD_CONSENT_03 : check 403 cross-tenant manquant."


def test_sg_rgpd_consent_04_cascade_trigger_preserved():
    """SG_RGPD_CONSENT_04 : Cascade trigger Phase 5.8 G1 préservé (cascade_recompute_on_change)."""
    content = _ROUTE_PATH.read_text(encoding="utf-8")

    cardinal_patterns = [
        "from regops.services.cascade_recompute_service import cascade_recompute_on_change",
        "cascade_recompute_on_change(",
        "field_modified=",
    ]
    missing = [p for p in cardinal_patterns if p not in content]
    assert not missing, (
        f"SG_RGPD_CONSENT_04 BLOQUANT : cascade trigger manquant : {missing}.\n"
        "Phase 5.8 G1 wiring cascade Org doit être préservé Phase 7.3 (cohérence cascade vivante)."
    )
