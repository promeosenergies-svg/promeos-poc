"""
PROMEOS — Staging Bridge API routes (Sprint F Connectors)

Prefix: /api/bridge
Bridge entre les flux Enedis staging et les MeterReading normalisées.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id

logger = logging.getLogger("promeos.routes.bridge")

router = APIRouter(prefix="/api/bridge", tags=["Staging Bridge"])


# --- Schemas ---


class BridgeRunRequest(BaseModel):
    prms: Optional[list[str]] = None  # None = tous les PRMs connus


class BridgeRunResponse(BaseModel):
    job_id: str
    prms_count: int
    total_inserted: int
    total_skipped: int
    total_errors: int
    details: list[dict]


class GapItem(BaseModel):
    start: str
    end: str
    expected_readings: int
    actual_readings: int
    missing_readings: int


class CoverageItem(BaseModel):
    prm: str
    meter_id: Optional[int] = None
    total_readings: int
    first_reading: Optional[str] = None
    last_reading: Optional[str] = None


# --- Endpoints ---


@router.post("/run", response_model=BridgeRunResponse)
def run_bridge(
    request: Request,
    body: BridgeRunRequest = BridgeRunRequest(),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Lance le bridge staging → MeterReading pour les PRMs de l'org."""
    from services.staging_bridge import bridge_all_prms
    from models.energy_models import DataImportJob, ImportStatus

    org_id = resolve_org_id(request, auth, db)

    # Créer un job d'import
    job = DataImportJob(
        job_type="staging_bridge",
        status=ImportStatus.PROCESSING,
        created_by="bridge_api",
    )
    db.add(job)
    db.flush()
    job_id = str(job.id)

    try:
        results = bridge_all_prms(db, prms=body.prms, import_job_id=job.id)

        total_inserted = sum(r.rows_inserted for r in results)
        total_skipped = sum(r.rows_skipped for r in results)
        total_errors = sum(r.rows_errored for r in results)

        job.status = ImportStatus.COMPLETED
        job.rows_total = total_inserted + total_skipped + total_errors
        job.rows_imported = total_inserted
        job.rows_skipped = total_skipped
        job.rows_errored = total_errors
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        return BridgeRunResponse(
            job_id=job_id,
            prms_count=len(results),
            total_inserted=total_inserted,
            total_skipped=total_skipped,
            total_errors=total_errors,
            details=[
                {
                    "prm": r.prm,
                    "meter_id": r.meter_id,
                    "inserted": r.rows_inserted,
                    "skipped": r.rows_skipped,
                    "errors": r.rows_errored,
                    "error_messages": r.errors[:5],  # Limiter les messages
                }
                for r in results
            ],
        )
    except Exception as e:
        job.status = ImportStatus.FAILED
        job.error_message = str(e)[:500]
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.exception("Bridge run failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
def get_bridge_status(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Retourne le statut d'un job de bridge."""
    resolve_org_id(request, auth, db)  # Ensure authenticated
    from models.energy_models import DataImportJob

    job = db.query(DataImportJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} non trouvé")

    return {
        "job_id": job.id,
        "job_type": job.job_type,
        "status": job.status.value if job.status else "unknown",
        "rows_total": job.rows_total,
        "rows_imported": job.rows_imported,
        "rows_skipped": job.rows_skipped,
        "rows_errored": job.rows_errored,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/gaps/{prm}", response_model=list[GapItem])
def get_gaps(
    prm: str,
    request: Request,
    start: Optional[str] = Query(None, description="Date début ISO (défaut: J-90)"),
    end: Optional[str] = Query(None, description="Date fin ISO (défaut: aujourd'hui)"),
    freq_minutes: int = Query(30, description="Fréquence attendue en minutes (30, 60)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détecte les trous de données pour un PRM."""
    from services.staging_bridge import detect_gaps, resolve_meter_for_prm
    from models.energy_models import Meter
    from models import Site, Portefeuille, EntiteJuridique

    org_id = resolve_org_id(request, auth, db)

    meter = resolve_meter_for_prm(prm, db)
    if not meter:
        raise HTTPException(status_code=404, detail=f"Aucun Meter pour PRM {prm}")

    # Verify meter belongs to org
    org_check = (
        db.query(Meter)
        .join(Site, Meter.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(Meter.id == meter.id, EntiteJuridique.organisation_id == org_id)
        .first()
    )
    if not org_check:
        raise HTTPException(status_code=404, detail=f"Aucun Meter pour PRM {prm}")

    now = datetime.now(timezone.utc)
    start_dt = datetime.fromisoformat(start) if start else now - timedelta(days=90)
    end_dt = datetime.fromisoformat(end) if end else now

    gaps = detect_gaps(meter.id, start_dt, end_dt, freq_minutes, db)

    return [
        GapItem(
            start=g.start.isoformat(),
            end=g.end.isoformat(),
            expected_readings=g.expected_readings,
            actual_readings=g.actual_readings,
            missing_readings=g.missing_readings,
        )
        for g in gaps
    ]


@router.get("/coverage", response_model=list[CoverageItem])
def get_coverage(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Résumé de couverture des données par PRM/compteur, scoped to org."""
    from sqlalchemy import func
    from models.energy_models import Meter, MeterReading
    from models import Site, Portefeuille, EntiteJuridique

    org_id = resolve_org_id(request, auth, db)

    # Sous-requête: stats par meter_id
    stats = (
        db.query(
            MeterReading.meter_id,
            func.count(MeterReading.id).label("total"),
            func.min(MeterReading.timestamp).label("first_ts"),
            func.max(MeterReading.timestamp).label("last_ts"),
        )
        .group_by(MeterReading.meter_id)
        .subquery()
    )

    rows = (
        db.query(Meter.meter_id, Meter.id, stats.c.total, stats.c.first_ts, stats.c.last_ts)
        .outerjoin(stats, Meter.id == stats.c.meter_id)
        .join(Site, Meter.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(Meter.is_active == True, EntiteJuridique.organisation_id == org_id)
        .order_by(Meter.meter_id)
        .all()
    )

    return [
        CoverageItem(
            prm=row[0],
            meter_id=row[1],
            total_readings=row[2] or 0,
            first_reading=row[3].isoformat() if row[3] else None,
            last_reading=row[4].isoformat() if row[4] else None,
        )
        for row in rows
    ]
