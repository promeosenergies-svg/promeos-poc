"""
PROMEOS — P0-B 2026-05-23 : enrichissement DATA_MISSING avec champs de remédiation.

Vérifie que chaque `RuleApplicability.to_dict()` avec status=DATA_MISSING expose :
- remediation_field, remediation_level, remediation_label_fr,
  remediation_hint_fr, cta_label_fr, affected_site_ids.

Et que les autres statuts (APPLICABLE / NOT_APPLICABLE / UNKNOWN) ne contiennent
PAS ces champs (zéro pollution).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regulatory.applicability_types import (  # noqa: E402
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from regulatory.reason_codes import REASON_CODES  # noqa: E402
from regulatory.remediation import REASON_CODE_TO_REMEDIATION, get_remediation  # noqa: E402


_REMEDIATION_KEYS = {
    "remediation_field",
    "remediation_level",
    "remediation_label_fr",
    "remediation_hint_fr",
    "cta_label_fr",
    "affected_site_ids",
}


def _audit() -> dict:
    return {
        "doctrine_version": "ADR-024-v1.0",
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "evaluator": "test",
        "evaluator_version": "test-1.0",
        "data_source": "test",
    }


def _data_missing_codes() -> list[str]:
    return [c for c in REASON_CODES if ".DATA_MISSING." in c]


def test_every_data_missing_code_has_a_remediation_entry():
    """Chaque code DATA_MISSING listé dans reason_codes.py doit avoir une remediation."""
    missing = [c for c in _data_missing_codes() if c not in REASON_CODE_TO_REMEDIATION]
    assert not missing, (
        "Codes DATA_MISSING sans entrée remediation :\n"
        + "\n".join(f"  - {c}" for c in missing)
    )


@pytest.mark.parametrize("code", sorted(REASON_CODE_TO_REMEDIATION))
def test_remediation_entry_has_required_fr_fields(code):
    """Toute entrée remediation doit avoir les 5 champs FR + niveau valide."""
    r = REASON_CODE_TO_REMEDIATION[code]
    for key in ("remediation_field", "remediation_level", "remediation_label_fr",
                "remediation_hint_fr", "cta_label_fr"):
        assert r.get(key), f"{code}.{key} manquant ou vide"
    # Niveau valide
    assert r["remediation_level"] in {"site", "batiment", "organisation", "entite_juridique"}
    # remediation_field est en notation pointée model.field
    assert "." in r["remediation_field"], (
        f"{code}.remediation_field={r['remediation_field']!r} doit être 'model.field'"
    )


@pytest.mark.parametrize("code", sorted(_data_missing_codes()))
def test_to_dict_enriches_data_missing_with_remediation(code):
    """`to_dict()` doit inclure les champs remediation pour un DATA_MISSING."""
    ra = RuleApplicability(
        rule_code=RuleCode.DT,  # arbitraire — le test porte sur le mapping
        rule_version="test-1.0",
        scope_level="site",
        scope_id=42,
        scope_label="Site Test",
        status=ApplicabilityStatus.DATA_MISSING,
        reason_code=code,
        reason_human="test",
        missing_inputs=["some.field"],
        _audit=_audit(),
    )
    payload = ra.to_dict()
    expected = get_remediation(code)
    assert expected is not None
    for k in ("remediation_field", "remediation_level", "remediation_label_fr",
              "remediation_hint_fr", "cta_label_fr"):
        assert payload[k] == expected[k]
    assert payload["affected_site_ids"] == [42]


def test_to_dict_does_not_pollute_applicable_status():
    """Status=APPLICABLE → AUCUN champ remediation_* dans le payload."""
    ra = RuleApplicability(
        rule_code=RuleCode.DT,
        rule_version="test-1.0",
        scope_level="site",
        scope_id=1,
        scope_label="Site OK",
        status=ApplicabilityStatus.APPLICABLE,
        reason_code="DT.APPLICABLE",
        reason_human="Site soumis au DT",
        _audit=_audit(),
    )
    payload = ra.to_dict()
    for key in _REMEDIATION_KEYS:
        assert key not in payload, f"APPLICABLE ne doit pas exposer {key}"


def test_to_dict_does_not_pollute_not_applicable():
    """Status=NOT_APPLICABLE → AUCUN champ remediation_*."""
    ra = RuleApplicability(
        rule_code=RuleCode.DT,
        rule_version="test-1.0",
        scope_level="site",
        scope_id=1,
        scope_label="Site",
        status=ApplicabilityStatus.NOT_APPLICABLE,
        reason_code="DT.NOT_APPLICABLE.SDP_LT_1000",
        reason_human="Surface < 1000 m²",
        _audit=_audit(),
    )
    payload = ra.to_dict()
    for key in _REMEDIATION_KEYS:
        assert key not in payload


def test_affected_site_ids_empty_for_org_scoped_rule():
    """Une règle org-scopée (SME) en DATA_MISSING expose affected_site_ids=[]."""
    ra = RuleApplicability(
        rule_code=RuleCode.SME,
        rule_version="test-1.0",
        scope_level="organisation",
        scope_id=100,
        scope_label="Org HELIOS",
        status=ApplicabilityStatus.DATA_MISSING,
        reason_code="SME.DATA_MISSING.EFFECTIF",
        reason_human="effectif manquant",
        missing_inputs=["organisation.effectif_total"],
        _audit=_audit(),
    )
    payload = ra.to_dict()
    assert payload["affected_site_ids"] == []
    assert payload["remediation_level"] == "organisation"


def test_data_missing_with_unknown_reason_code_does_not_crash():
    """Un reason_code DATA_MISSING.* non mappé ne doit pas faire crasher to_dict()."""
    # On force un code non whitelist (cas où source-guard whitelist serait court-circuitée)
    # En usage normal, reason_codes.py garde la liste sous contrôle.
    ra = RuleApplicability(
        rule_code=RuleCode.DT,
        rule_version="test-1.0",
        scope_level="site",
        scope_id=1,
        scope_label="Site X",
        status=ApplicabilityStatus.DATA_MISSING,
        reason_code="DT.DATA_MISSING.HYPOTHETICAL_FUTURE",
        reason_human="cas hypothétique",
        missing_inputs=["site.future_field"],
        _audit=_audit(),
    )
    payload = ra.to_dict()
    # Pas de remediation → pas de champs ajoutés, mais pas de crash
    for key in _REMEDIATION_KEYS:
        assert key not in payload
