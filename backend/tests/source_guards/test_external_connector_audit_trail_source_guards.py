"""
PROMEOS — Source guards Phase 7.5 — External Connectors audit trail (CNIL/ADR-018).

Anti-régression cardinal post-Phase 7.5 — clôture dernier P0 résiduel Sprint C-7
(D-Sprint-C7-External-Connectors-Audit-Trail-001) :

- SG_EXT_AUDIT_01 : Décorateur `audit_external_api_call` présent dans audit_log_service.py
- SG_EXT_AUDIT_02 : 4 connecteurs cardinaux décorés (DataConnect _api_get + exchange_code,
                    GRDF _api_get, Sirene hydrate)
- SG_EXT_AUDIT_03 : Sentinelles sanitisation présentes (Authorization/Bearer/client_secret/token)
- SG_EXT_AUDIT_04 : Action="connector.api_call" + resource_type=provider (convention dot-snake)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_AUDIT_SERVICE_PATH = _BACKEND_ROOT / "services" / "audit_log_service.py"
_DATACONNECT_PATH = _BACKEND_ROOT / "connectors" / "enedis_dataconnect.py"
_GRDF_PATH = _BACKEND_ROOT / "connectors" / "grdf_adict.py"
_SIRENE_HYDRATE_PATH = _BACKEND_ROOT / "services" / "sirene_hydrate.py"


def test_sg_ext_audit_01_decorator_present():
    """SG_EXT_AUDIT_01 cardinal : décorateur `audit_external_api_call` présent."""
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    cardinal_markers = [
        "def audit_external_api_call(",
        "def _record_external_api_event(",
        "def _sanitize_kwargs(",
        '"connector.api_call"',
    ]
    missing = [m for m in cardinal_markers if m not in content]
    assert not missing, (
        f"SG_EXT_AUDIT_01 BLOQUANT : marqueurs manquants dans audit_log_service.py : {missing}.\n"
        "Phase 7.5 cardinal : sans le décorateur, ADR-018 (CNIL preuve d'extraction) impossible.\n"
        "Clôt dernier P0 résiduel Sprint C-7 — D-Sprint-C7-External-Connectors-Audit-Trail-001."
    )


def test_sg_ext_audit_02_connectors_wired():
    """SG_EXT_AUDIT_02 cardinal : 4 connecteurs cardinaux décorés.

    Anti-régression : empêche suppression silencieuse du wiring → CNIL preuve d'extraction cassée.
    """
    files_with_required_decoration = {
        _DATACONNECT_PATH: 2,  # _api_get + exchange_code
        _GRDF_PATH: 1,  # _api_get
        _SIRENE_HYDRATE_PATH: 1,  # hydrate_siren_from_api
    }

    for path, min_count in files_with_required_decoration.items():
        content = path.read_text(encoding="utf-8")
        # Import présent
        assert "from services.audit_log_service import audit_external_api_call" in content, (
            f"SG_EXT_AUDIT_02 : import audit_external_api_call manquant dans {path.name}"
        )
        # Décorateur appliqué au moins N fois
        decorator_count = content.count("@audit_external_api_call(")
        assert decorator_count >= min_count, (
            f"SG_EXT_AUDIT_02 BLOQUANT : décorateur appliqué {decorator_count}/{min_count}+ "
            f"fois dans {path.name}.\n"
            "Phase 7.5 wiring 4 connecteurs cardinaux : DataConnect (_api_get+exchange_code), "
            "GRDF (_api_get), Sirene (hydrate_siren_from_api)."
        )


def test_sg_ext_audit_03_sanitization_keys_present():
    """SG_EXT_AUDIT_03 sécu : sentinelles redaction présentes (anti-régression leak secrets)."""
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    required_redact_patterns = [
        "authorization",
        "bearer",
        "client_secret",
        "api_key",
        "token",
        "code_verifier",
    ]
    missing = [p for p in required_redact_patterns if p not in content.lower()]
    assert not missing, (
        f"SG_EXT_AUDIT_03 BLOQUANT : sentinelles redaction manquantes : {missing}.\n"
        "Sans sanitisation, secrets fuites dans detail_json AuditLog → RGPD/CNIL violation."
    )

    required_hash_patterns = ["prm", "pce", "siren", "siret"]
    missing_hash = [p for p in required_hash_patterns if p not in content.lower()]
    assert not missing_hash, (
        f"SG_EXT_AUDIT_03 : identifiants à hasher manquants : {missing_hash}.\n"
        "PRM/PCE/SIREN doivent être hashés sha256[:16] (preuve présence sans exposition)."
    )

    assert "<redacted>" in content, "SG_EXT_AUDIT_03 : marqueur '<redacted>' absent"
    assert "sha256" in content, "SG_EXT_AUDIT_03 : hashing sha256 absent"


def test_sg_ext_audit_04_action_naming_convention():
    """SG_EXT_AUDIT_04 : action='connector.api_call' suit convention dot-snake AuditLog."""
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    assert '"connector.api_call"' in content, (
        "SG_EXT_AUDIT_04 : action='connector.api_call' manquant.\n"
        "Convention dot-snake cohérente Phase 7.4 'rgpd.consent_change' / "
        "'cascade.recompute' / 'patrimoine.update'."
    )

    # Anti-pattern : SHOUTING_CASE incohérent
    assert "CONNECTOR_API_CALL" not in content, (
        "SG_EXT_AUDIT_04 : SHOUTING_CASE 'CONNECTOR_API_CALL' détecté — convention PROMEOS = dot-snake."
    )
