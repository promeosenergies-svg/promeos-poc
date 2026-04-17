"""
PROMEOS - Window Detector : classification des slots J+7 en fenetres
FAVORABLE / SENSIBLE / NEUTRE.

Moteur pur (sans couplage DB) qui transforme une serie de slots de
signaux marche (prix spot, Tempo, RTE pointe) en classification horaire
utilisee par le module Pilotage des usages.

Integration S22 (avril 2026) : prise en compte des creneaux TURPE 7 HC
saisonnalises publies par le Barometre Flex 2026 (RTE / Enedis). Ces
creneaux sont traites comme un INDICE ADDITIONNEL au signal prix :

  - ils ne peuvent PAS inverser une classification deja donnee par le
    prix (un slot a prix bas reste FAVORABLE meme s'il tombe sur un
    creneau "a exclure", et reciproquement) ;
  - ils tranchent uniquement les slots marginaux (strictement entre
    threshold_low et threshold_high, classifies NEUTRE par le prix seul).

Sources :
  - Barometre Flex 2026 RTE/Enedis/GIMELEC/Think Smartgrids (avril 2026),
    section "Evolution Heures Creuses TURPE 7".
  - Enedis, communication TURPE 7 phase 2 (dec 2026 -> nov 2027) :
    saisonnalisation ete/hiver des plages HC residentielles + pro <=36 kVA.

Les slots sont indexes par leur timestamp de debut (datetime tz-aware ou
datetime naive interprete en Europe/Paris). Le pas temporel n'est pas
impose (support 15 min, 30 min, 1 h).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

from services.pilotage.constants import (
    HC_TURPE7_EXCLURE,
    HC_TURPE7_FAVORABLE,
    SAISON_BASSE_MOIS,
)


TZ_PARIS = ZoneInfo("Europe/Paris")


class WindowType(str, Enum):
    """Classification d'un slot issu de `classify_slots`."""

    FAVORABLE = "favorable"
    SENSIBLE = "sensible"
    NEUTRE = "neutre"


@dataclass(frozen=True)
class SlotMarket:
    """
    Signal marche sur un pas de temps (30 min par defaut).

    Attributs
    ---------
    prix_eur_mwh : float
        Prix spot day-ahead (EUR/MWh). Peut etre negatif (EnR excedentaire).
    prix_negatif : bool
        True si `prix_eur_mwh < 0`. Duplique pour clarte dans les logs.
    tempo_color : str | None
        Couleur Tempo EDF : "BLEU" | "BLANC" | "ROUGE" | None. ROUGE force
        la classification SENSIBLE quel que soit le prix.
    rte_pointe : bool
        True si RTE a declare une pointe (signal EcoWatt rouge). Force
        SENSIBLE.
    ecowatt : str | None
        Signal EcoWatt RTE : "vert" | "orange" | "rouge" | None.
        "orange" ou "rouge" forcent SENSIBLE.
    """

    prix_eur_mwh: float
    prix_negatif: bool = False
    tempo_color: Optional[str] = None
    rte_pointe: bool = False
    ecowatt: Optional[str] = None


@dataclass(frozen=True)
class SlotClassification:
    """Classification d'un slot produite par `classify_slots`."""

    window_type: WindowType
    # Raison dominante de la classification : "prix", "tempo_rouge",
    # "rte_pointe", "ecowatt", "turpe7_favorable", "turpe7_exclure",
    # "neutre". Utilisee pour tracer l'explication cockpit.
    raison: str = "prix"
    turpe7_favorable: bool = False
    turpe7_exclure: bool = False


# --- Helpers TURPE 7 HC saisonnalises ----------------------------------------


def _heure_locale(dt: datetime) -> tuple[int, int]:
    """
    Retourne (mois, heure) en heure locale Europe/Paris.

    Un datetime naif est interprete comme deja en heure locale Paris
    (convention interne module Pilotage).
    """
    if dt.tzinfo is None:
        local = dt.replace(tzinfo=TZ_PARIS)
    else:
        local = dt.astimezone(TZ_PARIS)
    return local.month, local.hour


def _saison(mois: int) -> str:
    """Retourne "ete" si le mois est en saison basse, "hiver" sinon."""
    return "ete" if mois in SAISON_BASSE_MOIS else "hiver"


def _heure_dans_plages(heure: int, plages: list[tuple[int, int]]) -> bool:
    """True si `heure` appartient a [h_debut, h_fin) pour au moins une plage."""
    return any(h_debut <= heure < h_fin for h_debut, h_fin in plages)


def is_hc_favorable(dt: datetime) -> bool:
    """
    True si `dt` tombe sur un creneau HC TURPE 7 *a favoriser*.

    Saison basse (avril-octobre) : 2h-6h + 11h-17h.
    Saison haute (nov-mars)     : 2h-6h + 21h-24h.

    Source : Barometre Flex 2026 (RTE/Enedis), section TURPE 7.
    """
    mois, heure = _heure_locale(dt)
    plages = HC_TURPE7_FAVORABLE[_saison(mois)]
    return _heure_dans_plages(heure, plages)


def is_hc_exclure(dt: datetime) -> bool:
    """
    True si `dt` tombe sur un creneau HC TURPE 7 *a exclure*.

    Saison basse (avril-octobre) : 7h-11h + 18h-23h.
    Saison haute (nov-mars)     : 7h-11h + 17h-21h.

    Source : Barometre Flex 2026 (RTE/Enedis), section TURPE 7.
    """
    mois, heure = _heure_locale(dt)
    plages = HC_TURPE7_EXCLURE[_saison(mois)]
    return _heure_dans_plages(heure, plages)


# --- Seuils de prix ----------------------------------------------------------


def compute_price_thresholds(
    slots: dict[datetime, SlotMarket],
    pct_low: float = 0.05,
    pct_high: float = 0.95,
) -> tuple[float, float]:
    """
    Calcule les seuils `threshold_low` / `threshold_high` de prix sur
    l'horizon de slots.

    Par defaut : 5e et 95e percentile. Les prix negatifs sont conserves
    tels quels (threshold_low peut etre < 0). Si la serie est homogene
    (tous les prix identiques), les deux seuils se confondent et aucun
    slot ne sera classifie FAVORABLE/SENSIBLE par le seul signal prix.

    Parametres
    ----------
    slots : dict[datetime, SlotMarket]
        Dictionnaire (non-vide) timestamp -> signal marche.
    pct_low, pct_high : float
        Percentiles bas et haut, dans [0, 1] avec pct_low <= pct_high.

    Retour
    ------
    (threshold_low, threshold_high) en EUR/MWh.
    """
    if not slots:
        raise ValueError("slots vide -- impossible de calculer les seuils")
    if not (0.0 <= pct_low <= pct_high <= 1.0):
        raise ValueError(f"percentiles invalides (pct_low={pct_low}, pct_high={pct_high})")

    prix = sorted(slot.prix_eur_mwh for slot in slots.values())
    n = len(prix)
    idx_low = max(0, int(pct_low * n))
    idx_high = min(n - 1, int(pct_high * n))
    return prix[idx_low], prix[idx_high]


# --- Classification des slots ------------------------------------------------


def classify_slots(
    slots: dict[datetime, SlotMarket],
    threshold_low: float,
    threshold_high: float,
) -> dict[datetime, SlotClassification]:
    """
    Classifie chaque slot en FAVORABLE / SENSIBLE / NEUTRE.

    Regles (ordre de priorite, premier match gagne)
    ------------------------------------------------
    1. Signaux reseau durs (non reversibles) :
         - Tempo ROUGE                      -> SENSIBLE
         - RTE pointe                        -> SENSIBLE
         - EcoWatt "orange" ou "rouge"       -> SENSIBLE
    2. Signal prix :
         - prix < threshold_low OU prix_negatif -> FAVORABLE
         - prix > threshold_high                -> SENSIBLE
         - sinon                                  -> candidat NEUTRE
    3. Indice TURPE 7 HC (S22, avril 2026) -- appliquee UNIQUEMENT aux
       candidats NEUTRE (sans alterer les slots deja classifies FAV/SEN
       par les regles 1 ou 2) :
         - creneau "a favoriser"  -> FAVORABLE (raison=turpe7_favorable)
         - creneau "a exclure"    -> SENSIBLE  (raison=turpe7_exclure)
         - ni l'un ni l'autre     -> NEUTRE

    Cette composition garantit que les creneaux TURPE 7 sont un INDICE
    ADDITIONNEL, jamais une substitution au signal prix : un slot a prix
    bas reste FAVORABLE meme s'il tombe sur un creneau "a exclure", et
    un slot a prix eleve reste SENSIBLE meme s'il tombe sur un creneau
    "a favoriser".

    Source TURPE 7 HC : Barometre Flex 2026 (RTE / Enedis / GIMELEC /
    Think Smartgrids), avril 2026, section "Evolution Heures Creuses
    TURPE 7" (phase 2 : dec 2026 -> nov 2027).

    Parametres
    ----------
    slots : dict[datetime, SlotMarket]
        Signaux marche indexes par timestamp de debut de slot.
    threshold_low, threshold_high : float
        Seuils de prix (EUR/MWh), typiquement issus de
        `compute_price_thresholds`.

    Retour
    ------
    dict[datetime, SlotClassification] de meme cardinalite que `slots`.
    """
    out: dict[datetime, SlotClassification] = {}
    for ts, slot in slots.items():
        # 1. Signaux reseau durs (forcent SENSIBLE)
        if slot.tempo_color == "ROUGE":
            out[ts] = SlotClassification(
                window_type=WindowType.SENSIBLE,
                raison="tempo_rouge",
                turpe7_favorable=is_hc_favorable(ts),
                turpe7_exclure=is_hc_exclure(ts),
            )
            continue
        if slot.rte_pointe:
            out[ts] = SlotClassification(
                window_type=WindowType.SENSIBLE,
                raison="rte_pointe",
                turpe7_favorable=is_hc_favorable(ts),
                turpe7_exclure=is_hc_exclure(ts),
            )
            continue
        if slot.ecowatt in ("orange", "rouge"):
            out[ts] = SlotClassification(
                window_type=WindowType.SENSIBLE,
                raison="ecowatt",
                turpe7_favorable=is_hc_favorable(ts),
                turpe7_exclure=is_hc_exclure(ts),
            )
            continue

        # 2. Signal prix
        prix = slot.prix_eur_mwh
        fav_hc = is_hc_favorable(ts)
        exc_hc = is_hc_exclure(ts)

        if slot.prix_negatif or prix < threshold_low:
            out[ts] = SlotClassification(
                window_type=WindowType.FAVORABLE,
                raison="prix",
                turpe7_favorable=fav_hc,
                turpe7_exclure=exc_hc,
            )
            continue
        if prix > threshold_high:
            out[ts] = SlotClassification(
                window_type=WindowType.SENSIBLE,
                raison="prix",
                turpe7_favorable=fav_hc,
                turpe7_exclure=exc_hc,
            )
            continue

        # 3. Slot marginal NEUTRE : l'indice TURPE 7 tranche
        if fav_hc and not exc_hc:
            out[ts] = SlotClassification(
                window_type=WindowType.FAVORABLE,
                raison="turpe7_favorable",
                turpe7_favorable=True,
                turpe7_exclure=False,
            )
        elif exc_hc and not fav_hc:
            out[ts] = SlotClassification(
                window_type=WindowType.SENSIBLE,
                raison="turpe7_exclure",
                turpe7_favorable=False,
                turpe7_exclure=True,
            )
        else:
            # Cas exceptionnel : fav_hc ET exc_hc (impossible si les dicts
            # sont disjoints, mais on reste defensif). Ou aucun creneau
            # TURPE 7 ne s'applique -> NEUTRE.
            out[ts] = SlotClassification(
                window_type=WindowType.NEUTRE,
                raison="neutre",
                turpe7_favorable=fav_hc,
                turpe7_exclure=exc_hc,
            )

    return out


__all__ = [
    "TZ_PARIS",
    "WindowType",
    "SlotMarket",
    "SlotClassification",
    "compute_price_thresholds",
    "classify_slots",
    "is_hc_favorable",
    "is_hc_exclure",
]
