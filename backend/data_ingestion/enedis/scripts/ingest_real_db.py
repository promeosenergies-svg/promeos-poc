"""Ingest real Enedis SGE files into flux_data.db.

.. deprecated:: SF4
    This script is deprecated. Use the CLI instead:
        python -m data_ingestion.enedis.cli ingest [--dir PATH] [--dry-run]
    Will be removed after SF4 validation is complete.

Runs the full pipeline (decrypt -> parse -> store) against the real database.
Displays a summary report at the end.

Usage:
    cd promeos-poc/backend
    python -m data_ingestion.enedis.scripts.ingest_real_db
"""

import sys
from pathlib import Path

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from database import FluxDataSessionLocal
from data_ingestion.enedis.decrypt import load_keys_from_env
from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
    EnedisFluxMesureR171,
)
from data_ingestion.enedis.enums import FluxStatus
from data_ingestion.enedis.pipeline import ingest_directory

# flux_enedis/ lives at the Promeos/ root level
FLUX_DIR = Path(__file__).resolve().parents[5] / "flux_enedis"


def main():
    if not FLUX_DIR.is_dir():
        print(f"ERROR: flux_enedis/ directory not found at {FLUX_DIR}")
        sys.exit(1)

    keys = load_keys_from_env()
    session = FluxDataSessionLocal()

    try:
        # Show pre-ingestion state
        pre_files = session.query(EnedisFluxFile).count()
        print(f"Pre-ingestion: {pre_files} files in enedis_flux_file")

        print(f"\nIngesting from {FLUX_DIR} (recursive)...")
        counters = ingest_directory(
            FLUX_DIR,
            session,
            keys,
            recursive=True,
        )

        # Report
        r4x_count = session.query(EnedisFluxMesureR4x).count()
        r171_count = session.query(EnedisFluxMesureR171).count()
        r50_count = session.query(EnedisFluxMesureR50).count()
        r151_count = session.query(EnedisFluxMesureR151).count()
        total_files = session.query(EnedisFluxFile).count()
        total_measures = r4x_count + r171_count + r50_count + r151_count

        print(f"\n{'=' * 60}")
        print("REAL DB INGESTION REPORT")
        print(f"{'=' * 60}")
        print(f"Counters: {counters}")
        print(f"Total flux files:  {total_files}")
        print(f"R4x measures:      {r4x_count:>8,}")
        print(f"R171 measures:     {r171_count:>8,}")
        print(f"R50 measures:      {r50_count:>8,}")
        print(f"R151 measures:     {r151_count:>8,}")
        print(f"TOTAL measures:    {total_measures:>8,}")

        # Show any errors
        errors = session.query(EnedisFluxFile).filter_by(status=FluxStatus.ERROR).all()
        if errors:
            print(f"\n{len(errors)} ERROR(S):")
            for e in errors:
                print(f"  {e.filename}: {e.error_message}")

        print(f"{'=' * 60}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
