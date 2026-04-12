"""
SF5 — CLI de promotion.

Usage :
    cd backend
    python -m data_staging.cli promote [--mode incremental|full] [--flux-types R4X,R50] [--dry-run] [--verbose]
"""

import argparse
import logging
import sys

from database import SessionLocal
from data_staging.engine import run_promotion


def main():
    parser = argparse.ArgumentParser(description="PROMEOS SF5 — Pipeline de promotion Enedis")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("promote", help="Lancer un run de promotion")
    p.add_argument("--mode", choices=["incremental", "full"], default="incremental")
    p.add_argument("--flux-types", type=str, default=None, help="R4X,R50,R171,R151 (comma-sep)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    if args.command != "promote":
        parser.print_help()
        sys.exit(1)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    ft = [f.strip().upper() for f in args.flux_types.split(",")] if args.flux_types else None

    db = SessionLocal()
    try:
        run = run_promotion(db, mode=args.mode, triggered_by="cli", flux_types=ft, dry_run=args.dry_run)
        print(f"\nPromotion run #{run.id} — {run.status}")
        print(f"  PRMs: {run.prms_total} total, {run.prms_matched} matched, {run.prms_unmatched} unmatched")
        print(f"  Rows: {run.rows_load_curve} LC, {run.rows_energy_index} EI, {run.rows_power_peak} PP")
        print(f"  Skipped: {run.rows_skipped}")
        if run.error_message:
            print(f"  Error: {run.error_message}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
