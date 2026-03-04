"""
PROMEOS KB - Seed Import CLI
Import YAML items into SQLite database with status awareness.

Usage:
    python backend/scripts/kb_seed_import.py
    python backend/scripts/kb_seed_import.py --include-drafts
    python backend/scripts/kb_seed_import.py --rebuild-index
"""

import sys
import yaml
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.kb.store import KBStore
from app.kb.indexer import KBIndexer


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Import KB YAML items to database")
    parser.add_argument("--include-drafts", action="store_true", help="Also import drafts from docs/kb/drafts/")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild FTS5 index after import")
    args = parser.parse_args()

    store = KBStore()

    # Find YAML files from items/
    items_dir = Path("docs/kb/items")
    yaml_files = list(items_dir.glob("**/*.yaml"))

    draft_files = []
    if args.include_drafts:
        drafts_dir = Path("docs/kb/drafts")
        if drafts_dir.exists():
            draft_files = list(drafts_dir.glob("**/*.yaml"))
            yaml_files.extend(draft_files)

    print(f"[INFO] Found {len(yaml_files)} YAML files ({len(draft_files)} drafts)")

    # Import
    success_count = 0
    error_count = 0
    validated_count = 0
    draft_count = 0

    for yaml_file in yaml_files:
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                item = yaml.safe_load(f)

            # Ensure status is set correctly based on source folder
            path_str = str(yaml_file.resolve())
            if "/drafts/" in path_str or "\\drafts\\" in path_str:
                # Force draft status for items from drafts/ folder
                item["status"] = "draft"
                draft_count += 1
            else:
                # Default to validated for items/ folder
                item.setdefault("status", "validated")
                if item["status"] == "validated":
                    validated_count += 1
                else:
                    draft_count += 1

            if store.upsert_item(item):
                success_count += 1
                status_tag = "[VALIDATED]" if item.get("status") == "validated" else "[DRAFT]"
                print(f"  {status_tag} {item['id']}")
            else:
                error_count += 1
                print(f"  [ERROR] {item['id']} (upsert failed)")

        except Exception as e:
            error_count += 1
            print(f"  [ERROR] {yaml_file.name}: {e}")

    # Rebuild FTS index if requested
    if args.rebuild_index:
        print("\n[INFO] Rebuilding FTS5 index...")
        indexer = KBIndexer()
        result = indexer.rebuild_index()
        print(f"  Indexed: {result['indexed']}, Errors: {len(result['errors'])}")

    # Report
    print(f"\n{'=' * 60}")
    print(f"Import complete:")
    print(f"  [OK]    Success:   {success_count}")
    print(f"  [ERROR] Errors:    {error_count}")
    print(f"  Validated items:   {validated_count}")
    print(f"  Draft items:       {draft_count}")
    print(f"{'=' * 60}")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
