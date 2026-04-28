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


@dataclass(frozen=True)
class MarketCapacity2026Defaults:
    """Defaults market_window_detector capacité 1/11/2026 (audit Sarah P0 #2)."""

    cost_per_mwh_eur: float
    cost_source: str
    deadline_iso: str  # YYYY-MM-DD parsée par le détecteur
    deadline_source: str
    proxy_consumption_mwh_per_site: int
    proxy_consumption_source: str


@dataclass(frozen=True)
class ContractRenewalDefaults:
    """Defaults contract_renewal_detector (audit CFO+Marie P0 #1 ét14).

    Permet de chiffrer la fourchette € de risque tacite reconduction.
    Avant ét14 : impact.value=None bloquait l'arbitrage data-room CFO.
    """

    tacite_spread_pct: float  # ex: 0.15 = +15 % vs spot
    tacite_spread_source: str
    market_price_elec_eur_per_mwh: float
    market_price_gaz_eur_per_mwh: float
    market_price_source: str
    proxy_volume_per_annex_mwh: int
    proxy_volume_source: str


@dataclass(frozen=True)
class AssetRegistryDefaults:
    """Defaults asset_registry_issue_detector (audit CFO P0 #2 ét14).

    Convertit les counts d'incohérences registre en € risque shadow billing.
    """

    blind_billing_exposure_per_dp_eur: float
    blind_billing_source: str
    orphan_contract_exposure_eur: float
    orphan_contract_source: str


@dataclass(frozen=True)
class BillingAnomalyDefaults:
    """Defaults billing_anomaly_detector (Vague E ét15 tier-2 étendu).

    Externalise les 3 seuils € severity (critical/warning/watch) +
    horizon NPV pour cohérence convention ADR-005.
    """

    threshold_critical_eur: float
    threshold_warning_eur: float
    threshold_watch_eur: float
    threshold_source: str
    npv_horizon_year_offset: int  # années ajoutées à now.year pour horizon NPV
    npv_horizon_source: str


@dataclass(frozen=True)
class ConsumptionDriftThresholds:
    """Defaults seuils severity consumption_drift_detector (ét15).

    Étend `ConsumptionDriftDefaults` avec les seuils € (auparavant inline).
    """

    threshold_critical_eur: float
    threshold_warning_eur: float
    threshold_watch_eur: float
    threshold_source: str


@dataclass(frozen=True)
class DataQualityDefaults:
    """Defaults data_quality_issue_detector (ét15).

    Seuils % données manquantes basés ISO 50001 §A.6.4.5.
    """

    threshold_critical_pct: float
    threshold_warning_pct: float
    threshold_watch_pct: float
    threshold_source: str


@dataclass(frozen=True)
class ActionOverdueDefaults:
    """Defaults action_overdue_detector (ét15).

    Seuils retard pour matrice (priority × jours).
    """

    overdue_critical_days: int
    overdue_warning_days: int
    overdue_source: str


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


def get_market_capacity_2026_defaults() -> MarketCapacity2026Defaults:
    """Charge les defaults market_window capacité 1/11/2026 (ét12g)."""
    raw = _load_raw()["market_capacity_2026"]
    return MarketCapacity2026Defaults(
        cost_per_mwh_eur=float(raw["cost_per_mwh_eur"]),
        cost_source=str(raw["cost_source"]),
        deadline_iso=str(raw["deadline_iso"]),
        deadline_source=str(raw["deadline_source"]),
        proxy_consumption_mwh_per_site=int(raw["proxy_consumption_mwh_per_site"]),
        proxy_consumption_source=str(raw["proxy_consumption_source"]),
    )


def get_contract_renewal_defaults() -> ContractRenewalDefaults:
    """Charge les defaults contract_renewal (ét14 P0 #1 CFO+Marie)."""
    raw = _load_raw()["contract_renewal"]
    return ContractRenewalDefaults(
        tacite_spread_pct=float(raw["tacite_spread_pct"]),
        tacite_spread_source=str(raw["tacite_spread_source"]),
        market_price_elec_eur_per_mwh=float(raw["market_price_elec_eur_per_mwh"]),
        market_price_gaz_eur_per_mwh=float(raw["market_price_gaz_eur_per_mwh"]),
        market_price_source=str(raw["market_price_source"]),
        proxy_volume_per_annex_mwh=int(raw["proxy_volume_per_annex_mwh"]),
        proxy_volume_source=str(raw["proxy_volume_source"]),
    )


def get_asset_registry_defaults() -> AssetRegistryDefaults:
    """Charge les defaults asset_registry (ét14 P0 #2 CFO)."""
    raw = _load_raw()["asset_registry"]
    return AssetRegistryDefaults(
        blind_billing_exposure_per_dp_eur=float(raw["blind_billing_exposure_per_dp_eur"]),
        blind_billing_source=str(raw["blind_billing_source"]),
        orphan_contract_exposure_eur=float(raw["orphan_contract_exposure_eur"]),
        orphan_contract_source=str(raw["orphan_contract_source"]),
    )


def get_billing_anomaly_defaults() -> BillingAnomalyDefaults:
    """Charge les defaults billing_anomaly (ét15 tier-2 étendu)."""
    raw = _load_raw()["billing_anomaly"]
    return BillingAnomalyDefaults(
        threshold_critical_eur=float(raw["threshold_critical_eur"]),
        threshold_warning_eur=float(raw["threshold_warning_eur"]),
        threshold_watch_eur=float(raw["threshold_watch_eur"]),
        threshold_source=str(raw["threshold_source"]),
        npv_horizon_year_offset=int(raw["npv_horizon_year_offset"]),
        npv_horizon_source=str(raw["npv_horizon_source"]),
    )


def get_consumption_drift_thresholds() -> ConsumptionDriftThresholds:
    """Charge les seuils severity consumption_drift (ét15)."""
    raw = _load_raw()["consumption_drift"]
    return ConsumptionDriftThresholds(
        threshold_critical_eur=float(raw["threshold_critical_eur"]),
        threshold_warning_eur=float(raw["threshold_warning_eur"]),
        threshold_watch_eur=float(raw["threshold_watch_eur"]),
        threshold_source=str(raw["threshold_source"]),
    )


def get_data_quality_defaults() -> DataQualityDefaults:
    """Charge les defaults data_quality_issue (ét15)."""
    raw = _load_raw()["data_quality"]
    return DataQualityDefaults(
        threshold_critical_pct=float(raw["threshold_critical_pct"]),
        threshold_warning_pct=float(raw["threshold_warning_pct"]),
        threshold_watch_pct=float(raw["threshold_watch_pct"]),
        threshold_source=str(raw["threshold_source"]),
    )


def get_action_overdue_defaults() -> ActionOverdueDefaults:
    """Charge les defaults action_overdue (ét15)."""
    raw = _load_raw()["action_overdue"]
    return ActionOverdueDefaults(
        overdue_critical_days=int(raw["overdue_critical_days"]),
        overdue_warning_days=int(raw["overdue_warning_days"]),
        overdue_source=str(raw["overdue_source"]),
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
    "ActionOverdueDefaults",
    "AssetRegistryDefaults",
    "BillingAnomalyDefaults",
    "ConsumptionDriftDefaults",
    "ConsumptionDriftThresholds",
    "ContractRenewalDefaults",
    "DataQualityDefaults",
    "DtComplianceDefaults",
    "MarketCapacity2026Defaults",
    "compute_npv_actualized",
    "get_action_overdue_defaults",
    "get_asset_registry_defaults",
    "get_billing_anomaly_defaults",
    "get_consumption_drift_defaults",
    "get_consumption_drift_thresholds",
    "get_contract_renewal_defaults",
    "get_data_quality_defaults",
    "get_discount_rate",
    "get_dt_compliance_defaults",
    "get_market_capacity_2026_defaults",
    "reload",
]
