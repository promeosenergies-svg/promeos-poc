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
from services.strategique.computes import (
    compute_next_contract_end,
    compute_spot_exposure,
    compute_trajectory_drift,
    compute_unvalued_cee_keur,
)
from services.strategique.mode_router import compute_strategic_mode
from services.strategique.mode_thresholds import StrategicMode


_logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/cockpit", tags=["Cockpit Strategique"])


# Phase 3.6 Vague AA : services compute_* livrés (computes.py). Le stub
# _DEMO_TRAJECTORY_DRIFT_STUB_PCT n'est plus utilisé — fallback minimal
# si le service retourne source=insufficient_data (cas DATA_INSUFFICIENT
# ou onboarding).
_DRIFT_FALLBACK_PCT: float = 0.0


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

    # 2. Calcul du mode (ADR-023 §9) — Phase 3.6 Vague AA computes réels
    has_dt_applicable = any(e.status == ApplicabilityStatus.APPLICABLE for e in applicability.get(RuleCode.DT, []))
    drift_info = compute_trajectory_drift(db, org_id) if has_dt_applicable else None
    contract_info = compute_next_contract_end(db, org_id)
    spot_info = compute_spot_exposure(db, org_id)
    cee_info = compute_unvalued_cee_keur(db, org_id)

    trajectory_drift_pct = drift_info["drift_pct"] if drift_info else _DRIFT_FALLBACK_PCT
    trajectory_drift_source = drift_info["source"] if drift_info else "not_applicable"

    target_mode = compute_strategic_mode(
        applicability=applicability,
        patrimoine_maturity=maturity,
        trajectory_drift_pct=trajectory_drift_pct,
        next_contract_end_days=contract_info["days"],
        spot_exposure_pct=spot_info["pct"],
        unvalued_cee_k_eur=cee_info["k_eur"],
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
    payload["_audit"]["next_contract_end_days"] = contract_info["days"]
    payload["_audit"]["spot_exposure_pct"] = spot_info["pct"]
    payload["_audit"]["unvalued_cee_k_eur"] = cee_info["k_eur"]
    if fallback_reason:
        payload["_audit"]["_fallback_reason"] = fallback_reason

    # 6. P0 cleanup cockpit (2026-05-25) — KPIs Bill Intelligence pour
    # remonter les signaux facturation dans CockpitStrategique (Cockpit P0
    # audit deep §3.4 P1-1) : surfacturations à contester, anomalies
    # ouvertes, anomalies par énergie, actions facturation ouvertes.
    # Chaque KPI expose source/formule/unité/période/périmètre. Le FE rend
    # `payload.billing_kpis` sans recalcul (doctrine §8.1).
    try:
        from services.billing_kpis_cockpit_service import compute_billing_kpis_cockpit

        payload["billing_kpis"] = compute_billing_kpis_cockpit(db, org_id)
    except Exception as e:
        # Fallback gracieux : si le service Billing échoue, on n'affiche pas
        # le bloc côté FE plutôt que de casser tout le payload Strategique.
        _logger.warning("[strategique] billing_kpis fetch failed: %s", e)
        payload["billing_kpis"] = {"kpis": [], "links": {}, "_error": str(e)}

    return payload
