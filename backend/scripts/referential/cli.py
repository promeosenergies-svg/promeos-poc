"""
PROMEOS Referentiel — CLI for managing regulatory sources.

Usage:
    python backend/scripts/referential/cli.py validate
    python backend/scripts/referential/cli.py fetch --since 2024-02-01 --until 2026-02-10
    python backend/scripts/referential/cli.py fetch --dry-run
    python backend/scripts/referential/cli.py build-manifest
    python backend/scripts/referential/cli.py report
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

# Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
WATCHLIST_PATH = BACKEND_DIR / "app" / "referential" / "sources_watchlist_24m.yaml"
SCHEMA_PATH = BACKEND_DIR / "app" / "referential" / "schemas" / "sources_watchlist.schema.json"
INDICES_DIR = BACKEND_DIR / "app" / "referential" / "indices"

# Allow imports
sys.path.insert(0, str(BACKEND_DIR))


def _load_watchlist() -> dict:
    """Load and return the YAML watchlist."""
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_validate(args):
    """Validate the watchlist YAML against rules (no external deps for JSON Schema)."""
    print("=" * 60)
    print("PROMEOS Referentiel — VALIDATE")
    print("=" * 60)

    errors = []
    warnings = []

    # Load YAML
    try:
        data = _load_watchlist()
    except Exception as e:
        print(f"FATAL: Cannot load watchlist: {e}")
        sys.exit(1)

    # Check required top-level keys
    for key in ("version", "window", "allowed_domains", "sources"):
        if key not in data:
            errors.append(f"Missing top-level key: {key}")

    if errors:
        _print_results(errors, warnings)
        sys.exit(1)

    allowed_domains = set(data["allowed_domains"])
    sources = data["sources"]
    ids_seen = set()

    print(f"  Watchlist version: {data['version']}")
    print(f"  Window: {data['window']['start']} -> {data['window']['end']}")
    print(f"  Allowed domains: {', '.join(allowed_domains)}")
    print(f"  Sources: {len(sources)}")
    print()

    for i, src in enumerate(sources):
        sid = src.get("id", f"<missing_id_{i}>")

        # Unique ID
        if sid in ids_seen:
            errors.append(f"Duplicate id: {sid}")
        ids_seen.add(sid)

        # ID format
        if not sid.replace("_", "").replace("0123456789", "").isalpha():
            import re
            if not re.match(r"^[a-z0-9_]+$", sid):
                errors.append(f"{sid}: id must be [a-z0-9_]")

        # Required fields
        for field in ("category", "energy", "authority", "url", "expected_type", "description", "tags"):
            if field not in src:
                errors.append(f"{sid}: missing required field '{field}'")

        # URL checks
        url = src.get("url", "")
        if not url.startswith("https://"):
            errors.append(f"{sid}: URL must be HTTPS: {url}")
        else:
            parsed = urlparse(url)
            domain = parsed.hostname or ""
            # Check domain against whitelist
            domain_ok = any(domain == d or domain.endswith("." + d) for d in allowed_domains)
            if not domain_ok:
                errors.append(f"{sid}: domain '{domain}' not in allowed_domains")

        # Category enum
        if src.get("category") not in ("tarif_reseau", "taxe"):
            errors.append(f"{sid}: invalid category '{src.get('category')}'")

        # Energy enum
        if src.get("energy") not in ("electricite", "gaz", "multi"):
            errors.append(f"{sid}: invalid energy '{src.get('energy')}'")

        # Authority enum
        if src.get("authority") not in ("CRE", "Legifrance", "BOFiP", "impots.gouv"):
            errors.append(f"{sid}: invalid authority '{src.get('authority')}'")

        # Tags non-empty
        if not src.get("tags"):
            errors.append(f"{sid}: tags must be non-empty")

        # Date hint format
        date_hint = src.get("date_hint")
        if date_hint:
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_hint):
                errors.append(f"{sid}: date_hint must be YYYY-MM-DD: {date_hint}")

        # Window check
        window_start = data["window"]["start"]
        window_end = data["window"]["end"]
        if date_hint and not src.get("baseline", False):
            if date_hint < window_start:
                warnings.append(f"{sid}: date_hint {date_hint} before window start {window_start} (not baseline)")

    _print_results(errors, warnings)

    if errors:
        sys.exit(1)
    print("VALIDATE OK")


def cmd_fetch(args):
    """Fetch sources from the watchlist."""
    print("=" * 60)
    print("PROMEOS Referentiel — FETCH")
    print("=" * 60)

    from scripts.referential.fetch_sources import fetch_all

    data = _load_watchlist()
    sources = data["sources"]

    print(f"  Sources: {len(sources)}")
    print(f"  Since: {args.since}")
    print(f"  Until: {args.until}")
    print(f"  Dry run: {args.dry_run}")
    print()

    results = fetch_all(
        sources,
        since=args.since,
        until=args.until,
        dry_run=args.dry_run,
    )

    # Summary
    ok = sum(1 for r in results if r["status"] == "ok")
    errors = sum(1 for r in results if r["status"] == "error")
    skipped = sum(1 for r in results if r["status"].startswith("skipped"))
    dry_ok = sum(1 for r in results if r["status"] == "dry_run_ok")

    print()
    print(f"  Results: {ok} ok, {errors} errors, {skipped} skipped, {dry_ok} dry-run")

    if errors > 0:
        print()
        print("  ERRORS:")
        for r in results:
            if r["status"] == "error":
                print(f"    {r['source_id']}: {r.get('error')}")

    # Compute success rate (excluding skipped)
    fetched = ok + errors
    if fetched > 0:
        rate = ok / fetched * 100
        print(f"\n  Success rate: {rate:.0f}% ({ok}/{fetched})")

    if errors > 0 and not args.dry_run:
        sys.exit(1)


def cmd_build_manifest(args):
    """Build the manifest from snapshots."""
    print("=" * 60)
    print("PROMEOS Referentiel — BUILD MANIFEST")
    print("=" * 60)

    from scripts.referential.build_manifest import build_manifest, write_manifest, build_sqlite_index

    data = _load_watchlist()
    window_start = data["window"]["start"]
    window_end = data["window"]["end"]

    manifest = build_manifest(window_start=window_start, window_end=window_end)
    out_path = write_manifest(manifest)

    stats = manifest["stats"]
    print(f"  Sources in manifest: {stats['total_sources']}")
    print(f"  Total snapshots: {stats['total_snapshots']}")
    print(f"  Sources with changes: {stats['sources_with_changes']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Written to: {out_path}")

    # Build SQLite index
    db_path = build_sqlite_index(manifest)
    print(f"  SQLite index: {db_path}")
    print()
    print("BUILD MANIFEST OK")


def cmd_report(args):
    """Print a summary report."""
    print("=" * 60)
    print("PROMEOS Referentiel — REPORT")
    print("=" * 60)

    manifest_path = INDICES_DIR / "sources_manifest.json"
    if not manifest_path.exists():
        print("  No manifest found. Run 'build-manifest' first.")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stats = manifest["stats"]
    sources = manifest["sources"]

    print(f"  Generated: {manifest['generated_at']}")
    print(f"  Window: {manifest['window']['start']} -> {manifest['window']['end']}")
    print(f"  Total sources: {stats['total_sources']}")
    print(f"  Total snapshots: {stats['total_snapshots']}")
    print()

    # By authority
    by_authority: dict[str, int] = {}
    by_energy: dict[str, int] = {}
    by_category: dict[str, int] = {}

    for sid, data in sources.items():
        auth = data.get("authority", "unknown")
        energy = data.get("energy", "unknown")
        cat = data.get("category", "unknown")
        by_authority[auth] = by_authority.get(auth, 0) + 1
        by_energy[energy] = by_energy.get(energy, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1

    print("  Par autorite:")
    for auth, count in sorted(by_authority.items()):
        print(f"    {auth}: {count}")
    print()
    print("  Par energie:")
    for energy, count in sorted(by_energy.items()):
        print(f"    {energy}: {count}")
    print()
    print("  Par categorie:")
    for cat, count in sorted(by_category.items()):
        print(f"    {cat}: {count}")

    # Changes detected
    changed = [sid for sid, data in sources.items() if data.get("has_content_changes")]
    if changed:
        print(f"\n  Changements detectes ({len(changed)}):")
        for sid in changed:
            print(f"    - {sid}")

    # List all sources with latest hash
    print(f"\n  Detail sources ({stats['total_sources']}):")
    print(f"  {'ID':<50} {'Auth':<12} {'Energy':<12} {'Hash (12)':<14}")
    print(f"  {'-'*50} {'-'*12} {'-'*12} {'-'*14}")
    for sid, data in sorted(sources.items()):
        latest = data.get("latest", {})
        h = latest.get("sha256_raw", "")[:12]
        print(f"  {sid:<50} {data.get('authority',''):<12} {data.get('energy',''):<12} {h:<14}")

    print()
    print("REPORT OK")


def _print_results(errors: list, warnings: list):
    """Print validation results."""
    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    WARN: {w}")
    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    ERROR: {e}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="referential-cli",
        description="PROMEOS Referentiel Tarifs & Taxes — CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # validate
    sub.add_parser("validate", help="Validate watchlist YAML")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Fetch sources")
    p_fetch.add_argument("--since", default="2024-02-01", help="Start date (YYYY-MM-DD)")
    p_fetch.add_argument("--until", default="2026-02-10", help="End date (YYYY-MM-DD)")
    p_fetch.add_argument("--dry-run", action="store_true", help="Validate config without downloading")

    # build-manifest
    sub.add_parser("build-manifest", help="Build manifest from snapshots")

    # report
    sub.add_parser("report", help="Print summary report")

    args = parser.parse_args()

    if args.command == "validate":
        cmd_validate(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "build-manifest":
        cmd_build_manifest(args)
    elif args.command == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()
