"""Decrypt Enedis SGE files and save XML to flux_enedis/decrypted_xml/.

Organizes output by flux type for easy manual inspection.

Usage:
    cd promeos-poc/backend
    python -m data_ingestion.enedis.scripts.decrypt_samples [--all | --first N]

Options:
    --all       Decrypt all files (default)
    --first N   Decrypt only the first N files per flux type
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from data_ingestion.enedis.decrypt import (
    classify_flux,
    decrypt_file,
    load_keys_from_env,
    SKIP_FLUX_TYPES,
)
from data_ingestion.enedis.enums import FluxType

# flux_enedis/ lives at the Promeos/ root level (parents[5] = .../Promeos/)
FLUX_DIR = Path(__file__).resolve().parents[5] / "flux_enedis"
OUTPUT_DIR = FLUX_DIR / "decrypted_xml"

FLUX_SOURCES = [
    ("R4H", "C1-C4", "*_R4H_CDC_*.zip"),
    ("R4M", "C1-C4", "*_R4M_CDC_*.zip"),
    ("R4Q", "C1-C4", "*_R4Q_CDC_*.zip"),
    ("R171", "C1-C4", "*R171*.zip"),
    ("R50", "C5", "*R50*.zip"),
    ("R151", "C5", "*R151*.zip"),
]


def main():
    parser = argparse.ArgumentParser(description="Decrypt Enedis SGE files to XML")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", default=True, help="Decrypt all files (default)")
    group.add_argument("--first", type=int, metavar="N", help="Decrypt first N files per flux type")
    args = parser.parse_args()

    if not FLUX_DIR.is_dir():
        print(f"ERROR: flux_enedis/ directory not found at {FLUX_DIR}")
        sys.exit(1)

    if not os.environ.get("KEY_1"):
        print("ERROR: KEY_1 env var not set. Check backend/.env")
        sys.exit(1)

    keys = load_keys_from_env()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_files = 0
    total_bytes = 0
    errors = []

    for flux_name, subdir, pattern in FLUX_SOURCES:
        flux_out = OUTPUT_DIR / flux_name
        flux_out.mkdir(exist_ok=True)

        files = sorted((FLUX_DIR / subdir).glob(pattern))
        if args.first:
            files = files[:args.first]

        print(f"\n{flux_name}: {len(files)} file(s)")

        for f in files:
            out_path = flux_out / (f.stem + ".xml")
            if out_path.exists():
                print(f"  SKIP {f.name} (already decrypted)")
                continue

            try:
                xml_bytes = decrypt_file(f, keys)
                out_path.write_bytes(xml_bytes)
                size = len(xml_bytes)
                total_bytes += size
                total_files += 1
                print(f"  OK   {f.name} -> {size:,} bytes")
            except Exception as e:
                errors.append((f.name, str(e)))
                print(f"  ERR  {f.name}: {e}")

    print(f"\n{'='*60}")
    print(f"Decrypted {total_files} files ({total_bytes:,} bytes total)")
    print(f"Output: {OUTPUT_DIR}")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for name, msg in errors:
            print(f"  {name}: {msg}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
