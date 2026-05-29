"""
PROMEOS — Explorer Insights Service (Sprint Énergie P0.S1c, brief P3).

SoT canonique des règles d'insight Explorer (page /consommations/explorer).
Remplace `frontend/src/pages/consumption/insightRules.js` (computeInsights)
qui codait 6 règles déterministes côté frontend (violation doctrine
« zéro calcul métier frontend » — seuils 15%, 10%, 0.7, 110% côté JS).

Doctrine
────────
- Tous les seuils sont déclarés ici, versionnés en code.
- Sources : skill `promeos-energy-fundamentals` + doctrine pilotage
  des usages (talon nuit > 35 %, week-end > 60 %, etc.).
- Le frontend consomme la liste d'insights via REST, sans logique.
- Chaque insight porte `provenance` (source, formula, threshold).

Règles (6 historiques) :
1. OUTSIDE_BAND_HIGH : % hors enveloppe P10-P90 > 15 % → warn ; > 30 % → crit
2. BASE_LOAD_DRIFT  : |dérive talon gaz| > 10 % → warn ; > 20 % → crit
3. HP_RATIO_HIGH    : ratio HP > 70 % → info ; > 85 % → warn
4. TARGET_OVER_BUDGET : YTD vs objectif > 110 % → warn ; > 130 % → crit
5. GAS_LEAK_SUSPECT : alerte primaryWeather.type == 'probable_leak' → crit
6. LOW_CONFIDENCE   : un panel a confidence == 'low' → info
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


# Seuils canoniques — extractibles vers YAML versionné si besoin.
# Source : skill `promeos-energy-fundamentals` + doctrine pilotage usages.
THRESHOLD_OUTSIDE_BAND_WARN = 15
THRESHOLD_OUTSIDE_BAND_CRIT = 30
THRESHOLD_BASE_DRIFT_WARN = 10
THRESHOLD_BASE_DRIFT_CRIT = 20
THRESHOLD_HP_RATIO_INFO = 0.70
THRESHOLD_HP_RATIO_WARN = 0.85
THRESHOLD_TARGET_OVER_WARN = 110
THRESHOLD_TARGET_OVER_CRIT = 130


@dataclass
class Insight:
    """Forme normalisée d'un insight Explorer."""

    id: str
    label: str
    severity: str  # info | warn | crit
    detail: str
    provenance: dict


_SEVERITY_ORDER = {"crit": 0, "warn": 1, "info": 2}


def build_explorer_insights(motor_data: dict[str, Any]) -> list[dict]:
    """Construit la liste d'insights à afficher dans l'Explorer.

    Args:
        motor_data : dict avec les payloads panels backend pré-calculés.
            Clés attendues (toutes optionnelles, robuste si manquantes) :
              - primaryTunnel : {outside_pct, confidence?}
              - primaryHphc   : {hp_ratio, confidence?}
              - primaryGas    : {confidence?}
              - primaryWeather: {drift: {base_drift_pct}, alerts: [...]}
              - primaryProgression: {progress_pct, run_rate_kwh}

    Returns:
        Liste d'insights `[{id, label, severity, detail, provenance}]`
        triée par sévérité (crit en tête, info en queue).
    """
    motor_data = motor_data or {}
    rules = (
        _rule_outside_band_high,
        _rule_base_load_drift,
        _rule_hp_ratio_high,
        _rule_target_over_budget,
        _rule_gas_leak_suspect,
        _rule_low_confidence,
    )
    insights: list[Insight] = []
    for rule in rules:
        try:
            ins = rule(motor_data)
        except Exception:  # noqa: BLE001 — robustesse rendering
            ins = None
        if ins is not None:
            insights.append(ins)
    insights.sort(key=lambda i: _SEVERITY_ORDER.get(i.severity, 3))
    return [asdict(i) for i in insights]


def _provenance(rule_id: str, formula: str, threshold: Any) -> dict:
    return {
        "source": "PROMEOS explorer_insights_service",
        "rule": rule_id,
        "formula": formula,
        "threshold": threshold,
        "doctrine_ref": "promeos-energy-fundamentals + pilotage-usages",
    }


def _rule_outside_band_high(data: dict) -> Optional[Insight]:
    tunnel = data.get("primaryTunnel") or {}
    pct = tunnel.get("outside_pct")
    if pct is None or pct <= THRESHOLD_OUTSIDE_BAND_WARN:
        return None
    severity = "crit" if pct > THRESHOLD_OUTSIDE_BAND_CRIT else "warn"
    return Insight(
        id="outside_band_high",
        label=f"{pct}% hors bande tunnel",
        severity=severity,
        detail=(f"{pct}% des relevés sont hors de l'enveloppe P10-P90 sur la période analysée."),
        provenance=_provenance(
            "outside_band_high",
            "outside_pct > 15 (warn) ou > 30 (crit)",
            {"warn": THRESHOLD_OUTSIDE_BAND_WARN, "crit": THRESHOLD_OUTSIDE_BAND_CRIT},
        ),
    )


def _rule_base_load_drift(data: dict) -> Optional[Insight]:
    weather = data.get("primaryWeather") or {}
    drift_obj = weather.get("drift") or {}
    drift = drift_obj.get("base_drift_pct")
    if drift is None or abs(drift) < THRESHOLD_BASE_DRIFT_WARN:
        return None
    severity = "crit" if abs(drift) > THRESHOLD_BASE_DRIFT_CRIT else "warn"
    sign = "+" if drift > 0 else ""
    return Insight(
        id="base_load_drift",
        label=f"Dérive talon gaz {sign}{drift}%",
        severity=severity,
        detail=(
            f"La consommation de base (hors chauffage) a dérivé de {drift}% par rapport à la période de référence."
        ),
        provenance=_provenance(
            "base_load_drift",
            "|base_drift_pct| > 10 (warn) ou > 20 (crit)",
            {"warn": THRESHOLD_BASE_DRIFT_WARN, "crit": THRESHOLD_BASE_DRIFT_CRIT},
        ),
    )


def _rule_hp_ratio_high(data: dict) -> Optional[Insight]:
    hphc = data.get("primaryHphc") or {}
    ratio = hphc.get("hp_ratio")
    if ratio is None or ratio <= THRESHOLD_HP_RATIO_INFO:
        return None
    severity = "warn" if ratio > THRESHOLD_HP_RATIO_WARN else "info"
    pct = round(ratio * 100)
    return Insight(
        id="hp_ratio_high",
        label=f"Ratio HP élevé ({pct}%)",
        severity=severity,
        detail=(
            f"{pct}% de la consommation électrique est en Heures Pleines. "
            f"Un report vers HC pourrait réduire la facture."
        ),
        provenance=_provenance(
            "hp_ratio_high",
            "hp_ratio > 0.70 (info) ou > 0.85 (warn)",
            {"info": THRESHOLD_HP_RATIO_INFO, "warn": THRESHOLD_HP_RATIO_WARN},
        ),
    )


def _rule_target_over_budget(data: dict) -> Optional[Insight]:
    prog = data.get("primaryProgression") or {}
    pct = prog.get("progress_pct")
    if pct is None or pct <= THRESHOLD_TARGET_OVER_WARN:
        return None
    over = round(pct - 100)
    severity = "crit" if pct > THRESHOLD_TARGET_OVER_CRIT else "warn"
    run_rate = prog.get("run_rate_kwh") or 0
    return Insight(
        id="target_over_budget",
        label=f"Budget dépassé de {over}%",
        severity=severity,
        detail=(f"La consommation YTD dépasse l'objectif de {over}%. Run-rate annuel : {round(run_rate)} kWh."),
        provenance=_provenance(
            "target_over_budget",
            "progress_pct > 110 (warn) ou > 130 (crit)",
            {"warn": THRESHOLD_TARGET_OVER_WARN, "crit": THRESHOLD_TARGET_OVER_CRIT},
        ),
    )


def _rule_gas_leak_suspect(data: dict) -> Optional[Insight]:
    weather = data.get("primaryWeather") or {}
    alerts = weather.get("alerts") or []
    leak = next((a for a in alerts if a.get("type") == "probable_leak"), None)
    if not leak:
        return None
    return Insight(
        id="gas_leak_suspect",
        label="Fuite gaz probable",
        severity="crit",
        detail=(leak.get("message") or "Consommation de base estivale anormalement élevée. Vérifiez l'installation."),
        provenance=_provenance(
            "gas_leak_suspect",
            "alerts[].type == 'probable_leak'",
            {"alert_type": "probable_leak"},
        ),
    )


def _rule_low_confidence(data: dict) -> Optional[Insight]:
    panels = [
        data.get("primaryTunnel"),
        data.get("primaryHphc"),
        data.get("primaryGas"),
    ]
    has_low = any((p or {}).get("confidence") == "low" for p in panels)
    if not has_low:
        return None
    return Insight(
        id="low_confidence",
        label="Données insuffisantes",
        severity="info",
        detail=("Un ou plusieurs panneaux disposent de peu de relevés. Les analyses peuvent être moins fiables."),
        provenance=_provenance(
            "low_confidence",
            "any panel.confidence == 'low'",
            {"low": "low"},
        ),
    )
