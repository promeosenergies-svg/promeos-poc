"""
PROMEOS - Tests Simulation NEBCO sur CDC reelle (Vague 2 Piste 4).

Couvre :
    1. Gain positif sur un site complet (CDC + spot + archetype connu)
    2. Pas de CDC -> gain 0 + trace dans hypotheses
    3. Pas de spot -> fallback 60 EUR/MWh
    4. Archetype inconnu -> fallback BUREAU_STANDARD
    5. Clamp period_days [7, 90]
    6. Somme des composantes coherente (gain_spread - compensation = net)
    7. Injection de l'horloge `now` : dates attendues exactement
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Meter, MeterReading, Site, TypeSite
from models.energy_models import EnergyVector, FrequencyType
from models.market_models import (
    MarketDataSource,
    MarketType,
    MktPrice,
    PriceZone,
    ProductType,
    Resolution,
)
from services.pilotage.nebco_simulation import simulate_nebco_gain


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def db_session():
    """Session DB SQLite in-memory, isolee par test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_site(db, *, archetype_code="COMMERCE_ALIMENTAIRE", nom="Site Test") -> Site:
    """Cree un Site + un Meter elec actif associe."""
    site = Site(
        nom=nom,
        type=TypeSite.MAGASIN,
        archetype_code=archetype_code,
        puissance_pilotable_kw=100.0,
    )
    db.add(site)
    db.flush()
    meter = Meter(
        meter_id=f"PRM-TEST-{site.id}",
        name="M1",
        site_id=site.id,
        energy_vector=EnergyVector.ELECTRICITY,
        is_active=True,
    )
    db.add(meter)
    db.flush()
    return site


def _seed_cdc(
    db,
    site_id: int,
    *,
    now: datetime,
    days: int = 30,
    kwh_per_hour: float = 50.0,
) -> int:
    """
    Seed `days * 24` MeterReading HOURLY pour tous les compteurs du site.
    Retourne le nombre de lignes inserees.
    """
    meter = db.query(Meter).filter(Meter.site_id == site_id).first()
    assert meter is not None
    # On stocke en naif (convention projet)
    base = now.replace(tzinfo=None) if now.tzinfo else now
    # On debute `days` jours avant `now`
    start = base - timedelta(days=days)
    rows = []
    for d in range(days):
        for h in range(24):
            rows.append(
                MeterReading(
                    meter_id=meter.id,
                    timestamp=start + timedelta(days=d, hours=h),
                    frequency=FrequencyType.HOURLY,
                    value_kwh=kwh_per_hour,
                    quality_score=0.95,
                    is_estimated=False,
                )
            )
    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


def _seed_spot(
    db,
    *,
    now: datetime,
    days: int = 30,
) -> int:
    """
    Seed prix spot FR day-ahead horaires : matin/soir chers (SENSIBLE),
    midi / nuit bon marche (FAVORABLE).
    """
    base = now.replace(tzinfo=None) if now.tzinfo else now
    # On utilise des timestamps UTC tz-aware pour matcher le storage MktPrice.
    start = base - timedelta(days=days)
    rows: list[MktPrice] = []
    for d in range(days):
        for h in range(24):
            ts = datetime(start.year, start.month, start.day, h, 0, tzinfo=timezone.utc) + timedelta(days=d)
            # Profil : matin (7-10) et soir (17-21) cher, creuse 11-16 et 0-5
            if 7 <= h < 10 or 17 <= h < 21:
                price = 150.0
            elif 11 <= h < 16 or 0 <= h < 5:
                price = 20.0
            else:
                price = 60.0
            rows.append(
                MktPrice(
                    source=MarketDataSource.ENTSOE,
                    market_type=MarketType.SPOT_DAY_AHEAD,
                    product_type=ProductType.HOURLY,
                    zone=PriceZone.FR,
                    delivery_start=ts,
                    delivery_end=ts + timedelta(hours=1),
                    price_eur_mwh=price,
                    resolution=Resolution.PT60M,
                    fetched_at=datetime.now(timezone.utc),
                )
            )
    db.add_all(rows)
    db.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Test 1 : gain positif sur site complet
# ---------------------------------------------------------------------------
def test_simulate_gain_positif_site_complet(db_session):
    """Site CDC + spot + archetype COMMERCE_ALIMENTAIRE -> gain > 0 coherent."""
    now = datetime(2026, 4, 15, 12, 0)
    site = _seed_site(db_session, archetype_code="COMMERCE_ALIMENTAIRE")
    _seed_cdc(db_session, site.id, now=now, days=30, kwh_per_hour=50.0)
    _seed_spot(db_session, now=now, days=30)

    result = simulate_nebco_gain(site, db_session, period_days=30, now=now)

    # Invariants structurels
    assert result["site_id"] == str(site.id)
    assert result["confiance"] == "indicative"
    assert "Baromètre Flex 2026" in result["source"]
    assert result["hypotheses"]["archetype"] == "COMMERCE_ALIMENTAIRE"
    assert result["hypotheses"]["taux_decalable_archetype"] == pytest.approx(0.45)
    assert result["hypotheses"]["compensation_ratio"] == pytest.approx(0.30)

    # Gain coherent
    assert result["kwh_decales_total"] > 0
    assert result["composantes"]["gain_spread_eur"] > 0
    assert result["composantes"]["net_eur"] > 0
    assert result["composantes"]["gain_spread_eur"] > result["composantes"]["compensation_fournisseur_eur"]
    assert result["spread_moyen_eur_mwh"] > 0


# ---------------------------------------------------------------------------
# Test 2 : pas de CDC -> gain 0 + trace
# ---------------------------------------------------------------------------
def test_simulate_pas_de_cdc_gain_zero(db_session):
    """Site sans MeterReading -> gain 0 + trace 'cdc_indisponible'."""
    now = datetime(2026, 4, 15, 12, 0)
    site = _seed_site(db_session, archetype_code="BUREAU_STANDARD")
    # Pas de CDC seedee, pas de spot non plus (pas necessaire)

    result = simulate_nebco_gain(site, db_session, period_days=30, now=now)

    assert result["gain_simule_eur"] == 0.0
    assert result["kwh_decales_total"] == 0.0
    assert result["n_fenetres_favorables"] == 0
    assert result["composantes"]["gain_spread_eur"] == 0.0
    assert result["composantes"]["compensation_fournisseur_eur"] == 0.0
    assert result["composantes"]["net_eur"] == 0.0
    assert "cdc_indisponible" in result["hypotheses"]["source_calibration"]


# ---------------------------------------------------------------------------
# Test 3 : pas de spot -> fallback 60 EUR/MWh
# ---------------------------------------------------------------------------
def test_simulate_pas_de_spot_fallback_60(db_session):
    """Site avec CDC mais 0 MktPrice -> spread fallback 60 EUR/MWh."""
    now = datetime(2026, 4, 15, 12, 0)
    site = _seed_site(db_session, archetype_code="COMMERCE_ALIMENTAIRE")
    _seed_cdc(db_session, site.id, now=now, days=30, kwh_per_hour=50.0)
    # Pas de spot seede

    result = simulate_nebco_gain(site, db_session, period_days=30, now=now)

    assert result["spread_moyen_eur_mwh"] == pytest.approx(60.0)
    assert "spot_fallback_60" in result["hypotheses"]["source_calibration"]
    # Gain > 0 car CDC x taux x 60 EUR/MWh
    assert result["kwh_decales_total"] > 0
    assert result["composantes"]["net_eur"] > 0


# ---------------------------------------------------------------------------
# Test 4 : archetype inconnu -> fallback BUREAU_STANDARD
# ---------------------------------------------------------------------------
def test_simulate_archetype_inconnu_fallback_bureau(db_session):
    """Site avec archetype_code=None -> fallback BUREAU_STANDARD + trace."""
    now = datetime(2026, 4, 15, 12, 0)
    site = _seed_site(db_session, archetype_code=None)
    _seed_cdc(db_session, site.id, now=now, days=30, kwh_per_hour=50.0)
    _seed_spot(db_session, now=now, days=30)

    result = simulate_nebco_gain(site, db_session, period_days=30, now=now)

    assert result["hypotheses"]["archetype"] == "BUREAU_STANDARD"
    assert result["hypotheses"]["taux_decalable_archetype"] == pytest.approx(0.30)
    assert "archetype_fallback_bureau" in result["hypotheses"]["source_calibration"]


def test_simulate_archetype_code_invalide_fallback_bureau(db_session):
    """archetype_code inconnu du calibrage -> fallback BUREAU_STANDARD."""
    now = datetime(2026, 4, 15, 12, 0)
    site = _seed_site(db_session, archetype_code="ARCHETYPE_INEXISTANT")
    _seed_cdc(db_session, site.id, now=now, days=30, kwh_per_hour=50.0)

    result = simulate_nebco_gain(site, db_session, period_days=30, now=now)

    assert result["hypotheses"]["archetype"] == "BUREAU_STANDARD"
    assert "archetype_fallback_bureau" in result["hypotheses"]["source_calibration"]


# ---------------------------------------------------------------------------
# Test 5 : clamp period_days
# ---------------------------------------------------------------------------
def test_simulate_period_days_clamp(db_session):
    """period_days < 7 -> clamp 7 ; > 90 -> clamp 90."""
    now = datetime(2026, 4, 15, 12, 0)
    site = _seed_site(db_session, archetype_code="BUREAU_STANDARD")
    # On seed 90 jours de CDC pour couvrir les deux scenarios
    _seed_cdc(db_session, site.id, now=now, days=95, kwh_per_hour=10.0)

    # Clamp a 7 jours
    res_short = simulate_nebco_gain(site, db_session, period_days=3, now=now)
    debut_short = datetime.fromisoformat(res_short["periode_debut"])
    fin_short = datetime.fromisoformat(res_short["periode_fin"])
    assert (fin_short - debut_short).days == 7

    # Clamp a 90 jours
    res_long = simulate_nebco_gain(site, db_session, period_days=120, now=now)
    debut_long = datetime.fromisoformat(res_long["periode_debut"])
    fin_long = datetime.fromisoformat(res_long["periode_fin"])
    assert (fin_long - debut_long).days == 90


# ---------------------------------------------------------------------------
# Test 6 : somme des composantes coherente
# ---------------------------------------------------------------------------
def test_simulate_composantes_somme_correcte(db_session):
    """gain_spread - compensation == net (a 0.01 EUR d'arrondi)."""
    now = datetime(2026, 4, 15, 12, 0)
    site = _seed_site(db_session, archetype_code="COMMERCE_ALIMENTAIRE")
    _seed_cdc(db_session, site.id, now=now, days=30, kwh_per_hour=50.0)
    _seed_spot(db_session, now=now, days=30)

    result = simulate_nebco_gain(site, db_session, period_days=30, now=now)
    c = result["composantes"]
    diff = c["gain_spread_eur"] - c["compensation_fournisseur_eur"]
    assert abs(diff - c["net_eur"]) < 0.02

    # compensation doit etre exactement 30% du gain_spread (a l'arrondi pres)
    assert abs(c["compensation_fournisseur_eur"] - (c["gain_spread_eur"] * 0.30)) < 0.02


# ---------------------------------------------------------------------------
# Test 7 : injection horloge -> dates exactes
# ---------------------------------------------------------------------------
def test_simulate_now_injection(db_session):
    """now=2026-04-15 + period_days=30 -> periode_debut=2026-03-16, fin=2026-04-15."""
    now = datetime(2026, 4, 15, 12, 0)
    site = _seed_site(db_session, archetype_code="BUREAU_STANDARD")
    # Pas besoin de CDC : on teste juste les bornes de date. Mais comme la
    # sortie 'cdc_indisponible' fournit deja les bornes, c'est valide.

    result = simulate_nebco_gain(site, db_session, period_days=30, now=now)

    assert result["periode_fin"] == "2026-04-15"
    assert result["periode_debut"] == "2026-03-16"


def test_simulate_now_injection_avec_cdc_et_spot(db_session):
    """Verifie la coherence des dates quand CDC + spot sont fournis."""
    now = datetime(2026, 2, 15, 10, 0)
    site = _seed_site(db_session, archetype_code="COMMERCE_ALIMENTAIRE")
    _seed_cdc(db_session, site.id, now=now, days=30, kwh_per_hour=50.0)
    _seed_spot(db_session, now=now, days=30)

    result = simulate_nebco_gain(site, db_session, period_days=30, now=now)

    assert result["periode_fin"] == "2026-02-15"
    assert result["periode_debut"] == "2026-01-16"
    # Gain effectivement calcule (non-zero)
    assert result["kwh_decales_total"] > 0
