"""
PROMEOS — Enedis SGE Flux REST API (SF4 Phase 5)
Trigger ingestion, list flux files, view stats.
No auth for POC (ops/admin only).
Prefix: /api/enedis
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, text, union
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from data_ingestion.enedis.config import get_flux_dir
from data_ingestion.enedis.decrypt import MissingKeyError, load_keys_from_env
from data_ingestion.enedis.enums import FluxStatus, IngestionRunStatus
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxFileError,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
    EnedisFluxMesureR50,
    IngestionRun,
)
from data_ingestion.enedis.pipeline import ingest_directory

logger = logging.getLogger("promeos.enedis.api")

router = APIRouter(prefix="/api/enedis", tags=["Enedis SGE Flux"])


# ========================================
# Pydantic schemas — Ingestion
# ========================================


class IngestRequest(BaseModel):
    recursive: bool = Field(True)
    dry_run: bool = Field(False)


class IngestErrorDetail(BaseModel):
    filename: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IngestResponse(BaseModel):
    run_id: int
    status: str
    dry_run: bool
    duration_seconds: float
    counters: dict[str, int]
    errors: list[IngestErrorDetail]


# ========================================
# Pydantic schemas — Flux files
# ========================================


class FluxFileResponse(BaseModel):
    id: int
    filename: str
    file_hash: str
    flux_type: str
    status: str
    error_message: Optional[str] = None
    measures_count: int = 0
    version: int
    supersedes_file_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("measures_count", mode="before")
    @classmethod
    def _normalize_measures_count(cls, v):
        return v if v is not None else 0


class FluxFileListResponse(BaseModel):
    total: int
    items: list[FluxFileResponse]
    limit: int
    offset: int


class ErrorHistoryItem(BaseModel):
    error_message: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FluxFileDetailResponse(FluxFileResponse):
    header_raw: Optional[dict[str, Any]] = None
    frequence_publication: Optional[str] = None
    nature_courbe_demandee: Optional[str] = None
    identifiant_destinataire: Optional[str] = None
    errors_history: list[ErrorHistoryItem] = []


# ========================================
# Pydantic schemas — Stats
# ========================================


class FileStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_flux_type: dict[str, int]


class MeasureStats(BaseModel):
    total: int
    r4x: int
    r171: int
    r50: int
    r151: int


class PrmStats(BaseModel):
    count: int
    identifiers: list[str]


class LastIngestion(BaseModel):
    run_id: int
    timestamp: Optional[datetime] = None
    files_count: int
    triggered_by: str


class StatsResponse(BaseModel):
    files: FileStats
    measures: MeasureStats
    prms: PrmStats
    last_ingestion: Optional[LastIngestion] = None


# ========================================
# POST /api/enedis/ingest
# ========================================


@router.post("/ingest", response_model=IngestResponse)
def trigger_ingest(body: IngestRequest, db: Session = Depends(get_db)):
    """Trigger the Enedis SGE ingestion pipeline (synchronous)."""
    # --- Pre-flight validation ---
    try:
        flux_dir = get_flux_dir()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        keys = load_keys_from_env()
    except MissingKeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # --- Concurrency guard (atomic via partial unique index) ---
    run = IngestionRun(
        started_at=datetime.now(timezone.utc),
        directory=str(flux_dir),
        recursive=body.recursive,
        dry_run=body.dry_run,
        status=IngestionRunStatus.RUNNING,
        triggered_by="api",
    )
    db.add(run)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing_run = db.query(IngestionRun).filter_by(status=IngestionRunStatus.RUNNING).first()
        detail = "An ingestion run is already in progress"
        if existing_run:
            detail = (
                f"Run #{existing_run.id} is already in progress "
                f"(started {existing_run.started_at})"
            )
        raise HTTPException(status_code=409, detail=detail)
    db.commit()

    # --- Execute pipeline ---
    t0 = time.monotonic()
    try:
        counters = ingest_directory(
            flux_dir,
            db,
            keys,
            recursive=body.recursive,
            dry_run=body.dry_run,
            run=run,
        )
    except Exception as exc:
        run.status = IngestionRunStatus.FAILED
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.error("Enedis ingestion run #%d failed: %s", run.id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Run #{run.id} interrupted (status: failed) — {exc}",
        )

    duration = time.monotonic() - t0

    # --- Collect error files from this run ---
    # Refresh run from DB so started_at has the same type as updated_at
    # (naive on SQLite, tz-aware on PostgreSQL with timezone=True columns),
    # avoiding mixed-type comparison errors.
    db.refresh(run)
    error_files = (
        db.query(EnedisFluxFile)
        .filter(
            EnedisFluxFile.status.in_([FluxStatus.ERROR, FluxStatus.PERMANENTLY_FAILED]),
            EnedisFluxFile.updated_at >= run.started_at,
        )
        .all()
    )

    return IngestResponse(
        run_id=run.id,
        status=run.status,
        dry_run=run.dry_run,
        duration_seconds=round(duration, 2),
        counters=counters,
        errors=[IngestErrorDetail.model_validate(f) for f in error_files],
    )


# ========================================
# GET /api/enedis/flux-files
# ========================================


@router.get("/flux-files", response_model=FluxFileListResponse)
def list_flux_files(
    status: Optional[str] = Query(None, description="Filter by status"),
    flux_type: Optional[str] = Query(None, description="Filter by flux type"),
    limit: int = Query(24, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List Enedis flux files with optional filters and pagination."""
    q = db.query(EnedisFluxFile)
    if status:
        q = q.filter(EnedisFluxFile.status == status)
    if flux_type:
        q = q.filter(EnedisFluxFile.flux_type == flux_type)

    total = q.count()
    items = q.order_by(EnedisFluxFile.id.desc()).offset(offset).limit(limit).all()

    return FluxFileListResponse(
        total=total,
        items=[FluxFileResponse.model_validate(f) for f in items],
        limit=limit,
        offset=offset,
    )


# ========================================
# GET /api/enedis/flux-files/{id}
# ========================================


@router.get("/flux-files/{file_id}", response_model=FluxFileDetailResponse)
def get_flux_file_detail(file_id: int, db: Session = Depends(get_db)):
    """Get detail of a single flux file including header_raw and error history."""
    f = db.query(EnedisFluxFile).filter(EnedisFluxFile.id == file_id).first()
    if f is None:
        raise HTTPException(status_code=404, detail=f"Flux file id={file_id} not found")

    return FluxFileDetailResponse(
        id=f.id,
        filename=f.filename,
        file_hash=f.file_hash,
        flux_type=f.flux_type,
        status=f.status,
        error_message=f.error_message,
        measures_count=f.measures_count,
        version=f.version,
        supersedes_file_id=f.supersedes_file_id,
        created_at=f.created_at,
        updated_at=f.updated_at,
        header_raw=f.get_header_raw(),
        frequence_publication=f.frequence_publication,
        nature_courbe_demandee=f.nature_courbe_demandee,
        identifiant_destinataire=f.identifiant_destinataire,
        errors_history=[ErrorHistoryItem.model_validate(e) for e in f.errors],
    )


# ========================================
# GET /api/enedis/stats
# ========================================


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Aggregated ingestion stats: files, measures, PRMs, last ingestion."""
    # --- Files by status ---
    status_rows = (
        db.query(EnedisFluxFile.status, func.count())
        .group_by(EnedisFluxFile.status)
        .all()
    )
    by_status = {row[0]: row[1] for row in status_rows}
    files_total = sum(by_status.values())

    # --- Files by flux type ---
    type_rows = (
        db.query(EnedisFluxFile.flux_type, func.count())
        .group_by(EnedisFluxFile.flux_type)
        .all()
    )
    by_flux_type = {row[0]: row[1] for row in type_rows}

    # --- Measures: use denormalized measures_count from flux file registry ---
    measure_rows = (
        db.query(
            EnedisFluxFile.flux_type,
            func.sum(EnedisFluxFile.measures_count),
        )
        .filter(EnedisFluxFile.status.in_([FluxStatus.PARSED, FluxStatus.NEEDS_REVIEW]))
        .group_by(EnedisFluxFile.flux_type)
        .all()
    )
    measure_by_type: dict[str, int] = {row[0]: int(row[1] or 0) for row in measure_rows}
    r4x = sum(v for k, v in measure_by_type.items() if k in ("R4H", "R4M", "R4Q"))
    r171 = measure_by_type.get("R171", 0)
    r50 = measure_by_type.get("R50", 0)
    r151 = measure_by_type.get("R151", 0)

    # --- PRMs: UNION DISTINCT across 4 measure tables (distinct point_id only) ---
    prm_union = union(
        db.query(EnedisFluxMesureR4x.point_id.distinct()),
        db.query(EnedisFluxMesureR171.point_id.distinct()),
        db.query(EnedisFluxMesureR50.point_id.distinct()),
        db.query(EnedisFluxMesureR151.point_id.distinct()),
    )
    prm_rows = db.execute(prm_union).fetchall()
    prm_identifiers = sorted(row[0] for row in prm_rows)

    # --- Last completed ingestion (non-dry-run) ---
    last_run = (
        db.query(IngestionRun)
        .filter(
            IngestionRun.status == IngestionRunStatus.COMPLETED,
            IngestionRun.dry_run == False,
        )
        .order_by(IngestionRun.finished_at.desc())
        .first()
    )
    last_ingestion = None
    if last_run:
        last_ingestion = LastIngestion(
            run_id=last_run.id,
            timestamp=last_run.finished_at,
            files_count=(
                (last_run.files_parsed or 0)
                + (last_run.files_skipped or 0)
                + (last_run.files_error or 0)
                + (last_run.files_needs_review or 0)
            ),
            triggered_by=last_run.triggered_by,
        )

    return StatsResponse(
        files=FileStats(
            total=files_total,
            by_status=by_status,
            by_flux_type=by_flux_type,
        ),
        measures=MeasureStats(
            total=r4x + r171 + r50 + r151,
            r4x=r4x,
            r171=r171,
            r50=r50,
            r151=r151,
        ),
        prms=PrmStats(
            count=len(prm_identifiers),
            identifiers=prm_identifiers,
        ),
        last_ingestion=last_ingestion,
    )
