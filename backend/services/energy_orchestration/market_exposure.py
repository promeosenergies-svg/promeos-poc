"""
PROMEOS — Service orchestration Marché & Exposition (Sprint P1.S2d).

Compose les SoT existants pour expliquer si le profil réel de
consommation d'un site est exposé aux heures chères du marché spot.

Doctrine produit :
- Aucune économie présentée comme certaine.
- Toute hypothèse est documentée (provenance + assumptions).
- Modèle MktPrice canonique uniquement (pas le legacy `market_prices`).
- Timezone Europe/Paris stricte.

SoT composés :
- MktPrice (table mkt_prices) — prix spot day-ahead / forwards.
- consumption_granularity_service.get_org_hourly_curve_kw — courbe
  horaire kWh par site.
- compute_quantiles — identification top 10 % prix coûts.

Règles métier :
- spot_cost_eur = kWh × spot_price_eur_mwh / 1000
- spot_avg_simple_eur_mwh = mean(spot_price)
- spot_avg_weighted_eur_mwh = Σ(kWh × prix) / Σ(kWh)
- baseload_kwh_per_hour = total_kwh / nombre_heures
- baseload_cost_eur = Σ(baseload_kwh_per_hour × spot_price / 1000)
- delta_vs_baseload_eur = real_profile_cost_eur - baseload_cost_eur
- top_10pct_expensive_hours = heures dont le coût (kwh × prix) est
  au-dessus du Q90 (méthode `compute_quantiles` SoT canonique).
- exposure_score borné [0, 100] via `clamp_score_0_100`.
- prix négatifs : spot_price_eur_mwh < 0.
"""

from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from schemas.energy_orchestration import (
    EnergyBaseloadComparison,
    EnergyDisplacementSimulation,
    EnergyExpensiveHour,
    EnergyFavorableHour,
    EnergyKpi,
    EnergyMarketContext,
    EnergyMarketExposureKpis,
    EnergyMarketExposurePoint,
    EnergyMarketExposureResponse,
    EnergyPeriod,
    EnergyScope,
)
from services.electric_monitoring.score_utils import clamp_score_0_100
from services.energy_orchestration.synthesis import _build_provenance, resolve_period


TZ_PARIS = ZoneInfo("Europe/Paris")


_VALID_MARKETS = {"day_ahead", "intraday", "future_baseload", "future_peakload"}
_VALID_ZONES = {"FR", "DE_LU", "BE", "ES", "NL", "GB", "CH", "IT_NORTH"}


class MarketExposureError(Exception):
    """Erreur fonctionnelle market-exposure (mappée HTTP 400)."""

    def __init__(self, message: str, hint: Optional[str] = None, *, http_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.http_code = http_code


# ── KPI helper ─────────────────────────────────────────────────────────


def _kpi(
    key: str,
    label: str,
    value,
    unit: str,
    scope: EnergyScope,
    period: EnergyPeriod,
    *,
    formula: str,
    confidence: float = 0.8,
    assumptions: Optional[list[str]] = None,
    state: Optional[str] = None,
) -> EnergyKpi:
    kpi_state = state if state else ("inactif" if value is None else "sain")
    return EnergyKpi(
        key=key,
        label=label,
        value=value,
        unit=unit,  # type: ignore[arg-type]
        state=kpi_state,  # type: ignore[arg-type]
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service=f"energy_orchestration.market_exposure._kpi ({key})",
            formula=formula,
            period=period,
            confidence=confidence if value is not None else 0.0,
            assumptions=assumptions or [],
        ),
    )


# ── Récupération données ──────────────────────────────────────────────


def _load_hourly_consumption(db: Session, scope: EnergyScope, period: EnergyPeriod) -> dict[datetime, float]:
    """Retourne la courbe horaire kWh par site sur la période.

    MVP : on agrège sur le dernier jour de la période (limitation du
    SoT `get_org_hourly_curve_kw`). Extension multi-jours prévue P1.S3.
    """
    if scope.kind not in ("site", "meter") or scope.id is None:
        return {}
    try:
        from services.consumption_granularity_service import get_org_hourly_curve_kw

        # MVP : récupère courbe horaire du dernier jour disponible.
        ref_day = period.end.date() if hasattr(period.end, "date") else period.end
        curve = get_org_hourly_curve_kw(db, scope.org_id, ref_day)
        out: dict[datetime, float] = {}
        for point in curve or []:
            kw = point.get("kw")
            if kw is None:
                continue
            hour = int(point.get("hour", 0))
            ts = datetime.combine(ref_day, datetime.min.time()).replace(tzinfo=TZ_PARIS, hour=hour)
            # 1 kW moyen sur 1h = 1 kWh
            out[ts] = float(kw)
        return out
    except Exception:
        return {}


def _load_spot_prices(
    db: Session, market_type: str, zone: str, start: datetime, end: datetime
) -> dict[datetime, float]:
    """Charge les prix MktPrice canonique sur la période.

    Returns:
        dict {delivery_start (Europe/Paris) → price_eur_mwh}
    """
    try:
        from models.market_models import MktPrice

        rows = (
            db.query(MktPrice.delivery_start, MktPrice.price_eur_mwh)
            .filter(
                MktPrice.delivery_start >= start.replace(tzinfo=None),
                MktPrice.delivery_start <= end.replace(tzinfo=None),
            )
            .all()
        )
        out: dict[datetime, float] = {}
        for r in rows:
            ts = r.delivery_start
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=TZ_PARIS)
            out[ts] = float(r.price_eur_mwh)
        return out
    except Exception:
        return {}


# ── Calculs marché ────────────────────────────────────────────────────


def _compute_spot_cost(kwh: float, price_eur_mwh: float) -> float:
    """Règle métier centrale : kWh × €/MWh / 1000 = €."""
    return round(kwh * price_eur_mwh / 1000.0, 4)


def _compute_baseload_comparison(
    series: list[EnergyMarketExposurePoint],
    period: EnergyPeriod,
    scope: EnergyScope,
) -> Optional[EnergyBaseloadComparison]:
    """Calcule le coût d'un profil plat équivalent vs le profil réel."""
    valid = [p for p in series if p.kwh is not None and p.spot_price_eur_mwh is not None]
    if not valid:
        return None
    total_kwh = sum(p.kwh for p in valid)
    n_hours = len(valid)
    if total_kwh <= 0 or n_hours <= 0:
        return None

    real_cost = round(sum(_compute_spot_cost(p.kwh, p.spot_price_eur_mwh) for p in valid), 2)
    baseload_kwh_per_hour = total_kwh / n_hours
    baseload_cost = round(
        sum(_compute_spot_cost(baseload_kwh_per_hour, p.spot_price_eur_mwh) for p in valid),
        2,
    )
    delta = round(real_cost - baseload_cost, 2)
    delta_eur_mwh = round((delta / (total_kwh / 1000.0)), 2) if total_kwh > 0 else None

    return EnergyBaseloadComparison(
        real_profile_cost_eur=real_cost,
        baseload_cost_eur=baseload_cost,
        delta_eur=delta,
        delta_eur_mwh=delta_eur_mwh,
        formula="comparaison coût spot pondéré réel vs consommation plate équivalente",
        provenance=_build_provenance(
            service="energy_orchestration.market_exposure._compute_baseload_comparison",
            formula="Σ(kwh_i × spot_i / 1000) vs Σ(baseload × spot_i / 1000)",
            period=period,
            confidence=0.9,
            assumptions=[
                f"baseload_kwh_per_hour = total_kwh / {n_hours}h",
                "delta_eur > 0 = profil plus coûteux que ruban",
            ],
        ),
    )


def _compute_top_expensive_hours(
    series: list[EnergyMarketExposurePoint],
    period: EnergyPeriod,
) -> tuple[list[EnergyExpensiveHour], Optional[float]]:
    """Identifie les heures top 10 % les plus coûteuses (Σ kwh × prix).

    Returns:
        (top_hours, top_10pct_cost_pct)
    """
    valid = [
        p for p in series if p.kwh is not None and p.spot_price_eur_mwh is not None and p.spot_cost_eur is not None
    ]
    if not valid:
        return [], None

    from services.consumption_granularity_service import compute_quantiles

    costs = [p.spot_cost_eur for p in valid]
    qs = compute_quantiles(costs, qs=[0.9])
    threshold = qs.get("p90")
    if threshold is None:
        return [], None

    above = [p for p in valid if p.spot_cost_eur >= threshold]
    above.sort(key=lambda p: p.spot_cost_eur, reverse=True)

    total_cost = sum(p.spot_cost_eur for p in valid)
    top_cost = sum(p.spot_cost_eur for p in above)
    top_share_pct = round(top_cost / total_cost * 100, 1) if total_cost > 0 else None

    out: list[EnergyExpensiveHour] = []
    for rank, p in enumerate(above[:24], start=1):  # cap soft à 24 entrées
        # Marquer dans la série originale
        p.is_top_expensive_hour = True
        out.append(
            EnergyExpensiveHour(
                timestamp=p.timestamp,
                spot_price_eur_mwh=p.spot_price_eur_mwh,
                kwh=p.kwh,
                cost_eur=p.spot_cost_eur,
                rank=rank,
                recommended_action="Analyser les usages pilotables sur cette plage horaire",
                provenance=_build_provenance(
                    service="energy_orchestration.market_exposure._compute_top_expensive_hours",
                    formula=f"spot_cost ≥ Q90 (Q90={threshold})",
                    period=period,
                    confidence=0.85,
                    assumptions=[
                        "méthode : quantile linéaire (compute_quantiles SoT)",
                        "seuil = P90 des coûts horaires",
                    ],
                ),
            )
        )
    return out, top_share_pct


def _compute_favorable_hours(
    series: list[EnergyMarketExposurePoint],
    period: EnergyPeriod,
) -> tuple[list[EnergyFavorableHour], Optional[float]]:
    """Identifie heures favorables (prix bas / négatifs / solaires).

    Returns:
        (favorable_hours, negative_price_consumption_pct)
    """
    valid = [p for p in series if p.spot_price_eur_mwh is not None]
    if not valid:
        return [], None

    # Prix négatifs (priorité haute pour la liste)
    negatives = [p for p in valid if p.spot_price_eur_mwh < 0]

    # Prix bas : sous le Q10
    out_list: list[EnergyFavorableHour] = []
    try:
        from services.consumption_granularity_service import compute_quantiles

        prices = [p.spot_price_eur_mwh for p in valid]
        qs = compute_quantiles(prices, qs=[0.1])
        q10 = qs.get("p10")
        low_price = [p for p in valid if q10 is not None and p.spot_price_eur_mwh <= q10]
    except Exception:
        q10 = None
        low_price = []

    def _provenance(reason_label: str) -> object:
        return _build_provenance(
            service="energy_orchestration.market_exposure._compute_favorable_hours",
            formula=f"prix favorable ({reason_label})",
            period=period,
            confidence=0.8,
            assumptions=[
                f"seuil prix bas = Q10 ({q10})",
                "prix négatif = spot_price_eur_mwh < 0",
            ],
        )

    # Prix négatifs en premier (top 12)
    for p in negatives[:12]:
        p.is_negative_price = True
        out_list.append(
            EnergyFavorableHour(
                timestamp=p.timestamp,
                spot_price_eur_mwh=p.spot_price_eur_mwh,
                kwh=p.kwh,
                reason="prix négatif",
                provenance=_provenance("prix négatif"),
            )
        )

    # Prix bas (Q10) — exclure ceux déjà comptés en négatifs
    counted = {p.timestamp for p in negatives}
    for p in sorted(low_price, key=lambda x: x.spot_price_eur_mwh)[:12]:
        if p.timestamp in counted:
            continue
        out_list.append(
            EnergyFavorableHour(
                timestamp=p.timestamp,
                spot_price_eur_mwh=p.spot_price_eur_mwh,
                kwh=p.kwh,
                reason="prix bas",
                provenance=_provenance("prix bas"),
            )
        )

    # Calcul du % consommation pendant prix négatif
    valid_with_kwh = [p for p in valid if p.kwh is not None]
    total_kwh = sum(p.kwh for p in valid_with_kwh) if valid_with_kwh else 0
    neg_kwh = sum(p.kwh for p in valid_with_kwh if p.spot_price_eur_mwh < 0)
    neg_pct = round(neg_kwh / total_kwh * 100, 2) if total_kwh > 0 else None

    return out_list, neg_pct


def _compute_exposure_score(
    spot_avg_simple: Optional[float],
    spot_avg_weighted: Optional[float],
    delta_vs_baseload_eur: Optional[float],
    top_share_pct: Optional[float],
) -> Optional[int]:
    """Calcule un score d'exposition borné [0, 100].

    Méthode :
    - 50 pts : top_10pct_cost_pct (les heures top 10 % génèrent X % du coût).
      Si X = 10 % (parfaitement équilibré) → 0 pts ; X = 50 % → 50 pts.
    - 30 pts : ratio prix pondéré / prix simple (>1 = exposé aux heures chères).
    - 20 pts : delta_vs_baseload_eur normalisé (signe + valeur).

    Tous les sous-scores tolèrent None (ignorés).
    """
    parts: list[float] = []

    if top_share_pct is not None:
        # 10 % attendu, on map [10..100] → [0..50]
        extra = max(0.0, top_share_pct - 10.0)
        parts.append(min(50.0, extra / 1.8))  # 100 % → 50 pts

    if spot_avg_simple and spot_avg_weighted:
        ratio = spot_avg_weighted / spot_avg_simple
        # 1.0 = neutre. Map [1.0..1.4] → [0..30]
        parts.append(min(30.0, max(0.0, (ratio - 1.0) * 75.0)))

    if delta_vs_baseload_eur is not None:
        # Positif = profil + coûteux que baseload. Normalisé brut.
        parts.append(min(20.0, max(0.0, delta_vs_baseload_eur / 100.0)))

    if not parts:
        return None
    return clamp_score_0_100(sum(parts), preserve_none=False)


# ── Orchestration principale ──────────────────────────────────────────


def build_market_exposure(
    db: Session,
    *,
    scope_kind: str,
    scope_id: Optional[int],
    org_id: Optional[int],
    period_label: str = "12m",
    market: str = "day_ahead",
    zone: str = "FR",
    baseload: bool = True,
    now: Optional[datetime] = None,
) -> EnergyMarketExposureResponse:
    """Compose la vue Marché & exposition."""

    if scope_kind not in ("site", "meter"):
        raise MarketExposureError(
            f"scope_kind '{scope_kind}' non supporté pour market-exposure",
            hint="utiliser scope='site' ou scope='meter'",
        )
    if scope_id is None:
        raise MarketExposureError(
            "scope_id obligatoire pour market-exposure",
            hint=f"fournir scope_id={scope_kind}_id pour cibler le profil",
        )
    if market not in _VALID_MARKETS:
        raise MarketExposureError(
            f"market '{market}' inconnu",
            hint=f"valeurs autorisées : {sorted(_VALID_MARKETS)}",
        )
    if zone not in _VALID_ZONES:
        raise MarketExposureError(
            f"zone '{zone}' inconnue",
            hint=f"valeurs autorisées : {sorted(_VALID_ZONES)}",
        )

    period = resolve_period(period_label, now=now)
    scope = EnergyScope(
        kind=scope_kind,  # type: ignore[arg-type]
        id=scope_id,
        org_id=org_id,
    )

    # 1. Charger consommation horaire + prix spot
    consumption = _load_hourly_consumption(db, scope, period)
    prices = _load_spot_prices(db, market, zone, period.start, period.end)

    warnings: list[str] = []
    empty_state: Optional[str] = None

    # Brief PHASE 3 : empty_state ciblé selon la cause
    has_consumption = bool(consumption)
    has_prices = bool(prices)
    if not has_consumption and not has_prices:
        empty_state = (
            "Aucune consommation et aucun prix marché disponibles sur la période. "
            "Vérifier la connexion compteur et l'ingestion MktPrice."
        )
    elif not has_consumption:
        empty_state = "Aucune consommation disponible sur la période."
    elif not has_prices:
        empty_state = "Aucun prix marché disponible sur la période."

    # 2. Construire la série superposée
    series: list[EnergyMarketExposurePoint] = []
    aligned_ts = sorted(set(consumption.keys()) & set(prices.keys()))
    if has_consumption and has_prices and not aligned_ts:
        warnings.append("Consommation et prix présents mais non alignés temporellement — série vide.")

    for ts in aligned_ts:
        kwh = consumption.get(ts)
        price = prices.get(ts)
        cost = _compute_spot_cost(kwh, price) if kwh is not None and price is not None else None
        series.append(
            EnergyMarketExposurePoint(
                timestamp=ts,
                kwh=kwh,
                kw_avg=kwh,  # 1 kWh sur 1 h ≡ 1 kW moyen
                spot_price_eur_mwh=price,
                spot_cost_eur=cost,
                is_top_expensive_hour=False,
                is_negative_price=False,
                quality_status="measured",
            )
        )

    # 3. KPIs marché
    valid_series = [p for p in series if p.kwh is not None and p.spot_price_eur_mwh is not None]
    total_kwh = sum(p.kwh for p in valid_series) if valid_series else 0.0
    spot_cost_total = round(sum(p.spot_cost_eur for p in valid_series), 2) if valid_series else None

    # Moyenne simple sur la série prix
    prices_only = [p.spot_price_eur_mwh for p in series if p.spot_price_eur_mwh is not None]
    spot_avg_simple = round(statistics.mean(prices_only), 2) if prices_only else None

    # Moyenne pondérée par la consommation (null si kwh=0 — pas de div/0)
    if total_kwh > 0 and spot_cost_total is not None:
        spot_avg_weighted = round(spot_cost_total / total_kwh * 1000.0, 2)
    else:
        spot_avg_weighted = None

    # 4. Comparaison baseload
    baseload_comp = _compute_baseload_comparison(series, period, scope) if baseload else None

    # 5. Top expensive hours + favorable hours
    top_hours, top_share_pct = _compute_top_expensive_hours(series, period)
    favorable, neg_pct = _compute_favorable_hours(series, period)

    # 6. Score d'exposition
    exposure_score = _compute_exposure_score(
        spot_avg_simple,
        spot_avg_weighted,
        baseload_comp.delta_eur if baseload_comp else None,
        top_share_pct,
    )

    # 7. KPIs
    kpis = EnergyMarketExposureKpis(
        spot_cost_theoretical_eur=_kpi(
            "spot_cost_theoretical_eur",
            "Coût spot théorique",
            spot_cost_total,
            "€",
            scope,
            period,
            formula="Σ(kwh_i × spot_i / 1000)",
            confidence=0.9,
            assumptions=["valorisation 100 % spot, hors taxes/TURPE"],
        ),
        spot_avg_simple_eur_mwh=_kpi(
            "spot_avg_simple_eur_mwh",
            "Spot moyen (simple)",
            spot_avg_simple,
            "€/MWh",
            scope,
            period,
            formula="mean(spot_price_eur_mwh) sur série",
            confidence=0.95,
        ),
        spot_avg_weighted_eur_mwh=_kpi(
            "spot_avg_weighted_eur_mwh",
            "Spot moyen pondéré conso",
            spot_avg_weighted,
            "€/MWh",
            scope,
            period,
            formula="Σ(kwh × prix) / Σ(kwh) × 1000",
            confidence=0.9,
            assumptions=["null si total_kwh = 0 (pas de division par zéro)"],
        ),
        baseload_cost_eur=_kpi(
            "baseload_cost_eur",
            "Coût ruban baseload",
            baseload_comp.baseload_cost_eur if baseload_comp else None,
            "€",
            scope,
            period,
            formula="Σ((total_kwh / n_hours) × spot_i / 1000)",
            confidence=0.9 if baseload_comp else 0.0,
        ),
        delta_vs_baseload_eur=_kpi(
            "delta_vs_baseload_eur",
            "Δ profil vs baseload",
            baseload_comp.delta_eur if baseload_comp else None,
            "€",
            scope,
            period,
            formula="real_profile_cost_eur - baseload_cost_eur",
            confidence=0.9 if baseload_comp else 0.0,
            assumptions=[">0 = profil plus coûteux que ruban équivalent"],
        ),
        top_10pct_expensive_hours_cost_pct=_kpi(
            "top_10pct_expensive_hours_cost_pct",
            "Part coût top 10 % heures chères",
            top_share_pct,
            "%",
            scope,
            period,
            formula="Σ coût(heures > Q90) / coût total × 100",
            confidence=0.85,
            assumptions=["méthode : quantile Q90 via compute_quantiles"],
        ),
        negative_price_consumption_pct=_kpi(
            "negative_price_consumption_pct",
            "Part conso pendant prix négatifs",
            neg_pct,
            "%",
            scope,
            period,
            formula="Σ kwh(prix<0) / Σ kwh × 100",
            confidence=0.95,
        ),
        exposure_score=_kpi(
            "exposure_score",
            "Score exposition marché",
            exposure_score,
            "/100",
            scope,
            period,
            formula="50 × top_share + 30 × ratio_pondéré + 20 × delta_baseload (clampé [0, 100])",
            confidence=0.7,
            assumptions=[
                "score borné [0, 100] via score_utils.clamp_score_0_100",
                "≥ 60 = vigilance ; ≥ 80 = critique",
            ],
            state=(
                "inactif"
                if exposure_score is None
                else "sain"
                if exposure_score < 60
                else "vigilance"
                if exposure_score < 80
                else "critique"
            ),
        ),
    )

    # 8. Simulation indicative
    simulation = EnergyDisplacementSimulation(
        label="Déplacement indicatif",
        flexible_share_pct=20.0,
        estimated_delta_eur=None,  # non engageant — calcul détaillé reporté
        warning="Simulation indicative — ne constitue pas une promesse d'économie.",
        provenance=_build_provenance(
            service="energy_orchestration.market_exposure.build_market_exposure",
            formula="ratio fixe 20 % de la conso flexible — pas de chiffrage € sans validation acheteur",
            period=period,
            confidence=0.3,
            assumptions=[
                "Doctrine PROMEOS : aucune économie présentée comme certaine",
                "Hypothèse 20 % charge flexible — à valider avec audit usages",
            ],
        ),
    )

    # 9. Contexte marché
    market_ctx = EnergyMarketContext(
        type=market,  # type: ignore[arg-type]
        zone=zone,  # type: ignore[arg-type]
        source="MktPrice canonique (mkt_prices)",
        price_unit="€/MWh",
        provenance=_build_provenance(
            service="MktPrice (models.market_models)",
            formula=f"SELECT * WHERE market_type='{market}' AND zone='{zone}' AND delivery_start ∈ [period]",
            period=period,
            confidence=0.95 if has_prices else 0.0,
            assumptions=[
                "modèle canonique MktPrice (table mkt_prices)",
                "MarketPrice legacy interdit (source-guard market_price_canonical)",
            ],
        ),
    )

    provenance = _build_provenance(
        service="energy_orchestration.market_exposure.build_market_exposure",
        formula="orchestration KPI marché + série superposée + top/favorable hours + baseload comparison",
        period=period,
        confidence=0.7 if valid_series else 0.0,
        assumptions=[
            "timezone Europe/Paris",
            "spot_cost = kWh × €/MWh / 1000",
            "all simulations are indicative — no guaranteed savings",
        ],
    )

    return EnergyMarketExposureResponse(
        scope=scope,
        period=period,
        market=market_ctx,
        kpis=kpis,
        series=series,
        top_expensive_hours=top_hours,
        favorable_hours=favorable,
        baseload_comparison=baseload_comp,
        simulation=simulation,
        warnings=warnings,
        empty_state=empty_state,
        provenance=provenance,
    )
