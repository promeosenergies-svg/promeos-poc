"""
PROMEOS — Classifieur de période tarifaire TURPE 7.
Réutilisable par : billing_shadow_v2, cost_by_period, power_optimizer.

Périodes TURPE 7 (option C4/C5 horosaisonnalisée) :
  HPH = Heures Pleines Hiver (nov-mars, postes TURPE)
  HCH = Heures Creuses Hiver (nov-mars, postes TURPE)
  HPB = Heures Pleines Été (avr-oct, postes TURPE)
  HCB = Heures Creuses Été (avr-oct, postes TURPE)
  P   = Pointe (déc-fév, jours ouvrés, 9h-11h et 18h-20h)

Délègue au résolveur unifié (period_resolver) qui utilise les postes
horosaisonniers TURPE 7 officiels via turpe_calendar, avec support
des jours fériés et distinction samedi/dimanche.

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


# ── Constantes rétro-compatibles (utilisées par d'autres modules) ──────────
WINTER_MONTHS = frozenset({11, 12, 1, 2, 3})
POINTE_MONTHS = frozenset({12, 1, 2})
POINTE_HOURS = frozenset({9, 10, 18, 19})

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

# Mapping str → TariffPeriod enum
_STR_TO_PERIOD = {
    "HPH": TariffPeriod.HPH,
    "HCH": TariffPeriod.HCH,
    "HPB": TariffPeriod.HPB,
    "HCB": TariffPeriod.HCB,
    "P": TariffPeriod.POINTE,
}


def classify_period(ts: datetime, has_pointe: bool = False) -> TariffPeriod:
    """Retourne la période tarifaire pour un timestamp.

    Délègue au résolveur unifié (turpe_calendar) pour une classification
    correcte avec jours fériés et postes horosaisonniers TURPE 7.

    La période POINTE (déc-fév, 9h-11h et 18h-20h) est gérée ici car
    elle n'existe que pour les segments C3+ et n'est pas dans turpe_calendar.
    """
    # Pointe : gestion spéciale (C3+ uniquement, pas dans turpe_calendar)
    if has_pointe:
        month = ts.month
        hour = ts.hour
        is_weekend = ts.weekday() >= 5
        if month in POINTE_MONTHS and not is_weekend and hour in POINTE_HOURS:
            return TariffPeriod.POINTE

    # Résolution via turpe_calendar (postes horosaisonniers officiels)
    from services.billing_engine.period_resolver import resolve_period_no_db

    period_str = resolve_period_no_db(ts)
    return _STR_TO_PERIOD.get(period_str, TariffPeriod.HPH)
