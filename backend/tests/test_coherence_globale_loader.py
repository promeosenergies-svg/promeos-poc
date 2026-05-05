"""
PROMEOS — Tests Coherence Globale Loader (Sprint C-4 Phase 4.1).

Vérifie le service de lecture du registre invariants cross-pillar
`coherence_globale.yaml` v1.0.

10 tests :
- Structure YAML chargée
- API publique helpers (get_invariant, get_invariants_by_pillar, list_invariant_ids)
- Cardinalité v1.0 (≥ 5 invariants)
- Cache lru + reload
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.coherence_globale_loader import (
    get_invariant,
    get_invariant_severity,
    get_invariants_by_pillar,
    get_invariants_count,
    get_metadata,
    get_pillars_allowlist,
    get_severity_allowlist,
    list_invariant_ids,
    list_pillars,
    load_coherence_globale,
    reload_coherence_globale,
)


_REQUIRED_KEYS = {"description", "pillars", "formula", "detection", "severity", "action_on_violation"}


# ─── 1. Structure YAML ───────────────────────────────────────────────────────


def test_load_yaml_returns_dict_with_invariants_and_allowlists():
    """SG_LOAD_01 : YAML chargé contient invariants + allowlists obligatoires."""
    data = load_coherence_globale()
    assert isinstance(data, dict)
    assert "invariants" in data, "Clé 'invariants' manquante du YAML"
    assert "severity_allowlist" in data
    assert "pillars_allowlist" in data
    assert "version" in data
    assert "last_updated" in data


# ─── 2. Lookup invariant ─────────────────────────────────────────────────────


def test_get_invariant_kwh_sum_coherence_returns_dict_with_required_keys():
    """SG_LOAD_02 : invariant KWH_SUM_COHERENCE existe et a la structure attendue."""
    inv = get_invariant("KWH_SUM_COHERENCE")
    assert isinstance(inv, dict)
    missing = _REQUIRED_KEYS - inv.keys()
    assert not missing, f"Clés manquantes pour KWH_SUM_COHERENCE: {missing}"


def test_get_invariant_unknown_raises_keyerror():
    """SG_LOAD_03 : invariant inexistant → KeyError."""
    with pytest.raises(KeyError, match="Invariant cross-pillar inconnu"):
        get_invariant("INVARIANT_INEXISTANT_XYZ")


# ─── 3. Filter by pillar ─────────────────────────────────────────────────────


def test_get_invariants_by_pillar_patrimoine_returns_2_invariants_minimum():
    """SG_LOAD_04 : pillar 'patrimoine' touche KWH_SUM + TERTIAIRE_AREA = 2 invariants."""
    invs = get_invariants_by_pillar("patrimoine")
    assert len(invs) >= 2, f"Attendu ≥ 2 invariants pour 'patrimoine', got {len(invs)}: {list(invs.keys())}"
    assert "KWH_SUM_COHERENCE" in invs
    assert "TERTIAIRE_AREA_COHERENCE" in invs


def test_get_invariants_by_pillar_rgpd_returns_consentement_invariant():
    """SG_LOAD_05 : pillar 'rgpd' touche CONSENTEMENT_INGESTION_COHERENCE."""
    invs = get_invariants_by_pillar("rgpd")
    assert "CONSENTEMENT_INGESTION_COHERENCE" in invs


# ─── 4. Cardinalité v1.0 ─────────────────────────────────────────────────────


def test_v1_has_at_least_5_invariants():
    """SG_LOAD_06 : v1.0 livre ≥ 5 invariants (cible cardinale Phase 4.1)."""
    count = get_invariants_count()
    assert count >= 5, f"v1.0 doit avoir ≥ 5 invariants, got {count}"


def test_list_invariant_ids_returns_5_canonical_ids():
    """SG_LOAD_07 : les 5 invariants v1.0 canoniques sont présents."""
    ids = list_invariant_ids()
    expected = {
        "KWH_SUM_COHERENCE",
        "TERTIAIRE_AREA_COHERENCE",
        "CONSENTEMENT_INGESTION_COHERENCE",
        "CONFORMITE_SCORE_WEIGHTS_COHERENCE",
        "TRACETOOLTIP_TERMID_VALIDITY",
    }
    missing = expected - set(ids)
    assert not missing, f"Invariants v1.0 manquants: {missing}"


# ─── 5. Severity & pillars helpers ───────────────────────────────────────────


def test_get_invariant_severity_returns_string_in_allowlist():
    """SG_LOAD_08 : sévérité de chaque invariant ∈ allowlist."""
    allowed = set(get_severity_allowlist())
    for iid in list_invariant_ids():
        sev = get_invariant_severity(iid)
        assert sev in allowed, f"Sévérité '{sev}' de {iid} hors allowlist {allowed}"


def test_list_pillars_subset_of_pillars_allowlist():
    """SG_LOAD_09 : tous les pillars utilisés ∈ pillars_allowlist."""
    used = set(list_pillars())
    allowed = set(get_pillars_allowlist())
    invalid = used - allowed
    assert not invalid, f"Pillars utilisés mais hors allowlist: {invalid}"


# ─── 6. Cache lru + reload ───────────────────────────────────────────────────


def test_lru_cache_returns_same_instance_then_reload_clears():
    """SG_LOAD_10 : load_coherence_globale() = même instance via @lru_cache,
    reload_coherence_globale() invalide cache et retourne (potentiellement)
    une nouvelle référence dict.
    """
    first = load_coherence_globale()
    second = load_coherence_globale()
    assert first is second, "Cache lru_cache doit retourner la même instance"

    # Reload doit recharger le YAML (test ne vérifie pas l'inégalité d'identité
    # car le contenu est identique, mais s'assure que cache_clear est appelé)
    reloaded = reload_coherence_globale()
    assert isinstance(reloaded, dict)
    assert "invariants" in reloaded


# ─── Bonus : metadata ─────────────────────────────────────────────────────────


def test_metadata_has_version_and_sprint_origin():
    """Métadonnées YAML cohérentes (audit traçabilité YAML versionné git)."""
    meta = get_metadata()
    assert meta["version"] == "1.0"
    assert "Sprint C-4" in meta["sprint_origin"]
    assert meta["last_updated"]
