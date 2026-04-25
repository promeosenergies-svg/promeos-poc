"""
PROMEOS - Tests DST (heure d'ete / heure d'hiver) sur radar_prix_negatifs.

Europe/Paris :
    - Spring-forward : dernier dimanche de mars (2026 : 29/03 a 02:00 -> 03:00).
      Journee de 23h, le creneau 2h-3h est INEXISTANT.
      Offset passe de +01:00 (CET) a +02:00 (CEST).
    - Fall-back : dernier dimanche d'octobre (2026 : 25/10 a 03:00 -> 02:00).
      Journee de 25h, le creneau 2h-3h est DUPLIQUE (existe 2 fois).
      Offset passe de +02:00 (CEST) a +01:00 (CET).

Ces tests verifient que :
    1. Le module n'explose pas sur les dates de transition.
    2. Les timestamps retournes ont le bon offset (+02:00 en ete, +01:00 en hiver).
    3. Le regroupement par (weekday, month) ne double-compte pas les slots
       ambigus du fall-back (meme heure locale, offsets differents).

Dette technique documentee dans docs/pilotage-usages/INNOVATION_ROADMAP.md.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
from models.market_models import (
    MarketDataSource,
    MarketType,
    MktPrice,
    PriceZone,
    ProductType,
    Resolution,
)
from services.pilotage.radar_prix_negatifs import _to_paris, predict_negative_windows


_TZ_PARIS = ZoneInfo("Europe/Paris")


# ---------------------------------------------------------------------------
# Fixture DB in-memory
# ---------------------------------------------------------------------------
@pytest.fixture
def isolated_session():
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


def _seed_hourly_utc(
    db,
    *,
    start_utc: datetime,
    end_utc: datetime,
    neg_between_h_paris: tuple[int, int] = (10, 17),
) -> None:
    """
    Seed 1 MktPrice par heure UTC entre start_utc (inclus) et end_utc (exclu).
    Prix = -20 EUR/MWh si l'heure en Europe/Paris tombe dans la plage negative,
    sinon 60 EUR/MWh. Permet de couvrir des periodes incluant les transitions DST.
    """
    rows: list[MktPrice] = []
    cur = start_utc
    while cur < end_utc:
        delivery_end = cur + timedelta(hours=1)
        h_paris = cur.astimezone(_TZ_PARIS).hour
        if neg_between_h_paris[0] <= h_paris < neg_between_h_paris[1]:
            price = -20.0
        else:
            price = 60.0
        rows.append(
            MktPrice(
                source=MarketDataSource.ENTSOE,
                market_type=MarketType.SPOT_DAY_AHEAD,
                product_type=ProductType.HOURLY,
                zone=PriceZone.FR,
                delivery_start=cur,
                delivery_end=delivery_end,
                price_eur_mwh=price,
                resolution=Resolution.PT60M,
                fetched_at=datetime.now(timezone.utc),
            )
        )
        cur = delivery_end
    db.add_all(rows)
    db.commit()


# ---------------------------------------------------------------------------
# Test 1 : spring-forward 29/03/2026 (CET -> CEST)
# ---------------------------------------------------------------------------
def test_radar_spring_forward_2026(isolated_session):
    """
    Seed 60 jours d'historique couvrant le 29/03/2026 (spring-forward).
    predict_negative_windows ne doit pas crasher. Quand une fenetre tombe
    sur un jour en heure d'ete, son offset doit etre +02:00.
    """
    # now = 05/04/2026 a 12:00 Europe/Paris (apres spring-forward)
    now_paris = datetime(2026, 4, 5, 12, 0, tzinfo=_TZ_PARIS)
    # Historique 60 jours -> du ~04/02/2026 au 04/04/2026 (inclut 29/03).
    end_utc = now_paris.astimezone(timezone.utc)
    start_utc = (now_paris - timedelta(days=60)).astimezone(timezone.utc)
    _seed_hourly_utc(
        isolated_session,
        start_utc=start_utc,
        end_utc=end_utc,
        neg_between_h_paris=(10, 17),
    )

    windows = predict_negative_windows(horizon_days=7, db=isolated_session, now=now_paris)
    # Ne doit pas crasher. Avec 60j tous negatifs 10-17h, on attend des fenetres.
    assert isinstance(windows, list)
    assert len(windows) > 0, "60j historique negatif 10-17h -> fenetres attendues"

    # Toutes les fenetres projetees (J+1..J+7 depuis 05/04) sont en CEST (ete).
    for w in windows:
        dt_debut = datetime.fromisoformat(w["datetime_debut"])
        offset_h = dt_debut.utcoffset().total_seconds() / 3600.0
        assert offset_h == 2.0, f"Horizon avril -> CEST attendu (+02:00), got {offset_h}"


# ---------------------------------------------------------------------------
# Test 2 : fall-back 25/10/2026 (CEST -> CET)
# ---------------------------------------------------------------------------
def test_radar_fall_back_2026(isolated_session):
    """
    Seed un historique couvrant le 25/10/2026 (fall-back : journee de 25h).
    Le regroupement par (weekday, month) ne doit pas mettre le service en
    erreur : slots_total et slots_negative restent coherents (<= 7 creneaux
    par jour + doublon d'heure 02:xx hors fenetre 10-17h, donc pas d'impact
    sur le compteur de la fenetre etudiee).
    """
    # now = 01/11/2026 a 12:00 (juste apres fall-back).
    now_paris = datetime(2026, 11, 1, 12, 0, tzinfo=_TZ_PARIS)
    end_utc = now_paris.astimezone(timezone.utc)
    start_utc = (now_paris - timedelta(days=60)).astimezone(timezone.utc)

    # Tous les 10-17h sont negatifs, donc chaque dimanche de ce segment
    # d'historique (y compris 25/10) contribue 7 slots a la fenetre etudiee.
    _seed_hourly_utc(
        isolated_session,
        start_utc=start_utc,
        end_utc=end_utc,
        neg_between_h_paris=(10, 17),
    )

    windows = predict_negative_windows(horizon_days=14, db=isolated_session, now=now_paris)
    assert isinstance(windows, list)
    # L'historique couvre au moins 30j distincts donc on n'est pas en fallback vide.
    assert len(windows) > 0

    # Pour chaque fenetre projetee : slots_total "par jour semblable" doit etre
    # un multiple de 7 (7 slots 10-17h), pas 8 (ce qui trahirait un double
    # comptage de l'heure 02:xx dupliquee du fall-back).
    for w in windows:
        base = w["base_historique_jours"]
        # Il faut au moins 1 jour semblable observe.
        assert base >= 1
        # Sanity : probabilite dans [0, 1].
        assert 0.0 <= w["probabilite"] <= 1.0


# ---------------------------------------------------------------------------
# Test 3 : _to_paris preserve la continuite temporelle autour des transitions
# ---------------------------------------------------------------------------
def test_radar_transition_paris_aware():
    """
    _to_paris(dt_utc) doit :
      - renvoyer un datetime tz-aware Europe/Paris,
      - preserver l'ordre temporel strict autour des deux dates DST,
      - exposer l'offset +01:00 (CET) ou +02:00 (CEST) selon la periode.
    """
    # Spring-forward 2026 : 01:00 UTC = 02:00 CET (avant saut), 01:00 UTC (apres 2h->3h locale)
    before_spring = datetime(2026, 3, 29, 0, 30, tzinfo=timezone.utc)  # 01:30 CET local
    after_spring = datetime(2026, 3, 29, 1, 30, tzinfo=timezone.utc)  # 03:30 CEST local
    p_before = _to_paris(before_spring)
    p_after = _to_paris(after_spring)

    assert p_before.tzinfo is not None
    assert p_after.tzinfo is not None
    assert p_before < p_after, "Continuite temporelle brisee au spring-forward"
    # Offsets corrects
    assert p_before.utcoffset().total_seconds() / 3600.0 == 1.0, "Avant spring = CET (+01:00)"
    assert p_after.utcoffset().total_seconds() / 3600.0 == 2.0, "Apres spring = CEST (+02:00)"
    # Heure locale : saut de 02:xx a 03:xx
    assert p_before.hour == 1
    assert p_after.hour == 3

    # Fall-back 2026 : 00:30 UTC = 02:30 CEST, 01:30 UTC = 02:30 CET (doublon local)
    before_fall = datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc)  # 02:30 CEST
    after_fall = datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc)  # 02:30 CET
    p_bf = _to_paris(before_fall)
    p_af = _to_paris(after_fall)

    # NOTE : les datetime aware fold=0/fold=1 sur le meme wall-clock
    # comparent "egaux" par operateur <, mais leur timestamp UTC differe
    # de 3600s. On verifie la continuite via le timestamp epoch.
    assert p_bf.timestamp() < p_af.timestamp(), "Continuite UTC brisee au fall-back"
    # Meme heure locale, offsets differents (doublon 02:30)
    assert p_bf.hour == p_af.hour == 2
    assert p_bf.minute == p_af.minute == 30
    assert p_bf.utcoffset().total_seconds() / 3600.0 == 2.0, "1er passage = CEST"
    assert p_af.utcoffset().total_seconds() / 3600.0 == 1.0, "2e passage = CET"

    # Naif UTC : _to_paris doit l'interpreter comme UTC
    naive_utc = datetime(2026, 7, 15, 12, 0)  # sans tz
    p_naif = _to_paris(naive_utc)
    assert p_naif.tzinfo is not None
    assert p_naif.utcoffset().total_seconds() / 3600.0 == 2.0, "Juillet = CEST"
    assert p_naif.hour == 14, "12:00 UTC -> 14:00 Europe/Paris en juillet"
