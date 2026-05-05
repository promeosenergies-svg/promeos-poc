"""
PROMEOS — Source guards coherence_globale.yaml structure (Sprint C-4 Phase 4.1).

Anti-régression structurelle du registre invariants cross-pillar v1.0.

4 source-guards :

- SG_COHERENCE_01 : tous invariants ont les keys obligatoires
  (description, pillars, formula, detection, severity, action_on_violation)
- SG_COHERENCE_02 : severity ∈ allowlist (P0, P1, P2, P0_dt_applicable_else_P1)
- SG_COHERENCE_03 : pillars non vide list + chaque pillar ∈ pillars_allowlist
- SG_COHERENCE_04 : ≥ 5 invariants minimum (cible cardinale v1.0)
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.coherence_globale_loader import (
    get_invariants_count,
    get_pillars_allowlist,
    get_severity_allowlist,
    list_invariant_ids,
    load_coherence_globale,
)


_REQUIRED_KEYS = {"description", "pillars", "formula", "detection", "severity", "action_on_violation"}
_MIN_INVARIANTS_V1 = 5


def test_sg_coherence_01_all_invariants_have_required_keys():
    """SG_COHERENCE_01 : chaque invariant a TOUTES les keys obligatoires."""
    data = load_coherence_globale()
    invariants = data.get("invariants", {})

    offenders: list[str] = []
    for iid, inv in invariants.items():
        missing = _REQUIRED_KEYS - set(inv.keys())
        if missing:
            offenders.append(f"{iid}: missing {sorted(missing)}")

    assert not offenders, (
        "Invariants avec clés obligatoires manquantes :\n  - "
        + "\n  - ".join(offenders)
        + f"\nClés obligatoires : {sorted(_REQUIRED_KEYS)}"
    )


def test_sg_coherence_02_severity_in_allowlist():
    """SG_COHERENCE_02 : sévérité de chaque invariant ∈ severity_allowlist YAML."""
    data = load_coherence_globale()
    invariants = data.get("invariants", {})
    allowed = set(get_severity_allowlist())

    offenders: list[str] = []
    for iid, inv in invariants.items():
        sev = inv.get("severity")
        if sev not in allowed:
            offenders.append(f"{iid}: severity={sev!r}")

    assert not offenders, f"Sévérités hors allowlist {sorted(allowed)} :\n  - " + "\n  - ".join(offenders)


def test_sg_coherence_03_pillars_non_empty_and_in_allowlist():
    """SG_COHERENCE_03 : pillars = liste non vide + chaque pillar ∈ pillars_allowlist."""
    data = load_coherence_globale()
    invariants = data.get("invariants", {})
    allowed = set(get_pillars_allowlist())

    offenders: list[str] = []
    for iid, inv in invariants.items():
        pillars = inv.get("pillars")
        if not isinstance(pillars, list) or not pillars:
            offenders.append(f"{iid}: pillars vide ou non-list ({pillars!r})")
            continue
        invalid = [p for p in pillars if p not in allowed]
        if invalid:
            offenders.append(f"{iid}: pillars hors allowlist {invalid}")

    assert not offenders, f"Invariants avec pillars invalides (allowlist {sorted(allowed)}) :\n  - " + "\n  - ".join(
        offenders
    )


def test_sg_coherence_04_at_least_5_invariants():
    """SG_COHERENCE_04 : v1.0 livre ≥ 5 invariants cardinaux (cible Phase 4.1)."""
    count = get_invariants_count()
    assert count >= _MIN_INVARIANTS_V1, (
        f"v1.0 doit avoir ≥ {_MIN_INVARIANTS_V1} invariants cardinaux, got {count}.\n"
        f"Invariants présents : {list_invariant_ids()}"
    )
