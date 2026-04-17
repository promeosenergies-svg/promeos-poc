"""
PROMEOS - Radar prix negatifs J+7 (Piste 1 V1 innovation).

Contexte (Barometre Flex 2026) : 513h de prix spot negatifs en 2025 (+46% vs 2024).
Les agregateurs voient H-1, PROMEOS doit voir J+7 grace a une prediction simple
sur historique day-ahead FR.

Approche MVP (sans ML) :
    - Fenetre d'analyse : 90 derniers jours de MktPrice day-ahead zone FR.
    - Pour chaque jour cible (J+1 a J+horizon), on regarde les memes jours de
      la semaine (lun/mar/...) du meme mois dans l'historique.
    - Si > 30 % des creneaux 10h-17h ont ete a prix negatif ce jour-semaine
      la, on emet une fenetre "favorable probable".
    - Probabilite = moyenne observee (part de creneaux negatifs dans la plage
      10h-17h des jours semblables).
    - Prix estime min = mediane des valeurs negatives observees (EUR/MWh).
    - Usages recommandes = liste fixe (ecs, ve_recharge, pre_charge_froid)
      calibree sur le Barometre Flex 2026.

Fallback gracieux :
    - < 30 jours d'historique => liste vide.
    - Aucun creneau negatif historique => liste vide.

Wording doctrine (cf. docs_ux_demo_strategy) : cote client on parle de
"fenetre favorable probable" (pas "prix negatif") -- cette couche renvoie les
donnees brutes, le front se charge du wording.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from statistics import median
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models.market_models import MarketType, MktPrice, PriceZone


# Fuseau reference France (timestamps Europe/Paris aware cote sortie)
_TZ_PARIS = ZoneInfo("Europe/Paris")

# Fenetre historique analysee
_HISTORY_DAYS = 90

# Seuil minimum d'historique pour produire une prediction (fallback si < 30j)
_MIN_HISTORY_DAYS = 30

# Plage horaire etudiee (surplus PV midi -> debut apres-midi)
_WINDOW_START_H = 10
_WINDOW_END_H = 17  # exclusif cote hours 10..16 => 7 creneaux horaires

# Seuil de recurrence : % creneaux negatifs parmi jours semblables pour emettre
_NEG_SHARE_THRESHOLD = 0.30

# Usages recommandes lorsqu'une fenetre favorable probable est detectee.
# Calibre sur Barometre Flex 2026 (flex diffuse residentielle/tertiaire).
_USAGES_RECOMMANDES = ["ecs", "ve_recharge", "pre_charge_froid"]


def _to_paris(dt: datetime) -> datetime:
    """Normalise un datetime en Europe/Paris (assume UTC si naif)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ_PARIS)


def predict_negative_windows(
    horizon_days: int = 7,
    db: Optional[Session] = None,
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """
    Predit les fenetres J+1..J+horizon probables en prix negatif.

    Parametres
    ----------
    horizon_days : int
        Nombre de jours a projeter (1..14). Defaut 7.
    db : Session
        Session SQLAlchemy (requis pour lire MktPrice). Si None, retourne [].
    now : datetime, optionnel
        Injection d'horloge pour tests. Defaut : datetime.now(Europe/Paris).

    Retour
    ------
    Liste de fenetres predites (dict) :
        - datetime_debut : ISO 8601 Europe/Paris aware
        - datetime_fin   : ISO 8601 Europe/Paris aware
        - probabilite    : float dans [0, 1]
        - prix_estime_min_eur_mwh : float (median des valeurs negatives)
        - usages_recommandes : list[str]
        - base_historique_jours  : int (nb de jours semblables observes)
    """
    if db is None:
        return []

    # Borne horizon de facon robuste (1..14)
    horizon_days = max(1, min(int(horizon_days), 14))

    now_paris = _to_paris(now) if now is not None else datetime.now(_TZ_PARIS)
    today_paris = now_paris.date()
    history_start_utc = (now_paris - timedelta(days=_HISTORY_DAYS)).astimezone(timezone.utc)

    # -----------------------------------------------------------------
    # 1) Chargement historique day-ahead FR sur 90 jours glissants.
    # -----------------------------------------------------------------
    rows = (
        db.query(MktPrice)
        .filter(
            MktPrice.zone == PriceZone.FR,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start >= history_start_utc,
            MktPrice.delivery_start < now_paris.astimezone(timezone.utc),
        )
        .all()
    )

    if not rows:
        return []

    # -----------------------------------------------------------------
    # 2) Regroupement par (weekday, month). Pour chaque paire on agrege :
    #      - jours distincts observes (pour gate _MIN_HISTORY_DAYS),
    #      - total de creneaux 10h-17h et nb negatifs,
    #      - prix negatifs observes (pour mediane).
    # -----------------------------------------------------------------
    stats: dict[tuple[int, int], dict[str, Any]] = defaultdict(
        lambda: {
            "days": set(),
            "slots_total": 0,
            "slots_negative": 0,
            "neg_prices": [],
        }
    )

    for row in rows:
        start_paris = _to_paris(row.delivery_start)
        hour = start_paris.hour
        if not (_WINDOW_START_H <= hour < _WINDOW_END_H):
            continue
        key = (start_paris.weekday(), start_paris.month)
        bucket = stats[key]
        bucket["days"].add(start_paris.date())
        bucket["slots_total"] += 1
        price = float(row.price_eur_mwh)
        if price < 0:
            bucket["slots_negative"] += 1
            bucket["neg_prices"].append(price)

    # Gate global : si l'historique couvre < 30 jours distincts => fallback vide
    all_days: set = set()
    for bucket in stats.values():
        all_days.update(bucket["days"])
    if len(all_days) < _MIN_HISTORY_DAYS:
        return []

    # -----------------------------------------------------------------
    # 3) Projection J+1..J+horizon.
    # -----------------------------------------------------------------
    predictions: list[dict[str, Any]] = []
    for offset in range(1, horizon_days + 1):
        target_date = today_paris + timedelta(days=offset)
        key = (target_date.weekday(), target_date.month)
        bucket = stats.get(key)
        if not bucket or bucket["slots_total"] == 0:
            continue
        neg_share = bucket["slots_negative"] / bucket["slots_total"]
        if neg_share < _NEG_SHARE_THRESHOLD:
            continue

        # Prix estime : mediane des valeurs negatives (fallback -5 EUR/MWh)
        if bucket["neg_prices"]:
            prix_min = float(median(bucket["neg_prices"]))
        else:
            prix_min = -5.0

        # Bornes fenetre prediction (Europe/Paris aware)
        dt_debut = datetime.combine(
            target_date,
            time(hour=_WINDOW_START_H, minute=0),
            tzinfo=_TZ_PARIS,
        )
        dt_fin = datetime.combine(
            target_date,
            time(hour=_WINDOW_END_H, minute=0),
            tzinfo=_TZ_PARIS,
        )

        predictions.append(
            {
                "datetime_debut": dt_debut.isoformat(),
                "datetime_fin": dt_fin.isoformat(),
                "probabilite": round(min(max(neg_share, 0.0), 1.0), 3),
                "prix_estime_min_eur_mwh": round(prix_min, 2),
                "usages_recommandes": list(_USAGES_RECOMMANDES),
                "base_historique_jours": len(bucket["days"]),
            }
        )

    return predictions
