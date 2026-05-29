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
    EnergyWeekProfileResponse,
)
from services.energy_orchestration.errors import (
    CODE_COMPARE_INVALID,
    CODE_GRANULARITY_TOO_FINE,
    CODE_GRANULARITY_UNKNOWN,
    CODE_PERIOD_INVALID,
    CODE_RANGE_INVALID,
    CODE_SCOPE_INVALID,
    energy_error,
)
from services.energy_orchestration.loadcurve import (
    LoadCurveError,
    build_loadcurve,
)
from services.energy_orchestration.synthesis import build_synthesis
from services.energy_orchestration.week_profile import (
    WeekProfileError,
    build_week_profile,
)


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
        raise energy_error(
            code=CODE_SCOPE_INVALID,
            message=f"scope='{scope}' invalide",
            hint="valeurs autorisées : org | portfolio | site",
            request=request,
        )
    if period not in ("7d", "30d", "90d", "12m", "ytd"):
        raise energy_error(
            code=CODE_PERIOD_INVALID,
            message=f"period='{period}' invalide",
            hint="valeurs autorisées : 7d | 30d | 90d | 12m | ytd",
            request=request,
        )
    if compare not in ("none", "n-1", "baseline", "contract"):
        raise energy_error(
            code=CODE_COMPARE_INVALID,
            message=f"compare='{compare}' invalide",
            hint="valeurs autorisées : none | n-1 | baseline | contract",
            request=request,
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
        raise energy_error(
            code=CODE_SCOPE_INVALID,
            message=f"scope='{scope}' invalide",
            hint="valeurs autorisées : org | portfolio | site | meter",
            request=request,
        )
    if compare not in ("none", "n-1", "baseline"):
        raise energy_error(
            code=CODE_COMPARE_INVALID,
            message=f"compare='{compare}' invalide",
            hint="valeurs autorisées : none | n-1 | baseline",
            request=request,
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
        # Sprint P1.S2b — code stable selon nature de l'erreur
        # (granularity_too_fine vs range_invalid vs unknown).
        msg = exc.message.lower()
        if "refusée" in msg or "granul" in msg and "(max" in exc.message:
            code = CODE_GRANULARITY_TOO_FINE
        elif "inconnue" in msg or "granularity '" in msg:
            code = CODE_GRANULARITY_UNKNOWN
        else:
            code = CODE_RANGE_INVALID
        raise energy_error(
            code=code,
            message=exc.message,
            hint=exc.hint,
            request=request,
        ) from exc


# ── GET /api/energy/week-profile ───────────────────────────────────────


@router.get("/week-profile", response_model=EnergyWeekProfileResponse)
def get_energy_week_profile(
    request: Request,
    scope: str = Query("site", description="site | meter"),
    scope_id: Optional[int] = Query(None, description="site_id ou meter_id"),
    days: int = Query(90, ge=7, le=365 * 2, description="fenêtre d'agrégation"),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Vue Semaine type — heatmap 7×24 + 4 KPI + provenance.

    Composer :
    - consumption_granularity_service (agrégation Σ MeterReading par
      weekday × hour)
    - data_freshness_service (qualité)
    - compute_quantiles (statut cellule via Tukey 3·IQR)
    """
    resolved_org_id = _resolve_org_id(request, auth, org_id)

    try:
        return build_week_profile(
            db,
            scope_kind=scope,
            scope_id=scope_id,
            org_id=resolved_org_id,
            days=days,
        )
    except WeekProfileError as exc:
        msg = exc.message.lower()
        if "scope_id" in msg:
            code = "ENERGY_SCOPE_ID_REQUIRED"
        elif "scope_kind" in msg or "non supporté" in msg:
            code = CODE_SCOPE_INVALID
        elif "insuffisant" in msg:
            code = "ENERGY_DAYS_INSUFFICIENT"
        else:
            code = CODE_RANGE_INVALID
        raise energy_error(
            code=code,
            message=exc.message,
            hint=exc.hint,
            request=request,
        ) from exc
