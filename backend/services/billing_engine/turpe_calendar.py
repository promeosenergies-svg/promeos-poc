"""
PROMEOS Billing Engine — Calendrier TURPE 7 officiel.

IMPORTANT : Ce module distingue DEUX concepts différents :

A) POSTES HOROSAISONNIERS TURPE (pour C4 BT, C5 CU4/MU4, HTA)
   = Classification système des heures pour le calcul du TURPE soutirage.
   HP = lundi-samedi 7h30-21h30, HC = 21h30-7h30 + dimanche + fériés.
   Source : Brochure TURPE 7 Enedis, postes horosaisonniers (CRE n°2025-78).
   → Utilisé par le billing engine pour ventiler kWh en HPH/HCH/HPB/HCB.

B) HC CONSOMMATEUR (pour C5 Tarif Bleu HP/HC)
   = 8h HC/jour programmées sur le compteur Linky par Enedis.
   Réforme : Phase 1 (nov 2025 → juin 2026), Phase 2 (déc 2026 → oct 2027).
   Règles CRE (délibération n°2026-33 du 4 fév 2026) :
     Été : HC favorisées 02-06h et 11-17h, interdites 07-10h et 18-23h
     Hiver : HC interdites 07-11h et 17-21h, gel 11-14h levé (n°2026-33)
   → Stocké dans TOUSchedule (par site/PRM), PAS dans ce module.

Sources :
  - CRE délibération n°2025-78 du 13 mars 2025 (TURPE 7 HTA-BT)
  - CRE délibération n°2026-33 du 4 février 2026 (levée gel HC 11-14h hiver)
  - Enedis brochure TURPE 7 (postes horosaisonniers)
  - Code du travail art. L3133-1 (jours fériés)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Set, Tuple


# ─── Saisons TURPE ───────────────────────────────────────────────────────────
# Source: CRE TURPE 7 — saison haute = hiver (novembre à mars)
#                        saison basse = été (avril à octobre)

_MOIS_HIVER = {1, 2, 3, 11, 12}  # Saison haute
_MOIS_ETE = {4, 5, 6, 7, 8, 9, 10}  # Saison basse


def get_season(d: date) -> str:
    """Retourne la saison TURPE pour une date donnée.

    Returns:
        "HIVER" (saison haute, nov-mars) ou "ETE" (saison basse, avr-oct)

    Source: CRE TURPE 7, délibération n°2025-78.
    """
    return "HIVER" if d.month in _MOIS_HIVER else "ETE"


# ─── Jours fériés français ───────────────────────────────────────────────────
# Source: Code du travail art. L3133-1

# Fériés fixes (mois, jour)
_FERIES_FIXES: List[Tuple[int, int]] = [
    (1, 1),  # Jour de l'An
    (5, 1),  # Fête du Travail
    (5, 8),  # Victoire 1945
    (7, 14),  # Fête nationale
    (8, 15),  # Assomption
    (11, 1),  # Toussaint
    (11, 11),  # Armistice 1918
    (12, 25),  # Noël
]


def _paques(year: int) -> date:
    """Calcul de la date de Pâques par l'algorithme de Butcher/Meeus.

    Source: algorithme de calcul computus (Meeus, Astronomical Algorithms).
    Valide pour les années 1583-4099.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


@lru_cache(maxsize=16)
def _jours_feries_annee(year: int) -> Set[date]:
    """Retourne l'ensemble des jours fériés français pour une année.

    Fériés fixes: 8 dates (Jour de l'An, Fête du Travail, 8 Mai, 14 Juillet,
                          Assomption, Toussaint, Armistice, Noël)
    Fériés mobiles: 3 dates (Lundi de Pâques, Ascension, Lundi de Pentecôte)

    Source: Code du travail art. L3133-1.
    """
    feries = set()

    # Fériés fixes
    for month, day in _FERIES_FIXES:
        feries.add(date(year, month, day))

    # Fériés mobiles (basés sur Pâques)
    paques = _paques(year)
    feries.add(paques + timedelta(days=1))  # Lundi de Pâques (J+1)
    feries.add(paques + timedelta(days=39))  # Ascension (J+39)
    feries.add(paques + timedelta(days=50))  # Lundi de Pentecôte (J+50)

    return feries


def is_jour_ferie(d: date) -> bool:
    """Vérifie si une date est un jour férié français.

    Source: Code du travail art. L3133-1.
    """
    return d in _jours_feries_annee(d.year)


def get_day_type(d: date) -> str:
    """Retourne le type de jour pour le calendrier TURPE.

    Returns:
        "holiday" — jour férié (traité comme dimanche pour les postes TURPE)
        "sunday"  — dimanche (HC toute la journée en postes TURPE)
        "saturday" — samedi (traité comme jour ouvré en postes TURPE)
        "weekday" — lundi à vendredi non férié

    Source: Enedis brochure TURPE 7, postes horosaisonniers.
    Note: En postes TURPE C4/HTA, samedi = jour ouvré (HP 7h30-21h30).
          Seuls dimanche et jours fériés sont entièrement HC.
    """
    if is_jour_ferie(d):
        return "holiday"
    wd = d.weekday()
    if wd == 6:  # dimanche
        return "sunday"
    if wd == 5:  # samedi
        return "saturday"
    return "weekday"


# ─── Postes horosaisonniers TURPE 7 ─────────────────────────────────────────
#
# Pour C4 BT (36-250 kVA), C5 CU4/MU4, HTA :
#
# Source: Brochure TURPE 7 Enedis, postes horosaisonniers.
#   HP = lundi-samedi 7h30-21h30 (14h/jour ouvré)
#   HC = 21h30-7h30 (10h/nuit ouvrée) + dimanche et jours fériés (24h)
#
# Arrondi à l'heure entière pour le calcul horaire :
#   HP = heures 8 à 21 incluses (08:00-22:00 = 14h)
#   HC = heures 0 à 7 + 22 à 23 (22:00-08:00 = 10h)
#   (7h30 arrondi à 8h en début, 21h30 arrondi à 22h en fin)
#
# Dimanche + fériés = HC toute la journée (24h)
# Samedi = comme jour de semaine (HP 08-22, HC 22-08)
#
# LEGACY (C5 Tarif Bleu HP/HC non saisonnalisé) :
#   HP = 06-22 (16h), HC = 22-06 (8h), tous les jours identiques
#   (pas de distinction samedi/dimanche dans la TOUSchedule)
#

# Tableaux indexés par heure (0-23), True = HP, False = HC
# Source: Enedis brochure TURPE 7 postes horosaisonniers

_HP_TURPE_OUVRE: List[bool] = [
    # 00  01  02  03  04  05  06  07  08  09  10  11
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    True,
    True,
    True,
    True,
    # 12  13  14  15  16  17  18  19  20  21  22  23
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    False,
    False,
]
# 14h HP (heures 8-21), 10h HC (heures 0-7 + 22-23)

_HP_TURPE_DIMANCHE: List[bool] = [False] * 24  # 24h HC

# Legacy C5 HP/HC (non saisonnalisé, tous jours identiques)
_HP_LEGACY: List[bool] = [
    # 00  01  02  03  04  05  06  07  08  09  10  11
    False,
    False,
    False,
    False,
    False,
    False,
    True,
    True,
    True,
    True,
    True,
    True,
    # 12  13  14  15  16  17  18  19  20  21  22  23
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    False,
    False,
]
# 16h HP (heures 6-21), 8h HC (heures 0-5 + 22-23)


def is_hp_hour(hour: int, day_type: str, mode: str = "TURPE") -> bool:
    """Détermine si une heure est en Heure Pleine pour un type de jour.

    Args:
        hour: Heure (0-23)
        day_type: "weekday", "saturday", "sunday" ou "holiday"
        mode: "TURPE" (postes horosaisonniers C4/HTA/CU4/MU4)
              ou "LEGACY" (C5 Tarif Bleu HP/HC simple)

    Returns:
        True si HP, False si HC

    Source: Enedis brochure TURPE 7, postes horosaisonniers.
    """
    if mode == "LEGACY":
        # Legacy C5 HP/HC : même plages tous les jours
        return _HP_LEGACY[hour]

    # Mode TURPE : postes horosaisonniers
    if day_type in ("sunday", "holiday"):
        return _HP_TURPE_DIMANCHE[hour]  # Toujours HC

    # Lundi-samedi = jour ouvré pour TURPE
    return _HP_TURPE_OUVRE[hour]


def get_period_for_datetime(dt: datetime, is_seasonal: bool = True) -> str:
    """Retourne le code de période TURPE pour un instant donné.

    Args:
        dt: Datetime à classifier
        is_seasonal: True = résolution 4 plages (HPH/HCH/HPB/HCB)
                     False = résolution 2 plages legacy (HP/HC)

    Returns:
        Code de période: "HPH", "HCH", "HPB", "HCB" (saisonnalisé)
                     ou "HP", "HC" (legacy non saisonnalisé)

    Source:
        - Postes TURPE 7 (CRE n°2025-78) pour mode saisonnalisé
        - EDF Tarif Bleu pour mode legacy
    """
    d = dt.date() if isinstance(dt, datetime) else dt
    day_type = get_day_type(d)

    if not is_seasonal:
        hp = is_hp_hour(dt.hour, day_type, mode="LEGACY")
        return "HP" if hp else "HC"

    season = get_season(d)
    hp = is_hp_hour(dt.hour, day_type, mode="TURPE")

    if season == "HIVER":
        return "HPH" if hp else "HCH"
    else:
        return "HPB" if hp else "HCB"


def count_hours_by_period(
    period_start: date,
    period_end: date,
    is_seasonal: bool = True,
) -> Dict[str, int]:
    """Compte les heures par plage TURPE sur une période.

    Itère jour par jour, heure par heure, et agrège les compteurs.

    Args:
        period_start: Date de début (incluse)
        period_end: Date de fin (exclue)
        is_seasonal: True = 4 plages postes TURPE, False = 2 plages legacy

    Returns:
        {"HPH": n, "HCH": n, "HPB": n, "HCB": n} ou {"HP": n, "HC": n}

    Source: Enedis brochure TURPE 7, postes horosaisonniers + calendrier.
    """
    if is_seasonal:
        counts = {"HPH": 0, "HCH": 0, "HPB": 0, "HCB": 0}
    else:
        counts = {"HP": 0, "HC": 0}

    current = period_start
    while current < period_end:
        day_type = get_day_type(current)
        season = get_season(current)

        for hour in range(24):
            if is_seasonal:
                hp = is_hp_hour(hour, day_type, mode="TURPE")
                if season == "HIVER":
                    counts["HPH" if hp else "HCH"] += 1
                else:
                    counts["HPB" if hp else "HCB"] += 1
            else:
                hp = is_hp_hour(hour, day_type, mode="LEGACY")
                counts["HP" if hp else "HC"] += 1

        current += timedelta(days=1)

    return counts


def count_hours_by_period_ratios(
    period_start: date,
    period_end: date,
    is_seasonal: bool = True,
) -> Dict[str, float]:
    """Calcule les ratios de répartition horaire par plage TURPE sur une période.

    Returns:
        Ratios normalisés (somme = 1.0).
        Ex: {"HPH": 0.35, "HCH": 0.15, "HPB": 0.30, "HCB": 0.20}
    """
    counts = count_hours_by_period(period_start, period_end, is_seasonal)
    total = sum(counts.values())
    if total == 0:
        n = len(counts)
        return {k: 1.0 / n for k in counts}
    return {k: v / total for k, v in counts.items()}
