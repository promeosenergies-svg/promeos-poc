"""
PROMEOS - Tests Radar prix negatifs J+7 (Piste 1 V1 innovation).

Couvre :
    1. Endpoint horizon par defaut = 7 jours.
    2. Fallback gracieux : aucune donnee historique => liste vide.
    3. Probabilite toujours dans [0, 1].
    4. Timestamps ISO 8601 aware Europe/Paris.
    5. Endpoint repond 200 et le payload respecte le schema Pydantic.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base
from models.market_models import (
    MarketDataSource,
    MarketType,
    MktPrice,
    PriceZone,
    ProductType,
    Resolution,
)
from services.pilotage.radar_prix_negatifs import predict_negative_windows


_TZ_PARIS = ZoneInfo("Europe/Paris")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def isolated_session():
    """Session DB SQLite in-memory isolee (sans override FastAPI)."""
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


@pytest.fixture
def client():
    """TestClient FastAPI + DB in-memory dediee."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def _override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    c = TestClient(app, raise_server_exceptions=False)
    # Expose la factory pour que les tests puissent seeder la meme DB.
    c.session_factory = SessionLocal  # type: ignore[attr-defined]
    yield c
    app.dependency_overrides.clear()


def _seed_history(
    db,
    *,
    now: datetime,
    days: int = 60,
    neg_share_in_window: float = 0.7,
) -> None:
    """
    Seed `days` jours d'historique day-ahead FR : pour chaque jour, 24 points
    horaires dont une fraction `neg_share_in_window` est negative dans la
    fenetre 10h-17h (les autres heures sont neutres positives).
    """
    rows: list[MktPrice] = []
    for d in range(1, days + 1):
        day = now - timedelta(days=d)
        for h in range(24):
            delivery_start = datetime(day.year, day.month, day.day, h, 0, tzinfo=timezone.utc)
            delivery_end = delivery_start + timedelta(hours=1)
            if 10 <= h < 17:
                # On force une part negative dans la fenetre etudiee
                price = -20.0 if (h - 10) / 7.0 < neg_share_in_window else 45.0
            else:
                price = 60.0
            rows.append(
                MktPrice(
                    source=MarketDataSource.ENTSOE,
                    market_type=MarketType.SPOT_DAY_AHEAD,
                    product_type=ProductType.HOURLY,
                    zone=PriceZone.FR,
                    delivery_start=delivery_start,
                    delivery_end=delivery_end,
                    price_eur_mwh=price,
                    resolution=Resolution.PT60M,
                    fetched_at=datetime.now(timezone.utc),
                )
            )
    db.add_all(rows)
    db.commit()


# ---------------------------------------------------------------------------
# Test 1 : endpoint horizon par defaut = 7 jours
# ---------------------------------------------------------------------------
def test_radar_horizon_default_7j(client):
    """L'endpoint sans parametre doit utiliser horizon_jours = 7."""
    r = client.get("/api/pilotage/radar-prix-negatifs")
    assert r.status_code == 200
    data = r.json()
    assert data["horizon_jours"] == 7
    assert "fenetres_predites" in data
    assert isinstance(data["fenetres_predites"], list)


# ---------------------------------------------------------------------------
# Test 2 : pas de crash si aucune donnee historique => liste vide
# ---------------------------------------------------------------------------
def test_radar_no_history_returns_empty(isolated_session):
    """Sans donnees MktPrice en DB, la prediction doit etre vide (pas de crash)."""
    result = predict_negative_windows(horizon_days=7, db=isolated_session)
    assert result == []


def test_radar_history_too_short_returns_empty(isolated_session):
    """Avec < 30 jours d'historique, fallback gracieux = liste vide."""
    now_utc = datetime.now(timezone.utc)
    _seed_history(isolated_session, now=now_utc, days=10, neg_share_in_window=0.9)
    result = predict_negative_windows(horizon_days=7, db=isolated_session)
    assert result == []


# ---------------------------------------------------------------------------
# Test 3 : probabilite dans [0, 1]
# ---------------------------------------------------------------------------
def test_radar_probabilite_entre_0_et_1(isolated_session):
    """Toute fenetre retournee a une probabilite dans [0, 1]."""
    now_utc = datetime.now(timezone.utc)
    _seed_history(isolated_session, now=now_utc, days=60, neg_share_in_window=0.8)
    windows = predict_negative_windows(horizon_days=7, db=isolated_session)
    assert len(windows) > 0, "Avec 60j d'historique fortement negatif on attend des fenetres"
    for w in windows:
        assert 0.0 <= w["probabilite"] <= 1.0
        assert isinstance(w["base_historique_jours"], int)
        assert w["base_historique_jours"] >= 1


# ---------------------------------------------------------------------------
# Test 4 : timestamps ISO 8601 aware Europe/Paris
# ---------------------------------------------------------------------------
def test_radar_timestamps_iso_europe_paris(isolated_session):
    """Les datetime retournes doivent etre ISO 8601 avec offset Europe/Paris."""
    now_utc = datetime.now(timezone.utc)
    _seed_history(isolated_session, now=now_utc, days=60, neg_share_in_window=0.8)
    windows = predict_negative_windows(horizon_days=7, db=isolated_session)
    assert windows, "Prerequis : au moins une fenetre predite"
    for w in windows:
        # Parse strict des ISO 8601
        dt_debut = datetime.fromisoformat(w["datetime_debut"])
        dt_fin = datetime.fromisoformat(w["datetime_fin"])
        # Doivent etre tz-aware
        assert dt_debut.tzinfo is not None
        assert dt_fin.tzinfo is not None
        # Offset Europe/Paris : +01:00 (hiver) ou +02:00 (ete)
        offset_h = dt_debut.utcoffset().total_seconds() / 3600.0
        assert offset_h in (1.0, 2.0), f"Offset inattendu : {offset_h}"
        # Debut avant fin
        assert dt_debut < dt_fin
        # Plage 10h-17h Europe/Paris
        assert dt_debut.astimezone(_TZ_PARIS).hour == 10
        assert dt_fin.astimezone(_TZ_PARIS).hour == 17


# ---------------------------------------------------------------------------
# Test 5 : endpoint 200 + schema Pydantic conforme
# ---------------------------------------------------------------------------
def test_radar_endpoint_200_et_schema(client):
    """L'endpoint repond 200 et le payload matche RadarPrixNegatifsResponse."""
    # Seed historique dans la meme DB que celle bindee au client
    SessionLocal = client.session_factory  # type: ignore[attr-defined]
    db = SessionLocal()
    try:
        _seed_history(db, now=datetime.now(timezone.utc), days=60, neg_share_in_window=0.8)
    finally:
        db.close()

    r = client.get("/api/pilotage/radar-prix-negatifs?horizon_days=7")
    assert r.status_code == 200
    data = r.json()

    # Schema racine
    assert set(data.keys()) >= {
        "fenetres_predites",
        "horizon_jours",
        "source",
        "confiance",
    }
    assert data["horizon_jours"] == 7
    assert data["source"] == "historique_entsoe_90j"
    assert data["confiance"] == "indicative"

    # Schema fenetre (si non-vide)
    for w in data["fenetres_predites"]:
        assert set(w.keys()) >= {
            "datetime_debut",
            "datetime_fin",
            "probabilite",
            "prix_estime_min_eur_mwh",
            "usages_recommandes",
            "base_historique_jours",
        }
        assert 0.0 <= w["probabilite"] <= 1.0
        assert isinstance(w["usages_recommandes"], list)
        assert w["usages_recommandes"], "usages_recommandes ne doit pas etre vide"
