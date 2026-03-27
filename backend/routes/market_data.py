"""
Routes API Market Data V2.
Tous les calculs sont backend -- le front ne fait qu'afficher.

NOTE: Ce fichier coexiste avec routes/market.py (Step 17 legacy).
Les endpoints sont sous /api/market/spot/*, /api/market/forwards, /api/market/tariffs/*, /api/market/freshness.
Pas de conflit avec les routes legacy /api/market/prices et /api/market/context.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.market_data_service import MarketDataService
from services.market_tariff_loader import get_current_tariff, load_tariffs_from_yaml
from services.price_decomposition_service import PriceDecompositionService
from models.market_models import (
    PriceZone,
    MarketType,
    TariffType,
    TariffComponent,
    ProductType,
    PriceDecomposition,
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


# ======================================================================
# Decomposition prix
# ======================================================================


@router.get("/decomposition/compute")
def decomposition_compute(
    profile: str = Query("C4", description="Profil: C5, C4, C2, HTA"),
    energy_price: Optional[float] = Query(None, description="Prix energie force (EUR/MWh)"),
    power_kw: Optional[float] = Query(None, description="Puissance souscrite (kW)"),
    volume_mwh: Optional[float] = Query(None, description="Volume annuel (MWh)"),
    db: Session = Depends(get_db),
):
    """Decomposition prix temps reel — pas de persistance."""
    svc = PriceDecompositionService(db)
    result = svc.compute(
        profile=profile,
        energy_price_eur_mwh=energy_price,
        power_kw=power_kw,
        volume_mwh=volume_mwh,
    )
    return result.to_dict()


@router.post("/decomposition/store")
def decomposition_store(
    org_id: int = Query(..., description="ID organisation"),
    site_id: Optional[int] = Query(None, description="ID site"),
    profile: str = Query("C4"),
    energy_price: Optional[float] = Query(None),
    power_kw: Optional[float] = Query(None),
    volume_mwh: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Calcul + persistance dans price_decompositions."""
    svc = PriceDecompositionService(db)
    result = svc.compute_and_store(
        org_id=org_id,
        site_id=site_id,
        profile=profile,
        energy_price_eur_mwh=energy_price,
        power_kw=power_kw,
        volume_mwh=volume_mwh,
    )
    return {"status": "ok", **result.to_dict()}


@router.get("/decomposition/latest")
def decomposition_latest(
    org_id: int = Query(...),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Derniere decomposition stockee pour un org/site."""
    q = db.query(PriceDecomposition).filter(PriceDecomposition.org_id == org_id)
    if site_id:
        q = q.filter(PriceDecomposition.site_id == site_id)
    record = q.order_by(PriceDecomposition.calculated_at.desc()).first()
    if not record:
        return {"status": "no_data", "message": "Aucune decomposition stockee"}
    return {
        "id": record.id,
        "profile": record.profile,
        "energy_eur_mwh": record.energy_eur_mwh,
        "turpe_eur_mwh": record.turpe_eur_mwh,
        "cspe_eur_mwh": record.cspe_eur_mwh,
        "capacity_eur_mwh": record.capacity_eur_mwh,
        "cee_eur_mwh": record.cee_eur_mwh,
        "cta_eur_mwh": record.cta_eur_mwh,
        "total_ht_eur_mwh": record.total_ht_eur_mwh,
        "tva_eur_mwh": record.tva_eur_mwh,
        "total_ttc_eur_mwh": record.total_ttc_eur_mwh,
        "calculation_method": record.calculation_method,
        "tariff_version": record.tariff_version,
        "calculated_at": record.calculated_at.isoformat() if record.calculated_at else None,
    }


@router.get("/decomposition/history")
def decomposition_history(
    org_id: int = Query(...),
    site_id: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Historique des decompositions pour un org/site."""
    q = db.query(PriceDecomposition).filter(PriceDecomposition.org_id == org_id)
    if site_id:
        q = q.filter(PriceDecomposition.site_id == site_id)
    records = q.order_by(PriceDecomposition.calculated_at.desc()).limit(limit).all()
    return {
        "count": len(records),
        "decompositions": [
            {
                "id": r.id,
                "profile": r.profile,
                "total_ttc_eur_mwh": r.total_ttc_eur_mwh,
                "total_ht_eur_mwh": r.total_ht_eur_mwh,
                "tariff_version": r.tariff_version,
                "calculated_at": r.calculated_at.isoformat() if r.calculated_at else None,
            }
            for r in records
        ],
    }


@router.get("/decomposition/compare")
def decomposition_compare(
    energy_price: Optional[float] = Query(None, description="Prix energie (EUR/MWh)"),
    power_kw: Optional[float] = Query(None),
    volume_mwh: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    """Comparaison C5/C4/C2 cote a cote — endpoint differenciant pour prospect."""
    svc = PriceDecompositionService(db)
    profiles = ["C5", "C4", "C2"]
    results = {}
    for p in profiles:
        r = svc.compute(
            profile=p,
            energy_price_eur_mwh=energy_price,
            power_kw=power_kw,
            volume_mwh=volume_mwh,
        )
        results[p] = r.to_dict()

    return {
        "profiles": profiles,
        "decompositions": results,
        "summary": {
            p: {
                "total_ht_eur_mwh": results[p]["total_ht_eur_mwh"],
                "total_ttc_eur_mwh": results[p]["total_ttc_eur_mwh"],
            }
            for p in profiles
        },
    }


@router.post("/tariffs/reload")
def reload_tariffs(
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Recharge les tarifs depuis le YAML (admin, authentification requise)."""
    result = load_tariffs_from_yaml(db)
    return {"status": "ok", **result}
