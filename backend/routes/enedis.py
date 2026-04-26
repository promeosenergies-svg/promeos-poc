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

from database import get_db, get_flux_data_db
from data_ingestion.enedis.config import get_flux_dir
from data_ingestion.enedis.decrypt import MissingKeyError, load_keys_from_env
from data_ingestion.enedis.enums import FluxStatus, IngestionRunStatus
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxFileError,
    EnedisFluxIndexR64,
    EnedisFluxItcC68,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
    EnedisFluxMesureR50,
    EnedisFluxMesureR63,
    IngestionRun,
)
from data_ingestion.enedis.pipeline import ingest_directory

logger = logging.getLogger("promeos.enedis.api")

router = APIRouter(prefix="/api/enedis", tags=["Enedis SGE Flux"])


def _require_auth():
    """Gate auth pour endpoints de promotion (DEMO_MODE = pass-through)."""
    import os

    if os.getenv("DEMO_MODE", "").lower() == "true":
        return None
    try:
        from middleware.auth import get_optional_auth

        # En mode production, exiger un token valide
        return Depends(get_optional_auth)
    except ImportError:
        return None


# Rate limit : max 1 promotion démarrée par fenêtre de 60s par source
_PROMOTION_RATE_LIMIT_WINDOW = 60.0
_last_promotion_trigger: dict[str, float] = {}


def _check_promotion_rate_limit(triggered_by: str = "api"):
    """Rate limit : max 1 run démarré par fenêtre de 60s par source. Anti DoS."""
    import time

    now = time.monotonic()
    last = _last_promotion_trigger.get(triggered_by, 0.0)
    elapsed = now - last
    if elapsed < _PROMOTION_RATE_LIMIT_WINDOW:
        wait = int(_PROMOTION_RATE_LIMIT_WINDOW - elapsed)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit : attendre {wait}s avant prochain run (source={triggered_by})",
        )
    _last_promotion_trigger[triggered_by] = now


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
    code_flux: Optional[str] = None
    type_donnee: Optional[str] = None
    id_demande: Optional[str] = None
    mode_publication: Optional[str] = None
    payload_format: Optional[str] = None
    num_sequence: Optional[str] = None
    siren_publication: Optional[str] = None
    code_contrat_publication: Optional[str] = None
    publication_horodatage: Optional[str] = None
    archive_members_count: Optional[int] = None
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
    r63: int
    r64: int
    r6x: int
    c68: int


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
def trigger_ingest(body: IngestRequest, db: Session = Depends(get_flux_data_db)):
    """Trigger the Enedis SGE ingestion pipeline (synchronous)."""
    # --- Pre-flight validation ---
    try:
        flux_dir = get_flux_dir()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        keys = load_keys_from_env()
    except MissingKeyError:
        keys = []

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
            detail = f"Run #{existing_run.id} is already in progress (started {existing_run.started_at})"
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
    db: Session = Depends(get_flux_data_db),
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
def get_flux_file_detail(file_id: int, db: Session = Depends(get_flux_data_db)):
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
        code_flux=f.code_flux,
        type_donnee=f.type_donnee,
        id_demande=f.id_demande,
        mode_publication=f.mode_publication,
        payload_format=f.payload_format,
        num_sequence=f.num_sequence,
        siren_publication=f.siren_publication,
        code_contrat_publication=f.code_contrat_publication,
        publication_horodatage=f.publication_horodatage,
        archive_members_count=f.archive_members_count,
        errors_history=[ErrorHistoryItem.model_validate(e) for e in f.errors],
    )


# ========================================
# GET /api/enedis/stats
# ========================================


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_flux_data_db)):
    """Aggregated ingestion stats: files, measures, PRMs, last ingestion."""
    # --- Files by status ---
    status_rows = db.query(EnedisFluxFile.status, func.count()).group_by(EnedisFluxFile.status).all()
    by_status = {row[0]: row[1] for row in status_rows}
    files_total = sum(by_status.values())

    # --- Files by flux type ---
    type_rows = db.query(EnedisFluxFile.flux_type, func.count()).group_by(EnedisFluxFile.flux_type).all()
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
    r63 = measure_by_type.get("R63", 0)
    r64 = measure_by_type.get("R64", 0)
    r6x = r63 + r64
    c68 = measure_by_type.get("C68", 0)

    # --- PRMs: UNION DISTINCT across raw row tables (distinct point_id only) ---
    prm_union = union(
        db.query(EnedisFluxMesureR4x.point_id.distinct()),
        db.query(EnedisFluxMesureR171.point_id.distinct()),
        db.query(EnedisFluxMesureR50.point_id.distinct()),
        db.query(EnedisFluxMesureR151.point_id.distinct()),
        db.query(EnedisFluxMesureR63.point_id.distinct()),
        db.query(EnedisFluxIndexR64.point_id.distinct()),
        db.query(EnedisFluxItcC68.point_id.distinct()),
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
            total=r4x + r171 + r50 + r151 + r6x + c68,
            r4x=r4x,
            r171=r171,
            r50=r50,
            r151=r151,
            r63=r63,
            r64=r64,
            r6x=r6x,
            c68=c68,
        ),
        prms=PrmStats(
            count=len(prm_identifiers),
            identifiers=prm_identifiers,
        ),
        last_ingestion=last_ingestion,
    )


# ========================================
# SF6 — Promotion Pipeline Endpoints
# ========================================


@router.post("/promotion/promote")
def trigger_promotion(
    mode: str = Query("incremental", pattern="^(incremental|full)$"),
    flux_types: Optional[str] = Query(None, description="R4X,R50,R171,R151 (comma-sep)"),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
    flux_db: Session = Depends(get_flux_data_db),
    _auth=Depends(_require_auth),
):
    """Déclenche un run de promotion archive brute → tables fonctionnelles.

    Rate limit : 1 run par fenêtre de 60s (anti DoS).
    Dry-run : exempt du rate limit pour debug.
    """
    from data_staging.engine import run_promotion

    if not dry_run:
        _check_promotion_rate_limit("api")

    ft = [f.strip().upper() for f in flux_types.split(",")] if flux_types else None
    try:
        run = run_promotion(db, mode=mode, triggered_by="api", flux_types=ft, dry_run=dry_run, flux_db=flux_db)
        return {
            "run_id": run.id,
            "status": run.status,
            "mode": run.mode,
            "prms_total": run.prms_total,
            "prms_matched": run.prms_matched,
            "prms_unmatched": run.prms_unmatched,
            "rows_load_curve": run.rows_load_curve,
            "rows_energy_index": run.rows_energy_index,
            "rows_power_peak": run.rows_power_peak,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/promotion/runs")
def list_promotion_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Liste les runs de promotion."""
    from data_staging.models import PromotionRun

    total = db.query(PromotionRun).count()
    runs = db.query(PromotionRun).order_by(PromotionRun.id.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "status": r.status,
                "mode": r.mode,
                "triggered_by": r.triggered_by,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "prms_total": r.prms_total,
                "prms_matched": r.prms_matched,
                "prms_unmatched": r.prms_unmatched,
                "rows_load_curve": r.rows_load_curve,
                "rows_energy_index": r.rows_energy_index,
                "rows_power_peak": r.rows_power_peak,
            }
            for r in runs
        ],
    }


@router.get("/promotion/runs/{run_id}")
def get_promotion_run(run_id: int, db: Session = Depends(get_db)):
    """Détail d'un run de promotion."""
    from data_staging.models import PromotionRun

    run = db.query(PromotionRun).filter(PromotionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": run.id,
        "status": run.status,
        "mode": run.mode,
        "triggered_by": run.triggered_by,
        "scope_flux_types": run.scope_flux_types,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "high_water_mark_before": run.high_water_mark_before,
        "high_water_mark_after": run.high_water_mark_after,
        "prms_total": run.prms_total,
        "prms_matched": run.prms_matched,
        "prms_unmatched": run.prms_unmatched,
        "prms_promoted": run.prms_promoted,
        "prms_failed": run.prms_failed,
        "rows_load_curve": run.rows_load_curve,
        "rows_energy_index": run.rows_energy_index,
        "rows_power_peak": run.rows_power_peak,
        "rows_skipped": run.rows_skipped,
        "rows_flagged": run.rows_flagged,
        "error_message": run.error_message,
    }


@router.get("/promotion/metrics")
def get_promotion_metrics(db: Session = Depends(get_db)):
    """Métriques du pipeline de promotion au format Prometheus-compatible.

    Retourne un texte exposition format Prometheus. Scrapable par Prometheus
    ou par un agent de monitoring sans dépendance externe.

    Usage :
        curl http://localhost:8001/api/enedis/promotion/metrics
    """
    from fastapi.responses import PlainTextResponse
    from data_staging.models import PromotionRun, UnmatchedPrm, MeterLoadCurve
    from sqlalchemy import func as sql_func

    # Collecter les métriques
    total_runs = db.query(PromotionRun).count()
    completed_runs = db.query(PromotionRun).filter(PromotionRun.status == "completed").count()
    failed_runs = db.query(PromotionRun).filter(PromotionRun.status == "failed").count()
    running_runs = db.query(PromotionRun).filter(PromotionRun.status == "running").count()

    last_completed = (
        db.query(PromotionRun).filter(PromotionRun.status == "completed").order_by(PromotionRun.id.desc()).first()
    )

    # Backlog
    backlog_pending = db.query(UnmatchedPrm).filter(UnmatchedPrm.status == "pending").count()
    backlog_resolved = db.query(UnmatchedPrm).filter(UnmatchedPrm.status == "resolved").count()

    # Volume tables fonctionnelles
    mlc_total = db.query(MeterLoadCurve).count()

    # Format Prometheus text exposition
    lines = [
        "# HELP promeos_promotion_runs_total Total promotion runs by status",
        "# TYPE promeos_promotion_runs_total counter",
        f'promeos_promotion_runs_total{{status="completed"}} {completed_runs}',
        f'promeos_promotion_runs_total{{status="failed"}} {failed_runs}',
        f'promeos_promotion_runs_total{{status="running"}} {running_runs}',
        f'promeos_promotion_runs_total{{status="all"}} {total_runs}',
        "",
        "# HELP promeos_promotion_backlog_prms Number of unmatched PRMs in backlog",
        "# TYPE promeos_promotion_backlog_prms gauge",
        f'promeos_promotion_backlog_prms{{status="pending"}} {backlog_pending}',
        f'promeos_promotion_backlog_prms{{status="resolved"}} {backlog_resolved}',
        "",
        "# HELP promeos_meter_load_curve_rows_total Total rows in meter_load_curve",
        "# TYPE promeos_meter_load_curve_rows_total gauge",
        f"promeos_meter_load_curve_rows_total {mlc_total}",
    ]

    if last_completed:
        lines.extend(
            [
                "",
                "# HELP promeos_last_promotion_prms_matched PRMs matched in last completed run",
                "# TYPE promeos_last_promotion_prms_matched gauge",
                f"promeos_last_promotion_prms_matched {last_completed.prms_matched or 0}",
                "",
                "# HELP promeos_last_promotion_prms_unmatched PRMs unmatched in last completed run",
                "# TYPE promeos_last_promotion_prms_unmatched gauge",
                f"promeos_last_promotion_prms_unmatched {last_completed.prms_unmatched or 0}",
                "",
                "# HELP promeos_last_promotion_rows_promoted Total rows promoted in last run",
                "# TYPE promeos_last_promotion_rows_promoted gauge",
                f"promeos_last_promotion_rows_promoted "
                f"{(last_completed.rows_load_curve or 0) + (last_completed.rows_energy_index or 0) + (last_completed.rows_power_peak or 0)}",
            ]
        )

        # Age du dernier run (secondes)
        if last_completed.finished_at:
            from datetime import datetime, timezone

            finished = last_completed.finished_at
            if finished.tzinfo is None:
                finished = finished.replace(tzinfo=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - finished).total_seconds()
            lines.extend(
                [
                    "",
                    "# HELP promeos_last_promotion_age_seconds Seconds since last completed run",
                    "# TYPE promeos_last_promotion_age_seconds gauge",
                    f"promeos_last_promotion_age_seconds {int(age_seconds)}",
                ]
            )

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@router.post("/opendata/refresh")
def refresh_opendata(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    dataset: str = Query("sup36", pattern="^(sup36|inf36|all)$"),
    db: Session = Depends(get_db),
    _auth=Depends(_require_auth),
):
    """Import/refresh des agrégats Enedis Open Data.

    Endpoint à appeler périodiquement (cron hebdomadaire recommandé) pour
    maintenir les benchmarks NAF à jour. Rate-limité pour éviter surcharge ODS.
    """
    _check_promotion_rate_limit("opendata_refresh")

    from connectors.registry import get_connector

    connector = get_connector("enedis_opendata")
    if not connector:
        raise HTTPException(status_code=500, detail="Connector enedis_opendata non trouvé")

    try:
        results = connector.sync(db, object_type=dataset, date_from=date_from, date_to=date_to)
        return {
            "status": "completed",
            "dataset": dataset,
            "date_from": date_from,
            "date_to": date_to,
            "results": results,
            "total_rows": sum(r.get("rows_imported", 0) for r in results),
        }
    except Exception as e:
        logger.error("ODS refresh failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"ODS refresh failed: {e}")


@router.get("/opendata/freshness")
def get_opendata_freshness(db: Session = Depends(get_db)):
    """Retourne l'état de fraîcheur des données Open Data.

    Permet aux dashboards de savoir si les benchmarks sont à jour.
    """
    from models.enedis_opendata import EnedisConsoSup36, EnedisConsoInf36
    from sqlalchemy import func as sql_func
    from datetime import datetime, timezone

    sup36_count = db.query(EnedisConsoSup36).count()
    inf36_count = db.query(EnedisConsoInf36).count()

    sup36_latest = db.query(sql_func.max(EnedisConsoSup36.created_at)).scalar()
    inf36_latest = db.query(sql_func.max(EnedisConsoInf36.created_at)).scalar()

    def _age_days(dt):
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - dt).total_seconds() / 86400, 1)

    sup36_age = _age_days(sup36_latest)
    inf36_age = _age_days(inf36_latest)

    status = "empty"
    alerts = []
    if sup36_count > 0:
        if sup36_age is not None and sup36_age > 90:
            status = "stale"
            alerts.append(f"Agrégats sup36 vieux de {sup36_age} jours (seuil : 90)")
        elif sup36_age is not None and sup36_age > 30:
            status = "aging"
        else:
            status = "fresh"

    return {
        "status": status,
        "alerts": alerts,
        "sup36": {
            "count": sup36_count,
            "latest_import": sup36_latest.isoformat() if sup36_latest else None,
            "age_days": sup36_age,
        },
        "inf36": {
            "count": inf36_count,
            "latest_import": inf36_latest.isoformat() if inf36_latest else None,
            "age_days": inf36_age,
        },
    }


@router.get("/promotion/health")
def get_promotion_health(db: Session = Depends(get_db)):
    """Health check du pipeline de promotion.

    Retourne : status (healthy/stale/warning/error/never_ran/running),
    dernier run, volumes, backlog, alertes actives.
    """
    from data_staging.models import PromotionRun, UnmatchedPrm, MeterLoadCurve
    from datetime import datetime, timezone

    last_run = db.query(PromotionRun).order_by(PromotionRun.id.desc()).first()
    last_completed = (
        db.query(PromotionRun).filter(PromotionRun.status == "completed").order_by(PromotionRun.id.desc()).first()
    )
    running = db.query(PromotionRun).filter(PromotionRun.status == "running").first()
    pending_backlog = db.query(UnmatchedPrm).filter(UnmatchedPrm.status == "pending").count()
    resolved_backlog = db.query(UnmatchedPrm).filter(UnmatchedPrm.status == "resolved").count()
    promoted_rows_total = db.query(MeterLoadCurve).count()

    alerts = []
    now = datetime.now(timezone.utc)

    if not last_run:
        status = "never_ran"
        alerts.append("Aucun run de promotion effectué")
    elif running:
        status = "running"
    elif last_completed:
        last_finished = last_completed.finished_at
        if last_finished and last_finished.tzinfo is None:
            last_finished = last_finished.replace(tzinfo=timezone.utc)

        if last_finished:
            age_hours = (now - last_finished).total_seconds() / 3600
            if age_hours > 48:
                status = "stale"
                alerts.append(f"Dernier run il y a {int(age_hours)}h (seuil : 48h)")
            elif age_hours > 24:
                status = "warning"
                alerts.append(f"Dernier run il y a {int(age_hours)}h (seuil warning : 24h)")
            else:
                status = "healthy"
        else:
            status = "unknown"
    else:
        status = "error"
        alerts.append("Aucun run complété avec succès")

    if pending_backlog > 100:
        alerts.append(f"Backlog élevé : {pending_backlog} PRMs non résolus")

    last_run_info = None
    if last_run:
        last_run_info = {
            "id": last_run.id,
            "status": last_run.status,
            "mode": last_run.mode,
            "triggered_by": last_run.triggered_by,
            "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
            "finished_at": last_run.finished_at.isoformat() if last_run.finished_at else None,
            "prms_total": last_run.prms_total,
            "prms_matched": last_run.prms_matched,
            "prms_unmatched": last_run.prms_unmatched,
            "rows_promoted": (
                (last_run.rows_load_curve or 0) + (last_run.rows_energy_index or 0) + (last_run.rows_power_peak or 0)
            ),
            "error_message": last_run.error_message,
        }

    return {
        "status": status,
        "alerts": alerts,
        "last_run": last_run_info,
        "volumes": {
            "meter_load_curve_total": promoted_rows_total,
            "backlog_pending": pending_backlog,
            "backlog_resolved": resolved_backlog,
        },
        "checked_at": now.isoformat(),
    }


@router.get("/promotion/backlog")
def get_promotion_backlog(
    status: str = Query("pending", pattern="^(pending|resolved|ignored|all)$"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Liste les PRM non résolus (backlog)."""
    from data_staging.models import UnmatchedPrm

    q = db.query(UnmatchedPrm)
    if status != "all":
        q = q.filter(UnmatchedPrm.status == status)

    total = q.count()
    items = q.order_by(UnmatchedPrm.last_seen_at.desc()).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": u.id,
                "point_id": u.point_id,
                "status": u.status,
                "block_reason": u.block_reason,
                "flux_types": u.flux_types,
                "measures_count": u.measures_count,
                "first_seen_at": u.first_seen_at.isoformat() if u.first_seen_at else None,
                "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
            }
            for u in items
        ],
    }
