"""PROMEOS — Enedis SGE ingestion CLI.

Usage:
    cd promeos-poc/backend
    python -m data_ingestion.enedis.cli ingest [OPTIONS]

Options:
    --dir PATH          Override ENEDIS_FLUX_DIR env var
    --dry-run           Scan and classify without writing to DB
    --no-recursive      Disable recursive directory scan (default: recursive)
    --verbose           Enable DEBUG logging
"""

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend/ is on sys.path for project imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# database import triggers load_dotenv() via connection.py
from sqlalchemy.exc import IntegrityError  # noqa: E402
from database import FluxDataSessionLocal as SessionLocal, flux_data_engine as engine  # noqa: E402

from data_ingestion.enedis.config import get_flux_dir  # noqa: E402
from data_ingestion.enedis.decrypt import MissingKeyError, load_keys_from_env  # noqa: E402
from data_ingestion.enedis.enums import FluxStatus, IngestionRunStatus  # noqa: E402
from data_ingestion.enedis.migrations import run_flux_data_migrations  # noqa: E402
from data_ingestion.enedis.models import (  # noqa: E402
    EnedisFluxFile,
    EnedisFluxIndexR64,
    EnedisFluxItcC68,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
    EnedisFluxMesureR63,
    IngestionRun,
)
from data_ingestion.enedis.pipeline import ingest_directory  # noqa: E402

logger = logging.getLogger("promeos.enedis.cli")


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def _ensure_tables(eng):
    """Create all tables if DB is missing or empty, then run migrations."""
    import data_ingestion.enedis.models  # noqa: F401 — register Enedis staging models

    run_flux_data_migrations(eng)


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m data_ingestion.enedis.cli",
        description="PROMEOS — Enedis SGE ingestion CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_p = subparsers.add_parser("ingest", help="Run ingestion pipeline")
    ingest_p.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Override ENEDIS_FLUX_DIR env var (must be an existing directory)",
    )
    ingest_p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Scan and classify without writing to DB",
    )
    ingest_p.set_defaults(recursive=True)
    ingest_p.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Disable recursive directory scan (default: recursive)",
    )
    ingest_p.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable DEBUG logging",
    )
    return parser


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def _print_report(
    counters: dict[str, int],
    session,
    run: IngestionRun,
    duration: float,
    flux_dir: Path,
    recursive: bool,
) -> None:
    """Structured report for normal (non-dry-run) ingestion."""
    mode = "recursive" if recursive else "non-recursive"

    print(f"\n=== ENEDIS SGE INGESTION REPORT ===")
    print(f"Run #{run.id}        triggered_by: {run.triggered_by}        status: {run.status}")
    print(f"Source:          {flux_dir} ({mode})")
    print(f"Duration:        {duration:.1f}s")
    print(f"Files received:  {counters['received']}")
    print(f"  parsed:        {counters['parsed']}")
    print(f"  skipped:       {counters['skipped']}")
    print(f"  error:         {counters['error']}")
    print(f"  needs_review:  {counters['needs_review']}")
    print(f"Retried:         {counters['retried']}  (from previous errors)")
    print(f"Max retries:     {counters['max_retries_reached']}  (permanently failed — skipped)")
    print(f"Perm. failed:    {counters['permanently_failed']}  (status set this run)")
    print(f"Already processed: {counters['already_processed']}")

    # Staging totals (all rows in each measure table)
    r4x_total = session.query(EnedisFluxMesureR4x).count()
    r171_total = session.query(EnedisFluxMesureR171).count()
    r50_total = session.query(EnedisFluxMesureR50).count()
    r151_total = session.query(EnedisFluxMesureR151).count()
    r63_total = session.query(EnedisFluxMesureR63).count()
    r64_total = session.query(EnedisFluxIndexR64).count()
    r6x_total = r63_total + r64_total
    c68_total = session.query(EnedisFluxItcC68).count()
    grand_total = r4x_total + r171_total + r50_total + r151_total + r6x_total + c68_total

    print(f"Measures stored (staging totals):")
    print(f"  R4x:    {r4x_total:>8,}")
    print(f"  R171:   {r171_total:>8,}")
    print(f"  R50:    {r50_total:>8,}")
    print(f"  R151:   {r151_total:>8,}")
    print(f"  R63:    {r63_total:>8,}")
    print(f"  R64:    {r64_total:>8,}")
    print(f"  R6X*:   {r6x_total:>8,}  (compat aggregate)")
    print(f"  C68:    {c68_total:>8,}")
    print(f"  TOTAL:  {grand_total:>8,}")

    # Error details from this run
    # Normalize to naive UTC for SQLite comparison (TimestampMixin stores naive)
    started_at_naive = run.started_at.replace(tzinfo=None) if run.started_at.tzinfo else run.started_at
    error_files = (
        session.query(EnedisFluxFile)
        .filter(
            EnedisFluxFile.status.in_([FluxStatus.ERROR, FluxStatus.PERMANENTLY_FAILED]),
            EnedisFluxFile.updated_at >= started_at_naive,
        )
        .all()
    )
    if error_files:
        print(f"ERRORS ({len(error_files)}):")
        for ef in error_files:
            print(f"  {ef.filename}: {ef.error_message}")


def _dry_run_report(
    counters: dict[str, int],
    run: IngestionRun,
    flux_dir: Path,
    recursive: bool,
) -> None:
    """Structured report for dry-run mode."""
    mode = "recursive" if recursive else "non-recursive"

    print(f"\n=== ENEDIS SGE DRY-RUN REPORT ===")
    print(f"Run #{run.id}        triggered_by: {run.triggered_by}  (dry-run)")
    print(f"Source:          {flux_dir} ({mode})")
    print(f"New files:       {counters['received']}")
    print(f"Retryable errors: {counters['retried']}  (eligible for retry, < MAX_RETRIES)")
    print(f"Max retries:     {counters['max_retries_reached']}  (permanently failed — will be skipped)")
    print(f"Perm. failed:    {counters['permanently_failed']}  (status set this run)")
    print(f"Already processed: {counters['already_processed']}")
    print(f"No data modifications made.")


# ---------------------------------------------------------------------------
# Command: ingest
# ---------------------------------------------------------------------------


def cmd_ingest(args: argparse.Namespace) -> int:
    """Run the Enedis ingestion pipeline. Returns exit code (0=success, 1=error)."""
    # Verbose logging — set level on the enedis logger hierarchy
    enedis_logger = logging.getLogger("promeos.enedis")
    if args.verbose:
        enedis_logger.setLevel(logging.DEBUG)
        if not enedis_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
            enedis_logger.addHandler(handler)
    else:
        enedis_logger.setLevel(logging.INFO)

    # --- Bootstrap ---
    _ensure_tables(engine)

    # --- Pre-flight validation ---
    try:
        flux_dir = get_flux_dir(override=args.dir)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        keys = load_keys_from_env()
    except MissingKeyError as exc:
        print(f"WARNING: {exc}. Direct-openable files will still be processed.", file=sys.stderr)
        keys = []

    # --- Open session ---
    session = SessionLocal()
    try:
        # --- Concurrency guard (atomic via partial unique index) ---
        run = IngestionRun(
            started_at=datetime.now(timezone.utc),
            directory=str(flux_dir),
            recursive=args.recursive,
            dry_run=args.dry_run,
            status=IngestionRunStatus.RUNNING,
            triggered_by="cli",
        )
        session.add(run)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            existing_run = session.query(IngestionRun).filter_by(status=IngestionRunStatus.RUNNING).first()
            detail = "another ingestion run is already in progress"
            if existing_run:
                detail = (
                    f"another ingestion run is already in progress "
                    f"(run #{existing_run.id}, started {existing_run.started_at})"
                )
            print(
                f"ERROR: {detail}. If the previous run crashed, update its status manually.",
                file=sys.stderr,
            )
            return 1
        session.commit()

        # --- Execute pipeline ---
        start_time = time.monotonic()
        try:
            counters = ingest_directory(
                flux_dir,
                session,
                keys,
                recursive=args.recursive,
                dry_run=args.dry_run,
                run=run,
            )
        except Exception as exc:
            run.status = IngestionRunStatus.FAILED
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
            print(f"ERROR: Run #{run.id} interrupted — status: failed", file=sys.stderr)
            traceback.print_exc()
            return 1

        duration = time.monotonic() - start_time

        # --- Report ---
        # run.status already set to COMPLETED by ingest_directory()
        if args.dry_run:
            _dry_run_report(counters, run, flux_dir, args.recursive)
        else:
            _print_report(counters, session, run, duration, flux_dir, args.recursive)

        return 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "ingest":
        sys.exit(cmd_ingest(args))


if __name__ == "__main__":
    main()
