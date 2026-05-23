"""
PROMEOS — Source-guard P0-B 2026-05-23 : tout `DATA_MISSING` reason_code doit
avoir une entrée dans `regulatory.remediation.REASON_CODE_TO_REMEDIATION`.

Empêche toute régression future qui ajouterait un nouveau code DATA_MISSING
dans `reason_codes.py` sans fournir d'instruction de remédiation utilisateur.
Le CadreApplicable et la page Patrimoine reposent sur ce contrat — un code
non mappé apparaîtrait comme un message sec sans CTA dans l'UI.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from regulatory.reason_codes import REASON_CODES  # noqa: E402
from regulatory.remediation import REASON_CODE_TO_REMEDIATION  # noqa: E402


def test_every_data_missing_reason_code_has_remediation():
    """Bijection : chaque DATA_MISSING listé doit avoir une remediation."""
    data_missing = sorted(c for c in REASON_CODES if ".DATA_MISSING." in c)
    missing = [c for c in data_missing if c not in REASON_CODE_TO_REMEDIATION]
    assert not missing, (
        "Codes DATA_MISSING sans entrée remediation (chaque ajout dans "
        "reason_codes.py doit s'accompagner d'une remediation FR) :\n"
        + "\n".join(f"  - {c}" for c in missing)
    )


def test_no_orphan_remediation_entry():
    """Aucune entrée remediation ne doit pointer vers un reason_code disparu de la whitelist."""
    orphan = sorted(c for c in REASON_CODE_TO_REMEDIATION if c not in REASON_CODES)
    assert not orphan, (
        "Entrées remediation orphelines (reason_code non whitelist) :\n"
        + "\n".join(f"  - {c}" for c in orphan)
    )


@pytest.mark.parametrize("code", sorted(REASON_CODE_TO_REMEDIATION))
def test_remediation_entry_structural(code):
    """Toute entrée remediation doit respecter le schéma minimal."""
    r = REASON_CODE_TO_REMEDIATION[code]
    required_fields = {
        "remediation_field",
        "remediation_level",
        "remediation_label_fr",
        "remediation_hint_fr",
        "cta_label_fr",
    }
    missing = required_fields - set(r.keys())
    assert not missing, f"{code} : clés manquantes {sorted(missing)}"
    for key in required_fields:
        value = r[key]
        assert isinstance(value, str) and value.strip(), (
            f"{code}.{key} doit être une chaîne non vide"
        )
    assert r["remediation_level"] in {"site", "batiment", "organisation", "entite_juridique"}
    assert "." in r["remediation_field"], (
        f"{code}.remediation_field={r['remediation_field']!r} doit suivre le format 'model.field'"
    )
