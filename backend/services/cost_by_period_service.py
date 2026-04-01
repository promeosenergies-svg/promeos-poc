"""
PROMEOS — Coût par période tarifaire × usage.
Croise les CDC 15min avec le classifieur TURPE pour montrer
QUAND chaque usage consomme et combien ça coûte par période.

Résultat démo : "87% du chauffage en HPH → décaler = −2 800 €/an."
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.energy_models import Meter, MeterReading
from models.usage import Usage, USAGE_LABELS_FR
from services.tariff_period_classifier import (
    classify_period,
    TariffPeriod,
    PERIOD_LABELS,
    PERIOD_PRICE_RATIO,
)

# Seuil de détection d'optimisation : si > 70% en HP, proposer shift
_HP_THRESHOLD_PCT = 70
# Économie estimée d'un shift de 1h (% de la conso HP qui passe en HC)
_SHIFT_1H_CAPTURE_PCT = 12


def get_cost_by_period(db: Session, site_id: int, months: int = 12) -> dict:
    """Ventile le coût par usage × période tarifaire TURPE 7."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=months * 30)

    # Prix de référence du site
    from services.usage_service import _resolve_site_price

    price_ref = _resolve_site_price(db, site_id)

    # Sous-compteurs avec usage
    subs = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.usage_id.isnot(None),
            Meter.parent_meter_id.isnot(None),
        )
        .all()
    )

    usages_result = []
    for sub in subs:
        usage = db.query(Usage).filter(Usage.id == sub.usage_id).first()
        label = (usage.label or USAGE_LABELS_FR.get(usage.type, usage.type.value)) if usage else "?"

        # Charger les readings
        readings = (
            db.query(MeterReading.timestamp, MeterReading.value_kwh)
            .filter(MeterReading.meter_id == sub.id, MeterReading.timestamp >= cutoff)
            .all()
        )
        if not readings:
            continue

        # Classifier chaque reading par période (toutes les périodes initialisées)
        by_period = {p.value: {"kwh": 0.0, "eur": 0.0, "count": 0} for p in TariffPeriod}
        total_kwh = 0.0

        for ts, kwh in readings:
            period = classify_period(ts)
            by_period[period.value]["kwh"] += kwh
            by_period[period.value]["count"] += 1
            total_kwh += kwh

        if total_kwh <= 0:
            continue

        # Détecter optimisation shift HP→HC (avant arrondi pour précision)
        raw_hph = by_period["HPH"]["kwh"]
        raw_hch = by_period["HCH"]["kwh"]
        raw_hpb = by_period["HPB"]["kwh"]
        raw_hcb = by_period["HCB"]["kwh"]
        hp_kwh = raw_hph + raw_hpb
        hc_kwh = raw_hch + raw_hcb
        hp_pct = round(hp_kwh / total_kwh * 100, 1) if total_kwh > 0 else 0

        optimization = None
        if hp_pct >= _HP_THRESHOLD_PCT:
            shifted_kwh = hp_kwh * _SHIFT_1H_CAPTURE_PCT / 100
            hp_avg_ratio = (PERIOD_PRICE_RATIO["HPH"] * raw_hph + PERIOD_PRICE_RATIO["HPB"] * raw_hpb) / max(hp_kwh, 1)
            hc_avg_ratio = (
                (PERIOD_PRICE_RATIO["HCH"] * raw_hch + PERIOD_PRICE_RATIO["HCB"] * raw_hcb) / max(hc_kwh, 1)
                if hc_kwh > 0
                else PERIOD_PRICE_RATIO["HCH"]
            )
            savings_eur = round(shifted_kwh * price_ref * (hp_avg_ratio - hc_avg_ratio))
            if savings_eur > 100:
                optimization = {
                    "hp_pct": hp_pct,
                    "action": f"Décaler le démarrage de {label.lower()} de 1h (7h→6h) pour basculer {_SHIFT_1H_CAPTURE_PCT}% de la conso HP vers HC",
                    "shifted_kwh": round(shifted_kwh),
                    "savings_eur": savings_eur,
                }

        # Calculer le coût par période avec ratio de prix + arrondir
        total_eur = 0.0
        for key, data in by_period.items():
            ratio = PERIOD_PRICE_RATIO.get(key, 1.0)
            data["eur"] = round(data["kwh"] * price_ref * ratio)
            data["pct_kwh"] = round(data["kwh"] / total_kwh * 100, 1)
            data["kwh"] = round(data["kwh"], 1)
            total_eur += data["eur"]

        for data in by_period.values():
            data["pct_eur"] = round(data["eur"] / total_eur * 100, 1) if total_eur > 0 else 0

        # Supprimer les périodes vides de la réponse
        by_period = {k: v for k, v in by_period.items() if v["count"] > 0}

        usages_result.append(
            {
                "usage": label,
                "usage_id": sub.usage_id,
                "meter_id": sub.id,
                "total_kwh": round(total_kwh, 1),
                "total_eur": round(total_eur),
                "by_period": by_period,
                "hp_pct": hp_pct,
                "optimization": optimization,
            }
        )

    usages_result.sort(key=lambda u: u["total_eur"], reverse=True)

    return {
        "site_id": site_id,
        "months": months,
        "price_ref_eur_kwh": price_ref,
        "usages": usages_result,
        "period_labels": PERIOD_LABELS,
        "total_optimization_eur": sum(u["optimization"]["savings_eur"] for u in usages_result if u.get("optimization")),
    }
