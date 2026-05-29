"""
PROMEOS — Service orchestration Synthèse Énergie (Sprint P1.S2a).

Compose les SoT existants pour exposer la vue Synthèse 30 secondes :
- consumption_unified_service (kWh, coverage)
- emissions_service (CO₂ ADEME V23.6)
- electric_monitoring score clamp
- consumption_granularity_service (peak)
- cost_by_period_service (coût)
- data_freshness_service (data quality)
- action_center (alerts, actions, impact financier — agrégé backend)

Doctrine : tout KPI exposé porte une `provenance` (source, service,
formula, period, confidence, assumptions). Scores bornés [0, 100].
Aucun calcul métier ne reste côté FE.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from schemas.energy_orchestration import (
    EnergyKpi,
    EnergyPeriod,
    EnergyProvenance,
    EnergyRecommendation,
    EnergyScope,
    EnergySynthesisResponse,
)
from services.electric_monitoring.score_utils import clamp_score_0_100


TZ_PARIS = ZoneInfo("Europe/Paris")

PeriodLabel = Literal["7d", "30d", "90d", "12m", "ytd", "custom"]
ScopeKind = Literal["org", "portfolio", "site", "meter"]


# ── Helpers période / scope ─────────────────────────────────────────────


def resolve_period(period_label: str, now: Optional[datetime] = None) -> EnergyPeriod:
    """Convertit un label période en EnergyPeriod (timezone Europe/Paris)."""
    if now is None:
        now = datetime.now(TZ_PARIS)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=TZ_PARIS)

    if period_label == "7d":
        start = now - timedelta(days=7)
        days = 7
    elif period_label == "30d":
        start = now - timedelta(days=30)
        days = 30
    elif period_label == "90d":
        start = now - timedelta(days=90)
        days = 90
    elif period_label == "12m":
        start = now - timedelta(days=365)
        days = 365
    elif period_label == "ytd":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        days = max(1, (now - start).days)
    else:
        raise ValueError(f"period_label inconnu : {period_label}")

    return EnergyPeriod(
        label=period_label,  # type: ignore[arg-type]
        start=start,
        end=now,
        days=days,
        timezone="Europe/Paris",
    )


def _build_provenance(
    service: str,
    formula: str,
    period: EnergyPeriod,
    *,
    source: str = "PROMEOS energy_orchestration",
    confidence: float = 1.0,
    assumptions: Optional[list[str]] = None,
) -> EnergyProvenance:
    return EnergyProvenance(
        source=source,
        service=service,
        formula=formula,
        period=f"{period.start.date()} → {period.end.date()}",
        confidence=confidence,
        assumptions=assumptions or [],
        doctrine_ref="promeos-energy-fundamentals + ADR cdc Europe/Paris",
    )


# ── KPI builders ────────────────────────────────────────────────────────


def _kpi_inactive(
    key: str,
    label: str,
    unit: str,
    scope: EnergyScope,
    period: EnergyPeriod,
    *,
    reason: str = "no_data",
) -> EnergyKpi:
    """KPI à état 'inactif' avec provenance + assumptions explicites."""
    return EnergyKpi(
        key=key,
        label=label,
        value=None,
        unit=unit,  # type: ignore[arg-type]
        state="inactif",
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service=f"energy_orchestration.synthesis._{key}",
            formula="aucune donnée disponible sur le scope/période",
            period=period,
            confidence=0.0,
            assumptions=[f"reason={reason}"],
        ),
    )


def _state_from_delta_or_threshold(
    value: Optional[float],
    *,
    sain_max: Optional[float] = None,
    vigilance_max: Optional[float] = None,
) -> str:
    """Calcule state {sain|vigilance|critique|inactif} à partir d'un seuil."""
    if value is None:
        return "inactif"
    if sain_max is None or value <= sain_max:
        return "sain"
    if vigilance_max is None or value <= vigilance_max:
        return "vigilance"
    return "critique"


# ── KPI individuels (composition des SoT) ──────────────────────────────


def _kpi_consumption_kwh(db: Session, scope: EnergyScope, period: EnergyPeriod) -> EnergyKpi:
    """KPI 1 : consommation totale kWh sur le scope/période."""
    try:
        if scope.kind == "site" and scope.id is not None:
            from services.consumption_unified_service import get_consumption_summary
            from models.enums import EnergyVector

            summary = get_consumption_summary(
                db,
                int(scope.id),
                period.start.date(),
                period.end.date(),
                energy_vector=EnergyVector.ELECTRICITY,
            )
            value = summary.get("value_kwh") if summary else None
            confidence = {"high": 1.0, "medium": 0.7, "low": 0.4, "none": 0.0}.get(
                summary.get("confidence", "none") if summary else "none", 0.0
            )
        else:
            # Org / portfolio : agrège via consumption_granularity_service
            from services.consumption_granularity_service import get_org_daily_range_kwh

            days = get_org_daily_range_kwh(db, scope.org_id, period.start.date(), period.end.date())
            metered_days = [d for d in days if d["kwh"] is not None]
            value = sum(d["kwh"] for d in metered_days) if metered_days else None
            confidence = round(len(metered_days) / max(1, len(days)), 2) if days else 0.0
    except Exception:
        value = None
        confidence = 0.0

    if value is None or value <= 0:
        return _kpi_inactive("consumption_kwh", "Consommation", "kWh", scope, period)

    return EnergyKpi(
        key="consumption_kwh",
        label="Consommation",
        value=round(value, 2),
        unit="kWh",
        state="sain",  # Volume brut — pas de seuil intrinsèque
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="consumption_unified_service.get_consumption_summary",
            formula="Σ MeterReading.value_kwh sur scope/période",
            period=period,
            confidence=confidence,
            assumptions=[
                "seuil 80 % couverture metered (sinon billed)",
                "energy_vector=ELECTRICITY",
            ],
        ),
    )


def _kpi_cost_eur(db: Session, scope: EnergyScope, period: EnergyPeriod) -> EnergyKpi:
    """KPI 2 : coût estimé €."""
    try:
        if scope.kind == "site" and scope.id is not None:
            from services.cost_by_period_service import get_cost_by_period

            months = max(1, period.days // 30)
            cost_data = get_cost_by_period(db, int(scope.id), months=months)
            total_eur = cost_data.get("total_eur") if isinstance(cost_data, dict) else None
        else:
            total_eur = None
    except Exception:
        total_eur = None

    if total_eur is None:
        return _kpi_inactive("cost_eur", "Coût estimé", "€", scope, period)

    return EnergyKpi(
        key="cost_eur",
        label="Coût estimé",
        value=round(total_eur, 0),
        unit="€",
        state="sain",
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="cost_by_period_service.get_cost_by_period",
            formula="Σ kWh_m × prix_moyen_m (TURPE inclus si contrat actif)",
            period=period,
            confidence=0.8,
            assumptions=[
                "DEFAULT_PRICE_ELEC_EUR_KWH si pas de contrat actif",
                "TURPE inclus si TariffCalendar attaché site",
            ],
        ),
    )


def _kpi_co2_kg(
    db: Session,
    scope: EnergyScope,
    period: EnergyPeriod,
    consumption_kpi: EnergyKpi,
) -> EnergyKpi:
    """KPI 3 : émissions CO₂ kgCO₂eq (ADEME V23.6)."""
    if consumption_kpi.value is None or not isinstance(consumption_kpi.value, (int, float)):
        return _kpi_inactive("co2_kg", "CO₂ équivalent", "kgCO₂eq", scope, period)

    try:
        from services.emissions_service import get_emission_factor

        factor_info = get_emission_factor(db, energy_type="electricity", region="FR")
        factor = factor_info["kgco2e_per_kwh"]
        co2_kg = round(float(consumption_kpi.value) * factor, 1)
    except Exception:
        return _kpi_inactive("co2_kg", "CO₂ équivalent", "kgCO₂eq", scope, period, reason="no_factor")

    return EnergyKpi(
        key="co2_kg",
        label="CO₂ équivalent",
        value=co2_kg,
        unit="kgCO₂eq",
        state="sain",
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="emissions_service.get_emission_factor",
            formula=f"consumption_kwh × {factor} kgCO₂eq/kWh (ADEME V23.6)",
            period=period,
            confidence=1.0,
            assumptions=[
                "ADEME Base Carbone V23.6",
                f"factor={factor} kgCO₂eq/kWh (elec FR mix moyen)",
            ],
        ),
    )


def _kpi_peak_kw(db: Session, scope: EnergyScope, period: EnergyPeriod) -> EnergyKpi:
    """KPI 4 : puissance max appelée."""
    try:
        from services.consumption_granularity_service import get_org_peak_kw

        # Pour MVP, on prend le pic sur le jour le plus récent de la période.
        day = period.end.date() if hasattr(period.end, "date") else period.end
        peak = get_org_peak_kw(db, scope.org_id, day) if scope.kind != "site" else None
        if scope.kind == "site" and scope.id is not None:
            from services.consumption_granularity_service import get_org_hourly_curve_kw

            curve = get_org_hourly_curve_kw(db, scope.org_id, day)
            peak_vals = [p["kw"] for p in curve if p["kw"] is not None]
            peak = max(peak_vals) if peak_vals else None
    except Exception:
        peak = None

    if peak is None:
        return _kpi_inactive("peak_kw", "Puissance max", "kW", scope, period)

    return EnergyKpi(
        key="peak_kw",
        label="Puissance max",
        value=round(peak, 2),
        unit="kW",
        state="sain",
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="consumption_granularity_service.get_org_peak_kw",
            formula="max(kw_avg horaire) sur jour le plus récent",
            period=period,
            confidence=0.7,
        ),
    )


def _kpi_weighted_price(
    consumption_kpi: EnergyKpi,
    cost_kpi: EnergyKpi,
    scope: EnergyScope,
    period: EnergyPeriod,
) -> EnergyKpi:
    """KPI 5 : prix moyen pondéré €/MWh (calcul backend = cost/kwh × 1000)."""
    if (
        consumption_kpi.value is None
        or cost_kpi.value is None
        or not isinstance(consumption_kpi.value, (int, float))
        or not isinstance(cost_kpi.value, (int, float))
        or consumption_kpi.value <= 0
    ):
        return _kpi_inactive("weighted_price_eur_mwh", "Prix moyen pondéré", "€/MWh", scope, period)

    weighted = round(float(cost_kpi.value) / float(consumption_kpi.value) * 1000.0, 1)

    return EnergyKpi(
        key="weighted_price_eur_mwh",
        label="Prix moyen pondéré",
        value=weighted,
        unit="€/MWh",
        state="sain",
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="energy_orchestration.synthesis._kpi_weighted_price",
            formula="cost_eur / consumption_kwh × 1000",
            period=period,
            confidence=min(
                consumption_kpi.provenance.confidence,
                cost_kpi.provenance.confidence,
            ),
            assumptions=["dépend de la précision cost_eur (cf. assumptions cost_eur)"],
        ),
    )


def _kpi_data_quality(db: Session, scope: EnergyScope, period: EnergyPeriod) -> EnergyKpi:
    """KPI 6 : score qualité données (data_freshness_service)."""
    score: Optional[int] = None
    confidence = 0.0
    try:
        # MVP : utilise la couverture metered comme proxy si site
        if scope.kind == "site" and scope.id is not None:
            from models import Meter

            meter = db.query(Meter).filter_by(site_id=int(scope.id), is_active=True).first()
            if meter:
                from services.data_freshness_service import compute_meter_freshness

                result = compute_meter_freshness(db, meter.id, window_hours=period.days * 24)
                score = result.freshness_score
                confidence = result.coverage_pct / 100.0 if result.coverage_pct else 0.5
    except Exception:
        score = None

    if score is None:
        return _kpi_inactive("data_quality_score", "Qualité données", "/100", scope, period)

    score = clamp_score_0_100(score)
    state = (
        "sain"
        if score is not None and score >= 80
        else "vigilance"
        if score is not None and score >= 60
        else "critique"
    )

    return EnergyKpi(
        key="data_quality_score",
        label="Qualité données",
        value=score,
        unit="/100",
        state=state,  # type: ignore[arg-type]
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="data_freshness_service.compute_meter_freshness",
            formula="40×score_delai + 40×coverage + 20×quality (clamp [0,100])",
            period=period,
            confidence=confidence,
            assumptions=[
                "window = period.days × 24h",
                "score borné [0, 100] via score_utils.clamp_score_0_100",
            ],
        ),
    )


def _kpi_sites_coverage(db: Session, scope: EnergyScope, period: EnergyPeriod) -> EnergyKpi:
    """KPI 7 : couverture sites (n/N) avec data."""
    try:
        from services.consumption_unified_service import get_portfolio_consumption

        if scope.org_id is None:
            return _kpi_inactive("sites_coverage_pct", "Couverture sites", "%", scope, period)

        portfolio = get_portfolio_consumption(db, scope.org_id, period.start.date(), period.end.date())
        if not isinstance(portfolio, dict):
            return _kpi_inactive("sites_coverage_pct", "Couverture sites", "%", scope, period)

        coverage = portfolio.get("weighted_coverage_pct")
    except Exception:
        coverage = None

    if coverage is None:
        return _kpi_inactive("sites_coverage_pct", "Couverture sites", "%", scope, period)

    state = "sain" if coverage >= 90 else "vigilance" if coverage >= 60 else "critique"

    return EnergyKpi(
        key="sites_coverage_pct",
        label="Couverture sites",
        value=round(coverage, 1),
        unit="%",
        state=state,  # type: ignore[arg-type]
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="consumption_unified_service.get_portfolio_consumption",
            formula="% sites avec relevés sur période",
            period=period,
            confidence=0.9,
        ),
    )


def _kpi_alerts_and_actions(
    db: Session, scope: EnergyScope, period: EnergyPeriod
) -> tuple[EnergyKpi, EnergyKpi, EnergyKpi]:
    """KPI 8/9/10 : alertes ouvertes, actions ouvertes, estimated_impact_eur.

    `estimated_impact_eur` est AGRÉGÉ BACKEND ici pour retirer la dernière
    whitelist source-guard (reduce post-filtre scope FE).
    """
    alerts_open = 0
    actions_open = 0
    estimated_impact_eur = 0.0
    confidence = 0.5

    try:
        from models import ConsumptionInsight, ActionItem
        from models.enums import InsightStatus

        # Insights ouverts (proxy pour alerts/impact)
        query = db.query(ConsumptionInsight).filter(
            ConsumptionInsight.insight_status == InsightStatus.OPEN.value,
        )
        if scope.kind == "site" and scope.id is not None:
            query = query.filter(ConsumptionInsight.site_id == int(scope.id))
        elif scope.org_id is not None:
            # Org-scope via sites joins
            from models import Site

            site_ids = [s.id for s in db.query(Site).filter(Site.organisation_id == scope.org_id).all()]
            if site_ids:
                query = query.filter(ConsumptionInsight.site_id.in_(site_ids))

        insights = query.all()
        alerts_open = len(insights)
        estimated_impact_eur = round(sum(i.estimated_loss_eur or 0 for i in insights), 2)

        # Actions ouvertes
        try:
            actions_q = db.query(ActionItem).filter(ActionItem.statut.in_(["open", "in_progress"]))
            if scope.kind == "site" and scope.id is not None:
                actions_q = actions_q.filter(ActionItem.site_id == int(scope.id))
            actions_open = actions_q.count()
        except Exception:
            actions_open = 0

        confidence = 0.9
    except Exception:
        confidence = 0.3

    kpi_alerts = EnergyKpi(
        key="alerts_open",
        label="Alertes ouvertes",
        value=alerts_open,
        unit="count",
        state="sain" if alerts_open == 0 else "vigilance" if alerts_open < 3 else "critique",
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="ConsumptionInsight (org/site scope filter)",
            formula="count(ConsumptionInsight WHERE insight_status='open' AND scope)",
            period=period,
            confidence=confidence,
        ),
    )

    kpi_actions = EnergyKpi(
        key="actions_open",
        label="Actions ouvertes",
        value=actions_open,
        unit="count",
        state="sain" if actions_open == 0 else "vigilance",
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="ActionItem (Centre d'Action V4)",
            formula="count(ActionItem WHERE statut IN ('open','in_progress'))",
            period=period,
            confidence=confidence,
        ),
    )

    kpi_impact = EnergyKpi(
        key="estimated_impact_eur",
        label="Impact financier estimé",
        value=estimated_impact_eur,
        unit="€",
        state=("sain" if estimated_impact_eur == 0 else "vigilance" if estimated_impact_eur < 5000 else "critique"),
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service="ConsumptionInsight.estimated_loss_eur (org/site scope filter)",
            formula="Σ insights.estimated_loss_eur WHERE status='open' AND scope",
            period=period,
            confidence=confidence,
            assumptions=[
                "agrégation pré-calculée backend post-filtre scope (retire dette whitelist FE reduce post-scope)"
            ],
        ),
    )
    return kpi_alerts, kpi_actions, kpi_impact


# ── Orchestration principale ──────────────────────────────────────────


def build_synthesis(
    db: Session,
    *,
    scope_kind: str,
    scope_id: Optional[int],
    org_id: Optional[int],
    period_label: str = "30d",
    compare: str = "none",
    now: Optional[datetime] = None,
) -> EnergySynthesisResponse:
    """Compose la vue Synthèse 30 secondes (10 KPI + narrative + provenance).

    Args:
        db : session SQLAlchemy.
        scope_kind : 'org' | 'portfolio' | 'site'.
        scope_id : id du scope (site_id, portfolio_id, org_id selon kind).
        org_id : id organisation pour scope_utils (toujours requis pour
            agrégations multi-sites).
        period_label : '7d' | '30d' | '90d' | '12m' | 'ytd'.
        compare : 'none' | 'n-1' | 'baseline' | 'contract'.

    Returns:
        EnergySynthesisResponse avec 10 KPI + recommendations + narrative
        + provenance globale.
    """
    period = resolve_period(period_label, now=now)
    scope = EnergyScope(
        kind=scope_kind,  # type: ignore[arg-type]
        id=scope_id,
        org_id=org_id,
        label=None,
    )

    # KPI 1 : consommation
    kpi_consumption = _kpi_consumption_kwh(db, scope, period)
    # KPI 2 : coût
    kpi_cost = _kpi_cost_eur(db, scope, period)
    # KPI 3 : CO₂
    kpi_co2 = _kpi_co2_kg(db, scope, period, kpi_consumption)
    # KPI 4 : puissance max
    kpi_peak = _kpi_peak_kw(db, scope, period)
    # KPI 5 : prix moyen pondéré
    kpi_weighted = _kpi_weighted_price(kpi_consumption, kpi_cost, scope, period)
    # KPI 6 : qualité données
    kpi_quality = _kpi_data_quality(db, scope, period)
    # KPI 7 : couverture sites
    kpi_coverage = _kpi_sites_coverage(db, scope, period)
    # KPI 8, 9, 10 : alerts / actions / impact (impact agrégé backend !)
    kpi_alerts, kpi_actions, kpi_impact = _kpi_alerts_and_actions(db, scope, period)

    kpis = {
        kpi.key: kpi
        for kpi in (
            kpi_consumption,
            kpi_cost,
            kpi_co2,
            kpi_peak,
            kpi_weighted,
            kpi_quality,
            kpi_coverage,
            kpi_alerts,
            kpi_actions,
            kpi_impact,
        )
    }

    narrative = _build_narrative(kpis)

    return EnergySynthesisResponse(
        scope=scope,
        period=period,
        compare=compare,  # type: ignore[arg-type]
        kpis=kpis,
        recommendations=[],
        narrative=narrative,
        warnings=[],
        provenance=_build_provenance(
            service="energy_orchestration.synthesis.build_synthesis",
            formula="orchestration 10 KPI (cf. provenance individuelles)",
            period=period,
            confidence=1.0,
            assumptions=[
                "estimated_impact_eur agrégé backend post-filtre scope",
                "tous les scores bornés [0, 100] via score_utils",
                "timezone Europe/Paris",
            ],
        ),
    )


def _build_narrative(kpis: dict[str, EnergyKpi]) -> str:
    """Construit un briefing 2-3 phrases Sol §5 à partir des KPI."""
    alerts = kpis.get("alerts_open")
    actions = kpis.get("actions_open")
    impact = kpis.get("estimated_impact_eur")

    n_alerts = alerts.value if alerts and isinstance(alerts.value, int) else 0
    n_actions = actions.value if actions and isinstance(actions.value, int) else 0
    impact_eur = impact.value if impact and isinstance(impact.value, (int, float)) else 0

    if n_alerts == 0 and n_actions == 0:
        return (
            "Aucune alerte active sur votre patrimoine — hygiène énergétique "
            "satisfaisante sur la période. Maintenez la veille."
        )
    parts = []
    if n_alerts > 0:
        parts.append(f"{n_alerts} alerte(s) active(s) sur votre patrimoine")
    if n_actions > 0:
        parts.append(f"{n_actions} action(s) à programmer")
    msg = " — ".join(parts) + "."
    if impact_eur > 0:
        msg += f" Impact estimé {round(impact_eur)} € récupérables par correction."
    return msg
