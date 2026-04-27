"""Détecteur `flex_opportunity` — chantier α Vague C ét13a (P0 VC Sarah Sequoia).

Doctrine §10 event_type `flex_opportunity` : émet un événement quand le
portefeuille présente un potentiel d'effacement (NEBCO post-ARENH, AOFD,
Tempo HC) chiffrable et actionnable.

Différenciant Series A : aucun concurrent (Metron/Tilt/Sobry/Deepki/
HelloWatt) n'expose le potentiel flex en grammaire CFO (€/an + payback +
NPV) avec routing owner Energy Manager. Sarah Sequoia P0 #3.

Réutilise SoT canonique `flex_nebco_service.compute_flex_portfolio`
(règle d'or détecteur §10 P3 « pas de SQL métier inline »). Pas de
NaN/None propagé : les sites sans données NEBCO sont skippés en amont.

Pattern mitigation EventImpact (cohérent ét12d/e) :
- impact.value = revenu mid estimé €/an (NEBCO + capacité)
- mitigation.capex_eur = coût BACS unlock si déverrouillage requis
- mitigation.payback_months = ROI portefeuille observé (si positif)
- mitigation.npv_eur = revenu × horizon - CAPEX BACS (5 ans typique)

Seuils € EM/CFO mid-market (cohérents billing_anomaly + consumption_drift) :
- revenue >= 50 k€/an → critical (opportunité majeure)
- revenue >= 10 k€/an → warning
- revenue >= 2 k€/an → watch
- sinon : skip (densification SolWeekCards en fallback)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..freshness import compute_freshness
from ..types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventMitigation,
    EventSource,
    SolEventCard,
)

# Seuils CFO mid-market (cohérent billing_anomaly_detector ét12a).
_THRESHOLD_CRITICAL_EUR = 50_000.0
_THRESHOLD_WARNING_EUR = 10_000.0
_THRESHOLD_WATCH_EUR = 2_000.0

# Horizon NPV flex : amortissement BACS typique 5 ans (durée de vie GTB).
_FLEX_NPV_HORIZON_YEARS = 5


def _severity_for_revenue(revenue_eur: float) -> str | None:
    """Mappe revenu flex → severity doctrine §10."""
    if revenue_eur >= _THRESHOLD_CRITICAL_EUR:
        return "critical"
    if revenue_eur >= _THRESHOLD_WARNING_EUR:
        return "warning"
    if revenue_eur >= _THRESHOLD_WATCH_EUR:
        return "watch"
    return None


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 0..2 événements `flex_opportunity` selon potentiel portefeuille.

    Doctrine §10 « 6 questions » :
    - quel fait : N sites NEBCO-éligibles, X kW pilotables
    - quel périmètre : sites flex (linked_assets.site_ids)
    - quel impact : revenu € mid estimé / an + mitigation BACS si lock
    - quelle action : route /flex + owner Energy Manager
    - quelle source : NaTran/RTE NEBCO (synthétisé par flex_nebco_service)
    - quelle confiance : depuis volumétrie échantillon sites
    """
    # Imports locaux pour éviter cycle (services/flex → narrative → event_bus)
    from config.mitigation_loader import compute_npv_actualized  # WACC actualisé
    from services.flex_nebco_service import compute_flex_portfolio
    from services.narrative.narrative_generator import _load_org_context

    ctx = _load_org_context(db, org_id)
    site_ids = [s.id for s in ctx.sites]
    if not site_ids:
        return []

    portfolio = compute_flex_portfolio(db, site_ids)
    revenue_mid = float(portfolio.get("revenue_mid_eur") or 0)
    if revenue_mid <= 0:
        return []

    severity = _severity_for_revenue(revenue_mid)
    if severity is None:
        return []

    now = datetime.now(timezone.utc)
    flex_sites = [s.get("site_id") for s in portfolio.get("sites", []) if s.get("site_id")]
    nebco_count = int(portfolio.get("nebco_sites") or 0)
    total_kw = float(portfolio.get("total_kw") or 0)

    # Mitigation BACS unlock si verrouillage GTB détecté
    bacs = portfolio.get("bacs_portfolio") or {}
    bacs_capex = float(bacs.get("total_cost_eur") or 0)
    bacs_revenue_year = float(bacs.get("total_revenue_eur_year") or 0)
    bacs_roi_months = bacs.get("portfolio_roi_months")

    mitigation = None
    if bacs_capex > 0 and bacs_roi_months:
        # ét12g (audit CFO #2) : NPV actualisé via WACC YAML (formule annuité)
        # au lieu de revenue × N - capex (VAN nominale, surévaluée 35-40% sur 5 ans).
        npv_eur = compute_npv_actualized(
            annual_flow_eur=bacs_revenue_year,
            horizon_year=now.year + _FLEX_NPV_HORIZON_YEARS,
            capex_eur=bacs_capex,
            current_year=now.year,
        )
        mitigation = EventMitigation(
            capex_eur=bacs_capex,
            payback_months=int(bacs_roi_months),
            npv_eur=npv_eur,
            npv_horizon_year=now.year + _FLEX_NPV_HORIZON_YEARS,
        )

    # Confidence basée sur volumétrie (>=10 sites = high, >=3 = medium, sinon low)
    if len(flex_sites) >= 10:
        confidence = "high"
    elif len(flex_sites) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # Narrative éditoriale §5 (acronymes décodés, ton journal)
    title_prefix = (
        "Opportunité d'effacement majeure"
        if severity == "critical"
        else "Opportunité d'effacement à étudier"
        if severity == "warning"
        else "Potentiel d'effacement à surveiller"
    )
    nebco_phrase = (
        f" {nebco_count} site{'s' if nebco_count > 1 else ''} éligible{'s' if nebco_count > 1 else ''} "
        "au mécanisme NEBCO post-ARENH (effacement rémunéré par RTE)."
        if nebco_count > 0
        else ""
    )
    bacs_phrase = (
        f" Investissement GTB {int(bacs_capex / 1000)} k€ déverrouille "
        f"{int(bacs.get('total_kw_unlockable') or 0)} kW supplémentaires."
        if bacs_capex > 0
        else ""
    )

    return [
        SolEventCard(
            id=f"flex_opportunity:org:{org_id}:portfolio",
            event_type="flex_opportunity",
            severity=severity,  # type: ignore[arg-type]
            title=f"{title_prefix} : {int(total_kw)} kW pilotables",
            narrative=(
                f"Potentiel d'effacement portefeuille estimé à {int(revenue_mid):,} €/an "
                f"(rémunération mécanismes RTE).{nebco_phrase}{bacs_phrase}"
            ).replace(",", " "),  # FR : séparateur millier = espace
            impact=EventImpact(
                value=revenue_mid,
                unit="€",
                period="year",
                mitigation=mitigation,
            ),
            source=EventSource(
                system="benchmark",  # flex_nebco_service synthétise NaTran/RTE
                last_updated_at=now,
                confidence=confidence,  # type: ignore[arg-type]
                freshness_status=compute_freshness("benchmark", now, now=now),
                methodology=(
                    f"Potentiel calculé sur {len(flex_sites)} site{'s' if len(flex_sites) > 1 else ''} "
                    "via flex_nebco_service. Revenu mid = moyenne plage NEBCO "
                    "low/high RTE (rémunération effacement) + capacité 1/11/2026. "
                    "Mitigation BACS = coût GTB pour déverrouiller pilotage HVAC/froid/IRVE."
                ),
            ),
            action=EventAction(
                label="Voir les opportunités flex",
                route="/flex",
                owner_role="Energy Manager",
            ),
            linked_assets=EventLinkedAssets(
                org_id=org_id,
                site_ids=flex_sites,
            ),
        )
    ]
