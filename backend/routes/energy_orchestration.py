"""
PROMEOS — Router orchestration énergie (Sprint P1.S2a).

Expose les endpoints d'orchestration `/api/energy/*` qui composent les
SoT existants pour servir les vues client (Synthèse, Courbe de charge,
+ Semaine type / Coût&contrat / Marché à venir P1.S2b/c/d).

Doctrine :
- Chaque KPI exposé porte une `provenance` (source-guard
  `test_energy_orchestration_provenance_source_guards.py`).
- Tous les scores bornés [0, 100] côté payload.
- Timezone Europe/Paris explicite.
- Org-scoping strict via `resolve_org_id` (IS11).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from schemas.energy_orchestration import (
    EnergyLoadCurveResponse,
    EnergySynthesisResponse,
)
from services.energy_orchestration.loadcurve import (
    LoadCurveError,
    build_loadcurve,
)
from services.energy_orchestration.synthesis import build_synthesis


router = APIRouter(prefix="/api/energy", tags=["Energy Orchestration"])


def _resolve_org_id(request: Request, auth: Optional[AuthContext], explicit: Optional[int]) -> Optional[int]:
    """Résout l'org_id à partir de auth > header > param query (lecture seule)."""
    if auth and getattr(auth, "org_id", None):
        return int(auth.org_id)
    raw = request.headers.get("X-Org-Id")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return explicit


# ── GET /api/energy/synthesis ──────────────────────────────────────────


@router.get("/synthesis", response_model=EnergySynthesisResponse)
def get_energy_synthesis(
    request: Request,
    scope: str = Query("org", description="org | portfolio | site"),
    scope_id: Optional[int] = Query(None, description="id du scope (site_id pour site)"),
    period: str = Query("30d", description="7d | 30d | 90d | 12m | ytd"),
    compare: str = Query("none", description="none | n-1 | baseline | contract"),
    org_id: Optional[int] = Query(None, description="org id explicite (fallback)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Vue Synthèse 30 secondes — 10 KPI + narrative + provenance.

    Compose : consumption_unified_service + cost_by_period_service +
    emissions_service + consumption_granularity_service +
    data_freshness_service + Insights/Actions backend (impact agrégé).
    """
    if scope not in ("org", "portfolio", "site"):
        raise HTTPException(
            status_code=400,
            detail=f"scope='{scope}' invalide (attendu: org|portfolio|site)",
        )
    if period not in ("7d", "30d", "90d", "12m", "ytd"):
        raise HTTPException(
            status_code=400,
            detail=f"period='{period}' invalide (attendu: 7d|30d|90d|12m|ytd)",
        )
    if compare not in ("none", "n-1", "baseline", "contract"):
        raise HTTPException(
            status_code=400,
            detail=f"compare='{compare}' invalide (attendu: none|n-1|baseline|contract)",
        )

    resolved_org_id = _resolve_org_id(request, auth, org_id)

    return build_synthesis(
        db,
        scope_kind=scope,
        scope_id=scope_id,
        org_id=resolved_org_id,
        period_label=period,
        compare=compare,
    )


# ── GET /api/energy/loadcurve ──────────────────────────────────────────


@router.get("/loadcurve", response_model=EnergyLoadCurveResponse)
def get_energy_loadcurve(
    request: Request,
    scope: str = Query("site", description="org | portfolio | site | meter"),
    scope_id: Optional[int] = Query(None),
    from_: datetime = Query(..., alias="from", description="ISO 8601 début"),
    to: datetime = Query(..., description="ISO 8601 fin"),
    granularity: str = Query("hour", description="15min | 30min | hour | day | week | month | year"),
    compare: str = Query("none", description="none | n-1 | baseline"),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Vue Courbe de charge — série temporelle + 4 KPI agrégés + provenance.

    Limites volumétriques par granularité :
    - 15min : période ≤ 7 j
    - 30min : période ≤ 30 j
    - hour  : période ≤ 90 j
    - day+  : larges périodes autorisées
    """
    if scope not in ("org", "portfolio", "site", "meter"):
        raise HTTPException(
            status_code=400,
            detail=f"scope='{scope}' invalide (attendu: org|portfolio|site|meter)",
        )
    if compare not in ("none", "n-1", "baseline"):
        raise HTTPException(
            status_code=400,
            detail=f"compare='{compare}' invalide",
        )

    resolved_org_id = _resolve_org_id(request, auth, org_id)

    try:
        return build_loadcurve(
            db,
            scope_kind=scope,
            scope_id=scope_id,
            org_id=resolved_org_id,
            from_dt=from_,
            to_dt=to,
            granularity=granularity,
            compare=compare,
        )
    except LoadCurveError as exc:
        detail = exc.message
        if exc.hint:
            detail = f"{detail} — hint: {exc.hint}"
        raise HTTPException(status_code=400, detail=detail) from exc
