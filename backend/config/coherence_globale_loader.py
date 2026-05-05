"""
PROMEOS — Coherence Globale Loader (Sprint C-4 Phase 4.1)

Loader pour le SoT des invariants cross-pillar PROMEOS — `coherence_globale.yaml`.

Pattern reproduit identique à `regulatory_sources_loader.py` (Sprint C-3 Phase 3.2) :
- `@lru_cache(maxsize=1)` sur `load_coherence_globale()` — 1 lecture YAML par process
- `reload_coherence_globale()` pour invalider le cache (tests, hot-patch)
- Helpers : `get_invariant`, `get_invariants_by_pillar`, `list_invariant_ids`

Doctrine SoT :
- YAML statique git versionné = registre invariants cross-pillar consultable
- Détections runtime branchées Phase 4.5+ (services.* références dans le YAML)
- Phase 3.8 reportée Sprint C-3 LIVRÉE Sprint C-4 Phase 4.1.

Schéma strict par invariant :
    {
        "description": str,                  # multiligne, contexte métier
        "pillars": list[str],                # allowlist (cf. pillars_allowlist YAML)
        "formula": str,                      # formule lisible (pseudocode)
        "detection": str,                    # service:method référence (Phase 4.5+)
        "severity": str,                     # allowlist (P0, P1, P2, P0_dt_applicable_else_P1)
        "action_on_violation": str,          # action attendue
        "notes": str|None                    # commentaire libre ou null
    }
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


_YAML_PATH = Path(__file__).resolve().parent / "coherence_globale.yaml"


# ─── Loaders ─────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def load_coherence_globale() -> dict:
    """Charge le YAML une fois par process. Cache invalidable via reload_*.

    Raises:
        FileNotFoundError: si `coherence_globale.yaml` introuvable.
        yaml.YAMLError: si YAML mal formé.
    """
    if not _YAML_PATH.exists():
        raise FileNotFoundError(f"coherence_globale.yaml introuvable: {_YAML_PATH}")
    return yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))


def reload_coherence_globale() -> dict:
    """Pour tests / hot-patch : invalide le cache et recharge."""
    load_coherence_globale.cache_clear()
    return load_coherence_globale()


# ─── API publique : lookup invariants ────────────────────────────────────────


def get_invariant(invariant_id: str) -> dict:
    """Récupère un invariant par ID.

    Returns:
        dict avec keys : description, pillars, formula, detection, severity,
        action_on_violation, notes.

    Raises:
        KeyError: si invariant_id absent du YAML.
    """
    data = load_coherence_globale()
    invariants = data.get("invariants", {})
    if invariant_id not in invariants:
        raise KeyError(f"Invariant cross-pillar inconnu: {invariant_id}")
    return invariants[invariant_id]


def get_invariants_by_pillar(pillar: str) -> dict:
    """Récupère tous les invariants concernant un pillar donné.

    Args:
        pillar: nom du pillar (cf. `pillars_allowlist` YAML, ex "patrimoine",
                "rgpd", "frontend_tracabilite").

    Returns:
        dict {invariant_id: invariant} filtré sur les invariants dont
        `pillars` contient le pillar demandé.
    """
    data = load_coherence_globale()
    invariants = data.get("invariants", {})
    return {iid: inv for iid, inv in invariants.items() if pillar in inv.get("pillars", [])}


def list_invariant_ids() -> list[str]:
    """Liste tous les invariant_id disponibles (utile diagnostic / tests)."""
    data = load_coherence_globale()
    return sorted(data.get("invariants", {}).keys())


def list_pillars() -> list[str]:
    """Liste tous les pillars distincts présents dans les invariants."""
    data = load_coherence_globale()
    pillars: set[str] = set()
    for inv in data.get("invariants", {}).values():
        pillars.update(inv.get("pillars", []))
    return sorted(pillars)


def get_invariant_severity(invariant_id: str) -> str:
    """Récupère uniquement la sévérité d'un invariant."""
    return get_invariant(invariant_id)["severity"]


# ─── API publique : allowlists ────────────────────────────────────────────────


def get_severity_allowlist() -> list[str]:
    """Liste des sévérités autorisées (cohérence vs source-guards Phase 4.1.4)."""
    data = load_coherence_globale()
    return list(data.get("severity_allowlist", []))


def get_pillars_allowlist() -> list[str]:
    """Liste des pillars autorisés (cohérence vs source-guards Phase 4.1.4)."""
    data = load_coherence_globale()
    return list(data.get("pillars_allowlist", []))


# ─── Helpers diagnostic ───────────────────────────────────────────────────────


def get_invariants_count() -> int:
    """Nombre total d'invariants v1.0 (cible source-guard SG_COHERENCE_04 ≥ 5)."""
    data = load_coherence_globale()
    return len(data.get("invariants", {}))


def get_metadata() -> dict[str, Any]:
    """Métadonnées YAML : version, last_updated, sprint_origin."""
    data = load_coherence_globale()
    return {
        "version": data.get("version"),
        "last_updated": data.get("last_updated"),
        "sprint_origin": data.get("sprint_origin"),
    }
