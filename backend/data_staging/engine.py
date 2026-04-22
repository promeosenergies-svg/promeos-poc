"""
SF5 — Moteur de promotion : orchestre discover → match → convert → promote → audit.

Modes :
- incremental : ne traite que les nouvelles rows staging (id > high_water_mark)
- full : retraite tout depuis le début

Garanties :
- Per-PRM atomicité (un PRM en erreur ne bloque pas les autres)
- Quality-first overwrite (meilleure qualité auto-promote)
- Backlog replay (PRM non résolus retentés à chaque run)
- Raw read path in flux_data.db, promoted write path in promeos.db
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import OperationalError, CompileError
from sqlalchemy.orm import Session

from data_staging.models import (
    MeterLoadCurve,
    MeterEnergyIndex,
    MeterPowerPeak,
    PromotionRun,
    UnmatchedPrm,
)
from data_staging.prm_matcher import resolve_prm
from data_staging.promoters import (
    promote_r4x_row,
    promote_r50_row,
    promote_r171_row,
    promote_r151_row,
)
from data_ingestion.enedis.models import (
    EnedisFluxMesureR4x,
    EnedisFluxMesureR171,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000

# Tables staging par type de flux
_STAGING_TABLES = {
    "R4X": (EnedisFluxMesureR4x, promote_r4x_row),
    "R50": (EnedisFluxMesureR50, promote_r50_row),
    "R171": (EnedisFluxMesureR171, promote_r171_row),
    "R151": (EnedisFluxMesureR151, promote_r151_row),
}


def run_promotion(
    db: Session,
    mode: str = "incremental",
    triggered_by: str = "api",
    flux_types: list[str] | None = None,
    dry_run: bool = False,
    flux_db: Session | None = None,
) -> PromotionRun:
    """Exécute un run de promotion complet.

    Retourne le PromotionRun avec tous les compteurs remplis.
    """
    if flux_types is None:
        flux_types = ["R4X", "R50", "R171", "R151"]
    if flux_db is None:
        flux_db = db

    # Vérifier qu'aucun run n'est déjà en cours
    running = db.query(PromotionRun).filter(PromotionRun.status == "running").first()
    if running:
        raise RuntimeError(f"Promotion déjà en cours (run_id={running.id})")

    run = PromotionRun(
        status="running",
        triggered_by=triggered_by,
        mode=mode,
        scope_flux_types=",".join(flux_types),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # High-water marks : lus du DERNIER RUN completed, pas du max(id) actuel
        # (sinon les rows ajoutées depuis le dernier run seraient ignorées)
        hwm_before = _load_last_hwm(db, flux_types) if mode == "incremental" else {}
        run.high_water_mark_before = json.dumps(hwm_before)

        # Discover : collecter tous les PRM distincts à traiter
        prm_rows = _discover_prms(flux_db, db, flux_types, hwm_before, mode)
        run.prms_total = len(prm_rows)

        counters = defaultdict(int)

        # Traiter par PRM (per-PRM atomicité)
        for prm_code, staging_entries in prm_rows.items():
            try:
                result = _process_prm(db, run.id, prm_code, staging_entries, dry_run)
                counters["matched" if result["matched"] else "unmatched"] += 1
                if result["matched"]:
                    counters["promoted"] += 1
                counters["rows_load_curve"] += result.get("lc", 0)
                counters["rows_energy_index"] += result.get("ei", 0)
                counters["rows_power_peak"] += result.get("pp", 0)
                counters["rows_skipped"] += result.get("skipped", 0)
            except Exception as e:
                db.rollback()
                logger.error("Promotion failed for PRM %s: %s", prm_code, e)
                counters["failed"] += 1

        # Finalize
        hwm_after = _get_high_water_marks(flux_db, flux_types)
        run.high_water_mark_after = json.dumps(hwm_after)
        run.prms_matched = counters["matched"]
        run.prms_unmatched = counters["unmatched"]
        run.prms_promoted = counters["promoted"]
        run.prms_failed = counters["failed"]
        run.rows_load_curve = counters["rows_load_curve"]
        run.rows_energy_index = counters["rows_energy_index"]
        run.rows_power_peak = counters["rows_power_peak"]
        run.rows_skipped = counters["rows_skipped"]
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

        # Invalider le cache bridge pour que les services utilisent les nouvelles données
        from data_staging.bridge import invalidate_promoted_cache

        invalidate_promoted_cache()

        logger.info(
            "Promotion run #%d completed: %d PRMs (%d matched, %d unmatched, %d failed), %d LC + %d EI + %d PP rows",
            run.id,
            run.prms_total,
            run.prms_matched,
            run.prms_unmatched,
            run.prms_failed,
            run.rows_load_curve,
            run.rows_energy_index,
            run.rows_power_peak,
        )

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)[:2000]
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.error("Promotion run #%d failed: %s", run.id, e)
        raise

    return run


def _discover_prms(
    flux_db: Session,
    db: Session,
    flux_types: list[str],
    hwm: dict,
    mode: str,
) -> dict[str, list[tuple[str, object]]]:
    """Découvre les PRM distincts à traiter depuis les tables staging.

    Retourne {prm_code: [(flux_key, staging_row), ...]}
    """
    prm_rows: dict[str, list] = defaultdict(list)

    for flux_key in flux_types:
        if flux_key not in _STAGING_TABLES:
            continue
        model_cls, _ = _STAGING_TABLES[flux_key]

        query = flux_db.query(model_cls)
        if mode == "incremental" and flux_key in hwm:
            query = query.filter(model_cls.id > hwm[flux_key])

        # Charger par chunks pour ne pas exploser la mémoire
        offset = 0
        while True:
            batch = query.order_by(model_cls.id).offset(offset).limit(CHUNK_SIZE).all()
            if not batch:
                break
            for row in batch:
                prm = getattr(row, "point_id", None)
                if prm:
                    prm_rows[prm].append((flux_key, row))
            offset += CHUNK_SIZE

    # Ajouter les PRM du backlog (unmatched_prm pending)
    backlog = db.query(UnmatchedPrm).filter(UnmatchedPrm.status == "pending").all()
    for uprm in backlog:
        if uprm.point_id not in prm_rows:
            prm_rows[uprm.point_id] = []  # Retry matching sans nouvelles données

    return prm_rows


def _process_prm(
    db: Session, run_id: int, prm_code: str, staging_entries: list[tuple[str, object]], dry_run: bool
) -> dict:
    """Traite un PRM : match → convert → promote."""
    result = {"matched": False, "lc": 0, "ei": 0, "pp": 0, "skipped": 0}

    # Stage 2: Match
    match = resolve_prm(db, prm_code)

    if not match.matched:
        _upsert_unmatched(db, prm_code, match.block_reason, staging_entries)
        return result

    # Si le PRM était dans le backlog, le résoudre
    _resolve_backlog(db, prm_code, match.meter_id)

    result["matched"] = True
    meter_id = match.meter_id

    # Stage 3-4: Convert & Route
    lc_rows = []
    ei_rows = []
    pp_rows = []

    for flux_key, row in staging_entries:
        _, promoter_fn = _STAGING_TABLES.get(flux_key, (None, None))
        if promoter_fn is None:
            continue

        promoted = promoter_fn(row, meter_id, run_id)
        if promoted is None:
            result["skipped"] += 1
            continue

        if isinstance(promoted, MeterLoadCurve):
            lc_rows.append(promoted)
        elif isinstance(promoted, MeterEnergyIndex):
            ei_rows.append(promoted)
        elif isinstance(promoted, MeterPowerPeak):
            pp_rows.append(promoted)

    if dry_run:
        result["lc"] = len(lc_rows)
        result["ei"] = len(ei_rows)
        result["pp"] = len(pp_rows)
        return result

    # Stage 5: Promote (UPSERT avec quality-first)
    result["lc"] = _upsert_load_curve(db, lc_rows, run_id)
    result["ei"] = _upsert_energy_index(db, ei_rows, run_id)
    result["pp"] = _upsert_power_peak(db, pp_rows, run_id)

    db.commit()
    return result


def _upsert_quality_first(
    db: Session,
    rows: list,
    unique_key_attrs: list[str],
    update_attrs: list[str],
    run_id: int,
) -> int:
    """UPSERT batch avec quality-first overwrite.

    Par chunk :
    1 query SELECT (batch fetch existing)
    1 query INSERT (bulk_save_objects pour nouveaux)
    1 query UPDATE (bulk_update_mappings pour existants avec meilleure qualité)

    Total : 3 queries par chunk de 1000 rows (vs 2000+ dans l'ancienne version).
    """
    if not rows:
        return 0

    model_cls = type(rows[0])
    count = 0
    all_update_attrs = [*update_attrs, "quality_score", "is_estimated", "promotion_run_id"]

    for chunk_start in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[chunk_start : chunk_start + CHUNK_SIZE]
        existing_map = _batch_fetch_existing(db, model_cls, unique_key_attrs, chunk)

        to_insert = []
        to_update_mappings: list[dict] = []

        for row in chunk:
            key = tuple(getattr(row, attr) for attr in unique_key_attrs)
            existing = existing_map.get(key)

            if existing:
                # Quality-first : update seulement si >= (latest wins on tie)
                if row.quality_score >= existing.quality_score:
                    mapping = {"id": existing.id}
                    for attr in update_attrs:
                        new_val = getattr(row, attr)
                        if new_val is not None:
                            mapping[attr] = new_val
                    mapping["quality_score"] = row.quality_score
                    mapping["is_estimated"] = row.is_estimated
                    mapping["promotion_run_id"] = run_id
                    to_update_mappings.append(mapping)
                    count += 1
            else:
                to_insert.append(row)

        # Batch INSERT (1 query)
        if to_insert:
            db.bulk_save_objects(to_insert)
            count += len(to_insert)

        # Batch UPDATE (1 query)
        if to_update_mappings:
            db.bulk_update_mappings(model_cls, to_update_mappings)

    return count


def _batch_fetch_existing(db: Session, model_cls, unique_key_attrs: list[str], rows: list) -> dict[tuple, object]:
    """Fetch batch des rows existantes par clés composites. 1 query par chunk."""
    if not rows:
        return {}

    # Pour SQLite, construire un filtre OR de toutes les clés composites
    from sqlalchemy import and_, or_, tuple_

    key_cols = [getattr(model_cls, attr) for attr in unique_key_attrs]

    # Construire les tuples de clés
    key_tuples = [tuple(getattr(row, attr) for attr in unique_key_attrs) for row in rows]

    # Utiliser tuple_().in_() pour les clés composites (SQLAlchemy >= 1.4)
    try:
        existing_rows = db.query(model_cls).filter(tuple_(*key_cols).in_(key_tuples)).all()
    except (OperationalError, CompileError):
        # Fallback si tuple_ IN pas supporté (vieux SQLite)
        conditions = []
        for key_vals in key_tuples:
            conditions.append(and_(*[getattr(model_cls, attr) == val for attr, val in zip(unique_key_attrs, key_vals)]))
        existing_rows = db.query(model_cls).filter(or_(*conditions)).all() if conditions else []

    # Indexer par clé composite
    result = {}
    for row in existing_rows:
        key = tuple(getattr(row, attr) for attr in unique_key_attrs)
        result[key] = row

    return result


def _upsert_load_curve(db: Session, rows: list[MeterLoadCurve], run_id: int) -> int:
    return _upsert_quality_first(
        db,
        rows,
        unique_key_attrs=["meter_id", "timestamp", "pas_minutes"],
        update_attrs=[
            "active_power_kw",
            "reactive_inductive_kvar",
            "reactive_capacitive_kvar",
            "voltage_v",
            "source_flux_type",
        ],
        run_id=run_id,
    )


def _upsert_energy_index(db: Session, rows: list[MeterEnergyIndex], run_id: int) -> int:
    return _upsert_quality_first(
        db,
        rows,
        unique_key_attrs=["meter_id", "date_releve", "tariff_class_code", "tariff_grid"],
        update_attrs=["value_wh"],
        run_id=run_id,
    )


def _upsert_power_peak(db: Session, rows: list[MeterPowerPeak], run_id: int) -> int:
    return _upsert_quality_first(
        db,
        rows,
        unique_key_attrs=["meter_id", "date_releve"],
        update_attrs=["value_va"],
        run_id=run_id,
    )


def _upsert_unmatched(db: Session, prm_code: str, reason: str, entries: list) -> None:
    """Ajoute ou met à jour un PRM dans le backlog unmatched."""
    existing = db.query(UnmatchedPrm).filter(UnmatchedPrm.point_id == prm_code).first()
    now = datetime.now(timezone.utc)

    flux_types = set()
    for flux_key, _ in entries:
        flux_types.add(flux_key)

    if existing:
        existing.last_seen_at = now
        existing.measures_count += len(entries)
        existing.block_reason = reason
        if flux_types:
            old = set((existing.flux_types or "").split(","))
            existing.flux_types = ",".join(sorted(old | flux_types))
    else:
        db.add(
            UnmatchedPrm(
                point_id=prm_code,
                first_seen_at=now,
                last_seen_at=now,
                flux_types=",".join(sorted(flux_types)),
                measures_count=len(entries),
                block_reason=reason,
            )
        )
    # Pas de commit ici — atomicité per-PRM gérée par _process_prm


def _resolve_backlog(db: Session, prm_code: str, meter_id: int) -> None:
    """Résout un PRM du backlog qui est maintenant matchable."""
    existing = (
        db.query(UnmatchedPrm)
        .filter(
            UnmatchedPrm.point_id == prm_code,
            UnmatchedPrm.status == "pending",
        )
        .first()
    )
    if existing:
        existing.status = "resolved"
        existing.resolved_at = datetime.now(timezone.utc)
        existing.resolved_meter_id = meter_id
        # Pas de commit ici — atomicité per-PRM gérée par _process_prm


def _get_high_water_marks(flux_db: Session, flux_types: list[str]) -> dict[str, int]:
    """Retourne le max(id) par table staging (snapshot courant)."""
    hwm = {}
    for flux_key in flux_types:
        if flux_key not in _STAGING_TABLES:
            continue
        model_cls, _ = _STAGING_TABLES[flux_key]
        max_id = flux_db.query(func.max(model_cls.id)).scalar()
        if max_id is not None:
            hwm[flux_key] = max_id
    return hwm


def _load_last_hwm(db: Session, flux_types: list[str]) -> dict[str, int]:
    """Charge le HWM du dernier run COMPLETED (source de vérité pour incrémental).

    Si aucun run précédent : retourne {} (= tout traiter).
    """
    last_run = (
        db.query(PromotionRun).filter(PromotionRun.status == "completed").order_by(PromotionRun.id.desc()).first()
    )
    if not last_run or not last_run.high_water_mark_after:
        return {}
    try:
        return json.loads(last_run.high_water_mark_after)
    except (json.JSONDecodeError, TypeError):
        return {}
