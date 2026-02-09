"""
PROMEOS Jobs - CLI pour executer le worker
Usage: python -m jobs.run --once|--watch|--drain
"""
import sys
import time
import argparse
from database import SessionLocal
from jobs.worker import process_one


def run_once():
    """Traite un seul job."""
    db = SessionLocal()
    try:
        processed = process_one(db)
        if processed:
            print("✓ Job processed")
        else:
            print("No pending jobs")
    finally:
        db.close()


def run_watch(interval: int = 5):
    """Loop infini qui traite les jobs toutes les `interval` secondes."""
    print(f"Starting worker in watch mode (interval: {interval}s)")
    print("Press Ctrl+C to stop")
    try:
        while True:
            db = SessionLocal()
            try:
                processed = process_one(db)
                if processed:
                    print(f"[{time.strftime('%H:%M:%S')}] Job processed")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
            finally:
                db.close()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nWorker stopped")


def run_drain():
    """Traite tous les jobs en attente jusqu'a ce qu'il n'y en ait plus."""
    print("Draining job queue...")
    db = SessionLocal()
    count = 0
    try:
        while process_one(db):
            count += 1
        print(f"✓ Processed {count} jobs")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PROMEOS Job Worker")
    parser.add_argument("--once", action="store_true", help="Process one job and exit")
    parser.add_argument("--watch", action="store_true", help="Watch mode (loop)")
    parser.add_argument("--drain", action="store_true", help="Drain all pending jobs")
    parser.add_argument("--interval", type=int, default=5, help="Watch interval in seconds")

    args = parser.parse_args()

    if args.once:
        run_once()
    elif args.watch:
        run_watch(args.interval)
    elif args.drain:
        run_drain()
    else:
        parser.print_help()
        sys.exit(1)
