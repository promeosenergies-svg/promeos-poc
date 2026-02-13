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


# -------------------------------------------------------------------
# Weather
# -------------------------------------------------------------------
@router.get("/weather")
def get_weather_data(
    site_id: int = Query(...),
    date_from: str = Query(...),
    date_to: str = Query(...),
    db: Session = Depends(get_db),
):
    from services.ems.weather_service import get_weather
    from datetime import date as date_cls
    df = date_cls.fromisoformat(date_from)
    dt = date_cls.fromisoformat(date_to)
    data = get_weather(db, site_id, df, dt)
    return {"site_id": site_id, "days": data}


# -------------------------------------------------------------------
# Energy Signature
# -------------------------------------------------------------------
@router.post("/signature/run")
def run_energy_signature(
    site_id: int = Query(...),
    date_from: str = Query(...),
    date_to: str = Query(...),
    meter_ids: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from services.ems.weather_service import get_weather
    from services.ems.signature_service import run_signature
    from services.ems.timeseries_service import query_timeseries
    from datetime import date as date_cls

    df = date_cls.fromisoformat(date_from)
    dt_to = date_cls.fromisoformat(date_to)
    parsed_meter_ids = [int(x) for x in meter_ids.split(",") if x.strip()] if meter_ids else None

    # Get daily consumption
    ts_data = query_timeseries(
        db, [site_id], parsed_meter_ids,
        datetime.combine(df, datetime.min.time()),
        datetime.combine(dt_to, datetime.min.time()),
        "daily", "aggregate", "kwh",
    )

    if not ts_data["series"] or not ts_data["series"][0]["data"]:
        raise HTTPException(404, "No consumption data for this site/period")

    daily_series = ts_data["series"][0]["data"]

    # Get weather
    weather = get_weather(db, site_id, df, dt_to)
    weather_map = {w["date"]: w["temp_avg_c"] for w in weather}

    # Align: only days with both consumption and weather
    daily_kwh = []
    daily_temp = []
    for pt in daily_series:
        date_key = pt["t"][:10]
        if date_key in weather_map:
            daily_kwh.append(pt["v"])
            daily_temp.append(weather_map[date_key])

    result = run_signature(daily_kwh, daily_temp)
    return result


# -------------------------------------------------------------------
# Saved Views CRUD
# -------------------------------------------------------------------
@router.get("/views")
def list_views(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    from models.ems_models import EmsSavedView
    q = db.query(EmsSavedView)
    if user_id is not None:
        # User's own views + shared views (user_id=null)
        q = q.filter((EmsSavedView.user_id == user_id) | (EmsSavedView.user_id.is_(None)))
    return [
        {"id": v.id, "user_id": v.user_id, "name": v.name, "config_json": v.config_json}
        for v in q.order_by(EmsSavedView.id).all()
    ]


@router.post("/views", status_code=201)
def create_view(
    name: str = Query(...),
    config_json: str = Query(...),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    from models.ems_models import EmsSavedView
    view = EmsSavedView(name=name, config_json=config_json, user_id=user_id)
    db.add(view)
    db.flush()
    return {"id": view.id, "name": view.name}


@router.get("/views/{view_id}")
def get_view(view_id: int, db: Session = Depends(get_db)):
    from models.ems_models import EmsSavedView
    view = db.query(EmsSavedView).filter(EmsSavedView.id == view_id).first()
    if not view:
        raise HTTPException(404, "View not found")
    return {"id": view.id, "user_id": view.user_id, "name": view.name, "config_json": view.config_json}


@router.put("/views/{view_id}")
def update_view(
    view_id: int,
    name: Optional[str] = None,
    config_json: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from models.ems_models import EmsSavedView
    view = db.query(EmsSavedView).filter(EmsSavedView.id == view_id).first()
    if not view:
        raise HTTPException(404, "View not found")
    if name is not None:
        view.name = name
    if config_json is not None:
        view.config_json = config_json
    db.flush()
    return {"id": view.id, "name": view.name}


@router.delete("/views/{view_id}")
def delete_view(view_id: int, db: Session = Depends(get_db)):
    from models.ems_models import EmsSavedView
    view = db.query(EmsSavedView).filter(EmsSavedView.id == view_id).first()
    if not view:
        raise HTTPException(404, "View not found")
    db.delete(view)
    db.flush()
    return {"deleted": True}
