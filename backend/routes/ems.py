"""
PROMEOS - EMS Consumption Explorer Routes
Timeseries, weather, energy signature, saved views, collections, demo data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import json

from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db

router = APIRouter(prefix="/api/ems", tags=["EMS Explorer"])


# -------------------------------------------------------------------
# V19-E: Pydantic response models for /timeseries (OpenAPI schema)
# -------------------------------------------------------------------
class TimeseriesDataPoint(BaseModel):
    t: str
    v: Optional[float] = None
    quality: Optional[float] = None
    estimated_pct: Optional[float] = None

class TimeseriesSeries(BaseModel):
    key: str
    label: str
    data: List[TimeseriesDataPoint]

class TimeseriesMeta(BaseModel):
    granularity: str
    metric: str
    n_points: int
    n_meters: int
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    sampling_minutes: Optional[int] = None
    available_granularities: Optional[List[str]] = None
    valid_count: Optional[int] = None

class TimeseriesAvailability(BaseModel):
    key: str
    expected_points: Optional[int] = None
    actual_points: Optional[int] = None
    coverage_pct: Optional[float] = None
    gaps: List = []

class TimeseriesResponse(BaseModel):
    series: List[TimeseriesSeries]
    meta: TimeseriesMeta
    availability: List[TimeseriesAvailability] = []


@router.get("/health")
def ems_health():
    return {"status": "ok", "module": "ems_explorer"}


# -------------------------------------------------------------------
# Usage Suggest (archetype + schedule)
# -------------------------------------------------------------------
def _archetype_to_profile(code: str) -> str:
    """Map KB archetype code to a profile name for schedule lookup."""
    c = code.lower()
    if "bureau" in c:
        return "office"
    if "commerce" in c or "magasin" in c or "restauration" in c:
        return "retail"
    if "hotel" in c:
        return "hotel"
    if "sante" in c or "hopital" in c:
        return "hospital"
    if "enseignement" in c:
        return "school"
    if "logistique" in c or "entrepot" in c:
        return "warehouse"
    return "office"


@router.get("/usage_suggest")
def usage_suggest(site_id: int = Query(...), db: Session = Depends(get_db)):
    """Suggest archetype + operating schedule for a site based on NAF code or site type."""
    from models import Site, SiteOperatingSchedule, KBMappingCode, TypeSite
    from services.demo_seed.gen_master import _PROFILE_SCHEDULES

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, "Site not found")

    # Current schedule
    schedule = db.query(SiteOperatingSchedule).filter_by(site_id=site_id).first()
    schedule_current = None
    if schedule:
        schedule_current = {
            "open_days": schedule.open_days,
            "open_time": schedule.open_time,
            "close_time": schedule.close_time,
            "is_24_7": schedule.is_24_7,
        }

    # Determine archetype
    archetype_code = None
    archetype_label = None
    archetype_source = "default"
    confidence = "low"
    profile_name = "office"
    reasons = []

    # 1. Try NAF mapping via KBMappingCode → KBArchetype
    if site.naf_code:
        mapping = (
            db.query(KBMappingCode)
            .filter_by(naf_code=site.naf_code)
            .order_by(KBMappingCode.priority.desc())
            .first()
        )
        if mapping and mapping.archetype:
            arch = mapping.archetype
            archetype_code = arch.code
            archetype_label = arch.title
            archetype_source = "naf"
            confidence = "high"
            profile_name = _archetype_to_profile(arch.code)
            reasons.append(f"NAF {site.naf_code} → {arch.code}")

    # 2. Fallback to site type
    _TYPE_FALLBACK = {
        TypeSite.BUREAU: ("BUREAU_STANDARD", "Bureau standard", "office"),
        TypeSite.COMMERCE: ("COMMERCE_ALIMENTAIRE", "Commerce alimentaire", "retail"),
        TypeSite.MAGASIN: ("COMMERCE_ALIMENTAIRE", "Commerce alimentaire", "retail"),
        TypeSite.ENTREPOT: ("LOGISTIQUE_ENTREPOT", "Logistique entrepot", "warehouse"),
        TypeSite.HOTEL: ("HOTEL", "Hotel", "hotel"),
        TypeSite.SANTE: ("SANTE_HOPITAL", "Sante hopital", "hospital"),
        TypeSite.ENSEIGNEMENT: ("ENSEIGNEMENT", "Enseignement", "school"),
        TypeSite.COPROPRIETE: ("BUREAU_STANDARD", "Bureau standard", "office"),
    }
    if not archetype_code:
        fb = _TYPE_FALLBACK.get(site.type)
        if fb:
            archetype_code, archetype_label, profile_name = fb
            archetype_source = "type_fallback"
            confidence = "medium"
            reasons.append(f"Type {site.type.value} → {archetype_code}")
        else:
            archetype_code = "BUREAU_STANDARD"
            archetype_label = "Bureau standard"
            confidence = "low"
            reasons.append("Archetype par defaut")

    # Schedule suggestion from profile
    sched_cfg = _PROFILE_SCHEDULES.get(profile_name, _PROFILE_SCHEDULES["office"])
    schedule_suggested = {
        "open_days": sched_cfg["open_days"],
        "open_time": sched_cfg["open_time"],
        "close_time": sched_cfg["close_time"],
        "is_24_7": sched_cfg["is_24_7"],
    }

    return {
        "site_id": site_id,
        "archetype_code": archetype_code,
        "archetype_label": archetype_label,
        "archetype_source": archetype_source,
        "confidence": confidence,
        "schedule_current": schedule_current,
        "schedule_suggested": schedule_suggested,
        "has_vacation": profile_name == "school",
        "reasons": reasons,
    }


# -------------------------------------------------------------------
# Benchmark by archetype
# -------------------------------------------------------------------
@router.get("/benchmark")
def ems_benchmark(site_id: int = Query(...), db: Session = Depends(get_db)):
    """Benchmark a site's KPIs against peers of the same archetype."""
    from models import Site, MonitoringSnapshot, KBMappingCode, TypeSite
    from services.electric_monitoring.benchmark import build_benchmark

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, "Site not found")

    # Get latest snapshot for target site
    target_snap = (
        db.query(MonitoringSnapshot)
        .filter(MonitoringSnapshot.site_id == site_id)
        .order_by(MonitoringSnapshot.id.desc())
        .first()
    )
    if not target_snap or not target_snap.kpis_json:
        return {"site_id": site_id, "insufficient": True, "peer_count": 0, "benchmarks": {}, "source": "demo"}

    target_kpis = target_snap.kpis_json

    # Determine peer group: same site type
    peer_site_ids = [
        r[0] for r in db.query(Site.id)
        .filter(Site.type == site.type, Site.id != site_id, Site.actif == True)
        .all()
    ]

    # Collect peer KPIs from latest snapshots
    peer_kpis_list = []
    for pid in peer_site_ids:
        snap = (
            db.query(MonitoringSnapshot)
            .filter(MonitoringSnapshot.site_id == pid)
            .order_by(MonitoringSnapshot.id.desc())
            .first()
        )
        if snap and snap.kpis_json:
            peer_kpis_list.append(snap.kpis_json)

    if len(peer_kpis_list) < 3:
        return {"site_id": site_id, "insufficient": True, "peer_count": len(peer_kpis_list), "benchmarks": {}, "source": "demo"}

    benchmark_keys = ["pbase_kw", "off_hours_ratio", "load_factor", "pmax_kw", "p95_kw"]
    benchmarks = build_benchmark(target_kpis, peer_kpis_list, benchmark_keys)

    return {
        "site_id": site_id,
        "archetype": site.type.value if site.type else "unknown",
        "peer_count": len(peer_kpis_list),
        "benchmarks": benchmarks,
        "source": "demo",
        "insufficient": False,
    }


# -------------------------------------------------------------------
# Schedule Suggest (from consumption data)
# -------------------------------------------------------------------
@router.get("/schedule_suggest")
def schedule_suggest(
    site_id: int = Query(...),
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Suggest operating schedule from actual consumption data."""
    from services.ems.schedule_suggest_service import suggest_schedule_from_consumption
    try:
        return suggest_schedule_from_consumption(db, site_id, days)
    except Exception as e:
        return {"error": "computation_error", "reasons": [str(e)[:200]], "schedule_suggested": None}


# -------------------------------------------------------------------
# Timeseries
# -------------------------------------------------------------------
@router.get("/timeseries", response_model=TimeseriesResponse)
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

    if mode not in ("aggregate", "overlay", "stack", "split"):
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
    site_id: Optional[int] = Query(None),
    site_ids: Optional[str] = Query(None, description="Comma-separated site IDs for multi-site average"),
    date_from: str = Query(...),
    date_to: str = Query(...),
    db: Session = Depends(get_db),
):
    from services.ems.weather_service import get_weather, get_weather_multi
    from datetime import date as date_cls
    df = date_cls.fromisoformat(date_from)
    dt = date_cls.fromisoformat(date_to)

    if site_ids:
        parsed_ids = [int(x) for x in site_ids.split(",") if x.strip()]
        result = get_weather_multi(db, parsed_ids, df, dt)
        return {"site_ids": parsed_ids, "days": result["days"], "meta": result["meta"], "mode": "average"}
    elif site_id:
        data = get_weather(db, site_id, df, dt)
        return {"site_id": site_id, "days": data}
    else:
        return {"days": [], "error": "Provide site_id or site_ids"}


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


@router.post("/signature/portfolio")
def run_portfolio_signature(
    site_ids: str = Query(..., description="Comma-separated site IDs"),
    date_from: str = Query(...),
    date_to: str = Query(...),
    meter_ids: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Run energy signature on aggregated consumption across multiple sites.
    Uses averaged weather and summed consumption for the portfolio.
    """
    from services.ems.weather_service import get_weather_multi
    from services.ems.signature_service import run_signature
    from services.ems.timeseries_service import query_timeseries
    from datetime import date as date_cls

    parsed_site_ids = [int(x) for x in site_ids.split(",") if x.strip()]
    if not parsed_site_ids:
        raise HTTPException(400, "No site IDs provided")

    df = date_cls.fromisoformat(date_from)
    dt_to = date_cls.fromisoformat(date_to)
    parsed_meter_ids = [int(x) for x in meter_ids.split(",") if x.strip()] if meter_ids else None

    # Get aggregated daily consumption across all sites
    ts_data = query_timeseries(
        db, parsed_site_ids, parsed_meter_ids,
        datetime.combine(df, datetime.min.time()),
        datetime.combine(dt_to, datetime.min.time()),
        "daily", "aggregate", "kwh",
    )

    if not ts_data["series"] or not ts_data["series"][0]["data"]:
        raise HTTPException(404, "No consumption data for this portfolio/period")

    daily_series = ts_data["series"][0]["data"]

    # Get averaged weather across sites
    weather_result = get_weather_multi(db, parsed_site_ids, df, dt_to)
    weather_map = {w["date"]: w["temp_avg_c"] for w in weather_result["days"]}

    # Align: only days with both consumption and weather
    daily_kwh = []
    daily_temp = []
    for pt in daily_series:
        date_key = pt["t"][:10]
        if date_key in weather_map:
            daily_kwh.append(pt["v"])
            daily_temp.append(weather_map[date_key])

    result = run_signature(daily_kwh, daily_temp)
    result["mode"] = "portfolio"
    result["n_sites"] = len(parsed_site_ids)
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


# -------------------------------------------------------------------
# Collections CRUD (Paniers de sites)
# -------------------------------------------------------------------
@router.get("/collections")
def list_collections(db: Session = Depends(get_db)):
    from models.ems_models import EmsCollection
    cols = db.query(EmsCollection).order_by(EmsCollection.is_favorite.desc(), EmsCollection.id).all()
    return [
        {"id": c.id, "name": c.name, "scope_type": c.scope_type,
         "site_ids": json.loads(c.site_ids_json), "is_favorite": bool(c.is_favorite)}
        for c in cols
    ]


@router.post("/collections", status_code=201)
def create_collection(
    name: str = Query(...),
    site_ids: str = Query(..., description="Comma-separated site IDs"),
    scope_type: str = Query("custom"),
    is_favorite: bool = Query(False),
    db: Session = Depends(get_db),
):
    from models.ems_models import EmsCollection
    parsed_ids = [int(x) for x in site_ids.split(",") if x.strip()]
    col = EmsCollection(
        name=name, scope_type=scope_type,
        site_ids_json=json.dumps(parsed_ids),
        is_favorite=1 if is_favorite else 0,
    )
    db.add(col)
    db.flush()
    return {"id": col.id, "name": col.name, "site_ids": parsed_ids}


@router.put("/collections/{col_id}")
def update_collection(
    col_id: int,
    name: Optional[str] = None,
    site_ids: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    from models.ems_models import EmsCollection
    col = db.query(EmsCollection).filter(EmsCollection.id == col_id).first()
    if not col:
        raise HTTPException(404, "Collection not found")
    if name is not None:
        col.name = name
    if site_ids is not None:
        col.site_ids_json = json.dumps([int(x) for x in site_ids.split(",") if x.strip()])
    if is_favorite is not None:
        col.is_favorite = 1 if is_favorite else 0
    db.flush()
    return {"id": col.id, "name": col.name}


@router.delete("/collections/{col_id}")
def delete_collection(col_id: int, db: Session = Depends(get_db)):
    from models.ems_models import EmsCollection
    col = db.query(EmsCollection).filter(EmsCollection.id == col_id).first()
    if not col:
        raise HTTPException(404, "Collection not found")
    db.delete(col)
    db.flush()
    return {"deleted": True}


# -------------------------------------------------------------------
# Demo Data Generation (WAOUH B2B realistic)
# -------------------------------------------------------------------
@router.post("/demo/generate")
def generate_ems_demo(
    portfolio_size: int = Query(12),
    days: int = Query(365),
    seed: int = Query(123),
    force: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Generate realistic multi-site demo data with anomalies and weather."""
    import math
    import random as _random
    from models import Site, Meter, MeterReading
    from models.energy_models import FrequencyType
    from models.ems_models import EmsWeatherCache

    rng = _random.Random(seed)

    # Check idempotence: if demo readings exist and not force, skip
    existing = db.query(MeterReading).join(Meter).filter(
        Meter.meter_id.like("EMS-DEMO-%")
    ).count()
    if existing > 0 and not force:
        return {"status": "skipped", "message": f"{existing} demo readings already exist. Use force=true to regenerate."}

    # If force, purge old demo data
    if force and existing > 0:
        demo_meters = db.query(Meter).filter(Meter.meter_id.like("EMS-DEMO-%")).all()
        for dm in demo_meters:
            db.query(MeterReading).filter(MeterReading.meter_id == dm.id).delete()
            db.query(EmsWeatherCache).filter(EmsWeatherCache.site_id == dm.site_id, EmsWeatherCache.source == "demo_ems").delete()
        db.flush()

    # Resolve sites from scope (use first N available)
    sites = db.query(Site).order_by(Site.id).limit(portfolio_size).all()
    if not sites:
        raise HTTPException(400, "No sites found. Seed basic data first.")

    # Site profiles (realistic B2B french energy)
    PROFILES = [
        {"archetype": "bureau", "base_kw": 8, "day_mult": 4.5, "wknd": 0.25, "season": 0.22, "night": 0.10, "heating_coeff": 0.4},
        {"archetype": "bureau", "base_kw": 6, "day_mult": 3.5, "wknd": 0.30, "season": 0.18, "night": 0.12, "heating_coeff": 0.3},
        {"archetype": "bureau", "base_kw": 10, "day_mult": 5.0, "wknd": 0.20, "season": 0.25, "night": 0.08, "heating_coeff": 0.5},
        {"archetype": "bureau", "base_kw": 7, "day_mult": 4.0, "wknd": 0.28, "season": 0.20, "night": 0.11, "heating_coeff": 0.35},
        {"archetype": "bureau", "base_kw": 9, "day_mult": 4.8, "wknd": 0.22, "season": 0.24, "night": 0.09, "heating_coeff": 0.45},
        {"archetype": "retail", "base_kw": 18, "day_mult": 1.8, "wknd": 0.85, "season": 0.12, "night": 0.55, "heating_coeff": 0.15},
        {"archetype": "retail", "base_kw": 22, "day_mult": 1.6, "wknd": 0.90, "season": 0.14, "night": 0.60, "heating_coeff": 0.12},
        {"archetype": "retail", "base_kw": 15, "day_mult": 2.0, "wknd": 0.80, "season": 0.10, "night": 0.50, "heating_coeff": 0.18},
        {"archetype": "logistique", "base_kw": 12, "day_mult": 3.0, "wknd": 0.15, "season": 0.08, "night": 0.05, "heating_coeff": 0.10},
        {"archetype": "logistique", "base_kw": 14, "day_mult": 2.8, "wknd": 0.12, "season": 0.06, "night": 0.04, "heating_coeff": 0.08},
        {"archetype": "datacenter", "base_kw": 50, "day_mult": 1.1, "wknd": 0.98, "season": 0.08, "night": 0.95, "heating_coeff": -0.2},
        {"archetype": "process", "base_kw": 25, "day_mult": 2.5, "wknd": 0.40, "season": 0.05, "night": 0.20, "heating_coeff": 0.05},
    ]

    # Anomaly injection targets
    ANOMALIES = {
        0: "high_night_base",   # Bureau with elevated night consumption
        5: "morning_peaks",     # Retail with recurring morning peaks
        8: "progressive_drift", # Logistique with progressive drift over months
        3: "profile_rupture",   # Bureau with schedule change mid-year
    }

    now = datetime.utcnow()
    start_date = datetime(now.year - 1, now.month, now.day)
    total_readings = 0
    site_reports = []

    for idx, site in enumerate(sites[:portfolio_size]):
        profile = PROFILES[idx % len(PROFILES)]
        meter_id_str = f"EMS-DEMO-{site.id:06d}"

        # Create or reuse meter
        meter = db.query(Meter).filter_by(meter_id=meter_id_str).first()
        if not meter:
            meter = Meter(
                meter_id=meter_id_str,
                name=f"{profile['archetype'].capitalize()} {site.nom}",
                site_id=site.id,
                subscribed_power_kva=profile["base_kw"] * profile["day_mult"] * 1.2,
            )
            db.add(meter)
            db.flush()

        readings = []
        anomaly_type = ANOMALIES.get(idx)
        site_rng = _random.Random(seed * 1000 + site.id)

        for day_offset in range(days):
            dt_day = start_date + __import__('datetime').timedelta(days=day_offset)
            dow = dt_day.weekday()
            is_wknd = dow >= 5
            month = dt_day.month
            day_of_year = dt_day.timetuple().tm_yday

            # Seasonal factor (heating peaks in winter, cooling in summer)
            seasonal = 1.0 + profile["season"] * math.cos(2 * math.pi * (month - 1) / 12.0)

            # Temperature-driven heating/cooling component
            temp_approx = 12 + 10 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
            temp_approx += site_rng.gauss(0, 2)
            heating_bonus = max(0, (15 - temp_approx)) * profile["heating_coeff"] * 0.1

            for hour in range(24):
                ts = dt_day.replace(hour=hour)

                if is_wknd:
                    factor = profile["wknd"]
                elif 8 <= hour <= 18:
                    factor = profile["day_mult"]
                elif 6 <= hour <= 7 or 19 <= hour <= 20:
                    factor = profile["day_mult"] * 0.5
                else:
                    factor = profile["night"]

                value = profile["base_kw"] * factor * seasonal + heating_bonus
                value *= site_rng.uniform(0.88, 1.12)

                # --- Anomaly injection ---
                if anomaly_type == "high_night_base" and (hour < 6 or hour > 21) and not is_wknd:
                    value *= 2.5  # Night consumption 2.5x normal
                elif anomaly_type == "morning_peaks" and 7 <= hour <= 9 and not is_wknd:
                    value *= 3.0 + site_rng.uniform(0, 1.5)  # Morning spikes
                elif anomaly_type == "progressive_drift":
                    drift = 1.0 + (day_offset / days) * 0.6  # +60% over the year
                    value *= drift
                elif anomaly_type == "profile_rupture" and day_offset > days // 2:
                    # Schedule shift: becomes active on weekends, different hours
                    if is_wknd:
                        value *= 3.0
                    if 20 <= hour <= 23:
                        value *= 2.0

                value = max(0.1, value)
                readings.append(MeterReading(
                    meter_id=meter.id,
                    timestamp=ts,
                    frequency=FrequencyType.HOURLY,
                    value_kwh=round(value, 2),
                    is_estimated=False,
                    quality_score=site_rng.uniform(0.85, 1.0),
                ))

            # Weather cache for this site/day
            weather_entry = EmsWeatherCache(
                site_id=site.id,
                date=dt_day,
                temp_avg_c=round(temp_approx, 1),
                temp_min_c=round(temp_approx - site_rng.uniform(2, 5), 1),
                temp_max_c=round(temp_approx + site_rng.uniform(2, 5), 1),
                source="demo_ems",
            )
            readings.append(weather_entry)

        # Separate readings and weather for bulk insert
        meter_readings = [r for r in readings if isinstance(r, MeterReading)]
        weather_entries = [r for r in readings if isinstance(r, EmsWeatherCache)]

        db.bulk_save_objects(meter_readings)
        # Weather: ignore conflicts (existing entries from weather_service)
        for w in weather_entries:
            existing_w = db.query(EmsWeatherCache).filter_by(site_id=w.site_id, date=w.date).first()
            if not existing_w:
                db.add(w)
        db.flush()

        total_readings += len(meter_readings)
        site_reports.append({
            "site_id": site.id, "site_nom": site.nom,
            "archetype": profile["archetype"],
            "readings": len(meter_readings),
            "anomaly": anomaly_type,
        })

    db.commit()

    return {
        "status": "ok",
        "total_readings": total_readings,
        "sites_generated": len(site_reports),
        "period": f"{start_date.date()} - {(start_date + __import__('datetime').timedelta(days=days)).date()}",
        "sites": site_reports,
    }


# -------------------------------------------------------------------
# V20-C: Per-site timeseries demo generator
# -------------------------------------------------------------------
class TimeseriesDemoResponse(BaseModel):
    site_id: int
    meter_id: str
    n_readings: int
    date_from: str
    date_to: str
    status: str


@router.post("/demo/generate_timeseries", response_model=TimeseriesDemoResponse)
def generate_timeseries_demo(
    site_id: int = Query(..., description="Site ID to generate demo timeseries for"),
    days: int = Query(default=90, ge=7, le=365),
    anomaly: bool = Query(default=True),
    energy_vector: str = Query(default="electricity", description="Energy vector: electricity|gas|heat|water"),
    db: Session = Depends(get_db),
):
    """Generate synthetic consumption (MeterReading) for a specific site.
    Supports electricity (hourly, bureau pattern) and gas (daily, seasonal pattern).
    Writes rows queryable by GET /api/ems/timeseries immediately after this call.
    """
    if energy_vector == "gas":
        from services.consumption_diagnostic import generate_demo_gas_consumption
        result = generate_demo_gas_consumption(db, site_id, days=days, anomaly=anomaly)
    else:
        from services.consumption_diagnostic import generate_demo_consumption
        result = generate_demo_consumption(db, site_id, days=days, anomaly=anomaly)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return TimeseriesDemoResponse(
        site_id=site_id,
        meter_id=str(result.get("meter_id", "")),
        n_readings=result.get("readings_count", 0),
        date_from=result.get("period_start", ""),
        date_to=result.get("period_end", ""),
        status="ok",
    )


@router.post("/demo/purge")
def purge_ems_demo(db: Session = Depends(get_db)):
    """Remove all EMS demo data."""
    from models import Meter, MeterReading
    from models.ems_models import EmsWeatherCache

    demo_meters = db.query(Meter).filter(Meter.meter_id.like("EMS-DEMO-%")).all()
    deleted_readings = 0
    deleted_weather = 0
    for dm in demo_meters:
        deleted_readings += db.query(MeterReading).filter(MeterReading.meter_id == dm.id).delete()
        deleted_weather += db.query(EmsWeatherCache).filter(
            EmsWeatherCache.site_id == dm.site_id,
            EmsWeatherCache.source == "demo_ems"
        ).delete()
        db.delete(dm)

    db.flush()
    db.commit()
    return {
        "status": "ok",
        "deleted_meters": len(demo_meters),
        "deleted_readings": deleted_readings,
        "deleted_weather": deleted_weather,
    }
