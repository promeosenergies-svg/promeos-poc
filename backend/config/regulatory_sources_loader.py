"""
PROMEOS — Regulatory Sources Loader (Sprint C-3 Phase 3.2)

Loader pour le SoT des sources réglementaires PROMEOS — `sources_reglementaires.yaml`.

Pattern reproduit identique à `tarif_loader.py` (Phase 22, Step 18) :
- `@lru_cache(maxsize=1)` sur `load_regulatory_sources()` — 1 lecture YAML par process
- `reload_regulatory_sources()` pour invalider le cache (tests, hot-patch)
- Helpers typés par domaine : `get_co2_factor`, `get_compliance_penalty`, etc.

Doctrine SoT :
- YAML statique git versionné = audit trail légal naturel
- Mirroir backend/doctrine/constants.py + config/emission_factors.py + config/tarifs_reglementaires.yaml
- Endpoint API associé : GET /api/regulatory/rates (Sprint C-3 Phase 3.3)

Schema strict par term :
    {
        "value": Any,                   # number | string (dates, doctrines)
        "unit": str,                    # ex "kgCO2e/kWh", "EUR/MWh", "%", "m²"
        "domain": str,                  # allowlist : co2, tarifs, accises, tva, dt, bacs, aper, audit_sme, operat
        "source": {
            "label": str,               # libellé humain
            "url": str,                 # URL Légifrance / CRE / ADEME / data.gouv (https://)
            "version": str,             # ex "V23.6", "TURPE 7", "LFI 2026"
            "effective_date": str,      # YYYY-MM-DD
            "legal_reference": str|None  # ex "JORFTEXT000053407616" ou null
        },
        "formula": str|None,            # formule lisible ou null
        "notes": str|None               # commentaire libre ou null
    }
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml


_YAML_PATH = Path(__file__).resolve().parent / "sources_reglementaires.yaml"


# ─── Loaders ─────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def load_regulatory_sources() -> dict:
    """Charge le YAML une fois par process. Cache invalidable via reload_*.

    Raises:
        FileNotFoundError: si `sources_reglementaires.yaml` introuvable.
        yaml.YAMLError: si YAML mal formé.
    """
    if not _YAML_PATH.exists():
        raise FileNotFoundError(f"sources_reglementaires.yaml introuvable: {_YAML_PATH}")
    return yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))


def reload_regulatory_sources() -> dict:
    """Pour tests / hot-patch : invalide le cache et recharge."""
    load_regulatory_sources.cache_clear()
    return load_regulatory_sources()


# ─── API publique : lookup générique ─────────────────────────────────────────


def get_term(term_id: str) -> dict:
    """Récupère un terme par ID.

    Returns:
        dict avec keys : value, unit, domain, source, formula, notes.

    Raises:
        KeyError: si term_id absent du YAML.
    """
    data = load_regulatory_sources()
    terms = data.get("terms", {})
    if term_id not in terms:
        raise KeyError(f"Terme réglementaire inconnu: {term_id}")
    return terms[term_id]


def get_term_value(term_id: str) -> Any:
    """Récupère uniquement la valeur d'un terme (sans la métadonnée source)."""
    return get_term(term_id)["value"]


def get_terms_by_domain(domain: str) -> dict:
    """Récupère tous les termes d'un domaine donné (filtre sur `term.domain`)."""
    data = load_regulatory_sources()
    return {tid: t for tid, t in data.get("terms", {}).items() if t.get("domain") == domain}


def list_all_term_ids() -> list[str]:
    """Liste tous les term_id disponibles (utile diagnostic / tests)."""
    data = load_regulatory_sources()
    return sorted(data.get("terms", {}).keys())


def list_all_domains() -> list[str]:
    """Liste tous les domaines distincts présents dans le YAML."""
    data = load_regulatory_sources()
    return sorted(set(t["domain"] for t in data.get("terms", {}).values()))


# ─── Helpers typés par domaine ───────────────────────────────────────────────


def get_co2_factor(fuel: str) -> float:
    """Récupère un facteur CO2 (kgCO2e/kWh).

    Args:
        fuel: "elec" | "gaz" | "gnl"

    Raises:
        ValueError: si fuel inconnu.
    """
    mapping = {
        "elec": "CO2_FACTOR_ELEC_KGCO2_PER_KWH",
        "gaz": "CO2_FACTOR_GAZ_NATUREL_KGCO2_PER_KWH",
        "gnl": "CO2_FACTOR_GNL_KGCO2_PER_KWH",
    }
    if fuel not in mapping:
        raise ValueError(f"Fuel inconnu: {fuel!r}. Attendu: {sorted(mapping.keys())}")
    return get_term_value(mapping[fuel])


def get_compliance_penalty(reglementation: str) -> float:
    """Récupère une pénalité compliance (EUR/an/site).

    Args:
        reglementation: "dt" | "dt_at_risk" | "bacs" | "aper" | "audit_sme" | "operat"

    Raises:
        ValueError: si reglementation inconnue.
    """
    mapping = {
        "dt": "COMPLIANCE_DT_PENALTY_EUR",
        "dt_at_risk": "COMPLIANCE_DT_PENALTY_AT_RISK_EUR",
        "bacs": "COMPLIANCE_BACS_PENALTY_EUR",
        "aper": "APER_PENALTY_EUR_PER_M2_PER_YEAR",
        "audit_sme": "COMPLIANCE_AUDIT_SME_PENALTY_EUR",
        "operat": "COMPLIANCE_OPERAT_PENALTY_EUR",
    }
    if reglementation not in mapping:
        raise ValueError(f"Réglementation inconnue: {reglementation!r}. Attendu: {sorted(mapping.keys())}")
    return get_term_value(mapping[reglementation])


def get_accise_rate(energy_type: str) -> float:
    """Récupère une accise (EUR/MWh).

    Args:
        energy_type: "elec" (T2 PME C4 par défaut) | "elec_t1" | "elec_c5" | "gaz"
    """
    mapping = {
        "elec": "ACCISE_ELEC_T2_EUR_PER_MWH",
        "elec_t1": "ACCISE_ELEC_T1_EUR_PER_MWH",
        "elec_c5": "ACCISE_ELEC_T2_C5_MENAGE_EUR_PER_MWH",
        "gaz": "ACCISE_GAZ_EUR_PER_MWH",
    }
    if energy_type not in mapping:
        raise ValueError(f"Energy type inconnu: {energy_type!r}. Attendu: {sorted(mapping.keys())}")
    return get_term_value(mapping[energy_type])


def get_dt_milestone(year: int) -> float:
    """Récupère l'objectif DT pour une année jalon (-40% / -50% / -60%).

    Args:
        year: 2030 | 2040 | 2050

    Returns:
        Pourcentage négatif (ex: -40.0 pour 2030).
    """
    mapping = {
        2030: "DT_MILESTONE_2030_PCT",
        2040: "DT_MILESTONE_2040_PCT",
        2050: "DT_MILESTONE_2050_PCT",
    }
    if year not in mapping:
        raise ValueError(f"Année jalon DT inconnue: {year}. Attendu: {sorted(mapping.keys())}")
    return get_term_value(mapping[year])


def get_audit_sme_threshold(periodicity: str) -> float:
    """Récupère un seuil audit SMÉ (GWh/an).

    Args:
        periodicity: "audit_4ans" (2.75 GWh) | "iso50001" (23.6 GWh)
    """
    mapping = {
        "audit_4ans": "AUDIT_SME_THRESHOLD_GWH_PERIODIC",
        "iso50001": "AUDIT_SME_THRESHOLD_GWH_ISO50001",
    }
    if periodicity not in mapping:
        raise ValueError(f"Periodicity inconnue: {periodicity!r}. Attendu: {sorted(mapping.keys())}")
    return get_term_value(mapping[periodicity])
