"""
PROMEOS - EMS Consumption Explorer Routes
Timeseries, weather, energy signature, saved views.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from database import get_db

router = APIRouter(prefix="/api/ems", tags=["EMS Explorer"])


@router.get("/health")
def ems_health():
    return {"status": "ok", "module": "ems_explorer"}


# -------------------------------------------------------------------
# Timeseries
# -------------------------------------------------------------------
@router.get("/timeseries")
def get_timeseries(
    site_ids: str = Query(..., description="Comma-separated site IDs"),
    date_from: str = Query(...),
    date_to: str = Query(...),
    granularity: str = Query("auto"),
    mode: str = Query("aggregate"),
    metric: str = Query("kwh"),
    meter_ids: Optional[str] = None,
    energy_vector: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from services.ems.timeseries_service import (
        query_timeseries, suggest_granularity, validate_cap_points, VALID_GRANULARITIES,
    )

    parsed_site_ids = [int(x) for x in site_ids.split(",") if x.strip()]
    parsed_meter_ids = [int(x) for x in meter_ids.split(",") if x.strip()] if meter_ids else None
    dt_from = datetime.fromisoformat(date_from)
    dt_to = datetime.fromisoformat(date_to)

    if granularity == "auto":
        granularity = suggest_granularity(dt_from, dt_to)

    if granularity not in VALID_GRANULARITIES:
        raise HTTPException(400, f"Invalid granularity: {granularity}")

    if mode not in ("aggregate", "stack", "split"):
        raise HTTPException(400, f"Invalid mode: {mode}")

    ok, suggested, estimated = validate_cap_points(dt_from, dt_to, granularity)
    if not ok:
        raise HTTPException(400, detail={
            "error": "too_many_points",
            "estimated": estimated,
            "cap": 5000,
            "suggested_granularity": suggested,
        })

    return query_timeseries(
        db, parsed_site_ids, parsed_meter_ids,
        dt_from, dt_to, granularity, mode, metric, energy_vector,
    )


@router.get("/timeseries/suggest")
def suggest_timeseries_granularity(
    date_from: str = Query(...),
    date_to: str = Query(...),
):
    from services.ems.timeseries_service import suggest_granularity
    dt_from = datetime.fromisoformat(date_from)
    dt_to = datetime.fromisoformat(date_to)
    recommended = suggest_granularity(dt_from, dt_to)
    return {"granularity": recommended}
