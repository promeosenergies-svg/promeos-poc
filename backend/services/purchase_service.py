"""
PROMEOS — Achat Energie Service V1
Estimation conso, profil, scenarios fixe/indexe/spot/reflex_solar, recommandation.
V74: + RéFlex Solar (blocs horaires, report, effort opérationnel).
"""

import hashlib
import json as _json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from models import (
    SiteOperatingSchedule,
    PurchaseStrategy,
    Site,
    EntiteJuridique,
    Portefeuille,
    ContractAnnexe,
)
from models.billing_models import EnergyContract
from services.billing_service import get_reference_price
from services.purchase_pricing import get_market_context, compute_strategy_price
from services.contract_v2_service import resolve_pricing, PERIOD_WEIGHTS

# Fallback volume if no data found
DEFAULT_VOLUME_KWH_AN = 500_000

# ── Premium Garantie d'Origine (GO) ──
GREEN_PREMIUM_EUR_MWH = 2.5

# ── Explications par stratégie ──
STRATEGY_EXPLANATIONS = {
    "fixe": "Budget prévisible à 100 %. Aucune exposition marché. Idéal si la visibilité budgétaire prime.",
    "indexe": "Prix suit un indice marché avec plafond. Potentiel d'économie si les prix baissent, risque limité par le cap.",
    "spot": "Exposition directe au marché temps réel. Économies maximales en marché baissier, risque élevé en tension.",
    "reflex_solar": "Report de consommation vers les heures solaires (11h-16h) où le prix spot est souvent négatif. Nécessite une flexibilité des usages.",
}


def get_current_contract_price(db: Session, site_id: int) -> dict:
    """
    Récupère le prix réel du contrat actif pour un site via Contrats V2.
    Fallback sur la moyenne marché 12 mois si aucun contrat trouvé.
    """
    from datetime import date as _date

    try:
        # Chercher l'annexe active pour ce site
        annexe = (
            db.query(ContractAnnexe)
            .join(EnergyContract, ContractAnnexe.contrat_cadre_id == EnergyContract.id)
            .filter(
                ContractAnnexe.site_id == site_id,
                ContractAnnexe.status == "active",
            )
            .first()
        )

        if annexe:
            pricing_lines = resolve_pricing(db, annexe)
            if pricing_lines:
                # Calcul du prix moyen pondéré (PERIOD_WEIGHTS)
                total_weight = 0.0
                weighted_price = 0.0
                for line in pricing_lines:
                    price = line.get("unit_price_eur_kwh")
                    if price is None or price <= 0:
                        continue
                    period = line.get("period_code", "BASE")
                    w = PERIOD_WEIGHTS.get(period, 0.5)
                    weighted_price += price * w
                    total_weight += w

                if total_weight > 0:
                    avg_price_kwh = weighted_price / total_weight
                    # Construire le label avec fournisseur et date fin
                    cadre = annexe.contrat_cadre
                    supplier = cadre.supplier_name if cadre else "Fournisseur"
                    end_dt = annexe.end_date_override or (cadre.end_date if cadre else None)
                    exp_label = ""
                    if end_dt:
                        exp_label = f", exp. {end_dt.strftime('%m/%Y')}"

                    return {
                        "price_eur_mwh": round(avg_price_kwh * 1000, 2),
                        "price_eur_kwh": round(avg_price_kwh, 6),
                        "source": "contrat",
                        "label": f"vs votre contrat ({supplier}{exp_label})",
                    }
    except Exception as e:
        logger.warning("get_current_contract_price: erreur contrat V2 site=%d: %s", site_id, e)

    # Fallback: moyenne marché 12 mois
    try:
        market_ctx = get_market_context(db, "ELEC")
        market_avg = market_ctx.get("spot_avg_30d_eur_mwh", 80.0)
        return {
            "price_eur_mwh": round(market_avg, 2),
            "price_eur_kwh": round(market_avg / 1000, 6),
            "source": "marche",
            "label": "vs moyenne marché 12 mois",
        }
    except Exception:
        return {
            "price_eur_mwh": 80.0,
            "price_eur_kwh": 0.08,
            "source": "marche",
            "label": "vs moyenne marché 12 mois",
        }


def compute_budget_badge(total_eur: float, benchmark_eur: float) -> dict:
    """Badge contextuel budget vs benchmark."""
    ratio = total_eur / benchmark_eur if benchmark_eur > 0 else 1.0
    if ratio <= 0.95:
        return {"label": "Budget optimisé", "color": "green"}
    if ratio <= 1.10:
        return {"label": "Budget standard", "color": "amber"}
    return {"label": "Budget élevé", "color": "red"}


# ── Profile factor thresholds ──
PROFILE_FLAT_24_7 = 0.85  # Flat/constant load profile
PROFILE_PEAK = 1.25  # Peak business hours profile
PROFILE_DEFAULT = 1.0  # Standard profile


def estimate_consumption(db: Session, site_id: int) -> dict:
    """
    Estimate annual consumption for a site via unified consumption service.
    Single source of truth — replaces direct MeterReading/Invoice queries.
    """
    from datetime import date
    from services.consumption_unified_service import get_consumption_summary

    today = date.today()
    twelve_months_ago = today - timedelta(days=365)

    summary = get_consumption_summary(db, site_id, twelve_months_ago, today)
    value_kwh = summary.get("value_kwh", 0)
    source_used = summary.get("source_used", "estimated")
    coverage_pct = summary.get("coverage_pct", 0)
    details = summary.get("details", {})

    if value_kwh and value_kwh > 0:
        # Annualize if partial coverage
        if coverage_pct and coverage_pct < 95:
            period_days = summary.get("period", {}).get("days", 365)
            covered_days = period_days * (coverage_pct / 100)
            volume = value_kwh * (365 / covered_days) if covered_days > 0 else value_kwh
        else:
            volume = value_kwh

        # Map source to legacy format
        source_map = {"metered": "meter_readings", "billed": "invoices", "estimated": "default"}
        months_covered = max(
            details.get("metered_days", 0) // 30,
            details.get("billed_months", 0),
        )

        return {
            "volume_kwh_an": round(volume, 0),
            "source": source_map.get(source_used, "default"),
            "months_covered": months_covered,
        }

    # No data at all
    return {
        "volume_kwh_an": DEFAULT_VOLUME_KWH_AN,
        "source": "default",
        "months_covered": 0,
    }


def compute_profile_factor(db: Session, site_id: int) -> float:
    """
    Compute profile factor from SiteOperatingSchedule.
    >1 = peak profile (higher spot cost), <1 = flat profile.
    """
    schedule = db.query(SiteOperatingSchedule).filter(SiteOperatingSchedule.site_id == site_id).first()
    if not schedule:
        return 1.0

    if schedule.is_24_7:
        return PROFILE_FLAT_24_7

    # Standard business hours (8h-19h weekdays) → peak profile
    if schedule.open_time <= "08:00" and schedule.close_time >= "19:00":
        return PROFILE_PEAK

    return PROFILE_DEFAULT


# ══════════════════════════════════════
# V74 — RéFlex Solar: blocs horaires
# ══════════════════════════════════════

REFLEX_BLOCS = {
    "solaire_ete_semaine": {"months": [4, 5, 6, 7, 8, 9], "weekday": True, "hours": (13, 16), "price_mult": 0.72},
    "solaire_ete_weekend": {"months": [4, 5, 6, 7, 8, 9], "weekday": False, "hours": (10, 17), "price_mult": 0.68},
    "pointe_hiver_matin": {"months": [1, 2, 3, 10, 11, 12], "weekday": True, "hours": (8, 10), "price_mult": 1.25},
    "pointe_hiver_soir": {"months": [1, 2, 3, 10, 11, 12], "weekday": True, "hours": (17, 20), "price_mult": 1.25},
    "hc": {"months": list(range(1, 13)), "weekday": None, "hours": (0, 6), "price_mult": 0.80},
    "hp": {"months": list(range(1, 13)), "weekday": None, "hours": (6, 22), "price_mult": 1.00},
}

# Weight of each bloc in total volume (simplified annual distribution)
REFLEX_BLOC_WEIGHTS = {
    "solaire_ete_semaine": 0.08,
    "solaire_ete_weekend": 0.04,
    "pointe_hiver_matin": 0.06,
    "pointe_hiver_soir": 0.06,
    "hc": 0.25,
    "hp": 0.51,
}


def compute_reflex_scenario(
    ref_price: float,
    volume_kwh_an: float,
    profile_factor: float,
    price_source: str,
    report_pct: float = 0.0,
) -> dict:
    """
    Compute RéFlex Solar scenario: weighted sum of blocs horaires.
    report_pct: fraction of HP volume shifted to solaire_ete (0.0=sans report, e.g. 0.15=15%).
    """
    blocs_detail = []
    total_eur = 0.0

    # Apply report: shift report_pct of HP volume to solaire_ete_semaine
    weights = dict(REFLEX_BLOC_WEIGHTS)
    if report_pct > 0:
        shift = min(report_pct * weights["hp"], weights["hp"])
        weights["hp"] -= shift
        weights["solaire_ete_semaine"] += shift

    for bloc_name, bloc in REFLEX_BLOCS.items():
        w = weights.get(bloc_name, 0)
        bloc_kwh = volume_kwh_an * w
        bloc_price = round(ref_price * bloc["price_mult"], 4)
        bloc_cost = round(bloc_price * bloc_kwh, 2)
        total_eur += bloc_cost
        blocs_detail.append(
            {
                "bloc": bloc_name,
                "weight_pct": round(w * 100, 1),
                "kwh": round(bloc_kwh, 0),
                "price_eur_kwh": bloc_price,
                "cost_eur": bloc_cost,
                "hours": list(bloc["hours"]),
            }
        )

    avg_price = round(total_eur / volume_kwh_an, 4) if volume_kwh_an > 0 else 0
    total_eur = round(total_eur, 2)

    # Effort opérationnel: report requires operational changes
    effort_score = 20 if report_pct == 0 else min(80, 20 + int(report_pct * 400))

    return {
        "strategy": PurchaseStrategy.REFLEX_SOLAR.value,
        "price_eur_per_kwh": avg_price,
        "total_annual_eur": total_eur,
        "risk_score": 40,
        "p10_eur": round(total_eur * 0.82, 2),
        "p90_eur": round(total_eur * 1.18, 2),
        "ref_price": ref_price,
        "ref_price_source": price_source,
        "effort_score": effort_score,
        "report_pct": round(report_pct * 100, 1),
        "blocs": blocs_detail,
    }


def compute_scenarios(
    db: Session,
    site_id: int,
    volume_kwh_an: float,
    profile_factor: float = 1.0,
    energy_type: str = "elec",
    report_pct: float = 0.0,
    horizon_months: int = 12,
    green_preference: bool = False,
) -> list:
    """
    Generate 4 purchase scenarios: Fixe, Indexe, Spot, RéFlex Solar.
    Uses market-based pricing from purchase_pricing engine.
    report_pct: fraction of HP volume shifted to solaire_ete (0.0–1.0).
    green_preference: si True, ajoute la prime GO à chaque scénario.
    Returns list of 4 scenario dicts.
    """
    ref_price, price_source = get_reference_price(db, site_id, energy_type)
    market_ctx = get_market_context(db, energy_type.upper())

    # P0: Benchmark vs prix contrat réel (Contrats V2) au lieu de billing ref
    contract_info = get_current_contract_price(db, site_id)
    benchmark_price_kwh = contract_info["price_eur_kwh"]
    benchmark_label = contract_info["label"]
    benchmark_source = contract_info["source"]

    logger.info(
        "compute_scenarios: site=%d vol=%.0f pf=%.2f ref_price=%.4f src=%s benchmark=%.4f(%s) spot_30d=%.2f",
        site_id,
        volume_kwh_an,
        profile_factor,
        ref_price,
        price_source,
        benchmark_price_kwh,
        benchmark_source,
        market_ctx["spot_avg_30d_eur_mwh"],
    )

    # Prime verte (Garantie d'Origine)
    green_premium_kwh = (GREEN_PREMIUM_EUR_MWH / 1000) if green_preference else 0.0

    scenarios = []
    strategy_map = {
        "fixe": PurchaseStrategy.FIXE.value,
        "indexe": PurchaseStrategy.INDEXE.value,
        "spot": PurchaseStrategy.SPOT.value,
        "reflex_solar": PurchaseStrategy.REFLEX_SOLAR.value,
    }

    for strategy_key, strategy_enum in strategy_map.items():
        if strategy_key == "reflex_solar":
            # RéFlex Solar keeps its detailed blocs horaires model
            reflex = compute_reflex_scenario(
                ref_price,
                volume_kwh_an,
                profile_factor,
                price_source,
                report_pct=report_pct,
            )
            # Enrich with market-based pricing metadata
            ths_pricing = compute_strategy_price(
                "reflex_solar",
                market_ctx,
                profile_factor,
                horizon_months,
            )
            if ths_pricing:
                reflex["breakdown"] = ths_pricing["breakdown"]
                reflex["methodology"] = ths_pricing["methodology"]
                reflex["risk_score"] = ths_pricing["risk_score"]
                reflex["p10_eur"] = round(ths_pricing["p10_eur_mwh"] / 1000 * volume_kwh_an, 2)
                reflex["p90_eur"] = round(ths_pricing["p90_eur_mwh"] / 1000 * volume_kwh_an, 2)
            # Appliquer prime verte
            if green_premium_kwh > 0:
                new_price = reflex["price_eur_per_kwh"] + green_premium_kwh
                reflex["total_annual_eur"] = round(new_price * volume_kwh_an, 2)
                reflex["price_eur_per_kwh"] = round(new_price, 6)
                reflex["green_premium_eur_mwh"] = GREEN_PREMIUM_EUR_MWH
            scenarios.append(reflex)
        else:
            pricing = compute_strategy_price(
                strategy_key,
                market_ctx,
                profile_factor,
                horizon_months,
            )
            price_kwh = pricing["price_eur_kwh"] + green_premium_kwh
            total = round(price_kwh * volume_kwh_an, 2)
            scenario_dict = {
                "strategy": strategy_enum,
                "price_eur_per_kwh": round(price_kwh, 6),
                "total_annual_eur": total,
                "risk_score": pricing["risk_score"],
                "p10_eur": round(pricing["p10_eur_mwh"] / 1000 * volume_kwh_an, 2),
                "p90_eur": round(pricing["p90_eur_mwh"] / 1000 * volume_kwh_an, 2),
                "ref_price": ref_price,
                "ref_price_source": price_source,
                "breakdown": pricing["breakdown"],
                "methodology": pricing["methodology"],
            }
            if green_premium_kwh > 0:
                scenario_dict["green_premium_eur_mwh"] = GREEN_PREMIUM_EUR_MWH
            scenarios.append(scenario_dict)

    # Enrichir chaque scénario: savings, benchmark, badge, market context
    benchmark_total = round(benchmark_price_kwh * volume_kwh_an, 2)
    for s in scenarios:
        if benchmark_total > 0:
            s["savings_vs_current_pct"] = round((1 - s["total_annual_eur"] / benchmark_total) * 100, 1)
        else:
            s["savings_vs_current_pct"] = 0
        s["benchmark_label"] = benchmark_label
        s["benchmark_source"] = benchmark_source
        s["explanation_text"] = STRATEGY_EXPLANATIONS.get(s["strategy"], "")
        s["budget_badge"] = compute_budget_badge(s["total_annual_eur"], benchmark_total)
        s["market_context"] = market_ctx

    return scenarios


def recommend_scenario(
    scenarios: list,
    risk_tolerance: str = "medium",
    budget_priority: float = 0.5,
    green_preference: bool = False,
) -> list:
    """
    Score scenarios and mark the best as recommended.
    Returns the updated scenarios list with is_recommended + reasoning.
    """
    if not scenarios:
        return scenarios

    # Filter by risk tolerance
    if risk_tolerance == "low":
        eligible = [s for s in scenarios if s["risk_score"] <= 50]
    elif risk_tolerance == "high":
        eligible = list(scenarios)
    else:  # medium
        eligible = [s for s in scenarios if s["risk_score"] <= 70]

    if not eligible:
        eligible = list(scenarios)  # fallback: all eligible

    # Normalize savings for scoring (max savings = 100 pts)
    max_savings = max(abs(s.get("savings_vs_current_pct", 0)) for s in eligible) or 1
    for s in eligible:
        savings_norm = (s.get("savings_vs_current_pct", 0) / max_savings) * 100
        safety_score = 100 - s["risk_score"]
        score = (1 - budget_priority) * safety_score + budget_priority * savings_norm

        # Green bonus for indexe and reflex_solar
        if green_preference and s["strategy"] in (PurchaseStrategy.INDEXE.value, PurchaseStrategy.REFLEX_SOLAR.value):
            score += 5

        s["_score"] = round(score, 1)

    # Mark recommended
    best = max(eligible, key=lambda s: s["_score"])
    for s in scenarios:
        s["is_recommended"] = s["strategy"] == best["strategy"]

    # Generate reasoning
    strategy_labels = {"fixe": "Prix Fixe", "indexe": "Indexe", "spot": "Spot", "reflex_solar": "ReFlex Solar"}
    reasoning_parts = []
    reasoning_parts.append(f"Strategie {strategy_labels.get(best['strategy'], best['strategy'])} recommandee")
    if best["risk_score"] <= 30:
        reasoning_parts.append("risque tres faible")
    elif best["risk_score"] <= 50:
        reasoning_parts.append("risque modere")
    else:
        reasoning_parts.append("economies significatives malgre un risque eleve")

    savings = best.get("savings_vs_current_pct", 0)
    if savings > 0:
        reasoning_parts.append(f"economie de {savings}% vs prix actuel")

    if green_preference and best["strategy"] in (PurchaseStrategy.INDEXE.value, PurchaseStrategy.REFLEX_SOLAR.value):
        reasoning_parts.append("compatible offre verte")

    best["reasoning"] = " — ".join(reasoning_parts)
    logger.info(
        "recommend_scenario: best=%s score risk=%s savings=%.1f%%",
        best["strategy"],
        best["risk_score"],
        best.get("savings_vs_current_pct", 0),
    )

    # Clean internal scores
    for s in scenarios:
        s.pop("_score", None)

    return scenarios


# ══════════════════════════════════════
# V1.1 — Portfolio / History helpers
# ══════════════════════════════════════


def get_org_site_ids(db: Session, org_id: int) -> list:
    """
    Resolve all active site IDs for an organisation.
    Path: Organisation → EntiteJuridique → Portefeuille → Site.
    """
    ej_ids = [ej.id for ej in db.query(EntiteJuridique.id).filter(EntiteJuridique.organisation_id == org_id).all()]
    if not ej_ids:
        return []
    pf_ids = [p.id for p in db.query(Portefeuille.id).filter(Portefeuille.entite_juridique_id.in_(ej_ids)).all()]
    if not pf_ids:
        return []
    return [s.id for s in db.query(Site.id).filter(Site.portefeuille_id.in_(pf_ids), Site.actif == True).all()]


def compute_inputs_hash(
    volume_kwh_an: float,
    profile_factor: float,
    horizon_months: int,
    energy_type: str,
    risk_tolerance: str,
    budget_priority: float,
    green_preference: bool,
) -> str:
    """SHA-256 of input parameters for run comparison / idempotency."""
    payload = _json.dumps(
        {
            "volume_kwh_an": volume_kwh_an,
            "profile_factor": profile_factor,
            "horizon_months": horizon_months,
            "energy_type": energy_type,
            "risk_tolerance": risk_tolerance,
            "budget_priority": budget_priority,
            "green_preference": green_preference,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def aggregate_portfolio_results(results_by_site: list) -> dict:
    """
    Aggregate scenario results across multiple sites.
    Weights risk & savings by each site's volume.
    """
    total_cost_eur = 0.0
    total_risk_weighted = 0.0
    total_volume_kwh = 0.0
    total_savings_weighted = 0.0
    sites_with_reco = 0

    for site_result in results_by_site:
        reco = next((s for s in site_result["scenarios"] if s.get("is_recommended")), None)
        if not reco:
            continue
        sites_with_reco += 1
        total_cost_eur += reco.get("total_annual_eur", 0)
        volume = site_result.get("volume_kwh_an", 0)
        if volume <= 0:
            continue  # Skip 0-volume sites from weighted averages
        total_volume_kwh += volume
        total_risk_weighted += reco.get("risk_score", 0) * volume
        total_savings_weighted += (reco.get("savings_vs_current_pct", 0) or 0) * volume

    weighted_risk = round(total_risk_weighted / total_volume_kwh, 1) if total_volume_kwh > 0 else 0
    weighted_savings = round(total_savings_weighted / total_volume_kwh, 1) if total_volume_kwh > 0 else 0

    return {
        "sites_count": sites_with_reco,
        "total_annual_cost_eur": round(total_cost_eur, 2),
        "weighted_risk_score": weighted_risk,
        "weighted_savings_pct": weighted_savings,
        "total_volume_kwh_an": round(total_volume_kwh, 0),
    }
