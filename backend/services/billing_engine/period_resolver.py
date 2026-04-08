"""
PROMEOS — Résolveur unifié de période tarifaire.

Remplace les 3 classifieurs indépendants :
  1. tariff_period_classifier.classify_period() → hardcodé 7h-23h
  2. tou_service._classify_period() → HP/HC binaire via JSON windows
  3. turpe_calendar.get_period_for_datetime() → postes TURPE système (fallback)

Architecture :
  resolve_period(timestamp, site_id, meter_id, db, tou_schedule)
    → cherche TOUSchedule actif (meter > site > default)
    → si is_seasonal : sélectionne windows hiver/été selon le mois
    → parse les fenêtres JSON pour déterminer HP/HC
    → combine avec la saison TURPE pour retourner HPH/HCH/HPB/HCB
    → fallback : turpe_calendar.get_period_for_datetime()

Distinction postes TURPE réseau ≠ plages HC consommateur :
  - Postes TURPE : tarifs d'acheminement réseau, fixes par segment (turpe_calendar)
  - Plages HC consommateur : créneaux Linky, varient par PRM (TOUSchedule)
  - Ce résolveur utilise les plages HC du TOUSchedule du PRM, combinées
    avec la saison TURPE, pour produire HPH/HCH/HPB/HCB.

Sources :
  - CRE délibération n°2025-78 (TURPE 7)
  - CRE délibération n°2026-33 (levée gel HC 11-14h hiver)
"""

from __future__ import annotations

import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .turpe_calendar import get_season, get_period_for_datetime


# ─── Résolution de fenêtres HC ──────────────────────────────────────────────


def _parse_time_minutes(time_str: str) -> int:
    """Convertit "HH:MM" en minutes depuis minuit."""
    parts = time_str.split(":")
    return int(parts[0]) * 60 + (int(parts[1]) if len(parts) > 1 else 0)


def _get_day_type_label(ts: datetime) -> str:
    """Retourne le type de jour pour le filtrage des fenêtres TOUSchedule."""
    wd = ts.weekday()
    if wd >= 5:
        return "weekend"
    return "weekday"


def is_in_hc_window(hour: int, minute: int, windows: List[Dict[str, Any]], day_type: str = "weekday") -> bool:
    """Vérifie si (hour, minute) tombe dans une fenêtre HC du TOUSchedule.

    Parcourt les fenêtres JSON du schedule. Une fenêtre est HC si son
    champ `period` contient "HC" (HC, HCH, HCB).

    Filtre par day_type si la fenêtre a un champ `day_types`.

    Format attendu de chaque fenêtre :
        {"day_types": ["weekday"], "start": "23:00", "end": "07:00", "period": "HC", ...}

    Gère les fenêtres overnight (start > end) comme 23:00→07:00.
    """
    time_min = hour * 60 + minute
    for w in windows:
        period = w.get("period", "")
        if "HC" not in period.upper():
            continue

        # Filtrer par day_type si spécifié dans la fenêtre
        w_day_types = w.get("day_types")
        if w_day_types and day_type not in w_day_types:
            continue

        start_min = _parse_time_minutes(w.get("start", "00:00"))
        end_min = _parse_time_minutes(w.get("end", "24:00"))

        if start_min <= end_min:
            # Plage intra-journée (ex: 11:00 → 14:00)
            if start_min <= time_min < end_min:
                return True
        else:
            # Plage overnight (ex: 23:00 → 07:00)
            if time_min >= start_min or time_min < end_min:
                return True
    return False


# ─── Sélection saisonnière des fenêtres ────────────────────────────────────


def select_windows(schedule_dict: Dict[str, Any], month: int) -> List[Dict[str, Any]]:
    """Sélectionne les fenêtres HC selon la saison.

    - Si is_seasonal et mois en saison basse (avr-oct) : windows_ete
    - Sinon : windows (hiver / toute l'année)

    Args:
        schedule_dict: Dict retourné par tou_service.get_active_schedule()
                       ou _serialize_schedule(). Doit avoir les clés
                       'windows', 'is_seasonal', 'windows_ete'.
        month: Mois (1-12)

    Returns:
        Liste de fenêtres HC/HP (dicts JSON).
    """
    is_seasonal = schedule_dict.get("is_seasonal", False)
    if is_seasonal and month not in {1, 2, 3, 11, 12}:
        windows_ete = schedule_dict.get("windows_ete")
        if windows_ete:
            return windows_ete
    return schedule_dict.get("windows") or []


# ─── Résolveur principal ───────────────────────────────────────────────────


def resolve_period(
    ts: datetime,
    site_id: Optional[int] = None,
    meter_id: Optional[int] = None,
    db: Optional[Session] = None,
    tou_schedule: Optional[Dict[str, Any]] = None,
) -> str:
    """Résout la période tarifaire pour un timestamp.

    Stratégie :
      1. Si tou_schedule fourni, l'utiliser directement
      2. Sinon, chercher le TOUSchedule actif via DB (meter > site > default)
      3. Sélectionner les fenêtres selon la saison (hiver/été)
      4. Déterminer HP/HC via les fenêtres
      5. Combiner avec la saison TURPE → HPH/HCH/HPB/HCB
      6. Fallback : turpe_calendar.get_period_for_datetime()

    Args:
        ts: Timestamp à classifier
        site_id: ID du site (pour lookup DB)
        meter_id: ID du compteur (priorité sur site)
        db: Session SQLAlchemy (pour lookup TOUSchedule)
        tou_schedule: Dict du schedule (évite le lookup DB si fourni)

    Returns:
        Code de période : "HPH", "HCH", "HPB", "HCB" (4 plages)
    """
    schedule = tou_schedule

    if schedule is None and db is not None and site_id is not None:
        from services.tou_service import get_active_schedule

        schedule = get_active_schedule(db, site_id, meter_id)

    if schedule is not None:
        windows = select_windows(schedule, ts.month)
        if windows:
            day_type = _get_day_type_label(ts)
            is_hc = is_in_hc_window(ts.hour, ts.minute, windows, day_type)
            season = get_season(ts.date() if isinstance(ts, datetime) else ts)
            is_hiver = season == "HIVER"

            if is_hc:
                return "HCH" if is_hiver else "HCB"
            else:
                return "HPH" if is_hiver else "HPB"

    # Fallback : postes TURPE système
    return get_period_for_datetime(ts, is_seasonal=True)


def resolve_period_binary(
    ts: datetime,
    site_id: Optional[int] = None,
    meter_id: Optional[int] = None,
    db: Optional[Session] = None,
    tou_schedule: Optional[Dict[str, Any]] = None,
) -> str:
    """Résout la période tarifaire en format binaire HP/HC.

    Wrapper backward-compatible pour les appelants qui attendent "HP" ou "HC"
    (ex: cost_by_period_service via classify_period).

    Returns:
        "HP" ou "HC"
    """
    period = resolve_period(ts, site_id, meter_id, db, tou_schedule)
    return "HC" if "HC" in period else "HP"


def resolve_period_no_db(ts: datetime) -> str:
    """Résout la période sans accès DB — fallback pur turpe_calendar.

    Utilisé par le wrapper classify_period() pour backward-compat
    quand aucun contexte DB n'est disponible.

    Returns:
        "HPH", "HCH", "HPB", "HCB"
    """
    return get_period_for_datetime(ts, is_seasonal=True)
