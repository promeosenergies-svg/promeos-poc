"""
PROMEOS — Tax & Network Cost Catalog Service (V1)
Versioned lookup of regulatory rates (TURPE, accises, TVA, CTA).
All rates have: valid_from/valid_to + source + fallback.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

_CATALOG_PATH = Path(__file__).resolve().parent / "tax_catalog.json"

# Module-level cache (loaded once)
_catalog: Optional[dict] = None


def _load_catalog() -> dict:
    global _catalog
    if _catalog is None:
        _catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return _catalog


def reload_catalog():
    """Force reload (useful after hot-patch or tests)."""
    global _catalog
    _catalog = None
    return _load_catalog()


def get_entry(code: str, at_date: Optional[date] = None) -> Optional[dict]:
    """
    Lookup a catalog entry by code, optionally filtered by date.

    Returns the entry dict if found and valid at at_date, else None.
    If at_date is None, returns the first matching entry (latest).
    """
    catalog = _load_catalog()
    at_date = at_date or date.today()

    for entry in catalog.get("entries", []):
        if entry["code"] != code:
            continue
        valid_from = _parse_date(entry.get("valid_from"))
        valid_to = _parse_date(entry.get("valid_to"))
        if valid_from and at_date < valid_from:
            continue
        if valid_to and at_date > valid_to:
            continue
        return entry

    # No date-matching entry found — return first match with fallback flag
    for entry in catalog.get("entries", []):
        if entry["code"] == code:
            return entry
    return None


def get_rate(code: str, at_date: Optional[date] = None) -> float:
    """
    Get the rate for a catalog code at a given date.
    Returns fallback if no matching entry.
    Raises KeyError if code is completely unknown.
    """
    entry = get_entry(code, at_date)
    if entry is None:
        raise KeyError(f"Tax catalog: unknown code '{code}'")
    return entry["rate"]


def trace(code: str, at_date: Optional[date] = None) -> dict:
    """
    Build an audit trace for a rate lookup.
    Returns {code, used_rate, source, fallback_used, valid_from, valid_to, unit, tva_rate}.
    """
    catalog = _load_catalog()
    at_date = at_date or date.today()

    # Try date-valid entry first
    matched = None
    fallback_used = False
    for entry in catalog.get("entries", []):
        if entry["code"] != code:
            continue
        valid_from = _parse_date(entry.get("valid_from"))
        valid_to = _parse_date(entry.get("valid_to"))
        in_range = True
        if valid_from and at_date < valid_from:
            in_range = False
        if valid_to and at_date > valid_to:
            in_range = False
        if in_range:
            matched = entry
            break

    # Fallback to first match
    if matched is None:
        for entry in catalog.get("entries", []):
            if entry["code"] == code:
                matched = entry
                fallback_used = True
                break

    if matched is None:
        return {"code": code, "error": "unknown_code"}

    return {
        "code": code,
        "used_rate": matched["rate"],
        "unit": matched.get("unit"),
        "tva_rate": matched.get("tva_rate"),
        "source": matched.get("source"),
        "fallback_used": fallback_used,
        "valid_from": matched.get("valid_from"),
        "valid_to": matched.get("valid_to"),
        "at_date": at_date.isoformat(),
        "catalog_version": catalog.get("version"),
    }


def get_catalog_version() -> str:
    """Return the catalog version string."""
    return _load_catalog().get("version", "unknown")


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
