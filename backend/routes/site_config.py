"""
PROMEOS - Routes Site Configuration (schedule + tariff)
GET/PUT /api/site/:id/schedule
GET/PUT /api/site/:id/tariff
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Site, SiteOperatingSchedule, SiteTariffProfile

router = APIRouter(prefix="/api/site", tags=["Site Config"])

# Default values
DEFAULT_OPEN_TIME = "08:00"
DEFAULT_CLOSE_TIME = "19:00"
DEFAULT_OPEN_DAYS = "0,1,2,3,4"
DEFAULT_TIMEZONE = "Europe/Paris"
DEFAULT_PRICE_REF = 0.18


# ---- Schemas ----

class ScheduleIn(BaseModel):
    timezone: str = Field(DEFAULT_TIMEZONE, max_length=50)
    open_days: str = Field(DEFAULT_OPEN_DAYS, max_length=20, description="CSV: 0=Mon,6=Sun")
    open_time: str = Field(DEFAULT_OPEN_TIME, max_length=5, pattern=r"^\d{2}:\d{2}$")
    close_time: str = Field(DEFAULT_CLOSE_TIME, max_length=5, pattern=r"^\d{2}:\d{2}$")
    is_24_7: bool = False
    exceptions_json: Optional[str] = None


class TariffIn(BaseModel):
    price_ref_eur_per_kwh: float = Field(DEFAULT_PRICE_REF, gt=0, le=2.0)
    currency: str = Field("EUR", max_length=3)


# ---- Schedule endpoints ----

@router.get("/{site_id}/schedule")
def get_schedule(site_id: int, db: Session = Depends(get_db)):
    """Return operating schedule for site (creates default if none)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    sched = db.query(SiteOperatingSchedule).filter(
        SiteOperatingSchedule.site_id == site_id
    ).first()

    if not sched:
        # Return defaults (don't persist yet)
        return {
            "site_id": site_id,
            "timezone": DEFAULT_TIMEZONE,
            "open_days": DEFAULT_OPEN_DAYS,
            "open_time": DEFAULT_OPEN_TIME,
            "close_time": DEFAULT_CLOSE_TIME,
            "is_24_7": False,
            "exceptions_json": None,
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
        "is_default": False,
    }


@router.put("/{site_id}/schedule")
def put_schedule(site_id: int, data: ScheduleIn, db: Session = Depends(get_db)):
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

    sched = db.query(SiteOperatingSchedule).filter(
        SiteOperatingSchedule.site_id == site_id
    ).first()

    if sched:
        sched.timezone = data.timezone
        sched.open_days = data.open_days
        sched.open_time = data.open_time
        sched.close_time = data.close_time
        sched.is_24_7 = data.is_24_7
        sched.exceptions_json = data.exceptions_json
    else:
        sched = SiteOperatingSchedule(
            site_id=site_id,
            timezone=data.timezone,
            open_days=data.open_days,
            open_time=data.open_time,
            close_time=data.close_time,
            is_24_7=data.is_24_7,
            exceptions_json=data.exceptions_json,
        )
        db.add(sched)

    db.commit()

    return {
        "site_id": site_id,
        "timezone": sched.timezone,
        "open_days": sched.open_days,
        "open_time": sched.open_time,
        "close_time": sched.close_time,
        "is_24_7": sched.is_24_7,
        "exceptions_json": sched.exceptions_json,
        "is_default": False,
    }


# ---- Tariff endpoints ----

@router.get("/{site_id}/tariff")
def get_tariff(site_id: int, db: Session = Depends(get_db)):
    """Return tariff profile for site (fallback to default if none)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    tariff = db.query(SiteTariffProfile).filter(
        SiteTariffProfile.site_id == site_id
    ).first()

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
def put_tariff(site_id: int, data: TariffIn, db: Session = Depends(get_db)):
    """Create or update tariff profile for site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    tariff = db.query(SiteTariffProfile).filter(
        SiteTariffProfile.site_id == site_id
    ).first()

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
    """Get schedule params for diagnostic. Returns dict with open_time, close_time, open_days, is_24_7."""
    sched = db.query(SiteOperatingSchedule).filter(
        SiteOperatingSchedule.site_id == site_id
    ).first()

    if sched:
        return {
            "open_time": int(sched.open_time.split(":")[0]),
            "close_time": int(sched.close_time.split(":")[0]),
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
    tariff = db.query(SiteTariffProfile).filter(
        SiteTariffProfile.site_id == site_id
    ).first()
    if tariff:
        return tariff.price_ref_eur_per_kwh
    return DEFAULT_PRICE_REF
