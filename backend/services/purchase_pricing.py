"""
PROMEOS — Moteur de pricing achat énergie

Remplace les multiplicateurs simplistes par un modèle structuré :
- Fixe : forward CAL + prime fournisseur + marge
- Indexé : index EPEX + spread fixe + cap optionnel
- Spot : EPEX moyen + frais agrégateur
- THS : spot avec pondération blocs horaires solaires

Les prix sont en EUR/MWh (convention marché) et convertis en EUR/kWh
pour l'affichage final.

Source de vérité prix : table mkt_prices (MktPrice) via market_models.py.
"""

import statistics
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.market_models import (
    MktPrice,
    MarketType,
    PriceZone,
    MarketDataSource,
)


def _date_to_utc(d: date) -> datetime:
    """Convertit une date en datetime UTC minuit."""
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def get_market_context(db: Session, energy_type: str = "ELEC", ref_date: date = None) -> dict:
    """
    Récupère le contexte marché depuis mkt_prices (V2).

    Retourne :
      spot_avg_30d_eur_mwh, spot_avg_12m_eur_mwh, spot_current_eur_mwh,
      volatility_12m_eur_mwh, trend_30d_vs_12m_pct
    """
    ref = ref_date or date.today()
    ref_dt = _date_to_utc(ref)

    # Spot moyen 30 derniers jours
    spot_30d = (
        db.query(func.avg(MktPrice.price_eur_mwh))
        .filter(
            MktPrice.zone == PriceZone.FR,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start >= ref_dt - timedelta(days=30),
            MktPrice.delivery_start <= ref_dt,
        )
        .scalar()
    )

    # Spot moyen 12 mois
    spot_12m = (
        db.query(func.avg(MktPrice.price_eur_mwh))
        .filter(
            MktPrice.zone == PriceZone.FR,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start >= ref_dt - timedelta(days=365),
            MktPrice.delivery_start <= ref_dt,
        )
        .scalar()
    )

    # Dernier prix
    last = (
        db.query(MktPrice.price_eur_mwh)
        .filter(
            MktPrice.zone == PriceZone.FR,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start <= ref_dt,
        )
        .order_by(MktPrice.delivery_start.desc())
        .first()
    )

    # Volatilité (écart-type 12 mois)
    prices_12m = (
        db.query(MktPrice.price_eur_mwh)
        .filter(
            MktPrice.zone == PriceZone.FR,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start >= ref_dt - timedelta(days=365),
        )
        .all()
    )

    vol = statistics.stdev([p[0] for p in prices_12m]) if len(prices_12m) > 30 else 15.0

    # Defaults réalistes si pas de données marché
    has_real_data = spot_30d is not None
    spot_30d = spot_30d or 68.0
    spot_12m = spot_12m or 72.0
    current = last[0] if last else 68.0
    trend = ((spot_30d - spot_12m) / spot_12m * 100) if spot_12m else 0

    # Detecter si les donnees sont seed/demo
    source_sample = (
        db.query(MktPrice.source)
        .filter(MktPrice.zone == PriceZone.FR, MktPrice.source.isnot(None))
        .order_by(MktPrice.delivery_start.desc())
        .first()
    )
    if source_sample:
        source_label = source_sample[0].value if hasattr(source_sample[0], "value") else str(source_sample[0])
    else:
        source_label = "fallback_defaults" if not has_real_data else "unknown"
    is_demo = not has_real_data or (source_label and "manual" in source_label.lower())

    return {
        "spot_avg_30d_eur_mwh": round(spot_30d, 2),
        "spot_avg_12m_eur_mwh": round(spot_12m, 2),
        "spot_current_eur_mwh": round(current, 2),
        "volatility_12m_eur_mwh": round(vol, 2),
        "trend_30d_vs_12m_pct": round(trend, 1),
        "source": source_label,
        "is_demo": is_demo,
    }


def compute_strategy_price(
    strategy: str,
    market_ctx: dict,
    profile_factor: float = 1.0,
    horizon_months: int = 12,
) -> dict | None:
    """
    Calcule le prix pour une stratégie donnée.

    Retourne : price_eur_mwh, price_eur_kwh, risk_score, p10_eur_mwh,
               p90_eur_mwh, breakdown, methodology
    """
    spot = market_ctx["spot_avg_30d_eur_mwh"]
    vol = market_ctx["volatility_12m_eur_mwh"]

    if strategy == "fixe":
        # Forward = spot + prime de terme (3% base + 0.3% par mois, cap 12%)
        terme_premium_pct = min(3 + horizon_months * 0.3, 12)
        forward = spot * (1 + terme_premium_pct / 100)
        supplier_margin = 2.5  # EUR/MWh — marge fournisseur typique B2B
        price = forward + supplier_margin

        return {
            "price_eur_mwh": round(price, 2),
            "price_eur_kwh": round(price / 1000, 6),
            "risk_score": 10 + max(0, horizon_months - 12) * 2,  # 10-34
            "p10_eur_mwh": round(price, 2),  # fixe = pas de bande
            "p90_eur_mwh": round(price, 2),
            "breakdown": {
                "spot_base": round(spot, 2),
                "terme_premium": round(forward - spot, 2),
                "supplier_margin": supplier_margin,
            },
            "methodology": f"Forward CAL ({terme_premium_pct:.1f}% prime terme) + marge fournisseur {supplier_margin} EUR/MWh",
        }

    elif strategy == "indexe":
        # Index = spot + spread fixe fournisseur
        spread = 4.0  # EUR/MWh — spread fournisseur B2B
        price = spot + spread
        # Bandes basées sur volatilité réelle
        p10 = price - vol * 1.3
        p90 = price + vol * 1.3
        cap = spot * 1.4  # cap à +40% du spot

        return {
            "price_eur_mwh": round(price, 2),
            "price_eur_kwh": round(price / 1000, 6),
            "risk_score": 35 + int(vol / 3),  # 35-55 selon volatilité
            "p10_eur_mwh": round(max(p10, 20), 2),
            "p90_eur_mwh": round(min(p90, cap), 2),
            "breakdown": {
                "spot_base": round(spot, 2),
                "spread": spread,
                "cap_eur_mwh": round(cap, 2),
            },
            "methodology": f"EPEX Spot FR + spread {spread} EUR/MWh, cap {cap:.0f} EUR/MWh",
        }

    elif strategy == "spot":
        # Spot pur = EPEX moyen × profil + frais agrégateur
        aggregator_fee = 1.5  # EUR/MWh — frais agrégateur
        price = spot * profile_factor + aggregator_fee
        p10 = (spot - vol * 1.6) * profile_factor + aggregator_fee
        p90 = (spot + vol * 1.6) * profile_factor + aggregator_fee

        return {
            "price_eur_mwh": round(price, 2),
            "price_eur_kwh": round(price / 1000, 6),
            "risk_score": 60 + int(vol / 2),  # 60-80+
            "p10_eur_mwh": round(max(p10, 15), 2),
            "p90_eur_mwh": round(p90, 2),
            "breakdown": {
                "spot_base": round(spot * profile_factor, 2),
                "aggregator_fee": aggregator_fee,
                "profile_adjustment": round((profile_factor - 1) * spot, 2),
            },
            "methodology": f"EPEX Spot FR × profil ({profile_factor:.2f}) + frais agrégateur {aggregator_fee} EUR/MWh",
        }

    elif strategy == "reflex_solar":
        # THS = spot avec blocs horaires pondérés
        solar_discount = 0.85  # -15% sur les heures solaires (10h-16h)
        off_solar = 1.05  # +5% sur les heures non-solaires
        # Estimation 40% heures solaires, 60% hors solaires
        blended = spot * (0.4 * solar_discount + 0.6 * off_solar)
        aggregator_fee = 2.0  # EUR/MWh — frais agrégateur THS
        price = blended + aggregator_fee
        p10 = (blended - vol * 1.2) + aggregator_fee
        p90 = (blended + vol * 1.2) + aggregator_fee

        return {
            "price_eur_mwh": round(price, 2),
            "price_eur_kwh": round(price / 1000, 6),
            "risk_score": 40 + int(vol / 3),
            "p10_eur_mwh": round(max(p10, 15), 2),
            "p90_eur_mwh": round(p90, 2),
            "breakdown": {
                "spot_base": round(spot, 2),
                "solar_discount_pct": -15,
                "off_solar_premium_pct": 5,
                "blended_price": round(blended, 2),
                "aggregator_fee": aggregator_fee,
            },
            "methodology": f"EPEX Spot pondéré blocs solaires (-15% 10h-16h) + {aggregator_fee} EUR/MWh",
        }

    return None
