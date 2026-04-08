"""
PROMEOS — GRDF ADICT API routes (Sprint F Connectors)

Prefix: /api/grdf
Consommation gaz (PCE), conversion PCS.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import insert
from sqlalchemy.orm import Session

from database import get_db

logger = logging.getLogger("promeos.routes.grdf")

router = APIRouter(prefix="/api/grdf", tags=["GRDF ADICT"])


# --- Schemas ---


class ConsumptionItem(BaseModel):
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    energie_kwh: Optional[float] = None
    volume_m3: Optional[float] = None


class SyncResponse(BaseModel):
    pce: str
    readings_count: int
    date_start: Optional[str] = None
    date_end: Optional[str] = None


class PcsResponse(BaseModel):
    region_code: Optional[str] = None
    pcs_kwh_m3: float


# --- Endpoints ---


@router.get("/pce/{pce}/consumption", response_model=list[ConsumptionItem])
def get_pce_consumption(
    pce: str,
    date_debut: date = Query(..., description="Date début"),
    date_fin: date = Query(..., description="Date fin"),
    db: Session = Depends(get_db),
):
    """Récupère la consommation informative pour un PCE via GRDF ADICT."""
    from connectors.grdf_adict import GrdfAdictConnector
    from connectors.grdf_errors import GrdfAdictError, PceNotFoundError, PceNotAuthorizedError

    try:
        connector = GrdfAdictConnector()
        data = connector.fetch_informative_consumption(pce, date_debut, date_fin, db)
        return [ConsumptionItem(**item) for item in data]
    except PceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PceNotAuthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except GrdfAdictError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/sync/{pce}", response_model=SyncResponse)
def sync_pce(
    pce: str,
    date_debut: Optional[date] = Query(None, description="Date début (défaut: J-365)"),
    date_fin: Optional[date] = Query(None, description="Date fin (défaut: aujourd'hui)"),
    region_code: Optional[str] = Query(None, description="Code région pour PCS (ex: IDF)"),
    db: Session = Depends(get_db),
):
    """Récupère la conso gaz et l'écrit en MeterReading (kWh via PCS)."""
    from connectors.grdf_adict import GrdfAdictConnector
    from connectors.grdf_errors import GrdfAdictError
    from models.energy_models import Meter, MeterReading, DataImportJob, FrequencyType, ImportStatus
    from services.grdf_pcs_service import m3_to_kwh

    date_debut = date_debut or (date.today() - timedelta(days=365))
    date_fin = date_fin or date.today()

    try:
        connector = GrdfAdictConnector()
        data = connector.fetch_informative_consumption(pce, date_debut, date_fin, db)
    except GrdfAdictError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Trouver le Meter
    meter = db.query(Meter).filter(Meter.meter_id == pce).first()
    if not meter:
        raise HTTPException(status_code=404, detail=f"Aucun Meter pour PCE {pce}")

    # Job d'import
    job = DataImportJob(
        job_type="grdf_adict_sync",
        status=ImportStatus.PROCESSING,
        meter_id=meter.id,
        date_start=datetime.combine(date_debut, datetime.min.time()),
        date_end=datetime.combine(date_fin, datetime.min.time()),
        created_by="grdf_adict",
    )
    db.add(job)
    db.flush()

    inserted = 0
    for item in data:
        try:
            date_str = item.get("date_fin") or item.get("date_debut")
            if not date_str:
                continue
            ts = datetime.strptime(date_str[:10], "%Y-%m-%d")

            # Conversion m³ → kWh si nécessaire
            kwh = item.get("energie_kwh")
            if kwh is None and item.get("volume_m3"):
                kwh = m3_to_kwh(float(item["volume_m3"]), region_code)
            if kwh is None:
                continue

            stmt = (
                insert(MeterReading)
                .prefix_with("OR IGNORE")
                .values(
                    meter_id=meter.id,
                    timestamp=ts,
                    frequency=FrequencyType.DAILY,
                    value_kwh=round(float(kwh), 3),
                    is_estimated=False,
                    quality_score=0.9,
                    import_job_id=job.id,
                    created_at=datetime.utcnow(),
                )
            )
            db.execute(stmt)
            inserted += 1
        except (ValueError, TypeError, KeyError) as e:
            logger.warning("Skip GRDF reading: %s", e)

    job.status = ImportStatus.COMPLETED
    job.rows_total = len(data)
    job.rows_imported = inserted
    job.completed_at = datetime.utcnow()
    db.commit()

    return SyncResponse(
        pce=pce,
        readings_count=inserted,
        date_start=date_debut.isoformat(),
        date_end=date_fin.isoformat(),
    )


@router.get("/pcs", response_model=PcsResponse)
def get_pcs(
    region_code: Optional[str] = Query(None, description="Code région (IDF, HDF, PAC, etc.)"),
):
    """Retourne le PCS (Pouvoir Calorifique Supérieur) pour une région."""
    from services.grdf_pcs_service import pcs_for_region

    return PcsResponse(
        region_code=region_code,
        pcs_kwh_m3=pcs_for_region(region_code),
    )
