"""
PROMEOS — Classifieur de période tarifaire TURPE 7.
Réutilisable par : billing_shadow_v2, cost_by_period, power_optimizer.

Périodes TURPE 7 (option C4/C5 horosaisonnalisée) :
  HPH = Heures Pleines Hiver (nov-mars, 7h-23h jours ouvrés)
  HCH = Heures Creuses Hiver (nov-mars, 23h-7h + weekends)
  HPB = Heures Pleines Été (avr-oct, 7h-23h jours ouvrés)
  HCB = Heures Creuses Été (avr-oct, 23h-7h + weekends)
  P   = Pointe (déc-fév, jours ouvrés, 9h-11h et 18h-20h)

Source : CRE Délibération n°2025-78 (TURPE 7, 1er août 2025)
"""

from datetime import datetime
from enum import Enum


class TariffPeriod(str, Enum):
    HPH = "HPH"
    HCH = "HCH"
    HPB = "HPB"
    HCB = "HCB"
    POINTE = "P"


WINTER_MONTHS = frozenset({11, 12, 1, 2, 3})
POINTE_MONTHS = frozenset({12, 1, 2})
POINTE_HOURS = frozenset({9, 10, 18, 19})
HP_START = 7
HP_END = 23

# Labels français pour l'affichage
PERIOD_LABELS = {
    "HPH": "Heures Pleines Hiver",
    "HCH": "Heures Creuses Hiver",
    "HPB": "Heures Pleines Été",
    "HCB": "Heures Creuses Été",
    "P": "Pointe",
}

# Ratio de prix relatif par période (HPH = 1.0, base de comparaison)
# Source : écarts moyens observés TURPE 7 C5
PERIOD_PRICE_RATIO = {
    "HPH": 1.00,
    "HCH": 0.62,
    "HPB": 0.78,
    "HCB": 0.50,
    "P": 1.30,
}


def classify_period(ts: datetime, has_pointe: bool = False) -> TariffPeriod:
    """Retourne la période tarifaire pour un timestamp."""
    month = ts.month
    hour = ts.hour
    is_weekend = ts.weekday() >= 5
    is_winter = month in WINTER_MONTHS
    is_hp = HP_START <= hour < HP_END and not is_weekend

    if has_pointe and month in POINTE_MONTHS and not is_weekend and hour in POINTE_HOURS:
        return TariffPeriod.POINTE

    if is_winter:
        return TariffPeriod.HPH if is_hp else TariffPeriod.HCH
    else:
        return TariffPeriod.HPB if is_hp else TariffPeriod.HCB
