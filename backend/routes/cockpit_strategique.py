"""PROMEOS — Endpoint `/api/cockpit/strategique` (Phase 3.5 Vague C.5).

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md` §1.

Endpoint orchestrateur de la page Synthèse Stratégique. Consommé par
`frontend/src/pages/CockpitStrategique.jsx` (Vague D).

Étapes (toutes pures, aucun side-effect DB en écriture) :
  1. Org-scoping via `resolve_org_id`
  2. Évalue l'applicabilité 5 règles + maturité patrimoine (ADR-024)
  3. Calcule le strategic_mode via cascade (ADR-023 §9)
  4. Fallback Phase 3.5 : PROCUREMENT/OPPORTUNITY → PERFORMANCE
     avec _fallback_reason="mode_not_implemented_v1.0"
  5. Dispatche vers le builder et retourne le payload complet

Discipline "from scratch" Phase 3.5 :
  AUCUN import depuis services/cockpit_*.py legacy ni routes/cockpit_v2.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from regulatory.applicability_service import (
    compute_applicability,
    compute_patrimoine_maturity,
)
from regulatory.applicability_types import ApplicabilityStatus, RuleCode
from services.scope_utils import resolve_org_id
from services.strategique.builders import (
    IMPLEMENTED_MODES,
    MODE_BUILDERS,
)
from services.strategique.mode_router import compute_strategic_mode
from services.strategique.mode_thresholds import StrategicMode


_logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/cockpit", tags=["Cockpit Strategique"])


# Fix code-reviewer P1-C 13/05/2026 : extraction du magic number.
# La valeur 8.0 simule une dérive trajectoire DT plausible (cible -40 %,
# atteint -32 %) qui déclenche le gate REGULATORY_DRIVEN. Sera remplacé
# Phase 3.6 par `compute_trajectory_drift(db, org_id)` qui lit
# RegAssessment.findings_json (cf. runbook punchlist #7+#10).
_DEMO_TRAJECTORY_DRIFT_STUB_PCT: float = 8.0


@router.get("/strategique")
def get_cockpit_strategique(
    request: Request,
    period_type: str = "month",
    persona: str = "dg_comex",
    horizon_year: int = 2030,
    portfolio_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> dict:
    """Renvoie le payload complet polymorphique de la Synthèse Stratégique."""
    org_id = resolve_org_id(request, auth, db)

    # 1. Évaluation cadre applicable (ADR-024)
    applicability = compute_applicability(db, org_id)
    maturity = compute_patrimoine_maturity(db, org_id)

    # 2. Calcul du mode (ADR-023 §9)
    # Phase 3.5 v1.0 : trajectory_drift / contract_end / spot / cee non encore
    # wirés à des services dédiés — passés à 0 par défaut. Le dispatcher
    # statuera donc DATA_INSUFFICIENT (si maturité basse), REGULATORY (si DT
    # APPLICABLE + drift sera wiré Phase 3.6), ou PERFORMANCE (défaut).
    # Pour HELIOS demo, on simule un drift > 5 si DT APPLICABLE détecté
    # → bascule sur REGULATORY_DRIVEN narratif (cf. _DEMO_TRAJECTORY_DRIFT_STUB_PCT).
    has_dt_applicable = any(e.status == ApplicabilityStatus.APPLICABLE for e in applicability.get(RuleCode.DT, []))
    trajectory_drift_pct = _DEMO_TRAJECTORY_DRIFT_STUB_PCT if has_dt_applicable else 0.0
    trajectory_drift_source = "stub_demo_v1.0" if has_dt_applicable else "not_applicable"

    target_mode = compute_strategic_mode(
        applicability=applicability,
        patrimoine_maturity=maturity,
        trajectory_drift_pct=trajectory_drift_pct,
    )

    # 3. Fallback Phase 3.5 — décision Q3 Amine
    effective_mode = target_mode
    fallback_reason: Optional[str] = None
    if target_mode not in IMPLEMENTED_MODES:
        _logger.info(
            "[strategique] mode=%s non implémenté Phase 3.5 → fallback PERFORMANCE_DRIVEN. org_id=%s",
            target_mode.value,
            org_id,
        )
        effective_mode = StrategicMode.PERFORMANCE_DRIVEN
        fallback_reason = "mode_not_implemented_v1.0"

    # 4. Dispatch vers le builder concret
    builder = MODE_BUILDERS[effective_mode]
    payload = builder.build(
        db=db,
        org_id=org_id,
        applicability=applicability,
        patrimoine_maturity=maturity,
        persona=persona,
        period_type=period_type,
        horizon_year=horizon_year,
    )

    # 5. Audit trail : trace mode demandé vs effectif si fallback
    payload["_audit"]["target_mode"] = target_mode.value
    payload["_audit"]["effective_mode"] = effective_mode.value
    payload["_audit"]["trajectory_drift_source"] = trajectory_drift_source
    payload["_audit"]["trajectory_drift_pct"] = trajectory_drift_pct
    if fallback_reason:
        payload["_audit"]["_fallback_reason"] = fallback_reason

    return payload
