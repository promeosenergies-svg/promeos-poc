"""
PROMEOS - Simulation NEBCO sur CDC reelle (Vague 2 Piste 4 INNOVATION_ROADMAP).

Differenciateur demo : "voici les 1847 EUR que vous auriez gagnes le mois
dernier en decalant vos usages vers les fenetres favorables". Preuve chiffree
sans engagement agregateur, alimentee par la CDC reelle du site + les prix
spot ENTSO-E FR + le calibrage archetype du Barometre Flex 2026.

Logique :

    1. Periode glissante : [now - period_days, now], avec period_days borne
       a [7, 90] jours (hors de ces bornes -> clamp).
    2. Chargement CDC : tous les `MeterReading` HOURLY des compteurs actifs
       du site sur la periode.
    3. Classification horaire via `window_detector.classify_slots` : chaque
       heure FAVORABLE / SENSIBLE / NEUTRE selon le prix spot + TURPE 7.
    4. Spread spot = prix moyen SENSIBLE - prix moyen FAVORABLE (EUR/MWh).
       Fallback 60 EUR/MWh si aucun prix n'est disponible (hypothese MVP
       Barometre Flex 2026).
    5. Volume decalable = kWh SENSIBLE x taux_decalable_archetype (0.30
       pour BUREAU_STANDARD, 0.45 COMMERCE_ALIMENTAIRE, etc.).
    6. Gain spread brut = volume x spread / 1000 (MWh -> kWh).
    7. Compensation fournisseur historique : 30% du gain brut (hypothese
       MVP NEBCO). Le net reverse au site = gain_spread - compensation.

Confiance : "indicative" - ordre de grandeur MVP, pas un engagement
commercial. Les hypotheses sont toujours exposees pour traceabilite.

Sources :
    - Barometre Flex 2026 (RTE / Enedis / GIMELEC, avril 2026)
    - CDC Enedis SF4 (flux mesures horaires)
    - Spot ENTSO-E day-ahead FR (MktPrice)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models.energy_models import FrequencyType, Meter, MeterReading
from models.enums import EnergyVector
from models.market_models import MarketType, MktPrice, PriceZone, Resolution
from services.pilotage.constants import ARCHETYPE_CALIBRATION_2024
from services.pilotage.window_detector import (
    SlotMarket,
    WindowType,
    classify_slots,
    compute_price_thresholds,
)

logger = logging.getLogger(__name__)

_TZ_PARIS = ZoneInfo("Europe/Paris")

# --- Fallbacks defensifs ------------------------------------------------------

# Archetype fallback quand le site n'a pas d'archetype_code ou code inconnu.
_DEFAULT_ARCHETYPE: str = "BUREAU_STANDARD"

# Spread spot moyen fallback (EUR/MWh) quand aucun prix n'est disponible en DB.
# Source : Barometre Flex 2026 (RTE/Enedis), ordre de grandeur 2025-2026
# entre prix SENSIBLE (pics matin/soir hiver) et FAVORABLE (surplus PV midi).
_SPREAD_FALLBACK_EUR_MWH: float = 60.0

# Part du gain reversee au fournisseur historique (hypothese MVP NEBCO).
# Modele simplifie avant finalisation de l'accord agregateur.
_COMPENSATION_RATIO: float = 0.30

# Bornes de clamp pour period_days (evite les periodes trop courtes ou trop
# longues qui biaisent la statistique ou ralentissent la requete DB).
_PERIOD_DAYS_MIN: int = 7
_PERIOD_DAYS_MAX: int = 90

# Citation source canonique exposee au payload.
_SOURCE_CITATION: str = "Baromètre Flex 2026 (RTE/Enedis/GIMELEC) + CDC Enedis SF4 + spot ENTSO-E FR"


@dataclass(frozen=True)
class _SimulationContext:
    """Contexte interne : periode + archetype resolu + calibrage associe."""

    now: datetime
    periode_debut: datetime
    periode_fin: datetime
    archetype: str
    taux_decalable: float
    source_calibration: str


def _clamp_period_days(period_days: int) -> int:
    """Borne `period_days` a [_PERIOD_DAYS_MIN, _PERIOD_DAYS_MAX]."""
    if period_days < _PERIOD_DAYS_MIN:
        logger.warning(
            "nebco_simulation: period_days=%d < %d, clamp a %d",
            period_days,
            _PERIOD_DAYS_MIN,
            _PERIOD_DAYS_MIN,
        )
        return _PERIOD_DAYS_MIN
    if period_days > _PERIOD_DAYS_MAX:
        logger.warning(
            "nebco_simulation: period_days=%d > %d, clamp a %d",
            period_days,
            _PERIOD_DAYS_MAX,
            _PERIOD_DAYS_MAX,
        )
        return _PERIOD_DAYS_MAX
    return period_days


def _resolve_archetype(site) -> tuple[str, float, str]:
    """
    Resout l'archetype du site + taux_decalable + trace source.

    Retour : (archetype_code, taux_decalable_moyen, source_trace)
        - archetype_code : code resolu (fallback BUREAU_STANDARD si inconnu)
        - taux_decalable : fraction 0-1 depuis ARCHETYPE_CALIBRATION_2024
        - source_trace   : "archetype_site" | "fallback_bureau" selon la trace
    """
    code = getattr(site, "archetype_code", None)
    if code and code in ARCHETYPE_CALIBRATION_2024:
        calib = ARCHETYPE_CALIBRATION_2024[code]
        return code, float(calib["taux_decalable_moyen"]), "archetype_site"

    # Fallback : archetype manquant ou inconnu -> BUREAU_STANDARD
    calib = ARCHETYPE_CALIBRATION_2024[_DEFAULT_ARCHETYPE]
    return _DEFAULT_ARCHETYPE, float(calib["taux_decalable_moyen"]), "fallback_bureau"


def _load_cdc_readings(
    site_id: int,
    periode_debut: datetime,
    periode_fin: datetime,
    db: Session,
) -> dict[datetime, float]:
    """
    Charge la CDC horaire du site sur la periode.

    Regroupe par timestamp (somme des kWh des compteurs actifs) pour eviter
    les double-comptes sur les sites multi-compteurs. Retourne un dict
    {timestamp_naive_paris: kWh_total}.
    """
    # Conversion timestamp vers naif pour matcher le storage MeterReading
    # (timestamps stockes en naif Europe/Paris dans la convention PROMEOS)
    debut = periode_debut.replace(tzinfo=None) if periode_debut.tzinfo else periode_debut
    fin = periode_fin.replace(tzinfo=None) if periode_fin.tzinfo else periode_fin

    # Fix P0 audit Vague 2 : filtrer explicitement sur ELECTRICITY.
    # Un site multi-vecteur (elec + gaz) risquait d'additionner les kWh gaz
    # dans le volume decalable puis d'appliquer le taux decalable tertiaire
    # elec et le spread spot elec -> gain faux (x2-x3 selon mix).
    # Fix P1 : exclure `is_estimated=True` de la "preuve chiffree" -- les
    # extrapolations SF4 gonfleraient artificiellement le gain simule.
    rows = (
        db.query(MeterReading.timestamp, MeterReading.value_kwh)
        .join(Meter, MeterReading.meter_id == Meter.id)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.energy_vector == EnergyVector.ELECTRICITY,
            MeterReading.frequency == FrequencyType.HOURLY,
            MeterReading.is_estimated.is_(False),
            MeterReading.timestamp >= debut,
            MeterReading.timestamp <= fin,
        )
        .all()
    )

    agg: dict[datetime, float] = {}
    for ts, value in rows:
        agg[ts] = agg.get(ts, 0.0) + float(value or 0.0)
    return agg


def _load_spot_prices(
    periode_debut: datetime,
    periode_fin: datetime,
    db: Session,
) -> dict[datetime, float]:
    """
    Charge les prix spot ENTSO-E FR day-ahead horaires sur la periode.

    Les timestamps MktPrice sont tz-aware (UTC typiquement). On renvoie un
    dict {timestamp_naive_paris: prix_eur_mwh} pour l'alignement avec la CDC.
    """
    # Borner large : MktPrice.delivery_start peut etre en UTC, la periode
    # en Paris. On etend les bornes d'1h pour couvrir les decalages.
    debut_tz = periode_debut.astimezone(_TZ_PARIS) if periode_debut.tzinfo else periode_debut.replace(tzinfo=_TZ_PARIS)
    fin_tz = periode_fin.astimezone(_TZ_PARIS) if periode_fin.tzinfo else periode_fin.replace(tzinfo=_TZ_PARIS)

    rows = (
        db.query(MktPrice.delivery_start, MktPrice.price_eur_mwh)
        .filter(
            MktPrice.zone == PriceZone.FR,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.resolution == Resolution.PT60M,
            MktPrice.delivery_start >= debut_tz - timedelta(hours=1),
            MktPrice.delivery_start <= fin_tz + timedelta(hours=1),
        )
        .all()
    )

    out: dict[datetime, float] = {}
    for ts, price in rows:
        # Normaliser vers Paris naif pour l'alignement CDC
        if ts.tzinfo is not None:
            local = ts.astimezone(_TZ_PARIS).replace(tzinfo=None)
        else:
            local = ts
        # Arrondir a l'heure pleine pour stabiliser l'alignement
        local = local.replace(minute=0, second=0, microsecond=0)
        out[local] = float(price)
    return out


def _build_market_slots(spot: dict[datetime, float]) -> dict[datetime, SlotMarket]:
    """Convertit dict prix -> dict SlotMarket attendu par `classify_slots`."""
    return {ts: SlotMarket(prix_eur_mwh=price, prix_negatif=price < 0) for ts, price in spot.items()}


def _count_fenetres_favorables(
    classification: dict[datetime, object],
) -> int:
    """
    Compte le nombre de fenetres (plages contigues) FAVORABLE.

    Une fenetre = suite d'heures consecutives classees FAVORABLE. Les
    timestamps sont tries avant de detecter les ruptures de continuite.
    """
    if not classification:
        return 0

    tri = sorted(classification.keys())
    n = 0
    in_fenetre = False
    prev_ts: Optional[datetime] = None

    for ts in tri:
        is_fav = classification[ts].window_type == WindowType.FAVORABLE  # type: ignore[attr-defined]
        if is_fav:
            if not in_fenetre:
                # Nouvelle fenetre (soit premiere, soit rupture de continuite)
                n += 1
                in_fenetre = True
            elif prev_ts is not None and (ts - prev_ts) > timedelta(hours=1, minutes=5):
                # Rupture de continuite : nouvelle fenetre
                n += 1
        else:
            in_fenetre = False
        prev_ts = ts

    return n


def simulate_nebco_gain(
    site,
    db: Session,
    period_days: int = 30,
    now: Optional[datetime] = None,
) -> dict:
    """
    Simule le gain NEBCO qu'un site aurait obtenu sur les N derniers jours
    en decalant ses usages flexibles vers les fenetres FAVORABLES du marche.

    Parametres
    ----------
    site : models.Site
        Site avec `archetype_code` + `puissance_pilotable_kw` (peut etre None).
    db : Session
        Session DB SQLAlchemy.
    period_days : int
        Nombre de jours de la periode simulee. Clampe a [7, 90].
    now : datetime | None
        Horloge injectee pour tests. Default = `datetime.now(Europe/Paris)`.

    Retour
    ------
    dict conforme au contrat d'interface Vague 2 Piste 4 (cf. sprint doc).
    """
    # --- 1. Periode + horloge -------------------------------------------------
    period_days = _clamp_period_days(period_days)
    now_dt = now if now is not None else datetime.now(_TZ_PARIS)
    # Les tests injectent typiquement un naif : on le traite comme Paris local.
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=_TZ_PARIS)

    periode_fin = now_dt
    periode_debut = periode_fin - timedelta(days=period_days)

    # --- 2. Archetype + taux decalable ----------------------------------------
    archetype, taux_decalable, archetype_trace = _resolve_archetype(site)

    # --- 3. CDC lookup --------------------------------------------------------
    cdc = _load_cdc_readings(site.id, periode_debut, periode_fin, db)

    # Trace de calibration (source_calibration) : reflete les bascules fallback
    trace_parts: list[str] = []
    if not cdc:
        trace_parts.append("cdc_indisponible")
    if archetype_trace == "fallback_bureau":
        trace_parts.append("archetype_fallback_bureau")

    if not cdc:
        # Pas de CDC -> gain 0, trace explicite, on sort tot.
        return {
            "site_id": str(site.id),
            "periode_debut": periode_debut.date().isoformat(),
            "periode_fin": periode_fin.date().isoformat(),
            "gain_simule_eur": 0.0,
            "kwh_decales_total": 0.0,
            "n_fenetres_favorables": 0,
            "spread_moyen_eur_mwh": 0.0,
            "composantes": {
                "gain_spread_eur": 0.0,
                "compensation_fournisseur_eur": 0.0,
                "net_eur": 0.0,
            },
            "hypotheses": {
                "taux_decalable_archetype": taux_decalable,
                "compensation_ratio": _COMPENSATION_RATIO,
                "archetype": archetype,
                "source_calibration": ",".join(trace_parts) or "cdc_indisponible",
            },
            "confiance": "indicative",
            "source": _SOURCE_CITATION,
        }

    # --- 4. Spot lookup + classification --------------------------------------
    spot = _load_spot_prices(periode_debut, periode_fin, db)

    # Alignement : on ne classe que les heures ou on a au moins la CDC.
    # Pour les heures sans prix spot, on utilise une valeur neutre = mediane
    # des prix disponibles (ou 0 si aucun). Mais la classification necessite
    # des seuils qui exigent au minimum 1 prix. Si spot est vide -> fallback
    # 60 EUR/MWh sur l'ensemble et on construit une classification
    # synthetique par heure (matin/soir = SENSIBLE, midi/nuit = FAVORABLE).
    spot_disponible = bool(spot)
    if not spot_disponible:
        trace_parts.append("spot_fallback_60")

    classification: dict[datetime, object] = {}
    prix_favorable: list[float] = []
    prix_sensible: list[float] = []

    if spot_disponible:
        slots = _build_market_slots(spot)
        threshold_low, threshold_high = compute_price_thresholds(slots)
        classification = classify_slots(slots, threshold_low, threshold_high)  # type: ignore[assignment]

        # Calcul du spread observe
        for ts, cls in classification.items():
            p = spot.get(ts)
            if p is None:
                continue
            wt = cls.window_type  # type: ignore[attr-defined]
            if wt == WindowType.FAVORABLE:
                prix_favorable.append(p)
            elif wt == WindowType.SENSIBLE:
                prix_sensible.append(p)

    # --- 5. Spread moyen ------------------------------------------------------
    if prix_favorable and prix_sensible:
        spread_moyen = (sum(prix_sensible) / len(prix_sensible)) - (sum(prix_favorable) / len(prix_favorable))
        # Fix P0 audit Vague 2 : distinguer spread plat (0, serie stable) de
        # spread negatif (bug amont : thresholds inverses, donnees polluees).
        # Masquer les deux cas sous un seul label camouflerait les incidents.
        if spread_moyen < 0.0:
            logger.warning(
                "nebco_simulation: spread negatif observe (%.2f EUR/MWh) -- "
                "indice probable de thresholds inverses ou donnees polluees",
                spread_moyen,
            )
            spread_moyen = _SPREAD_FALLBACK_EUR_MWH
            trace_parts.append("spread_negatif_fallback_60")
        elif spread_moyen == 0.0:
            spread_moyen = _SPREAD_FALLBACK_EUR_MWH
            trace_parts.append("spread_plat_fallback_60")
    else:
        spread_moyen = _SPREAD_FALLBACK_EUR_MWH
        if spot_disponible:
            # Prix dispos mais pas les deux classes -> trace
            trace_parts.append("spread_classes_manquantes_fallback_60")

    # --- 6. Volume decalable --------------------------------------------------
    # Somme des kWh sur slots SENSIBLE. Si spot indisponible, on estime que
    # la CDC complete est potentiellement sensible (approximation MVP) et
    # on applique le taux_decalable directement sur le total.
    if spot_disponible:
        kwh_sensible_total = 0.0
        for ts, cls in classification.items():
            if cls.window_type == WindowType.SENSIBLE:  # type: ignore[attr-defined]
                # On cumule les kWh CDC qui tombent sur ce timestamp
                kwh_sensible_total += cdc.get(ts, 0.0)
    else:
        # Sans spot, toute la conso est consideree potentiellement decalable
        # (hypothese conservatrice MVP, tracee dans source_calibration).
        kwh_sensible_total = sum(cdc.values())

    kwh_decales_total = kwh_sensible_total * taux_decalable

    # --- 7. Calcul gain -------------------------------------------------------
    gain_spread_eur = kwh_decales_total * (spread_moyen / 1000.0)
    compensation_fournisseur_eur = gain_spread_eur * _COMPENSATION_RATIO
    net_eur = gain_spread_eur - compensation_fournisseur_eur

    # --- 8. Fenetres favorables (contigues) -----------------------------------
    n_fenetres_favorables = _count_fenetres_favorables(classification) if spot_disponible else 0

    # --- 9. Trace finale ------------------------------------------------------
    source_calibration = ",".join(trace_parts) if trace_parts else "nominal"

    return {
        "site_id": str(site.id),
        "periode_debut": periode_debut.date().isoformat(),
        "periode_fin": periode_fin.date().isoformat(),
        "gain_simule_eur": round(net_eur, 0),
        "kwh_decales_total": round(kwh_decales_total, 2),
        "n_fenetres_favorables": n_fenetres_favorables,
        "spread_moyen_eur_mwh": round(spread_moyen, 2),
        "composantes": {
            "gain_spread_eur": round(gain_spread_eur, 2),
            "compensation_fournisseur_eur": round(compensation_fournisseur_eur, 2),
            "net_eur": round(net_eur, 2),
        },
        "hypotheses": {
            "taux_decalable_archetype": taux_decalable,
            "compensation_ratio": _COMPENSATION_RATIO,
            "archetype": archetype,
            "source_calibration": source_calibration,
        },
        "confiance": "indicative",
        "source": _SOURCE_CITATION,
    }


__all__ = ["simulate_nebco_gain"]
