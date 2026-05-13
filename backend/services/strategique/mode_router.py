"""PROMEOS — compute_strategic_mode v1.0 — cascade des 5 gates.

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md` §9.

Cascade canonique (gates dans l'ordre, premier match gagne) :
    Gate 1 — DATA_INSUFFICIENT  : maturité < 60 % OU unknown_ratio > 30 %
    Gate 2 — REGULATORY_DRIVEN  : DT ou BACS APPLICABLE ET trajectory_drift > 5 %
    Gate 3 — PROCUREMENT_DRIVEN : next_contract_end < 90 j OU spot_exposure > 40 %
    Gate 4 — OPPORTUNITY_DRIVEN : APER APPLICABLE OU unvalued_cee > 50 k€
    Default                      : PERFORMANCE_DRIVEN

Inputs cardinaux du dispatcher :
    applicability        — sortie de regulatory.applicability_service.compute_applicability
    patrimoine_maturity  — sortie de regulatory.applicability_service.compute_patrimoine_maturity
    trajectory_drift_pct — float, % de dérive DT vs cible -40 %/2030 (signed positif si en retard)
    next_contract_end_days — int, jours jusqu'à prochaine échéance contrat élec/gaz
    spot_exposure_pct    — float, % volume exposé au spot
    unvalued_cee_k_eur   — float, valeur CEE non encore valorisée

Tous les inputs hors `applicability`/`maturity` sont actuellement attendus
calculés par le builder amont (Vague C). Le dispatcher reste pur (pas
d'accès DB direct) pour rester testable + cacheable.

Fallback Phase 3.5 (décision Phase 0 Q3) :
    PROCUREMENT_DRIVEN et OPPORTUNITY_DRIVEN sont stubs typés (Vague C.4).
    Si le dispatcher renvoie l'un de ces modes mais que le builder
    correspondant est non implémenté, le caller doit basculer
    automatiquement sur PERFORMANCE_DRIVEN avec
    `_fallback_reason="mode_not_implemented_v1.0"` dans l'audit trail.
"""

from __future__ import annotations

import logging
from typing import Any

from regulatory.applicability_service import count_unknown_or_missing
from regulatory.applicability_types import ApplicabilityStatus, RuleCode

from services.strategique.mode_thresholds import (
    MODE_THRESHOLDS_V1,
    ModeThresholds,
    StrategicMode,
)


_logger = logging.getLogger(__name__)


def compute_strategic_mode(
    applicability: dict[RuleCode, list],
    patrimoine_maturity: float,
    trajectory_drift_pct: float = 0.0,
    next_contract_end_days: int = 99999,
    spot_exposure_pct: float = 0.0,
    unvalued_cee_k_eur: float = 0.0,
    thresholds: ModeThresholds | None = None,
) -> StrategicMode:
    """Détermine le mode narratif de la Synthèse Stratégique.

    Args:
        applicability: dict[RuleCode → list[RuleApplicability]] sortie du
            moteur d'assujettissement (ADR-024).
        patrimoine_maturity: float ∈ [0,1] — ratio champs critiques renseignés.
        trajectory_drift_pct: float — dérive DT en points vs cible -40 %/2030.
            Convention : positif = en retard (ex. -32 % atteint vs -40 % cible
            → drift = 8). 0.0 si non calculable.
        next_contract_end_days: int — jours jusqu'à prochaine échéance contrat
            (sentinelle 99999 par défaut = aucun contrat à renouveler).
        spot_exposure_pct: float — % volume exposé au spot. 0.0 par défaut.
        unvalued_cee_k_eur: float — valeur CEE non valorisée k€/an.
        thresholds: ModeThresholds optionnel (défaut = MODE_THRESHOLDS_V1).

    Returns:
        StrategicMode (membre du StrEnum).
    """
    t = thresholds if thresholds is not None else MODE_THRESHOLDS_V1

    # ── Gate 1 — DATA_INSUFFICIENT (priorité 1) ────────────────────────
    if patrimoine_maturity < t.MIN_PATRIMOINE_MATURITY:
        return StrategicMode.DATA_INSUFFICIENT
    total, bad = count_unknown_or_missing(applicability)
    unknown_ratio = (bad / total) if total > 0 else 0.0
    if unknown_ratio > t.MAX_UNKNOWN_RULES_RATIO:
        return StrategicMode.DATA_INSUFFICIENT

    # ── Gate 2 — REGULATORY_DRIVEN ─────────────────────────────────────
    has_dt_or_bacs_applicable = any(
        entry.status == ApplicabilityStatus.APPLICABLE
        for entry in (list(applicability.get(RuleCode.DT, [])) + list(applicability.get(RuleCode.BACS, [])))
    )
    if has_dt_or_bacs_applicable and trajectory_drift_pct > t.MIN_TRAJECTORY_DRIFT_PCT:
        return StrategicMode.REGULATORY_DRIVEN

    # ── Gate 3 — PROCUREMENT_DRIVEN ────────────────────────────────────
    if next_contract_end_days < t.MAX_CONTRACT_END_DAYS or spot_exposure_pct > t.MAX_SPOT_EXPOSURE_PCT:
        return StrategicMode.PROCUREMENT_DRIVEN

    # ── Gate 4 — OPPORTUNITY_DRIVEN ────────────────────────────────────
    has_aper_applicable = any(
        entry.status == ApplicabilityStatus.APPLICABLE for entry in applicability.get(RuleCode.APER, [])
    )
    if has_aper_applicable or unvalued_cee_k_eur > t.MIN_OPPORTUNITY_VALUE_K_EUR:
        return StrategicMode.OPPORTUNITY_DRIVEN

    # ── Default — PERFORMANCE_DRIVEN ───────────────────────────────────
    return StrategicMode.PERFORMANCE_DRIVEN
