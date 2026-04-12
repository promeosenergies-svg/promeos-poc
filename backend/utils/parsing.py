"""
Utilitaires de parsing partagés — source unique pour safe_float, safe_int,
parse_date, parse_iso_datetime.

Remplace les 7+ copies dispersées dans le codebase.
"""

from datetime import date, datetime


def safe_float(val) -> float | None:
    """Convertit en float ou None. Gère NaN."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None


def safe_int(val) -> int | None:
    """Convertit en int ou None (via float pour gérer '42.7')."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def parse_date(val) -> date | None:
    """Parse YYYY-MM-DD (ou datetime string tronquée) en date."""
    if not val:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    try:
        s = str(val)[:10]
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def parse_iso_datetime(val) -> datetime | None:
    """Parse ISO 8601 flexible en datetime naive (UTC implicite).

    Gère : 2025-06-15T10:30:00, ...+02:00, ...Z
    Retourne toujours naive (tzinfo stripped) pour stockage UTC interne.
    """
    if not val:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    try:
        s = str(val).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except (ValueError, TypeError):
        return None
