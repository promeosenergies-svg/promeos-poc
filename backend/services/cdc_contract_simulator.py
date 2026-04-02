"""
Simule le coût annuel de chaque stratégie d'achat avec la CDC réelle du site.

4 stratégies : Fixe 12 mois, Indexé EPEX Spot, Mixte baseload/pointe, THS.
Le profil CDC (baseload_ratio, seasonality, hp_ratio) détermine la recommandation.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH
from models.site import Site
from models.energy_models import Meter, MeterReading, FrequencyType

logger = logging.getLogger(__name__)

# Prix de référence (€/kWh) — fallback si pas de données marché
PRIX_FIXE_12M = 0.072
PRIX_SPOT_MID = DEFAULT_PRICE_ELEC_EUR_KWH
PRIX_THS_SOLAIRE = 0.055
PRIX_THS_NON_SOLAIRE = 0.085

# Profils spot mensuels (ratio vs prix moyen) — source EPEX 2024-2025
SPOT_MONTHLY_RATIO = {
    1: 1.35,
    2: 1.25,
    3: 1.05,
    4: 0.85,
    5: 0.75,
    6: 0.70,
    7: 0.72,
    8: 0.68,
    9: 0.80,
    10: 0.95,
    11: 1.15,
    12: 1.40,
}


def simulate_contract_strategies(db: Session, site_id: int) -> dict | None:
    """Simule 4 stratégies d'achat avec la CDC réelle du site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return None

    meters = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.parent_meter_id.is_(None),
        )
        .all()
    )
    if not meters:
        return {"error": "Aucun compteur principal"}

    start_date = date.today() - timedelta(days=365)
    hourly_profile = _build_hourly_profile(db, [m.id for m in meters], start_date)

    if len(hourly_profile) < 100:
        return {"error": "Données CDC insuffisantes", "groups": len(hourly_profile)}

    cdc_profile = _characterize_cdc(hourly_profile)
    total_kwh = sum(h["kwh"] for h in hourly_profile)

    strategies = []

    # 1. Fixe 12 mois
    cost_fixe = total_kwh * PRIX_FIXE_12M
    strategies.append(
        {
            "name": "Fixe 12 mois",
            "cost_eur_year": round(cost_fixe),
            "price_avg_eur_kwh": PRIX_FIXE_12M,
            "risk_level": "faible",
            "description": "Prix fixe garanti, pas de surprise budgétaire.",
        }
    )

    # 2. Indexé EPEX Spot (3 scénarios)
    cost_spot_mid = sum(h["kwh"] * PRIX_SPOT_MID * SPOT_MONTHLY_RATIO.get(h["month"], 1.0) for h in hourly_profile)
    strategies.append(
        {
            "name": "Indexé EPEX Spot",
            "cost_eur_year_low": round(cost_spot_mid * 0.78),
            "cost_eur_year_mid": round(cost_spot_mid),
            "cost_eur_year_high": round(cost_spot_mid * 1.45),
            "cost_eur_year": round(cost_spot_mid),
            "price_avg_eur_kwh": round(cost_spot_mid / max(total_kwh, 1), 4),
            "risk_level": "élevé",
            "description": "Moins cher en moyenne, mais volatil (hiver +40%).",
        }
    )

    # 3. Mixte baseload/pointe
    baseload_kwh = total_kwh * cdc_profile["baseload_ratio"]
    peak_kwh = total_kwh - baseload_kwh
    cost_mixte = (baseload_kwh * PRIX_FIXE_12M * 0.95) + (peak_kwh * PRIX_SPOT_MID * 1.1)
    bl_pct = int(cdc_profile["baseload_ratio"] * 100)
    strategies.append(
        {
            "name": f"Mixte {bl_pct}/{100 - bl_pct}",
            "cost_eur_year": round(cost_mixte),
            "price_avg_eur_kwh": round(cost_mixte / max(total_kwh, 1), 4),
            "risk_level": "modéré",
            "description": f"Baseload fixe ({bl_pct}%) + pointe spot.",
        }
    )

    # 4. THS (Heures Solaires)
    solar_kwh = sum(h["kwh"] for h in hourly_profile if _is_solar_hour(h["month"], h["hour"]))
    non_solar_kwh = total_kwh - solar_kwh
    cost_ths = (solar_kwh * PRIX_THS_SOLAIRE) + (non_solar_kwh * PRIX_THS_NON_SOLAIRE)
    solar_pct = round((solar_kwh / max(total_kwh, 1)) * 100, 1)
    ths_relevant = solar_pct > 25
    strategies.append(
        {
            "name": "THS (Heures Solaires)",
            "cost_eur_year": round(cost_ths),
            "price_avg_eur_kwh": round(cost_ths / max(total_kwh, 1), 4),
            "risk_level": "faible",
            "solar_pct": solar_pct,
            "ths_relevant": ths_relevant,
            "description": f"{solar_pct:.0f}% en heures solaires. {'Pertinent' if ths_relevant else 'Non optimal'} pour ce profil.",
        }
    )

    recommendation = _recommend_strategy(cdc_profile, strategies)

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "total_kwh_year": round(total_kwh),
        "cdc_profile": cdc_profile,
        "strategies": strategies,
        "recommendation": recommendation,
    }


def _build_hourly_profile(db: Session, meter_ids: list[int], start_date: date) -> list[dict]:
    """Agrège les readings en profil mois × heure."""
    rows = (
        db.query(
            extract("month", MeterReading.timestamp).label("mo"),
            extract("hour", MeterReading.timestamp).label("hr"),
            func.sum(MeterReading.value_kwh).label("total_kwh"),
        )
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.frequency == FrequencyType.MIN_15,
            MeterReading.timestamp >= start_date.isoformat(),
        )
        .group_by(
            extract("month", MeterReading.timestamp),
            extract("hour", MeterReading.timestamp),
        )
        .all()
    )
    return [{"month": int(r.mo), "hour": int(r.hr), "kwh": float(r.total_kwh or 0)} for r in rows]


def _characterize_cdc(hourly_profile: list[dict]) -> dict:
    """Classifie le profil CDC : baseload_dominant, saisonnier, bureau, mixte."""
    kwh_values = [h["kwh"] for h in hourly_profile]
    avg_kwh = sum(kwh_values) / len(kwh_values)

    night_values = [h["kwh"] for h in hourly_profile if 0 <= h["hour"] <= 5]
    baseload = sorted(night_values)[len(night_values) // 2] if night_values else avg_kwh * 0.4

    day_values = [h["kwh"] for h in hourly_profile if 8 <= h["hour"] <= 18]
    max_day = max(day_values) if day_values else avg_kwh

    baseload_ratio = min(baseload / max(max_day, 1), 1.0)

    # Saisonnalité
    monthly_totals: dict[int, float] = {}
    for h in hourly_profile:
        monthly_totals[h["month"]] = monthly_totals.get(h["month"], 0) + h["kwh"]
    if monthly_totals:
        monthly_vals = list(monthly_totals.values())
        monthly_avg = sum(monthly_vals) / len(monthly_vals)
        variance = sum((v - monthly_avg) ** 2 for v in monthly_vals) / len(monthly_vals)
        seasonality = (variance**0.5) / max(monthly_avg, 1)
    else:
        seasonality = 0

    # HP ratio (7h-23h)
    hp_kwh = sum(h["kwh"] for h in hourly_profile if 7 <= h["hour"] < 23)
    total = sum(h["kwh"] for h in hourly_profile)
    hp_ratio = hp_kwh / max(total, 1)

    if baseload_ratio > 0.75:
        profile_type = "baseload_dominant"
    elif seasonality > 0.3:
        profile_type = "saisonnier_fort"
    elif hp_ratio > 0.65:
        profile_type = "bureau_classique"
    else:
        profile_type = "mixte"

    return {
        "type": profile_type,
        "baseload_ratio": round(baseload_ratio, 2),
        "seasonality_index": round(seasonality, 3),
        "hp_ratio": round(hp_ratio, 2),
        "baseload_kwh_h": round(baseload, 1),
        "peak_kwh_h": round(max_day, 1),
    }


def _recommend_strategy(profile: dict, strategies: list) -> dict:
    """Recommande la meilleure stratégie selon le profil CDC."""
    ptype = profile["type"]

    if ptype == "baseload_dominant":
        best = next((s for s in strategies if "Fixe" in s["name"]), strategies[0])
        reasoning = (
            "Profil baseload dominant — prix fixe ruban 24/7 optimal. Le spot n'apporte pas de gain sur un profil plat."
        )
    elif ptype == "saisonnier_fort":
        best = next((s for s in strategies if "Indexé" in s["name"]), strategies[1])
        reasoning = "Profil très saisonnier — indexé spot avantageux en été (prix bas). Prévoir un cap hiver."
    elif ptype == "bureau_classique":
        ths = next((s for s in strategies if "THS" in s["name"]), None)
        if ths and ths.get("ths_relevant"):
            best = ths
            reasoning = f"Profil bureau HP {profile['hp_ratio'] * 100:.0f}% — THS pertinent ({ths['solar_pct']:.0f}% en heures solaires)."
        else:
            best = next((s for s in strategies if "Fixe" in s["name"]), strategies[0])
            reasoning = (
                f"Profil bureau HP {profile['hp_ratio'] * 100:.0f}% mais peu d'heures solaires — fixe 12 mois plus sûr."
            )
    else:
        best = next((s for s in strategies if "Mixte" in s["name"]), strategies[2])
        reasoning = "Profil mixte — stratégie hybride baseload fixe + pointe spot."

    fixe_cost = next((s["cost_eur_year"] for s in strategies if "Fixe" in s["name"]), 0)
    best_cost = best.get("cost_eur_year", fixe_cost)
    savings = max(0, fixe_cost - best_cost)

    return {
        "strategy": best["name"],
        "reasoning": reasoning,
        "estimated_cost_eur": best_cost,
        "savings_vs_fixe_eur": savings,
        "risk_level": best["risk_level"],
    }


def _is_solar_hour(month: int, hour: int) -> bool:
    if month in (4, 5, 6, 7, 8, 9):
        return 10 <= hour < 16
    return 11 <= hour < 15
