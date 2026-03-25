"""
Routes API Market Data V2.
Tous les calculs sont backend -- le front ne fait qu'afficher.

NOTE: Ce fichier coexiste avec routes/market.py (Step 17 legacy).
Les endpoints sont sous /api/market/spot/*, /api/market/forwards, /api/market/tariffs/*, /api/market/freshness.
Pas de conflit avec les routes legacy /api/market/prices et /api/market/context.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from database import get_db
from services.market_data_service import MarketDataService
from services.market_tariff_loader import get_current_tariff, load_tariffs_from_yaml
from models.market_models import (
    PriceZone, MarketType, TariffType, TariffComponent, ProductType
)

router = APIRouter(prefix="/api/market", tags=["Market Data V2"])


@router.get("/spot/latest")
def get_latest_spot(
    zone: str = Query("FR"),
    db: Session = Depends(get_db),
):
    """Dernier prix spot connu."""
    svc = MarketDataService(db)
    price = svc.get_latest_price(zone=PriceZone(zone))
    if not price:
        return {"status": "no_data", "message": "Aucun prix spot disponible"}
    return {
        "zone": price.zone.value,
        "price_eur_mwh": price.price_eur_mwh,
        "delivery_start": price.delivery_start.isoformat(),
        "delivery_end": price.delivery_end.isoformat(),
        "source": price.source.value,
        "fetched_at": price.fetched_at.isoformat(),
    }


@router.get("/spot/history")
def get_spot_history(
    zone: str = Query("FR"),
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Historique prix spot."""
    svc = MarketDataService(db)
    start = datetime.now(timezone.utc) - timedelta(days=days)
    prices = svc.get_spot_prices(zone=PriceZone(zone), start=start, limit=days * 24)
    return {
        "zone": zone,
        "period_days": days,
        "count": len(prices),
        "prices": [
            {
                "delivery_start": p.delivery_start.isoformat(),
                "price_eur_mwh": p.price_eur_mwh,
            }
            for p in sorted(prices, key=lambda x: x.delivery_start)
        ],
    }


@router.get("/spot/stats")
def get_spot_stats(
    zone: str = Query("FR"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Statistiques prix spot (moyenne, min, max)."""
    svc = MarketDataService(db)
    return svc.get_price_stats(zone=PriceZone(zone), days=days)


@router.get("/forwards")
def get_forward_curves(
    zone: str = Query("FR"),
    product: str = Query("BASELOAD"),
    db: Session = Depends(get_db),
):
    """Forward curves (CAL, Q, M)."""
    svc = MarketDataService(db)
    curves = svc.get_forward_curves(
        zone=PriceZone(zone),
        product=ProductType(product),
    )
    return {
        "zone": zone,
        "product": product,
        "curves": [
            {
                "market_type": c.market_type.value,
                "delivery_start": c.delivery_start.isoformat(),
                "delivery_end": c.delivery_end.isoformat(),
                "price_eur_mwh": c.price_eur_mwh,
                "source": c.source.value,
            }
            for c in curves
        ],
    }


@router.get("/tariffs/current")
def get_current_tariffs(
    profile: str = Query("C4", description="Profil: C5, C4, C2"),
    db: Session = Depends(get_db),
):
    """Tarifs reglementes en vigueur pour un profil donne."""
    # Mapper profil -> composante CSPE
    cspe_map = {"C5": TariffComponent.CSPE_C5, "C4": TariffComponent.CSPE_C4, "C2": TariffComponent.CSPE_C2}
    cspe_component = cspe_map.get(profile, TariffComponent.CSPE_C4)

    cspe = get_current_tariff(db, TariffType.CSPE, cspe_component)
    capacity = get_current_tariff(db, TariffType.CAPACITY, TariffComponent.CAPACITY_PRICE_MW)
    vnu_bas = get_current_tariff(db, TariffType.VNU, TariffComponent.VNU_SEUIL_BAS)
    vnu_haut = get_current_tariff(db, TariffType.VNU, TariffComponent.VNU_SEUIL_HAUT)
    cee = get_current_tariff(db, TariffType.CEE, TariffComponent.CEE_OBLIGATION)
    cta = get_current_tariff(db, TariffType.CTA, TariffComponent.CTA_TAUX)

    return {
        "profile": profile,
        "cspe_eur_mwh": cspe.value if cspe else None,
        "capacity_eur_mw": capacity.value if capacity else None,
        "vnu_seuil_bas_eur_mwh": vnu_bas.value if vnu_bas else None,
        "vnu_seuil_haut_eur_mwh": vnu_haut.value if vnu_haut else None,
        "cee_eur_mwh": cee.value if cee else None,
        "cta_pct": cta.value if cta else None,
        "sources": {
            "cspe": cspe.source_name if cspe else None,
            "cspe_version": cspe.version if cspe else None,
        },
    }


@router.get("/freshness")
def get_data_freshness(db: Session = Depends(get_db)):
    """Etat de fraicheur des donnees marche."""
    svc = MarketDataService(db)
    return svc.get_data_freshness()


@router.post("/tariffs/reload")
def reload_tariffs(db: Session = Depends(get_db)):
    """Recharge les tarifs depuis le YAML (admin)."""
    result = load_tariffs_from_yaml(db)
    return {"status": "ok", **result}
