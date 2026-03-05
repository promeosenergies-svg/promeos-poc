"""
PROMEOS — KPI Service (centralized, cached, auditable).
Single source of truth for all cross-brique KPIs.
Playbook 2.2.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    Site,
    Portefeuille,
    EntiteJuridique,
    Organisation,
    not_deleted,
)

_logger = logging.getLogger("promeos.kpi")

# ── Data classes ─────────────────────────────────────────────────


@dataclass
class KpiScope:
    """Scope for KPI queries."""
    org_id: Optional[int] = None
    portfolio_id: Optional[int] = None
    site_id: Optional[int] = None
    period_start: Optional[str] = None  # ISO date
    period_end: Optional[str] = None    # ISO date


@dataclass
class KpiResult:
    """Standardized KPI result with metadata."""
    value: float
    unit: str
    source: str
    formula: str
    confidence: str = "high"  # high, medium, low
    period: Optional[str] = None
    scope_description: Optional[str] = None


# ── Cache ────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, KpiResult]] = {}
_CACHE_TTL = 300  # 5 minutes


def _cache_key(method: str, scope: KpiScope) -> str:
    return f"{method}:{scope.org_id}:{scope.portfolio_id}:{scope.site_id}:{scope.period_start}:{scope.period_end}"


def _get_cached(key: str) -> Optional[KpiResult]:
    if key in _cache:
        ts, result = _cache[key]
        if time.monotonic() - ts < _CACHE_TTL:
            return result
        del _cache[key]
    return None


def _set_cached(key: str, result: KpiResult):
    _cache[key] = (time.monotonic(), result)


# ── Helper: scoped sites query ───────────────────────────────────


def _sites_query(db: Session, scope: KpiScope):
    """Base query for non-deleted sites filtered by scope."""
    q = not_deleted(db.query(Site), Site)

    if scope.site_id:
        return q.filter(Site.id == scope.site_id)

    if scope.portfolio_id:
        return q.filter(Site.portefeuille_id == scope.portfolio_id)

    if scope.org_id:
        q = (
            q.join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(EntiteJuridique.organisation_id == scope.org_id)
        )

    return q


# ── KPI Service ──────────────────────────────────────────────────


class KpiService:
    """Source unique de vérité pour tous les KPIs PROMEOS."""

    def __init__(self, db: Session):
        self.db = db

    def get_financial_risk_eur(self, scope: KpiScope) -> KpiResult:
        """Risque financier total en EUR HT."""
        key = _cache_key("financial_risk", scope)
        cached = _get_cached(key)
        if cached:
            return cached

        total = (
            _sites_query(self.db, scope)
            .with_entities(func.coalesce(func.sum(Site.risque_financier_euro), 0))
            .scalar()
        ) or 0

        result = KpiResult(
            value=round(float(total), 2),
            unit="EUR",
            source="Site.risque_financier_euro (computed by compliance engine)",
            formula="SUM(sites.risque_financier_euro) WHERE scope",
            confidence="high",
            scope_description=_scope_desc(scope),
        )

        _logger.info("KPI financial_risk: %.2f EUR (scope=%s)", result.value, result.scope_description)
        _set_cached(key, result)
        return result

    def get_total_sites(self, scope: KpiScope) -> KpiResult:
        """Nombre total de sites actifs."""
        key = _cache_key("total_sites", scope)
        cached = _get_cached(key)
        if cached:
            return cached

        total = _sites_query(self.db, scope).filter(Site.actif == True).count()

        result = KpiResult(
            value=float(total),
            unit="sites",
            source="Site.actif = True",
            formula="COUNT(sites) WHERE actif=True AND scope",
            confidence="high",
            scope_description=_scope_desc(scope),
        )
        _set_cached(key, result)
        return result

    def get_compliance_score(self, scope: KpiScope) -> KpiResult:
        """Score conformité composite (% sites conformes)."""
        key = _cache_key("compliance_score", scope)
        cached = _get_cached(key)
        if cached:
            return cached

        from models import StatutConformite

        sites_q = _sites_query(self.db, scope)
        total = sites_q.count()
        if total == 0:
            result = KpiResult(
                value=0.0, unit="%", source="No sites in scope",
                formula="0 (no sites)", confidence="low",
                scope_description=_scope_desc(scope),
            )
            _set_cached(key, result)
            return result

        conformes = sites_q.filter(
            Site.statut_decret_tertiaire == StatutConformite.CONFORME
        ).count()

        score = round((conformes / total) * 100, 1)

        result = KpiResult(
            value=score,
            unit="%",
            source="Site.statut_decret_tertiaire = CONFORME",
            formula=f"({conformes}/{total}) * 100",
            confidence="high" if total >= 3 else "medium",
            scope_description=_scope_desc(scope),
        )

        _logger.info("KPI compliance_score: %.1f%% (scope=%s)", result.value, result.scope_description)
        _set_cached(key, result)
        return result

    def get_avancement_decret_pct(self, scope: KpiScope) -> KpiResult:
        """Avancement moyen Décret Tertiaire (%)."""
        key = _cache_key("avancement", scope)
        cached = _get_cached(key)
        if cached:
            return cached

        avg = (
            _sites_query(self.db, scope)
            .with_entities(func.avg(Site.avancement_decret_pct))
            .scalar()
        ) or 0

        result = KpiResult(
            value=round(float(avg), 1),
            unit="%",
            source="AVG(Site.avancement_decret_pct)",
            formula="AVG(sites.avancement_decret_pct) WHERE scope",
            confidence="high",
            scope_description=_scope_desc(scope),
        )
        _set_cached(key, result)
        return result

    def get_compliance_status_counts(self, scope: KpiScope) -> dict:
        """Nombre de sites par statut conformité tertiaire."""
        key = _cache_key("status_counts", scope)
        cached = _get_cached(key)
        if cached:
            return cached

        from models import StatutConformite

        sites_q = _sites_query(self.db, scope)
        total = sites_q.count()
        conformes = sites_q.filter(Site.statut_decret_tertiaire == StatutConformite.CONFORME).count()
        a_risque = sites_q.filter(Site.statut_decret_tertiaire == StatutConformite.A_RISQUE).count()
        non_conformes = sites_q.filter(Site.statut_decret_tertiaire == StatutConformite.NON_CONFORME).count()

        result = KpiResult(
            value=float(total),
            unit="sites",
            source="Site.statut_decret_tertiaire breakdown",
            formula=f"conformes={conformes}, a_risque={a_risque}, non_conformes={non_conformes}",
            confidence="high",
            scope_description=_scope_desc(scope),
        )
        # Store extra data in a wrapper
        result._counts = {
            "total": total,
            "conformes": conformes,
            "a_risque": a_risque,
            "non_conformes": non_conformes,
        }
        _set_cached(key, result)
        return result

    def get_summary(self, scope: KpiScope) -> dict:
        """All KPIs in one call — reduces N requests from frontend/routes."""
        risk = self.get_financial_risk_eur(scope)
        avancement = self.get_avancement_decret_pct(scope)
        compliance = self.get_compliance_score(scope)
        sites = self.get_total_sites(scope)
        surface = self.get_total_surface_m2(scope)
        status_counts = self.get_compliance_status_counts(scope)

        return {
            "risque_financier_euro": risk.value,
            "avancement_decret_pct": avancement.value,
            "compliance_score_pct": compliance.value,
            "total_sites": int(sites.value),
            "total_surface_m2": surface.value,
            "status_counts": status_counts._counts,
        }

    def get_total_surface_m2(self, scope: KpiScope) -> KpiResult:
        """Surface totale en m²."""
        key = _cache_key("surface", scope)
        cached = _get_cached(key)
        if cached:
            return cached

        total = (
            _sites_query(self.db, scope)
            .with_entities(func.coalesce(func.sum(Site.surface_m2), 0))
            .scalar()
        ) or 0

        result = KpiResult(
            value=round(float(total), 0),
            unit="m²",
            source="SUM(Site.surface_m2)",
            formula="SUM(sites.surface_m2) WHERE scope",
            confidence="high",
            scope_description=_scope_desc(scope),
        )
        _set_cached(key, result)
        return result


def _scope_desc(scope: KpiScope) -> str:
    """Human-readable scope description."""
    parts = []
    if scope.org_id:
        parts.append(f"org:{scope.org_id}")
    if scope.portfolio_id:
        parts.append(f"portfolio:{scope.portfolio_id}")
    if scope.site_id:
        parts.append(f"site:{scope.site_id}")
    if scope.period_start:
        parts.append(f"from:{scope.period_start}")
    if scope.period_end:
        parts.append(f"to:{scope.period_end}")
    return ", ".join(parts) or "global"
