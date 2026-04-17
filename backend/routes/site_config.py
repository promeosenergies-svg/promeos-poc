"""
PROMEOS - Routes Site Configuration (schedule + tariff)
GET/PUT /api/site/:id/schedule
GET/PUT /api/site/:id/tariff
"""

import json
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access
from models import Site, SiteOperatingSchedule, SiteTariffProfile

router = APIRouter(prefix="/api/site", tags=["Site Config"])

# Default values
DEFAULT_OPEN_TIME = "08:00"
DEFAULT_CLOSE_TIME = "19:00"
DEFAULT_OPEN_DAYS = "0,1,2,3,4"
DEFAULT_TIMEZONE = "Europe/Paris"
DEFAULT_PRICE_REF = 0.068  # Aligne sur config/default_prices.py (EPEX Spot moyen 2025)

VALID_DAY_KEYS = {"0", "1", "2", "3", "4", "5", "6"}
HH_MM_RE = re.compile(r"^\d{2}:\d{2}$")


# ---- Interval validation ----


def _parse_hhmm(t: str) -> int:
    """Parse HH:MM to total minutes. Raises ValueError on bad format."""
    if not HH_MM_RE.match(t):
        raise ValueError(f"Format invalide: '{t}' (attendu HH:MM)")
    h, m = int(t[:2]), int(t[3:])
    if h > 23 or m > 59:
        raise ValueError(f"Heure invalide: '{t}'")
    return h * 60 + m


def validate_intervals(intervals: dict) -> list:
    """Validate multi-interval schedule.

    Args:
        intervals: {"0": [{"start":"08:00","end":"12:00"}, ...], ...}

    Returns:
        list of error dicts if invalid, empty list if valid.

    Rules:
        - Keys must be "0"-"6"
        - Each interval: start < end (no midnight crossing)
        - Format HH:MM strict
        - Sorted by start
        - No overlap: prev.end <= next.start (adjacency OK)
        - Empty list for a day is valid (day closed)
    """
    errors = []
    if not isinstance(intervals, dict):
        return [{"day": None, "code": "invalid_type", "message": "intervals doit etre un objet"}]

    for day_key, slots in intervals.items():
        if day_key not in VALID_DAY_KEYS:
            errors.append({"day": day_key, "code": "invalid_day", "message": f"Cle jour invalide: '{day_key}'"})
            continue

        if not isinstance(slots, list):
            errors.append({"day": day_key, "code": "invalid_slots", "message": "Les plages doivent etre un tableau"})
            continue

        if len(slots) == 0:
            continue  # day closed — valid

        parsed = []
        for idx, slot in enumerate(slots):
            if not isinstance(slot, dict) or "start" not in slot or "end" not in slot:
                errors.append(
                    {
                        "day": day_key,
                        "index": idx,
                        "code": "missing_fields",
                        "message": f"Jour {day_key} plage {idx}: champs start/end requis",
                    }
                )
                continue

            try:
                s_min = _parse_hhmm(slot["start"])
            except ValueError as e:
                errors.append({"day": day_key, "index": idx, "code": "invalid_start", "message": str(e)})
                continue
            try:
                e_min = _parse_hhmm(slot["end"])
            except ValueError as e:
                errors.append({"day": day_key, "index": idx, "code": "invalid_end", "message": str(e)})
                continue

            if s_min >= e_min:
                errors.append(
                    {
                        "day": day_key,
                        "index": idx,
                        "code": "start_ge_end",
                        "message": f"Jour {day_key} plage {idx}: debut ({slot['start']}) >= fin ({slot['end']})",
                    }
                )
                continue

            parsed.append((s_min, e_min, idx, slot["start"], slot["end"]))

        # Sort by start and check overlaps
        parsed.sort(key=lambda x: x[0])
        for i in range(1, len(parsed)):
            prev_end = parsed[i - 1][1]
            curr_start = parsed[i][0]
            if curr_start < prev_end:
                errors.append(
                    {
                        "day": day_key,
                        "index": parsed[i][2],
                        "code": "overlap",
                        "message": (
                            f"Jour {day_key}: chevauchement entre "
                            f"{parsed[i - 1][3]}\u2013{parsed[i - 1][4]} et "
                            f"{parsed[i][3]}\u2013{parsed[i][4]}"
                        ),
                    }
                )

    return errors


def _intervals_to_legacy(intervals: dict) -> tuple:
    """Convert intervals dict to legacy open_days/open_time/close_time.

    Uses earliest start and latest end across all open days.
    Returns (open_days_csv, open_time, close_time).
    """
    open_day_keys = sorted(k for k, v in intervals.items() if v)
    if not open_day_keys:
        return (DEFAULT_OPEN_DAYS, DEFAULT_OPEN_TIME, DEFAULT_CLOSE_TIME)

    open_days_csv = ",".join(open_day_keys)
    earliest = "23:59"
    latest = "00:00"
    for slots in intervals.values():
        for slot in slots:
            if slot["start"] < earliest:
                earliest = slot["start"]
            if slot["end"] > latest:
                latest = slot["end"]
    return (open_days_csv, earliest, latest)


# ---- Schemas ----


class ScheduleIn(BaseModel):
    timezone: str = Field(DEFAULT_TIMEZONE, max_length=50)
    open_days: str = Field(DEFAULT_OPEN_DAYS, max_length=20, description="CSV: 0=Mon,6=Sun")
    open_time: str = Field(DEFAULT_OPEN_TIME, max_length=5, pattern=r"^\d{2}:\d{2}$")
    close_time: str = Field(DEFAULT_CLOSE_TIME, max_length=5, pattern=r"^\d{2}:\d{2}$")
    is_24_7: bool = False
    exceptions_json: Optional[str] = None
    intervals_json: Optional[str] = None


class TariffIn(BaseModel):
    price_ref_eur_per_kwh: float = Field(DEFAULT_PRICE_REF, gt=0, le=2.0)
    currency: str = Field("EUR", max_length=3)


# ---- Schedule endpoints ----


def _build_schedule_response(site_id: int, sched, is_default: bool = False) -> dict:
    """Build schedule response dict from SiteOperatingSchedule or defaults."""
    if is_default:
        return {
            "site_id": site_id,
            "timezone": DEFAULT_TIMEZONE,
            "open_days": DEFAULT_OPEN_DAYS,
            "open_time": DEFAULT_OPEN_TIME,
            "close_time": DEFAULT_CLOSE_TIME,
            "is_24_7": False,
            "exceptions_json": None,
            "intervals_json": None,
            "is_default": True,
        }
    return {
        "site_id": site_id,
        "timezone": sched.timezone,
        "open_days": sched.open_days,
        "open_time": sched.open_time,
        "close_time": sched.close_time,
        "is_24_7": sched.is_24_7,
        "exceptions_json": sched.exceptions_json,
        "intervals_json": sched.intervals_json,
        "is_default": False,
    }


@router.get("/{site_id}/schedule")
def get_schedule(site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)):
    check_site_access(auth, site_id)
    """Return operating schedule for site (creates default if none)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    sched = db.query(SiteOperatingSchedule).filter(SiteOperatingSchedule.site_id == site_id).first()

    if not sched:
        return _build_schedule_response(site_id, None, is_default=True)

    return _build_schedule_response(site_id, sched)


@router.put("/{site_id}/schedule")
def put_schedule(
    site_id: int,
    data: ScheduleIn,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    check_site_access(auth, site_id)
    """Create or update operating schedule for site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    # Validate exceptions_json if provided
    if data.exceptions_json:
        try:
            parsed = json.loads(data.exceptions_json)
            if not isinstance(parsed, list):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=422, detail="exceptions_json doit etre un JSON array de dates")

    # Validate intervals_json if provided
    intervals_raw = None
    if data.intervals_json:
        try:
            intervals_raw = json.loads(data.intervals_json)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=422, detail="intervals_json doit etre du JSON valide")

        errs = validate_intervals(intervals_raw)
        if errs:
            raise HTTPException(status_code=422, detail={"errors": errs})

        # Sync legacy columns from intervals for backward compatibility
        open_days_csv, open_time, close_time = _intervals_to_legacy(intervals_raw)
        data.open_days = open_days_csv
        data.open_time = open_time
        data.close_time = close_time

    # Simple legacy validation: open_time < close_time (unless 24/7)
    if not data.is_24_7 and not data.intervals_json:
        try:
            open_min = _parse_hhmm(data.open_time)
            close_min = _parse_hhmm(data.close_time)
            if open_min >= close_min:
                raise HTTPException(
                    status_code=422,
                    detail="open_time doit etre anterieur a close_time",
                )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    sched = db.query(SiteOperatingSchedule).filter(SiteOperatingSchedule.site_id == site_id).first()

    if sched:
        sched.timezone = data.timezone
        sched.open_days = data.open_days
        sched.open_time = data.open_time
        sched.close_time = data.close_time
        sched.is_24_7 = data.is_24_7
        sched.exceptions_json = data.exceptions_json
        sched.intervals_json = data.intervals_json
    else:
        sched = SiteOperatingSchedule(
            site_id=site_id,
            timezone=data.timezone,
            open_days=data.open_days,
            open_time=data.open_time,
            close_time=data.close_time,
            is_24_7=data.is_24_7,
            exceptions_json=data.exceptions_json,
            intervals_json=data.intervals_json,
        )
        db.add(sched)

    db.commit()

    return _build_schedule_response(site_id, sched)


# ---- Tariff endpoints ----


@router.get("/{site_id}/tariff")
def get_tariff(site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)):
    check_site_access(auth, site_id)
    """Return tariff profile for site (fallback to default if none)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    tariff = db.query(SiteTariffProfile).filter(SiteTariffProfile.site_id == site_id).first()

    if not tariff:
        return {
            "site_id": site_id,
            "price_ref_eur_per_kwh": DEFAULT_PRICE_REF,
            "currency": "EUR",
            "is_default": True,
        }

    return {
        "site_id": site_id,
        "price_ref_eur_per_kwh": tariff.price_ref_eur_per_kwh,
        "currency": tariff.currency,
        "is_default": False,
    }


@router.put("/{site_id}/tariff")
def put_tariff(
    site_id: int,
    data: TariffIn,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    check_site_access(auth, site_id)
    """Create or update tariff profile for site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    tariff = db.query(SiteTariffProfile).filter(SiteTariffProfile.site_id == site_id).first()

    if tariff:
        tariff.price_ref_eur_per_kwh = data.price_ref_eur_per_kwh
        tariff.currency = data.currency
    else:
        tariff = SiteTariffProfile(
            site_id=site_id,
            price_ref_eur_per_kwh=data.price_ref_eur_per_kwh,
            currency=data.currency,
        )
        db.add(tariff)

    db.commit()

    return {
        "site_id": site_id,
        "price_ref_eur_per_kwh": tariff.price_ref_eur_per_kwh,
        "currency": tariff.currency,
        "is_default": False,
    }


# ---- Helper for consumption_diagnostic ----


def get_site_schedule_params(db: Session, site_id: int) -> dict:
    """Get schedule params for diagnostic. Returns dict with open_time, close_time, open_days, is_24_7.

    If intervals_json is set, derives open_time/close_time from the first interval
    of each day for backward compatibility with the off-hours detector.
    """
    sched = db.query(SiteOperatingSchedule).filter(SiteOperatingSchedule.site_id == site_id).first()

    if sched:
        open_time_h = int(sched.open_time.split(":")[0])
        close_time_h = int(sched.close_time.split(":")[0])

        return {
            "open_time": open_time_h,
            "close_time": close_time_h,
            "open_days": set(int(d) for d in sched.open_days.split(",") if d.strip()),
            "is_24_7": sched.is_24_7,
            "exceptions": json.loads(sched.exceptions_json) if sched.exceptions_json else [],
        }

    return {
        "open_time": 8,
        "close_time": 19,
        "open_days": {0, 1, 2, 3, 4},
        "is_24_7": False,
        "exceptions": [],
    }


def get_site_price_ref(db: Session, site_id: int) -> float:
    """Get EUR/kWh price for a site. Fallback to DEFAULT_PRICE_REF."""
    tariff = db.query(SiteTariffProfile).filter(SiteTariffProfile.site_id == site_id).first()
    if tariff:
        return tariff.price_ref_eur_per_kwh
    return DEFAULT_PRICE_REF
