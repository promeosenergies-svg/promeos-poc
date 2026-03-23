"""
PROMEOS Billing Engine — Résolution saisonnière des kWh.

Ventile un total kWh en plages horosaisonnières TURPE 7 (HPH/HCH/HPB/HCB)
à partir du calendrier officiel CRE.

Stratégie de résolution :
  1. Passthrough si kwh_by_period déjà en 4 plages
  2. Calcul calendaire jour/heure via turpe_calendar
  3. Profils fournisseur par défaut (fallback)

Sources :
  - CRE délibération n°2025-78 (TURPE 7)
  - CRE délibération n°2026-33 du 4 février 2026 (levée gel HC 11h-14h hiver)
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional, Set

from .turpe_calendar import count_hours_by_period_ratios
from .types import TariffOption, TariffSegment

# ─── Codes de période ────────────────────────────────────────────────────────

_4P_CODES: Set[str] = {"HPH", "HCH", "HPB", "HCB"}
_2P_CODES: Set[str] = {"HP", "HC"}
_1P_CODES: Set[str] = {"BASE"}

# Options tarifaires nécessitant une ventilation 4 plages
_OPTIONS_4P: Set[TariffOption] = {
    TariffOption.CU,  # C4 BT Courte Utilisation (4 plages)
    TariffOption.MU,  # C4 BT Moyenne Utilisation (4 plages) / C5 MU4
    TariffOption.LU,  # C4 BT Longue Utilisation (4 plages)
}

# ─── Profils fournisseur par défaut ──────────────────────────────────────────
# Utilisés quand le calcul calendaire n'est pas possible (période courte, etc.)
# Ratios moyens annualisés pour la France métropolitaine.

PROFILS_DEFAUT: Dict[str, Dict[str, float]] = {
    "HP_HC_SIMPLE": {"HP": 0.65, "HC": 0.35},
    "4P_ANNUEL": {"HPH": 0.28, "HCH": 0.14, "HPB": 0.38, "HCB": 0.20},
}


def needs_seasonal_upgrade(
    kwh_by_period: Dict[str, float],
    tariff_option: Optional[TariffOption],
    segment: TariffSegment,
) -> bool:
    """Détermine si la ventilation kWh doit être upgradée en 4 plages.

    Conditions :
    - L'option tarifaire nécessite 4 plages (CU/MU/LU)
    - Les données actuelles sont en 2 plages (HP/HC) ou 1 plage (BASE)
    - Le segment est C4 BT ou C3 HTA (ou C5 avec option 4P)

    Returns:
        True si upgrade nécessaire.
    """
    if tariff_option not in _OPTIONS_4P:
        return False

    period_keys = set(kwh_by_period.keys())

    # Déjà en 4 plages → pas d'upgrade
    if period_keys & _4P_CODES:
        return False

    # En 2 plages ou 1 plage → upgrade nécessaire
    if period_keys & _2P_CODES or period_keys & _1P_CODES:
        return True

    return False


def resolve_kwh_by_season(
    total_kwh: float,
    period_start: date,
    period_end: date,
    tariff_option: TariffOption,
    is_seasonal: bool = True,
) -> Dict[str, float]:
    """Ventile un total kWh en plages horosaisonnières TURPE 7.

    Utilise le calendrier TURPE officiel pour calculer les ratios
    jour par jour sur la période de facturation.

    Args:
        total_kwh: Consommation totale en kWh
        period_start: Début de la période (inclus)
        period_end: Fin de la période (exclu)
        tariff_option: Option tarifaire du contrat
        is_seasonal: True = 4 plages (HPH/HCH/HPB/HCB),
                     False = 2 plages legacy (HP/HC)

    Returns:
        Dict avec kWh par plage. Somme = total_kwh.
        Ex: {"HPH": 3500, "HCH": 1500, "HPB": 3800, "HCB": 1200}

    Invariant: sum(result.values()) == total_kwh (à l'arrondi près)
    """
    if tariff_option == TariffOption.BASE:
        return {"BASE": total_kwh}

    if tariff_option == TariffOption.HP_HC and not is_seasonal:
        # Legacy HP/HC simple — pas de résolution saisonnière
        ratios = count_hours_by_period_ratios(period_start, period_end, is_seasonal=False)
        return _apply_ratios(total_kwh, ratios)

    if tariff_option in _OPTIONS_4P or is_seasonal:
        # Résolution 4 plages par calendrier TURPE
        ratios = count_hours_by_period_ratios(period_start, period_end, is_seasonal=True)
        return _apply_ratios(total_kwh, ratios)

    # Fallback : 2 plages legacy
    ratios = count_hours_by_period_ratios(period_start, period_end, is_seasonal=False)
    return _apply_ratios(total_kwh, ratios)


def _apply_ratios(total_kwh: float, ratios: Dict[str, float]) -> Dict[str, float]:
    """Applique des ratios à un total kWh en préservant la somme exacte.

    Stratégie d'arrondi : arrondi individuel à 1 décimale,
    puis ajustement du plus grand poste pour compenser le delta.

    Invariant: sum(result.values()) == round(total_kwh, 1)
    """
    if not ratios:
        return {"BASE": total_kwh}

    # Calcul brut
    raw = {k: total_kwh * v for k, v in ratios.items()}

    # Arrondi à 1 décimale
    rounded = {k: round(v, 1) for k, v in raw.items()}

    # Ajustement pour préserver la somme
    delta = round(total_kwh - sum(rounded.values()), 1)
    if delta != 0.0 and rounded:
        # Ajouter le delta au plus grand poste
        max_key = max(rounded, key=rounded.get)
        rounded[max_key] = round(rounded[max_key] + delta, 1)

    return rounded


def compute_seasonal_ratios(
    period_start: date,
    period_end: date,
    is_seasonal: bool = True,
) -> Dict[str, float]:
    """Calcule les ratios de répartition par plage TURPE sur une période.

    Wrapper de turpe_calendar.count_hours_by_period_ratios pour
    faciliter l'utilisation depuis le billing engine.

    Args:
        period_start: Début (inclus)
        period_end: Fin (exclu)
        is_seasonal: True = 4 plages, False = 2 plages

    Returns:
        Ratios normalisés (somme = 1.0).
        Ex: {"HPH": 0.35, "HCH": 0.15, "HPB": 0.30, "HCB": 0.20}
    """
    return count_hours_by_period_ratios(period_start, period_end, is_seasonal)
