"""PROMEOS — Mitigation Defaults Loader (Sprint 2 Vague C ét12e).

Charge `mitigation_defaults.yaml` versionné via `@lru_cache` (cohérent
pattern `tarif_loader.py`). Expose des helpers typés consommés par les
détecteurs `event_bus` pour produire `EventMitigation` (doctrine §10).

Audit Architecture P0 #2 + CFO indirect : externalise les constantes
hardcoded (`_DT_AUDIT_PROXY_CAPEX_EUR=8000`, `_DT_AUDIT_PAYBACK_MONTHS_PROXY=9`,
`_DT_NPV_HORIZON_YEAR=2030`, taux d'actualisation NPV) vers un fichier
versionné — règle d'or chiffres « SoT canonique, pas magic constant ».

Convention :
  - 1 helper typé par section YAML (`get_dt_compliance_defaults`,
    `get_consumption_drift_defaults`, `get_discount_rate`)
  - chaque helper retourne un dataclass frozen avec source citée
  - tests : `test_mitigation_loader.py` valide chargement + valeurs
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

_YAML_PATH = Path(__file__).resolve().parent / "mitigation_defaults.yaml"


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    """Lit + parse le YAML une seule fois (process lifetime)."""
    return yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))


def reload() -> dict:
    """Force le rechargement (tests, hot-patch)."""
    _load_raw.cache_clear()
    return _load_raw()


# ── DTOs typés (frozen pour cohérence event_bus.types) ───────────────


@dataclass(frozen=True)
class DtComplianceDefaults:
    """Defaults Décret Tertiaire (compliance_deadline_detector)."""

    capex_per_site_eur: float
    capex_source: str
    payback_months: int
    payback_source: str
    npv_horizon_year: int
    npv_horizon_source: str


@dataclass(frozen=True)
class ConsumptionDriftDefaults:
    """Defaults consumption_drift_detector (action comportementale)."""

    capex_eur: Optional[float]
    payback_months: int
    payback_source: str


# ── API publique ─────────────────────────────────────────────────────


def get_discount_rate() -> float:
    """Taux d'actualisation NPV — règle CFO 27/04 « pas de NPV nominal »."""
    return float(_load_raw()["discount_rate"])


def get_dt_compliance_defaults() -> DtComplianceDefaults:
    """Charge les defaults DT compliance pour `compliance_deadline_detector`."""
    raw = _load_raw()["dt_compliance"]
    return DtComplianceDefaults(
        capex_per_site_eur=float(raw["capex_per_site_eur"]),
        capex_source=str(raw["capex_source"]),
        payback_months=int(raw["payback_months"]),
        payback_source=str(raw["payback_source"]),
        npv_horizon_year=int(raw["npv_horizon_year"]),
        npv_horizon_source=str(raw["npv_horizon_source"]),
    )


def get_consumption_drift_defaults() -> ConsumptionDriftDefaults:
    """Charge les defaults consumption_drift_detector."""
    raw = _load_raw()["consumption_drift"]
    return ConsumptionDriftDefaults(
        capex_eur=raw["capex_eur"],  # peut être None (action comportementale)
        payback_months=int(raw["payback_months"]),
        payback_source=str(raw["payback_source"]),
    )


def compute_npv_actualized(
    annual_flow_eur: float,
    horizon_year: int,
    capex_eur: float,
    *,
    discount_rate: Optional[float] = None,
    current_year: Optional[int] = None,
) -> float:
    """NPV actualisé : Σ (annual_flow / (1+r)^t) - capex (audit CFO P0 #1).

    Avant ét12e : NPV = annual_flow × années_horizon - capex (VAN nominale,
    surévalue de ~35-40% sur 5 ans). Le CFO se faisait corriger en CODIR.

    Args:
        annual_flow_eur: flux annuel récurrent évité (ex: pénalité DT).
        horizon_year: année cible (ex: 2030 pour DT).
        capex_eur: investissement initial (ex: audit + quick-wins).
        discount_rate: taux d'actualisation (défaut: lit YAML 0.04).
        current_year: année de référence (défaut: année courante UTC).

    Returns:
        NPV actualisée en euros (peut être négative si CAPEX > flux actualisés).
    """
    from datetime import datetime, timezone

    if discount_rate is None:
        discount_rate = get_discount_rate()
    if current_year is None:
        current_year = datetime.now(timezone.utc).year

    years_to_horizon = max(0, horizon_year - current_year)
    if years_to_horizon == 0:
        # Pas d'horizon → pas de flux actualisé, NPV = -CAPEX
        return -capex_eur

    # Σ_{t=1}^{N} flux / (1+r)^t = flux × (1 - (1+r)^-N) / r (annuité)
    if discount_rate == 0:
        # Cas dégénéré : pas d'actualisation, somme naïve
        actualized_flows = annual_flow_eur * years_to_horizon
    else:
        annuity_factor = (1 - (1 + discount_rate) ** -years_to_horizon) / discount_rate
        actualized_flows = annual_flow_eur * annuity_factor

    return float(actualized_flows - capex_eur)


__all__ = [
    "ConsumptionDriftDefaults",
    "DtComplianceDefaults",
    "compute_npv_actualized",
    "get_consumption_drift_defaults",
    "get_discount_rate",
    "get_dt_compliance_defaults",
    "reload",
]
