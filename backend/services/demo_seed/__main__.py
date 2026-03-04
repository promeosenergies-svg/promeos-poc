"""
PROMEOS - Demo Seed CLI
Usage: python -m services.demo_seed --pack helios --size S [--reset] [--seed 42]
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import SessionLocal
from .orchestrator import SeedOrchestrator
from .packs import list_packs


def main():
    parser = argparse.ArgumentParser(description="PROMEOS Demo Seed CLI")
    parser.add_argument(
        "--pack", default="helios", choices=["helios", "tertiaire"], help="Pack to seed (default: helios)"
    )
    parser.add_argument("--size", default="S", choices=["S", "M"], help="Size: S (small) or M (medium)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for deterministic output")
    parser.add_argument("--days", type=int, default=90, help="Lookback days for readings")
    parser.add_argument("--reset", action="store_true", help="Reset all data before seeding")
    parser.add_argument("--list", action="store_true", help="List available packs")
    parser.add_argument("--status", action="store_true", help="Show current data status")

    args = parser.parse_args()

    db = SessionLocal()
    orch = SeedOrchestrator(db)

    if args.list:
        packs = list_packs()
        print("Available packs:")
        for p in packs:
            print(f"  {p['key']:12s} {p['label']} — {p['description']}")
            print(f"               Sizes: {', '.join(p['sizes'])}")
        return

    if args.status:
        status = orch.status()
        print("Current data status:")
        for k, v in status.items():
            print(f"  {k:25s} {v:>8}")
        return

    if args.reset:
        print("Resetting all data...")
        result = orch.reset(mode="hard")
        print(f"Reset complete: {json.dumps(result.get('deleted', {}), indent=2)}")

    print(f"Seeding pack={args.pack} size={args.size} seed={args.seed} days={args.days}...")
    result = orch.seed(pack=args.pack, size=args.size, rng_seed=args.seed, days=args.days)

    if result.get("error"):
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    print(f"\nSeed complete in {result.get('elapsed_s', '?')}s:")
    print(f"  Organisation: {result.get('org_nom')} (id={result.get('org_id')})")
    print(f"  Sites:        {result.get('sites_count')}")
    print(f"  Meters:       {result.get('meters_count')}")
    print(f"  Readings:     {result.get('readings_count')}")
    print(f"  Weather:      {result.get('weather_days')} days")
    print(f"  Compliance:   {result.get('compliance', {}).get('findings_count', 0)} findings")
    print(
        f"  Monitoring:   {result.get('monitoring', {}).get('snapshots_count', 0)} snapshots, "
        f"{result.get('monitoring', {}).get('alerts_count', 0)} alerts"
    )
    print(f"  Billing:      {result.get('billing', {}).get('invoices_count', 0)} invoices")
    print(f"  Actions:      {result.get('actions', {}).get('actions_count', 0)}")
    print(f"  Purchase:     {result.get('purchase', {}).get('scenarios', 0)} scenarios")

    db.close()


if __name__ == "__main__":
    main()
