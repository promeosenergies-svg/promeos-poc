"""
PROMEOS — Source guard cascade consentement RGPD (Sprint C-4 Phase 4.5, ADR-007).

Anti-régression cardinal RGPD : les colonnes consentement DP local
(`consentement_dataconnect_local` / `consentement_grdf_local`) NE DOIVENT JAMAIS
être modifiées par cascade automatique (Option B archi-helios — `_local` est un
override RGPD-protégé qui ne se laisse pas écraser par la cascade Org global).

L'override local doit être modifiable UNIQUEMENT via :
- Migrations Alembic (création initiale)
- Tests (setup fixtures)
- Service dédié `consent_service.set_local_override()` (à créer Sprint C-5+)

Source-guards :

- SG_CONSENT_NO_PROP_01 : helpers cascade `_propagate_consentement_*` ne contiennent
  PAS d'écriture sur `dp.consentement_*_local` (lecture seule via consent_service)
- SG_CONSENT_NO_PROP_02 : `consent_service.get_effective_consent` est read-only
  (pas de db.commit / db.flush dans le helper)
- SG_CONSENT_NO_PROP_03 : module `consent_service.py` exporte `get_effective_consent`
  + `is_consent_active` (API publique stable Phase 4.5)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_CASCADE_PATH = _BACKEND_ROOT / "regops" / "services" / "cascade_recompute_service.py"
_CONSENT_SERVICE_PATH = _BACKEND_ROOT / "services" / "consent_service.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_function_block(src: str, fn_name: str) -> str:
    """Extrait le corps d'une fonction depuis `def <fn_name>(` jusqu'à la prochaine
    définition top-level (`def `/`class ` en début de ligne) ou EOF."""
    start = src.find(f"def {fn_name}(")
    if start == -1:
        return ""
    rest = src[start:]
    next_def = rest.find("\ndef ", 1)
    next_class = rest.find("\nclass ", 1)
    candidates = [pos for pos in (next_def, next_class) if pos != -1]
    end = min(candidates) if candidates else len(rest)
    return rest[:end]


def test_sg_consent_no_prop_01_cascade_helpers_dont_write_local_override():
    """SG_CONSENT_NO_PROP_01 : helpers `_propagate_consentement_*` NE DOIVENT PAS
    contenir d'assignation `dp.consentement_*_local =` (écraserait override RGPD).
    """
    content = _read(_CASCADE_PATH)

    for helper_name in (
        "_propagate_consentement_dataconnect",
        "_propagate_consentement_grdf",
    ):
        block = _extract_function_block(content, helper_name)
        assert block, f"Helper {helper_name} introuvable (Phase 4.5 attendu)"

        # Pattern interdit : `dp.consentement_<type>_local = ...`
        forbidden_pattern = re.compile(
            r"(?:dp|delivery_point)\.consentement_\w+_local\s*=",
        )
        offenders = forbidden_pattern.findall(block)
        assert not offenders, (
            f"Helper {helper_name} CONTIENT des écritures interdites sur "
            f"`dp.consentement_*_local` (violation ADR-007 RGPD override) :\n"
            f"  Patterns détectés : {offenders}\n"
            f"  Doctrine Phase 4.5 : Option B (effective consent runtime via consent_service), "
            f"pas d'écrasement physique."
        )


def test_sg_consent_no_prop_02_consent_service_is_readonly():
    """SG_CONSENT_NO_PROP_02 : `consent_service.py` est read-only — pas de db.commit/flush
    ni d'assignation sur cols consentement.
    """
    content = _read(_CONSENT_SERVICE_PATH)

    forbidden_patterns = [
        (re.compile(r"\.commit\(\)"), "db.commit()"),
        (re.compile(r"\.flush\(\)"), "db.flush()"),
        (re.compile(r"consentement_\w+\s*=\s*[^=]"), "assignation consentement_*"),
    ]

    offenders: list[str] = []
    for pattern, label in forbidden_patterns:
        if pattern.search(content):
            offenders.append(label)

    assert not offenders, (
        f"`consent_service.py` doit être lecture seule (Option B Phase 4.5). Patterns interdits détectés : {offenders}"
    )


def test_sg_consent_no_prop_03_consent_service_exports_public_api():
    """SG_CONSENT_NO_PROP_03 : `consent_service.py` exporte les 2 helpers cardinaux
    (`get_effective_consent` + `is_consent_active`) — API publique Phase 4.5.
    """
    content = _read(_CONSENT_SERVICE_PATH)

    required_exports = ["get_effective_consent", "is_consent_active"]
    missing = [name for name in required_exports if f"def {name}(" not in content]
    assert not missing, (
        f"`consent_service.py` doit exporter {required_exports} (API Phase 4.5 stable). Manquants : {missing}"
    )

    # ConsentType Literal doit également être exporté pour typage correct des consumers
    assert "ConsentType" in content, (
        "`ConsentType = Literal['dataconnect', 'grdf']` doit être exporté pour cardinal de signature"
    )
