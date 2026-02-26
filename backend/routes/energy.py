"""
PROMEOS - Routes API pour l'Energie (Import & Analysis)
Import CSV/XLSX/JSON consumption data, run KB-driven analytics
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access
from models import (
    Site, Meter, MeterReading, DataImportJob, UsageProfile,
    Anomaly as AnomalyModel, Recommendation as RecommendationModel,
    ImportStatus, FrequencyType, AnomalySeverity, RecommendationStatus
)
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
import csv
import io
import hashlib
import json


router = APIRouter(prefix="/api/energy", tags=["Energy"])


# --- Pydantic models ---

class MeterCreate(BaseModel):
    meter_id: str
    name: str
    site_id: int
    energy_vector: str = "electricity"
    subscribed_power_kva: Optional[float] = None
    tariff_type: Optional[str] = None


class MeterResponse(BaseModel):
    id: int
    meter_id: str
    name: str
    site_id: int
    energy_vector: str
    subscribed_power_kva: Optional[float] = None
    readings_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ImportJobResponse(BaseModel):
    id: int
    status: str
    filename: Optional[str] = None
    file_format: Optional[str] = None
    rows_total: Optional[int] = None
    rows_imported: Optional[int] = None
    rows_skipped: Optional[int] = None
    rows_errored: Optional[int] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisSummary(BaseModel):
    meter_id: str
    site_name: str
    period: str
    archetype_code: Optional[str] = None
    archetype_match_score: Optional[float] = None
    kwh_total: Optional[float] = None
    kwh_m2_year: Optional[float] = None
    anomalies_count: int = 0
    recommendations_count: int = 0
    top_anomalies: List[dict] = []
    top_recommendations: List[dict] = []


class DemoDataRequest(BaseModel):
    site_id: int
    meter_name: str = "Compteur Principal"
    days: int = 365
    archetype: str = "BUREAU_STANDARD"


# --- Meter endpoints ---

@router.post("/meters", response_model=MeterResponse)
def create_meter(
    meter: MeterCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create a new energy meter"""
    check_site_access(auth, meter.site_id)
    # Verify site exists
    site = db.query(Site).filter_by(id=meter.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {meter.site_id} not found")

    # Check uniqueness
    existing = db.query(Meter).filter_by(meter_id=meter.meter_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Meter '{meter.meter_id}' already exists")

    new_meter = Meter(
        meter_id=meter.meter_id,
        name=meter.name,
        site_id=meter.site_id,
        subscribed_power_kva=meter.subscribed_power_kva,
        tariff_type=meter.tariff_type
    )
    db.add(new_meter)
    db.commit()
    db.refresh(new_meter)

    return MeterResponse(
        id=new_meter.id,
        meter_id=new_meter.meter_id,
        name=new_meter.name,
        site_id=new_meter.site_id,
        energy_vector=new_meter.energy_vector.value,
        subscribed_power_kva=new_meter.subscribed_power_kva,
        readings_count=0
    )


@router.get("/meters", response_model=List[MeterResponse])
def list_meters(
    site_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List all meters, optionally filtered by site"""
    query = db.query(Meter)
    if auth and auth.site_ids is not None:
        query = query.filter(Meter.site_id.in_(auth.site_ids))
    if site_id:
        query = query.filter_by(site_id=site_id)

    meters = query.all()
    result = []
    for m in meters:
        count = db.query(MeterReading).filter_by(meter_id=m.id).count()
        result.append(MeterResponse(
            id=m.id,
            meter_id=m.meter_id,
            name=m.name,
            site_id=m.site_id,
            energy_vector=m.energy_vector.value,
            subscribed_power_kva=m.subscribed_power_kva,
            readings_count=count
        ))

    return result


# --- Import endpoints ---

@router.post("/import/upload")
async def upload_consumption_data(
    file: UploadFile = File(...),
    meter_id: str = Query(..., description="Meter ID (PRM/PDL)"),
    frequency: str = Query("hourly", description="Data frequency: 15min, 30min, hourly, daily, monthly"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Upload consumption data file (CSV/XLSX/JSON)"""
    # Validate meter
    meter = db.query(Meter).filter_by(meter_id=meter_id).first()
    if not meter:
        raise HTTPException(status_code=404, detail=f"Meter '{meter_id}' not found")
    check_site_access(auth, meter.site_id)

    # Determine format
    filename = file.filename or "unknown"
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext not in ('csv', 'xlsx', 'json'):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}. Use CSV, XLSX, or JSON")

    # Read file content
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate imports
    existing_job = db.query(DataImportJob).filter_by(
        file_hash=file_hash,
        status=ImportStatus.COMPLETED
    ).first()
    if existing_job:
        raise HTTPException(status_code=409, detail=f"This file was already imported (job #{existing_job.id})")

    # Validate frequency
    freq_map = {
        "15min": FrequencyType.MIN_15,
        "30min": FrequencyType.MIN_30,
        "hourly": FrequencyType.HOURLY,
        "daily": FrequencyType.DAILY,
        "monthly": FrequencyType.MONTHLY,
    }
    if frequency not in freq_map:
        raise HTTPException(status_code=400, detail=f"Invalid frequency: {frequency}")

    freq_type = freq_map[frequency]

    # Create import job
    job = DataImportJob(
        job_type="consumption_import",
        status=ImportStatus.PROCESSING,
        filename=filename,
        file_format=ext,
        file_size_bytes=len(content),
        file_hash=file_hash,
        site_id=meter.site_id,
        meter_id=meter.id,
        started_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Parse and import
    try:
        if ext == 'csv':
            rows_imported, rows_skipped, rows_errored, date_range = _import_csv(
                content, meter.id, freq_type, db
            )
        elif ext == 'json':
            rows_imported, rows_skipped, rows_errored, date_range = _import_json(
                content, meter.id, freq_type, db
            )
        else:
            raise HTTPException(status_code=400, detail="XLSX support requires openpyxl - use CSV or JSON")

        # Update job
        job.status = ImportStatus.COMPLETED
        job.rows_total = rows_imported + rows_skipped + rows_errored
        job.rows_imported = rows_imported
        job.rows_skipped = rows_skipped
        job.rows_errored = rows_errored
        job.date_start = date_range[0] if date_range else None
        job.date_end = date_range[1] if date_range else None
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "completed",
            "job_id": job.id,
            "rows_imported": rows_imported,
            "rows_skipped": rows_skipped,
            "rows_errored": rows_errored,
            "date_range": {
                "start": date_range[0].isoformat() if date_range and date_range[0] else None,
                "end": date_range[1].isoformat() if date_range and date_range[1] else None,
            }
        }

    except Exception as e:
        job.status = ImportStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/import/jobs", response_model=List[ImportJobResponse])
def list_import_jobs(
    meter_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List import jobs"""
    query = db.query(DataImportJob).order_by(DataImportJob.created_at.desc())

    if meter_id:
        meter = db.query(Meter).filter_by(meter_id=meter_id).first()
        if meter:
            query = query.filter_by(meter_id=meter.id)

    jobs = query.limit(50).all()

    return [ImportJobResponse(
        id=j.id,
        status=j.status.value,
        filename=j.filename,
        file_format=j.file_format,
        rows_total=j.rows_total,
        rows_imported=j.rows_imported,
        rows_skipped=j.rows_skipped,
        rows_errored=j.rows_errored,
        date_start=j.date_start.isoformat() if j.date_start else None,
        date_end=j.date_end.isoformat() if j.date_end else None,
        error_message=j.error_message,
        created_at=j.created_at.isoformat() if j.created_at else None
    ) for j in jobs]


# --- Analysis endpoints ---

@router.post("/analysis/run")
def run_analysis(
    meter_id: str = Query(..., description="Meter ID to analyze"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Run KB-driven analysis on meter data"""
    from services.analytics_engine import AnalyticsEngine

    meter = db.query(Meter).filter_by(meter_id=meter_id).first()
    if not meter:
        raise HTTPException(status_code=404, detail=f"Meter '{meter_id}' not found")
    check_site_access(auth, meter.site_id)

    # Check for data
    readings_count = db.query(MeterReading).filter_by(meter_id=meter.id).count()
    if readings_count == 0:
        raise HTTPException(status_code=400, detail="No consumption data available for this meter")

    engine = AnalyticsEngine(db)
    result = engine.analyze(meter.id)

    return result


@router.get("/analysis/summary")
def get_analysis_summary(
    meter_id: str = Query(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get latest analysis summary for a meter"""
    meter = db.query(Meter).filter_by(meter_id=meter_id).first()
    if not meter:
        raise HTTPException(status_code=404, detail=f"Meter '{meter_id}' not found")
    check_site_access(auth, meter.site_id)

    # Get latest profile
    profile = db.query(UsageProfile).filter_by(
        meter_id=meter.id
    ).order_by(UsageProfile.created_at.desc()).first()

    # Get anomalies
    anomalies = db.query(AnomalyModel).filter_by(
        meter_id=meter.id, is_active=True
    ).order_by(AnomalyModel.severity.desc()).all()

    # Get recommendations
    recommendations = db.query(RecommendationModel).filter_by(
        meter_id=meter.id
    ).filter(RecommendationModel.status != RecommendationStatus.DISMISSED).order_by(
        RecommendationModel.ice_score.desc()
    ).all()

    site = db.query(Site).filter_by(id=meter.site_id).first()

    return AnalysisSummary(
        meter_id=meter.meter_id,
        site_name=site.nom if site else "Unknown",
        period=f"{profile.period_start.date()} - {profile.period_end.date()}" if profile else "N/A",
        archetype_code=profile.archetype_code if profile else None,
        archetype_match_score=profile.archetype_match_score if profile else None,
        kwh_total=profile.features_json.get("kwh_total") if profile and profile.features_json else None,
        kwh_m2_year=profile.features_json.get("kwh_m2_year") if profile and profile.features_json else None,
        anomalies_count=len(anomalies),
        recommendations_count=len(recommendations),
        top_anomalies=[{
            "code": a.anomaly_code,
            "title": a.title,
            "severity": a.severity.value,
            "confidence": a.confidence,
            "measured": a.measured_value,
            "threshold": a.threshold_value,
        } for a in anomalies[:5]],
        top_recommendations=[{
            "code": r.recommendation_code,
            "title": r.title,
            "ice_score": r.ice_score,
            "savings_pct": r.estimated_savings_pct,
            "status": r.status.value,
        } for r in recommendations[:5]]
    )


# --- Demo endpoints ---

@router.post("/demo/generate")
def generate_demo_data(
    request: DemoDataRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Generate synthetic consumption data for demo purposes"""
    import random
    import math

    check_site_access(auth, request.site_id)
    site = db.query(Site).filter_by(id=request.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {request.site_id} not found")

    # Create meter if not exists
    meter_id_str = f"PRM-{request.site_id:06d}"
    meter = db.query(Meter).filter_by(meter_id=meter_id_str).first()
    if not meter:
        meter = Meter(
            meter_id=meter_id_str,
            name=request.meter_name,
            site_id=request.site_id,
            subscribed_power_kva=100.0
        )
        db.add(meter)
        db.commit()
        db.refresh(meter)

    # Purge existing readings to avoid duplicate constraint violation
    db.query(MeterReading).filter(MeterReading.meter_id == meter.id).delete()
    db.flush()

    # Archetype-based generation profiles
    profiles = {
        "BUREAU_STANDARD": {
            "base_kwh": 7.0, "day_multiplier": 4.0,
            "weekend_ratio": 0.3, "seasonal_amplitude": 0.20,
            "night_base": 0.12
        },
        "COMMERCE_ALIMENTAIRE": {
            "base_kwh": 20.0, "day_multiplier": 1.5,
            "weekend_ratio": 0.9, "seasonal_amplitude": 0.15,
            "night_base": 0.60
        },
        "RESTAURATION_SERVICE": {
            "base_kwh": 10.0, "day_multiplier": 3.0,
            "weekend_ratio": 0.7, "seasonal_amplitude": 0.15,
            "night_base": 0.15
        },
        "INDUSTRIE_LEGERE": {
            "base_kwh": 15.0, "day_multiplier": 3.5,
            "weekend_ratio": 0.2, "seasonal_amplitude": 0.10,
            "night_base": 0.10
        },
    }

    profile = profiles.get(request.archetype, profiles["BUREAU_STANDARD"])

    # Generate hourly data
    now = datetime.now(timezone.utc)
    start = datetime(now.year - 1, now.month, now.day)
    readings = []
    total_kwh = 0.0

    for day_offset in range(request.days):
        dt = start.replace(hour=0, minute=0, second=0) + __import__('datetime').timedelta(days=day_offset)
        day_of_week = dt.weekday()  # 0=Monday
        is_weekend = day_of_week >= 5
        month = dt.month

        # Seasonal factor (heating winter, cooling summer)
        seasonal = 1.0 + profile["seasonal_amplitude"] * math.cos(2 * math.pi * (month - 1) / 12.0)

        for hour in range(24):
            ts = dt.replace(hour=hour)

            # Hour profile
            if is_weekend:
                factor = profile["weekend_ratio"]
            elif 8 <= hour <= 18:
                factor = profile["day_multiplier"]
            elif 6 <= hour <= 7 or 19 <= hour <= 20:
                factor = profile["day_multiplier"] * 0.5
            else:
                factor = profile["night_base"]

            value = profile["base_kwh"] * factor * seasonal
            value *= random.uniform(0.85, 1.15)  # Noise
            value = max(0.1, value)

            readings.append(MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=round(value, 2),
                is_estimated=False
            ))
            total_kwh += value

    # Bulk insert
    db.bulk_save_objects(readings)
    db.commit()

    return {
        "status": "ok",
        "meter_id": meter.meter_id,
        "readings_generated": len(readings),
        "total_kwh": round(total_kwh, 1),
        "period": f"{start.date()} - {(start + __import__('datetime').timedelta(days=request.days)).date()}",
        "archetype": request.archetype
    }


# --- Helper functions ---

def _import_csv(content: bytes, meter_id: int, frequency: FrequencyType, db: Session):
    """Parse CSV and import readings"""
    text = content.decode('utf-8-sig')  # Handle BOM
    reader = csv.DictReader(io.StringIO(text), delimiter=';')

    rows_imported = 0
    rows_skipped = 0
    rows_errored = 0
    min_date = None
    max_date = None

    batch = []

    for row in reader:
        try:
            # Flexible column name detection
            ts_str = row.get('timestamp') or row.get('date') or row.get('horodatage') or row.get('Date')
            val_str = row.get('value_kwh') or row.get('kwh') or row.get('valeur') or row.get('Valeur')

            if not ts_str or not val_str:
                rows_skipped += 1
                continue

            # Parse timestamp (multiple formats)
            ts = _parse_timestamp(ts_str.strip())
            if ts is None:
                rows_errored += 1
                continue

            # Parse value
            val_str = val_str.strip().replace(',', '.')
            value = float(val_str)

            if value < 0:
                rows_errored += 1
                continue

            batch.append(MeterReading(
                meter_id=meter_id,
                timestamp=ts,
                frequency=frequency,
                value_kwh=round(value, 3),
                is_estimated=False
            ))

            if min_date is None or ts < min_date:
                min_date = ts
            if max_date is None or ts > max_date:
                max_date = ts

            rows_imported += 1

            # Batch commit every 5000 rows
            if len(batch) >= 5000:
                _save_readings_ignore_dupes(db, batch)
                batch = []

        except Exception:
            rows_errored += 1

    # Final batch
    if batch:
        _save_readings_ignore_dupes(db, batch)

    db.commit()

    return rows_imported, rows_skipped, rows_errored, (min_date, max_date)


def _import_json(content: bytes, meter_id: int, frequency: FrequencyType, db: Session):
    """Parse JSON and import readings"""
    data = json.loads(content.decode('utf-8'))

    if isinstance(data, dict):
        readings_list = data.get('readings', data.get('data', []))
    else:
        readings_list = data

    rows_imported = 0
    rows_skipped = 0
    rows_errored = 0
    min_date = None
    max_date = None

    batch = []

    for item in readings_list:
        try:
            ts_str = item.get('timestamp') or item.get('date') or item.get('horodatage')
            value = item.get('value_kwh') or item.get('kwh') or item.get('valeur')

            if not ts_str or value is None:
                rows_skipped += 1
                continue

            ts = _parse_timestamp(str(ts_str).strip())
            if ts is None:
                rows_errored += 1
                continue

            value = float(value)
            if value < 0:
                rows_errored += 1
                continue

            batch.append(MeterReading(
                meter_id=meter_id,
                timestamp=ts,
                frequency=frequency,
                value_kwh=round(value, 3),
                is_estimated=False
            ))

            if min_date is None or ts < min_date:
                min_date = ts
            if max_date is None or ts > max_date:
                max_date = ts

            rows_imported += 1

            if len(batch) >= 5000:
                db.bulk_save_objects(batch)
                db.flush()
                batch = []

        except Exception:
            rows_errored += 1

    if batch:
        db.bulk_save_objects(batch)
        db.flush()

    db.commit()

    return rows_imported, rows_skipped, rows_errored, (min_date, max_date)


def _save_readings_ignore_dupes(db: Session, readings: list):
    """Save readings, skipping duplicates on (meter_id, timestamp) unique constraint."""
    try:
        db.bulk_save_objects(readings)
        db.flush()
    except Exception:
        db.rollback()
        # Fallback: insert one-by-one, skip duplicates
        for r in readings:
            try:
                db.add(r)
                db.flush()
            except Exception:
                db.rollback()


def _parse_timestamp(ts_str: str) -> datetime:
    """Parse timestamp in multiple formats"""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue

    return None
