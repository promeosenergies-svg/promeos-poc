"""
PROMEOS — Helpers cardinal datetime cross-services.

Phase L16.3 audit fix P1 — consolide les conversions Date ↔ DateTime utilisées
dans les filters SQL temporels (MeterReading.timestamp range queries).

Pattern bug systémique découvert Phase L13.4 (R27 anomaly_detector) propagé
dans Phase L14.1 (routes/ems.py × 3 callsites). Audit cumul Phase L16 a
identifié 6 callsites supplémentaires dans `services/power/*` + `routes/portfolio.py`
utilisant CORRECTEMENT le pattern `combine(d + timedelta(days=1), min.time())`
inline. Ce module centralise la convention pour anti-drift futur.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta


def to_exclusive_next_day_dt(d: date) -> datetime:
    """Convertit une `date` upper-bound en `datetime` next-day midnight (exclusive).

    Pattern à utiliser pour les filtres SQL `< upper_bound` sur colonnes DateTime,
    quand la borne sémantique est une `date` (jour entier inclus).

    Avant L13.4 : `combine(d, min.time())` produisait `d 00:00:00`. Avec strict `<`,
    les lectures de `d` après 00:00:00 étaient silencieusement exclues.

    Après L13.4 : `combine(d + 1 day, min.time())` capture la totalité de `d`.

    Examples:
        >>> to_exclusive_next_day_dt(date(2026, 4, 30))
        datetime.datetime(2026, 5, 1, 0, 0)
        >>> to_exclusive_next_day_dt(date(2026, 12, 31))
        datetime.datetime(2027, 1, 1, 0, 0)

    Args:
        d : date upper-bound (jour entier à inclure)

    Returns:
        datetime du jour suivant à 00:00:00 (exclusive bound pour strict <)
    """
    return datetime.combine(d + timedelta(days=1), time.min)


def to_inclusive_end_of_day_dt(d: date) -> datetime:
    """Convertit une `date` upper-bound en `datetime` 23:59:59 (inclusive).

    Pattern à utiliser pour les filtres SQL `<= upper_bound` sur colonnes DateTime,
    quand la borne sémantique est une `date`.

    Pattern aligné `services/bill_intelligence/anomaly_detector.py` R27 (Phase L13.4)
    qui utilise `<=` inclusif via `combine(period_end, time(23, 59, 59))`.

    Examples:
        >>> to_inclusive_end_of_day_dt(date(2026, 4, 30))
        datetime.datetime(2026, 4, 30, 23, 59, 59)

    Args:
        d : date upper-bound (jour entier à inclure)

    Returns:
        datetime du même jour à 23:59:59 (inclusive bound pour <=)
    """
    return datetime.combine(d, time(23, 59, 59))


def to_start_of_day_dt(d: date) -> datetime:
    """Convertit une `date` lower-bound en `datetime` 00:00:00.

    Pattern symétrique à `to_exclusive_next_day_dt` pour la borne basse `>=`.

    Examples:
        >>> to_start_of_day_dt(date(2026, 4, 1))
        datetime.datetime(2026, 4, 1, 0, 0)

    Args:
        d : date lower-bound

    Returns:
        datetime du même jour à 00:00:00
    """
    return datetime.combine(d, time.min)
