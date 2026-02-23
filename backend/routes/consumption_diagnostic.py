"""
PROMEOS - Routes Diagnostic Consommation V2 (World-Class)
GET /api/consumption/insights — insights aggreges par org
POST /api/consumption/diagnose — lancer le diagnostic
POST /api/consumption/seed-demo — generer des conso demo
GET /api/consumption/site/:id — insights d'un site
GET /api/consumption/tunnel — enveloppe quantiles P10-P90
CRUD /api/consumption/targets — objectifs & budgets
CRUD /api/consumption/tou_schedules — grilles HP/HC
GET /api/consumption/hp_hc — ratio HP/HC
GET /api/consumption/gas/summary — resume gaz
"""
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access
from models import Organisation, Site, ConsumptionInsight, not_deleted
from models.enums import InsightStatus
from services.consumption_diagnostic import (
    generate_demo_consumption,
    run_diagnostic,
    run_diagnostic_org,
    get_insights_summary,
)
from services.scope_utils import get_scope_org_id, resolve_org_id
from services.tunnel_service import compute_tunnel, compute_tunnel_v2
from services.targets_service import (
    get_targets, create_target, update_target, delete_target, get_progression, get_progression_v2,
)
from services.tou_service import (
    get_schedules, get_active_schedule, create_schedule, update_schedule,
    delete_schedule, compute_hp_hc_ratio, compute_hphc_breakdown_v2,
)
from models.tariff_calendar import TariffCalendar


class InsightPatch(BaseModel):
    insight_status: Optional[str] = None

router = APIRouter(prefix="/api/consumption", tags=["Consumption Diagnostic"])


def _get_header_org_id(request: Request) -> Optional[int]:
    """Extract X-Org-Id header as int, or None."""
    raw = request.headers.get("X-Org-Id")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return None


@router.get("/insights")
def consumption_insights(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Aggregate consumption insights for an organisation.
    Scope priority: auth token > X-Org-Id header > org_id query param > DEMO_MODE fallback.
    """
    org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    return get_insights_summary(db, org_id)


@router.get("/site/{site_id}")
def site_insights(site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)):
    """Get consumption insights for a specific site."""
    check_site_access(auth, site_id)
    import json
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    insights = (
        db.query(ConsumptionInsight)
        .filter(ConsumptionInsight.site_id == site_id)
        .all()
    )

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "insights": [
            {
                "id": ci.id,
                "type": ci.type,
                "severity": ci.severity,
                "message": ci.message,
                "estimated_loss_kwh": ci.estimated_loss_kwh,
                "estimated_loss_eur": ci.estimated_loss_eur,
                "recommended_actions": json.loads(ci.recommended_actions_json) if ci.recommended_actions_json else [],
                "metrics": json.loads(ci.metrics_json) if ci.metrics_json else {},
                "period_start": ci.period_start.isoformat() if ci.period_start else None,
                "period_end": ci.period_end.isoformat() if ci.period_end else None,
                "insight_status": ci.insight_status.value if ci.insight_status else "open",
            }
            for ci in insights
        ],
    }


@router.post("/diagnose")
def diagnose(
    request: Request,
    org_id: Optional[int] = Query(None),
    days: int = Query(30),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Run diagnostics for all sites of an organisation."""
    org_id = resolve_org_id(request, auth, db, org_id_override=org_id)

    result = run_diagnostic_org(db, org_id, days=days)
    return {"status": "ok", **result}


@router.post("/seed-demo")
def seed_demo_consumption(
    site_id: Optional[int] = Query(None),
    days: int = Query(30),
    db: Session = Depends(get_db),
):
    """Generate demo consumption data for a site (or all sites if site_id is None).
    Also seeds TariffCalendar references and gas weather data."""
    import json, math
    from datetime import datetime, timedelta
    from models import Meter, MeterReading
    from models.energy_models import EnergyVector

    if site_id:
        result = generate_demo_consumption(db, site_id, days=days)
        return {"status": "ok", "sites": [result]}

    # Seed all sites
    sites = not_deleted(db.query(Site), Site).filter(Site.actif == True).all()
    if not sites:
        raise HTTPException(status_code=400, detail="Aucun site actif.")

    results = []
    for site in sites:
        r = generate_demo_consumption(db, site.id, days=days)
        results.append(r)

    # --- Seed TariffCalendar references (idempotent) ---
    tariff_seeded = 0
    existing_names = {t.name for t in db.query(TariffCalendar.name).all()}

    turpe6_windows = json.dumps([
        {"day_types": ["weekday"], "start": "06:00", "end": "22:00", "period": "HP"},
        {"day_types": ["weekday"], "start": "22:00", "end": "06:00", "period": "HC"},
        {"day_types": ["saturday", "sunday"], "start": "00:00", "end": "24:00", "period": "HC"},
    ])
    turpe7_windows = json.dumps([
        {"day_types": ["weekday"], "start": "07:00", "end": "23:00", "period": "HP"},
        {"day_types": ["weekday"], "start": "23:00", "end": "07:00", "period": "HC"},
        {"day_types": ["saturday"], "start": "07:00", "end": "14:00", "period": "HP"},
        {"day_types": ["saturday"], "start": "14:00", "end": "07:00", "period": "HC"},
        {"day_types": ["sunday"], "start": "00:00", "end": "24:00", "period": "HC"},
    ])

    if "TURPE 6 HTA" not in existing_names:
        db.add(TariffCalendar(
            name="TURPE 6 HTA", version="6.0", effective_from="2024-01-01",
            region="national", ruleset_json=turpe6_windows, is_active=True,
            source="CRE", notes="Grille TURPE 6 standard HTA",
        ))
        tariff_seeded += 1
    if "TURPE 7 HTA-nov2025" not in existing_names:
        db.add(TariffCalendar(
            name="TURPE 7 HTA-nov2025", version="7.0-beta", effective_from="2025-11-01",
            region="national", ruleset_json=turpe7_windows, is_active=True,
            source="CRE", notes="Grille TURPE 7 simulee (projet nov 2025)",
        ))
        tariff_seeded += 1

    # --- Seed seasonal gas readings for gas meters ---
    gas_seeded = 0
    now = datetime.utcnow()
    for site in sites:
        gas_meters = db.query(Meter).filter(
            Meter.site_id == site.id, Meter.is_active == True,
            Meter.energy_vector == EnergyVector.GAS,
        ).all()
        for meter in gas_meters:
            # Check if already has enough readings
            count = db.query(MeterReading).filter(
                MeterReading.meter_id == meter.id,
                MeterReading.timestamp >= now - timedelta(days=days),
            ).count()
            if count >= days * 12:
                continue  # Already seeded

            for day_offset in range(days):
                dt_base = now - timedelta(days=days - day_offset)
                doy = dt_base.timetuple().tm_yday
                # DJU-based seasonal pattern
                t_avg = 12 + 10 * math.sin(2 * math.pi * (doy - 80) / 365)
                dju = max(0, 18 - t_avg)
                daily_kwh = 25 + 6 * dju + (math.sin(doy * 3.7) * 3)  # base + heating + noise
                for h in [0, 4, 8, 12, 16, 20]:  # 6 readings/day (every 4h)
                    db.add(MeterReading(
                        meter_id=meter.id,
                        timestamp=dt_base.replace(hour=h, minute=0, second=0),
                        value_kwh=round(daily_kwh / 6, 2),
                    ))
            gas_seeded += 1

    db.commit()

    return {
        "status": "ok", "sites": results, "total": len(results),
        "tariff_calendars_seeded": tariff_seeded,
        "gas_meters_seeded": gas_seeded,
    }


# =============================================
# V10.1 — Availability (data presence check)
# =============================================

ENERGY_TYPE_ALIASES = {
    "electricity": "electricity", "elec": "electricity", "electricite": "electricity",
    "électricité": "electricity", "electric": "electricity",
    "gas": "gas", "gaz": "gas",
}


def _normalize_energy_type(raw: str) -> str:
    """Tolerate various energy type spellings."""
    return ENERGY_TYPE_ALIASES.get(raw.lower().strip(), raw.lower().strip())


@router.get("/availability")
def consumption_availability(
    site_id: int = Query(..., description="Site ID"),
    energy_type: str = Query("electricity"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Check data availability for a site: meters, readings, date range, reason codes."""
    from models import Meter, MeterReading
    from models.energy_models import EnergyVector
    from sqlalchemy import func

    check_site_access(auth, site_id)
    energy_type = _normalize_energy_type(energy_type)
    reasons = []

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {"has_data": False, "reasons": ["no_site"], "energy_types": [], "meters_count": 0}

    # All active meters for this site
    all_meters = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).all()
    if not all_meters:
        return {"has_data": False, "reasons": ["no_meter"], "energy_types": [], "meters_count": 0,
                "site_nom": site.nom}

    # Available energy types
    ev_map = {"electricity": EnergyVector.ELECTRICITY, "gas": EnergyVector.GAS}
    available_types = list({
        "electricity" if m.energy_vector == EnergyVector.ELECTRICITY
        else "gas" if m.energy_vector == EnergyVector.GAS
        else "other"
        for m in all_meters
    })

    # Filter by requested energy type
    target_ev = ev_map.get(energy_type)
    matching_meters = [m for m in all_meters if m.energy_vector == target_ev] if target_ev else all_meters

    if not matching_meters:
        reasons.append("wrong_energy_type")
        return {
            "has_data": False, "reasons": reasons, "energy_types": available_types,
            "meters_count": len(all_meters), "matching_meters": 0,
            "site_nom": site.nom,
        }

    meter_ids = [m.id for m in matching_meters]

    # Date range of available readings
    stats = db.query(
        func.count(MeterReading.id),
        func.min(MeterReading.timestamp),
        func.max(MeterReading.timestamp),
    ).filter(MeterReading.meter_id.in_(meter_ids)).first()

    readings_count = stats[0] or 0
    first_ts = stats[1].isoformat() if stats[1] else None
    last_ts = stats[2].isoformat() if stats[2] else None

    if readings_count == 0:
        reasons.append("no_readings")
        return {
            "has_data": False, "reasons": reasons, "energy_types": available_types,
            "meters_count": len(matching_meters), "readings_count": 0,
            "site_nom": site.nom,
        }

    if readings_count < 48:
        reasons.append("insufficient_readings")

    return {
        "has_data": readings_count >= 48,
        "reasons": reasons,
        "energy_types": available_types,
        "meters_count": len(matching_meters),
        "readings_count": readings_count,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "site_nom": site.nom,
    }


@router.patch("/insights/{insight_id}")
def patch_consumption_insight(
    insight_id: int,
    data: InsightPatch,
    db: Session = Depends(get_db),
):
    """PATCH /api/consumption/insights/{insight_id} — workflow update (ack, resolved, false_positive)."""
    ci = db.query(ConsumptionInsight).filter(ConsumptionInsight.id == insight_id).first()
    if not ci:
        raise HTTPException(status_code=404, detail="Insight non trouve")
    if data.insight_status is not None:
        try:
            ci.insight_status = InsightStatus(data.insight_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {data.insight_status}")
    db.commit()
    db.refresh(ci)
    return {"status": "updated", "id": ci.id, "insight_status": ci.insight_status.value}


# =============================================
# V10 — Tunnel (Enveloppe Quantile)
# =============================================

@router.get("/tunnel")
def get_tunnel(
    site_id: int = Query(..., description="Site ID"),
    days: int = Query(90, ge=7, le=365),
    energy_type: str = Query("electricity"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Enveloppe de consommation (tunnel P10-P90) pour un site."""
    check_site_access(auth, site_id)
    energy_type = _normalize_energy_type(energy_type)
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")
    return compute_tunnel(db, site_id, days=days, energy_type=energy_type)


# =============================================
# V11 — Tunnel V2 (energy + power mode)
# =============================================

@router.get("/tunnel_v2")
def get_tunnel_v2(
    site_id: int = Query(..., description="Site ID"),
    days: int = Query(90, ge=7, le=365),
    energy_type: str = Query("electricity"),
    mode: str = Query("energy", description="energy (kWh) or power (kW)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Tunnel V2: enveloppe quantile P10-P90 en mode energie (kWh) ou puissance (kW)."""
    check_site_access(auth, site_id)
    energy_type = _normalize_energy_type(energy_type)
    if mode not in ("energy", "power"):
        raise HTTPException(status_code=400, detail="mode must be 'energy' or 'power'")
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")
    return compute_tunnel_v2(db, site_id, days=days, energy_type=energy_type, mode=mode)


# =============================================
# V10 — Targets (Objectifs & Budgets)
# =============================================

class TargetCreateRequest(BaseModel):
    site_id: int
    energy_type: str = "electricity"
    period: str = Field("monthly", pattern=r"^(monthly|yearly)$")
    year: int
    month: Optional[int] = Field(None, ge=1, le=12)
    target_kwh: Optional[float] = None
    target_eur: Optional[float] = None
    target_co2e_kg: Optional[float] = None
    source: str = "manual"
    notes: Optional[str] = None


class TargetUpdateRequest(BaseModel):
    target_kwh: Optional[float] = None
    target_eur: Optional[float] = None
    target_co2e_kg: Optional[float] = None
    actual_kwh: Optional[float] = None
    actual_eur: Optional[float] = None
    actual_co2e_kg: Optional[float] = None
    notes: Optional[str] = None
    source: Optional[str] = None


@router.get("/targets")
def list_targets(
    site_id: int = Query(...),
    energy_type: str = Query("electricity"),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les objectifs de consommation pour un site."""
    check_site_access(auth, site_id)
    energy_type = _normalize_energy_type(energy_type)
    return get_targets(db, site_id, energy_type=energy_type, year=year)


@router.post("/targets")
def create_consumption_target(
    req: TargetCreateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Cree ou met a jour un objectif de consommation."""
    check_site_access(auth, req.site_id)
    return create_target(
        db,
        site_id=req.site_id,
        energy_type=req.energy_type,
        period=req.period,
        year=req.year,
        month=req.month,
        target_kwh=req.target_kwh,
        target_eur=req.target_eur,
        target_co2e_kg=req.target_co2e_kg,
        source=req.source,
        notes=req.notes,
    )


@router.patch("/targets/{target_id}")
def patch_target(
    target_id: int,
    req: TargetUpdateRequest,
    db: Session = Depends(get_db),
):
    """Met a jour un objectif existant."""
    result = update_target(db, target_id, **req.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Objectif non trouve")
    return result


@router.delete("/targets/{target_id}")
def remove_target(
    target_id: int,
    db: Session = Depends(get_db),
):
    """Supprime un objectif."""
    if not delete_target(db, target_id):
        raise HTTPException(status_code=404, detail="Objectif non trouve")
    return {"status": "deleted"}


@router.get("/targets/progression")
def targets_progression(
    site_id: int = Query(...),
    energy_type: str = Query("electricity"),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Progression objectifs vs reel avec prevision annuelle."""
    check_site_access(auth, site_id)
    energy_type = _normalize_energy_type(energy_type)
    return get_progression(db, site_id, energy_type=energy_type, year=year)


# =============================================
# V11 — Targets V2 (variance decomposition)
# =============================================

@router.get("/targets/progress_v2")
def targets_progression_v2(
    site_id: int = Query(...),
    energy_type: str = Query("electricity"),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Progression V2 : objectifs + decomposition de variance (top 3 causes) + run-rate."""
    check_site_access(auth, site_id)
    energy_type = _normalize_energy_type(energy_type)
    return get_progression_v2(db, site_id, energy_type=energy_type, year=year)


# =============================================
# V10 — TOU Schedules (Grilles HP/HC)
# =============================================

class TOUWindowSchema(BaseModel):
    day_types: List[str]
    start: str
    end: str
    period: str
    price_eur_kwh: Optional[float] = None


class TOUCreateRequest(BaseModel):
    site_id: Optional[int] = None
    meter_id: Optional[int] = None
    name: str = "HC/HP Standard"
    effective_from: str  # ISO date
    effective_to: Optional[str] = None
    windows: List[TOUWindowSchema]
    source: str = "manual"
    source_ref: Optional[str] = None
    price_hp_eur_kwh: Optional[float] = None
    price_hc_eur_kwh: Optional[float] = None


class TOUUpdateRequest(BaseModel):
    name: Optional[str] = None
    effective_to: Optional[str] = None
    is_active: Optional[bool] = None
    windows: Optional[List[TOUWindowSchema]] = None
    source: Optional[str] = None
    source_ref: Optional[str] = None
    price_hp_eur_kwh: Optional[float] = None
    price_hc_eur_kwh: Optional[float] = None


@router.get("/tou_schedules")
def list_tou_schedules(
    site_id: Optional[int] = Query(None),
    meter_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les grilles tarifaires HP/HC."""
    if site_id:
        check_site_access(auth, site_id)
    return get_schedules(db, site_id=site_id, meter_id=meter_id, active_only=active_only)


@router.get("/tou_schedules/active")
def active_tou_schedule(
    site_id: int = Query(...),
    meter_id: Optional[int] = Query(None),
    ref_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Grille HP/HC active pour un site/compteur a une date donnee."""
    check_site_access(auth, site_id)
    d = date.fromisoformat(ref_date) if ref_date else None
    return get_active_schedule(db, site_id, meter_id=meter_id, ref_date=d)


@router.post("/tou_schedules")
def create_tou_schedule(
    req: TOUCreateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Cree une nouvelle version de grille HP/HC."""
    if req.site_id:
        check_site_access(auth, req.site_id)
    eff_from = date.fromisoformat(req.effective_from)
    eff_to = date.fromisoformat(req.effective_to) if req.effective_to else None
    windows = [w.model_dump() for w in req.windows]
    return create_schedule(
        db,
        site_id=req.site_id,
        meter_id=req.meter_id,
        name=req.name,
        effective_from=eff_from,
        effective_to=eff_to,
        windows=windows,
        source=req.source,
        source_ref=req.source_ref,
        price_hp_eur_kwh=req.price_hp_eur_kwh,
        price_hc_eur_kwh=req.price_hc_eur_kwh,
    )


@router.patch("/tou_schedules/{schedule_id}")
def patch_tou_schedule(
    schedule_id: int,
    req: TOUUpdateRequest,
    db: Session = Depends(get_db),
):
    """Met a jour une grille HP/HC."""
    data = req.model_dump(exclude_none=True)
    if "windows" in data:
        data["windows"] = [w if isinstance(w, dict) else w.model_dump() for w in data["windows"]]
    result = update_schedule(db, schedule_id, **data)
    if not result:
        raise HTTPException(status_code=404, detail="Grille non trouvee")
    return result


@router.delete("/tou_schedules/{schedule_id}")
def remove_tou_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """Desactive une grille HP/HC."""
    if not delete_schedule(db, schedule_id):
        raise HTTPException(status_code=404, detail="Grille non trouvee")
    return {"status": "deactivated"}


# =============================================
# V10 — HP/HC Ratio
# =============================================

@router.get("/hp_hc")
def get_hp_hc_ratio(
    site_id: int = Query(...),
    meter_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Ratio HP/HC avec couts ventiles."""
    check_site_access(auth, site_id)
    return compute_hp_hc_ratio(db, site_id, meter_id=meter_id, days=days)


# =============================================
# V11 — HP/HC V2 (heatmap + opportunity + simulation)
# =============================================

@router.get("/hphc_breakdown_v2")
def get_hphc_breakdown_v2(
    site_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    calendar_id: Optional[int] = Query(None),
    simulate: bool = Query(False),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """HP/HC V2 : breakdown + heatmap 7x24 + opportunite + simulation calendrier alternatif."""
    check_site_access(auth, site_id)
    return compute_hphc_breakdown_v2(db, site_id, days=days, calendar_id=calendar_id, simulate=simulate)


# =============================================
# V10 — Gas Summary (Beta)
# =============================================

@router.get("/gas/summary")
def gas_summary(
    site_id: int = Query(...),
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Resume consommation gaz : conso journaliere, base ete, sensibilite meteo (beta)."""
    check_site_access(auth, site_id)
    from models import Meter, MeterReading
    from models.energy_models import EnergyVector
    from datetime import datetime, timedelta
    from collections import defaultdict

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    meters = db.query(Meter).filter(
        Meter.site_id == site_id,
        Meter.is_active == True,
        Meter.energy_vector == EnergyVector.GAS,
    ).all()

    if not meters:
        return {
            "site_id": site_id,
            "energy_type": "gas",
            "days": days,
            "readings_count": 0,
            "daily_kwh": [],
            "total_kwh": 0,
            "avg_daily_kwh": 0,
            "summer_base_kwh": 0,
            "confidence": "low",
        }

    meter_ids = [m.id for m in meters]
    readings = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_date,
            MeterReading.timestamp <= end_date,
        )
        .order_by(MeterReading.timestamp)
        .all()
    )

    # Aggregate by day
    daily = defaultdict(float)
    for r in readings:
        day_key = r.timestamp.strftime("%Y-%m-%d")
        daily[day_key] += r.value_kwh

    daily_list = [{"date": k, "kwh": round(v, 1)} for k, v in sorted(daily.items())]
    total_kwh = sum(d["kwh"] for d in daily_list)
    avg_daily = total_kwh / max(len(daily_list), 1)

    # Summer base: average daily consumption for months 6-9 (June-September)
    summer_days = [d for d in daily_list if d["date"][5:7] in ("06", "07", "08", "09")]
    summer_base = sum(d["kwh"] for d in summer_days) / max(len(summer_days), 1) if summer_days else 0

    confidence = "high" if len(readings) >= days * 20 else ("medium" if len(readings) >= days * 5 else "low")

    return {
        "site_id": site_id,
        "energy_type": "gas",
        "days": days,
        "readings_count": len(readings),
        "daily_kwh": daily_list,
        "total_kwh": round(total_kwh, 1),
        "avg_daily_kwh": round(avg_daily, 1),
        "summer_base_kwh": round(summer_base, 1),
        "confidence": confidence,
    }


# =============================================
# V11 — Gas Weather Normalized (DJU)
# =============================================

@router.get("/gas/weather_normalized")
def gas_weather_normalized(
    site_id: int = Query(...),
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Conso gaz normalisee meteo : modele DJU + alertes (fuite, derive, chauffage precoce)."""
    check_site_access(auth, site_id)
    from services.gas_weather_service import compute_weather_normalized
    return compute_weather_normalized(db, site_id, days=days)
