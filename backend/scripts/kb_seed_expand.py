"""
PROMEOS KB - Seed Expand CLI
Incrementally add new KB items from seed packs without overwriting existing validated items.

Usage:
    python backend/scripts/kb_seed_expand.py --pack v1_base
    python backend/scripts/kb_seed_expand.py --pack v1_base --dry-run
    python backend/scripts/kb_seed_expand.py --list-packs

Rules:
    - Never overwrite a validated item with a draft
    - Only add items that don't already exist (by ID)
    - Report what was added/skipped
"""
import sys
import yaml
import shutil
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent.parent
SEED_PACKS_DIR = PROJECT_ROOT / "docs" / "kb" / "seed_packs"
ITEMS_DIR = PROJECT_ROOT / "docs" / "kb" / "items"
DRAFTS_DIR = PROJECT_ROOT / "docs" / "kb" / "drafts"


def list_packs():
    """List available seed packs"""
    if not SEED_PACKS_DIR.exists():
        print("[INFO] No seed_packs directory found")
        return []

    packs = []
    for pack_dir in sorted(SEED_PACKS_DIR.iterdir()):
        if pack_dir.is_dir():
            manifest_path = pack_dir / "manifest.yaml"
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = yaml.safe_load(f)
                packs.append({
                    "pack_id": manifest.get("pack_id", pack_dir.name),
                    "version": manifest.get("version", "?"),
                    "description": manifest.get("description", ""),
                    "total_items": manifest.get("stats", {}).get("total_items", len(manifest.get("items", []))),
                    "path": pack_dir
                })
    return packs


def get_existing_item_ids():
    """Get IDs of all items currently in items/ and drafts/"""
    ids = set()
    for yaml_file in ITEMS_DIR.glob("**/*.yaml"):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                item = yaml.safe_load(f)
            ids.add(item.get("id"))
        except Exception:
            pass

    if DRAFTS_DIR.exists():
        for yaml_file in DRAFTS_DIR.glob("**/*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)
                ids.add(item.get("id"))
            except Exception:
                pass

    return ids


def expand_pack(pack_id: str, dry_run: bool = False):
    """Expand a seed pack, adding missing items"""
    pack_dir = SEED_PACKS_DIR / pack_id
    manifest_path = pack_dir / "manifest.yaml"

    if not manifest_path.exists():
        print(f"[ERROR] Manifest not found: {manifest_path}")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    pack_items = manifest.get("items", [])
    existing_ids = get_existing_item_ids()

    print(f"[INFO] Pack '{pack_id}' v{manifest.get('version')}: {len(pack_items)} items")
    print(f"[INFO] Existing KB items: {len(existing_ids)}")

    added = 0
    skipped = 0
    errors = 0

    for pack_item in pack_items:
        item_id = pack_item["id"]
        source_file = PROJECT_ROOT / "docs" / "kb" / pack_item["file"]

        if item_id in existing_ids:
            print(f"  [SKIP] {item_id} (already exists)")
            skipped += 1
            continue

        if not source_file.exists():
            print(f"  [ERROR] {item_id}: source file not found ({pack_item['file']})")
            errors += 1
            continue

        # Determine target based on status
        target_status = pack_item.get("status", "validated")
        if target_status == "validated":
            # Load item to get domain for target path
            with open(source_file, "r", encoding="utf-8") as f:
                item = yaml.safe_load(f)
            domain = item.get("domain", "usages")
            target_dir = ITEMS_DIR / domain
        else:
            with open(source_file, "r", encoding="utf-8") as f:
                item = yaml.safe_load(f)
            domain = item.get("domain", "usages")
            target_dir = DRAFTS_DIR / domain

        target_path = target_dir / source_file.name

        if dry_run:
            print(f"  [DRY RUN] Would add {item_id} -> {target_path.relative_to(PROJECT_ROOT)}")
            added += 1
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_path)
        added += 1
        print(f"  [ADDED] {item_id} -> {target_path.relative_to(PROJECT_ROOT)}")

    print(f"\n{'='*60}")
    print(f"Seed expand complete:")
    print(f"  Added:   {added}")
    print(f"  Skipped: {skipped} (already exist)")
    print(f"  Errors:  {errors}")
    print(f"{'='*60}")

    return errors == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Expand KB from seed packs")
    parser.add_argument("--pack", help="Seed pack ID to expand")
    parser.add_argument("--list-packs", action="store_true", help="List available seed packs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without doing it")
    args = parser.parse_args()

    if args.list_packs:
        packs = list_packs()
        if not packs:
            print("[INFO] No seed packs found in docs/kb/seed_packs/")
        else:
            print(f"Available seed packs ({len(packs)}):\n")
            for p in packs:
                print(f"  {p['pack_id']} v{p['version']} ({p['total_items']} items)")
                print(f"    {p['description']}")
                print()
        sys.exit(0)

    if not args.pack:
        print("[ERROR] Specify --pack <pack_id> or --list-packs")
        sys.exit(1)

    result = expand_pack(args.pack, dry_run=args.dry_run)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
