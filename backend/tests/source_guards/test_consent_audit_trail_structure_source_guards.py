"""
PROMEOS — Source guards audit trail RGPD consentement (Sprint C-5 Phase 5.3, ADR-007 ext).

Anti-régression cardinal post-implémentation ADR-007 ext (audit RGPD complet) :

- SG_CONSENT_AUDIT_01 : Org a 4 cols cardinaux audit RGPD
  (consentement_{dataconnect|grdf}_{by|cgu_version})
- SG_CONSENT_AUDIT_02 : DP a 4 cols cardinaux audit RGPD local
  (consentement_{dataconnect|grdf}_local_{by|cgu_version})
- SG_CONSENT_AUDIT_03 : FK users.id ondelete=SET NULL CARDINAL (RGPD droit oubli préservé)
- SG_CONSENT_AUDIT_04 : Helper get_effective_consent_with_audit signature stable (5 clés dict)

Si quelqu'un retire un col audit ou change ondelete sans coordonner les callsites,
ces SG flaggent à la collection pytest.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ORG_PATH = _BACKEND_ROOT / "models" / "organisation.py"
_DP_PATH = _BACKEND_ROOT / "models" / "patrimoine.py"
_CONSENT_SERVICE_PATH = _BACKEND_ROOT / "services" / "consent_service.py"


def test_sg_consent_audit_01_org_has_4_cardinal_audit_cols():
    """SG_CONSENT_AUDIT_01 : Org a 4 cols cardinaux audit RGPD étendu."""
    content = _ORG_PATH.read_text(encoding="utf-8")

    cardinal_cols = [
        "consentement_dataconnect_by",
        "consentement_dataconnect_cgu_version",
        "consentement_grdf_by",
        "consentement_grdf_cgu_version",
    ]

    missing = [c for c in cardinal_cols if c not in content]
    assert not missing, (
        f"Org cols audit RGPD manquantes : {missing}.\n"
        "Sprint C-5 Phase 5.3 (ADR-007 ext) requiert ces 4 cols pour audit trail complet "
        "(qui + quelle CGU + quand + scope). "
        "Si suppression intentionnelle, coordonner avec consent_service.get_effective_consent_with_audit."
    )


def test_sg_consent_audit_02_dp_has_4_cardinal_local_audit_cols():
    """SG_CONSENT_AUDIT_02 : DP a 4 cols cardinaux audit RGPD local override."""
    content = _DP_PATH.read_text(encoding="utf-8")

    cardinal_cols = [
        "consentement_dataconnect_local_by",
        "consentement_dataconnect_local_cgu_version",
        "consentement_grdf_local_by",
        "consentement_grdf_local_cgu_version",
    ]

    missing = [c for c in cardinal_cols if c not in content]
    assert not missing, (
        f"DP cols audit RGPD local manquantes : {missing}.\n"
        "Sprint C-5 Phase 5.3 (ADR-007 ext) requiert ces 4 cols pour override local audit complet."
    )


def test_sg_consent_audit_03_ondelete_set_null_cardinal():
    """SG_CONSENT_AUDIT_03 : FK users.id ondelete=SET NULL préservé (RGPD droit oubli).

    Cardinal : suppression user ne doit PAS casser l'historique de consentement.
    Pattern attendu : `ForeignKey("users.id", ondelete="SET NULL")` × 4 occurrences
    (2 Org + 2 DP).
    """
    org_content = _ORG_PATH.read_text(encoding="utf-8")
    dp_content = _DP_PATH.read_text(encoding="utf-8")

    pattern = 'ForeignKey("users.id", ondelete="SET NULL")'

    org_count = org_content.count(pattern)
    dp_count = dp_content.count(pattern)

    assert org_count >= 2, (
        f"Org doit avoir 2 FK users.id ondelete=SET NULL (dataconnect_by + grdf_by). "
        f"Trouvé : {org_count}. RGPD droit oubli compromis si CASCADE/RESTRICT à la place."
    )
    assert dp_count >= 2, (
        f"DP doit avoir 2 FK users.id ondelete=SET NULL (dataconnect_local_by + grdf_local_by). Trouvé : {dp_count}."
    )


def test_sg_consent_audit_04_helper_signature_stable():
    """SG_CONSENT_AUDIT_04 : helper get_effective_consent_with_audit signature stable."""
    content = _CONSENT_SERVICE_PATH.read_text(encoding="utf-8")

    assert "def get_effective_consent_with_audit(dp, type_: ConsentType) -> dict:" in content, (
        "Signature get_effective_consent_with_audit modifiée.\n"
        "Contrat sérialisation API : retour dict avec 5 clés stables "
        "(active + by_user_id + cgu_version + at + scope).\n"
        "Adaptation Phase 5.3 — audit RGPD officiel + Cockpit RGPD UI dépendent de ce contrat."
    )

    # Vérifier les 5 clés cardinales du dict de retour
    cardinal_keys = ['"active"', '"by_user_id"', '"cgu_version"', '"at"', '"scope"']
    missing_keys = [k for k in cardinal_keys if k not in content]
    assert not missing_keys, (
        f"Clés dict retour manquantes : {missing_keys}.\n"
        "Le contrat de sérialisation get_effective_consent_with_audit garantit ces 5 clés."
    )

    # Vérifier les 3 scopes possibles
    scopes = ['"local"', '"global"', '"none"']
    missing_scopes = [s for s in scopes if s not in content]
    assert not missing_scopes, (
        f"Scopes manquants : {missing_scopes}.\n"
        "Hiérarchie ADR-007 requiert 3 scopes : local (DP override) / global (Org fallback) / none."
    )
