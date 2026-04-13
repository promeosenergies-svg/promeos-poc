#!/usr/bin/env python3
"""Run Enedis raw ingestion flow-by-flow into backend/data/enedis.db.

The script deliberately reuses the existing SF1-SF4 CLI unchanged by:
- switching DATABASE_URL to a dedicated SQLite database
- invoking `python -m data_ingestion.enedis.cli ingest`
- running one flow directory per CLI execution

Examples:
    python backend/scripts/load_enedis_lab_flow.py R171 --reset-db
    python backend/scripts/load_enedis_lab_flow.py flux_enedis/R50
    python backend/scripts/load_enedis_lab_flow.py --all --reset-db
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
BACKEND_DIR = SCRIPT_PATH.parents[1]
REPO_ROOT = SCRIPT_PATH.parents[2]
WORKSPACE_ROOT = SCRIPT_PATH.parents[3]

DEFAULT_DB_PATH = BACKEND_DIR / "data" / "enedis.db"
DEFAULT_PROMEOS_DB_PATH = BACKEND_DIR / "data" / "promeos.db"
DEFAULT_LOG_DIR = BACKEND_DIR / "data" / "enedis_lab_logs"
DEFAULT_BACKEND_PYTHON = BACKEND_DIR / "venv" / "bin" / "python3"

DEFAULT_FLOWS = OrderedDict(
    [
        ("R171", WORKSPACE_ROOT / "flux_enedis" / "R171"),
        ("R151", WORKSPACE_ROOT / "flux_enedis" / "R151"),
        ("R50", WORKSPACE_ROOT / "flux_enedis" / "R50"),
        ("R4H", WORKSPACE_ROOT / "flux_enedis" / "R4H"),
        ("R4M", WORKSPACE_ROOT / "flux_enedis" / "R4M"),
        ("R4Q", WORKSPACE_ROOT / "flux_enedis" / "R4Q"),
    ]
)

REQUIRED_TABLES = (
    "enedis_flux_file",
    "enedis_flux_file_error",
    "enedis_ingestion_run",
    "enedis_flux_mesure_r4x",
    "enedis_flux_mesure_r171",
    "enedis_flux_mesure_r50",
    "enedis_flux_mesure_r151",
)

MEASURE_TABLES = (
    "enedis_flux_mesure_r4x",
    "enedis_flux_mesure_r171",
    "enedis_flux_mesure_r50",
    "enedis_flux_mesure_r151",
)

EXPECTED_MEASURE_TABLE = {
    "R171": "enedis_flux_mesure_r171",
    "R151": "enedis_flux_mesure_r151",
    "R50": "enedis_flux_mesure_r50",
    "R4H": "enedis_flux_mesure_r4x",
    "R4M": "enedis_flux_mesure_r4x",
    "R4Q": "enedis_flux_mesure_r4x",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load Enedis raw flows into backend/data/enedis.db")
    parser.add_argument(
        "source",
        nargs="?",
        help="Flow alias (R171/R151/R50/R4H/R4M/R4Q) or directory path",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run the default flow sequence on the same enedis.db",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Delete enedis.db before the first run",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Target SQLite DB path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help=f"Directory for appended run logs (default: {DEFAULT_LOG_DIR})",
    )
    return parser


def resolve_flows(source: str | None, run_all: bool) -> list[tuple[str, Path]]:
    if run_all:
        return list(DEFAULT_FLOWS.items())

    if not source:
        raise SystemExit("ERROR: provide a flow alias/path or use --all")

    flow_key = source.strip().upper()
    if flow_key in DEFAULT_FLOWS:
        return [(flow_key, DEFAULT_FLOWS[flow_key])]

    path = Path(source).expanduser()
    candidates = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.extend([Path.cwd() / path, REPO_ROOT / path, WORKSPACE_ROOT / path])

    for candidate in candidates:
        if candidate.is_dir():
            return [(candidate.name.upper(), candidate.resolve())]

    raise SystemExit(f"ERROR: could not resolve source directory from {source!r}")


def ensure_parent_dirs(db_path: Path, log_dir: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)


def reset_db_files(db_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        target = Path(f"{db_path}{suffix}")
        if target.exists():
            target.unlink()


def get_db_snapshot(db_path: Path) -> dict:
    snapshot = {
        "tables": set(),
        "counts": {name: 0 for name in REQUIRED_TABLES},
        "latest_run": None,
    }
    if not db_path.exists():
        return snapshot

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        snapshot["tables"] = {row[0] for row in cur.fetchall()}

        for table in REQUIRED_TABLES:
            if table in snapshot["tables"]:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                snapshot["counts"][table] = int(cur.fetchone()[0])

        if "enedis_ingestion_run" in snapshot["tables"]:
            cur.execute(
                """
                SELECT id, status, triggered_by, directory, recursive, dry_run,
                       files_received, files_parsed, files_skipped, files_error,
                       files_needs_review, files_retried, files_already_processed
                FROM enedis_ingestion_run
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if row is not None:
                snapshot["latest_run"] = {
                    "id": row[0],
                    "status": row[1],
                    "triggered_by": row[2],
                    "directory": row[3],
                    "recursive": row[4],
                    "dry_run": row[5],
                    "files_received": row[6],
                    "files_parsed": row[7],
                    "files_skipped": row[8],
                    "files_error": row[9],
                    "files_needs_review": row[10],
                    "files_retried": row[11],
                    "files_already_processed": row[12],
                }
    finally:
        conn.close()

    return snapshot


def build_log_path(log_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d")
    return log_dir / f"enedis_lab_load_{stamp}.log"


def resolve_python_executable() -> str:
    if DEFAULT_BACKEND_PYTHON.exists():
        return str(DEFAULT_BACKEND_PYTHON)
    return sys.executable


def stream_cli_run(flow_name: str, source_dir: Path, db_path: Path, log_path: Path) -> int:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    python_executable = resolve_python_executable()

    command = [
        python_executable,
        "-u",
        "-m",
        "data_ingestion.enedis.cli",
        "ingest",
        "--dir",
        str(source_dir),
        "--no-recursive",
    ]

    started_at = datetime.now().isoformat(timespec="seconds")
    header = [
        "",
        "=" * 88,
        f"[{started_at}] Flow={flow_name} DB={db_path}",
        f"Command: {' '.join(command)}",
        "=" * 88,
    ]

    with log_path.open("a", encoding="utf-8") as log_file:
        for line in header:
            print(line)
            log_file.write(f"{line}\n")
        log_file.flush()

        process = subprocess.Popen(
            command,
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log_file.write(line)
        return_code = process.wait()
        log_file.write(f"\n[exit_code={return_code}]\n")
        log_file.flush()

    return return_code


def print_verification(
    flow_name: str, source_dir: Path, before: dict, after: dict, db_path: Path, promeos_before_mtime
):
    print("\nVerification")
    print(f"  DB: {db_path}")
    missing_tables = [name for name in REQUIRED_TABLES if name not in after["tables"]]
    if missing_tables:
        print(f"  Missing Enedis tables: {', '.join(missing_tables)}")
    else:
        print("  Required Enedis tables: OK")

    before_runs = before["counts"]["enedis_ingestion_run"]
    after_runs = after["counts"]["enedis_ingestion_run"]
    print(f"  Ingestion runs: {before_runs} -> {after_runs} (delta {after_runs - before_runs:+d})")

    latest_run = after["latest_run"]
    if latest_run is not None:
        print(
            "  Latest run: "
            f"#{latest_run['id']} status={latest_run['status']} "
            f"dir={latest_run['directory']} recursive={latest_run['recursive']} dry_run={latest_run['dry_run']}"
        )

    before_files = before["counts"]["enedis_flux_file"]
    after_files = after["counts"]["enedis_flux_file"]
    print(f"  Flux registry rows: {before_files} -> {after_files} (delta {after_files - before_files:+d})")

    expected_table = EXPECTED_MEASURE_TABLE.get(flow_name)
    for table in MEASURE_TABLES:
        before_count = before["counts"][table]
        after_count = after["counts"][table]
        delta = after_count - before_count
        marker = " expected" if table == expected_table else ""
        print(f"  {table}: {before_count} -> {after_count} (delta {delta:+d}){marker}")

    grown_tables = [table for table in MEASURE_TABLES if after["counts"][table] > before["counts"][table]]
    if expected_table and grown_tables == [expected_table]:
        print("  Matching measurement table growth: OK")
    elif expected_table and not grown_tables:
        print("  Matching measurement table growth: none detected")
    else:
        print(f"  Matching measurement table growth: unexpected set {grown_tables}")

    promeos_path = DEFAULT_PROMEOS_DB_PATH
    if promeos_path.exists():
        current_mtime = promeos_path.stat().st_mtime
        unchanged = promeos_before_mtime == current_mtime
        print(f"  promeos.db unchanged during this run: {'YES' if unchanged else 'NO'}")
    else:
        print("  promeos.db unchanged during this run: file not present")

    print(f"  Source dir: {source_dir}")


def run_flow(flow_name: str, source_dir: Path, db_path: Path, log_path: Path) -> int:
    before = get_db_snapshot(db_path)
    promeos_before_mtime = DEFAULT_PROMEOS_DB_PATH.stat().st_mtime if DEFAULT_PROMEOS_DB_PATH.exists() else None
    exit_code = stream_cli_run(flow_name, source_dir, db_path, log_path)
    after = get_db_snapshot(db_path)
    print_verification(flow_name, source_dir, before, after, db_path, promeos_before_mtime)
    return exit_code


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    flows = resolve_flows(args.source, args.all)
    db_path = args.db_path.expanduser().resolve()
    log_dir = args.log_dir.expanduser().resolve()
    ensure_parent_dirs(db_path, log_dir)

    if args.reset_db:
        reset_db_files(db_path)

    log_path = build_log_path(log_dir)
    overall_exit_code = 0

    for flow_name, source_dir in flows:
        if not source_dir.is_dir():
            print(f"ERROR: source directory not found: {source_dir}", file=sys.stderr)
            return 1
        exit_code = run_flow(flow_name, source_dir.resolve(), db_path, log_path)
        if exit_code != 0:
            overall_exit_code = exit_code
            break

    if overall_exit_code == 0:
        print(f"\nAll requested flow runs completed. Log file: {log_path}")
        print(f"Target DB: {db_path}")

    return overall_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
