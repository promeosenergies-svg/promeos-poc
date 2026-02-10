"""
PROMEOS KB - Build Index CLI
Rebuild FTS5 full-text search index
Usage: python backend/scripts/kb_build_index.py
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.kb.indexer import KBIndexer
from app.kb.store import KBStore


def main():
    indexer = KBIndexer()
    store = KBStore()

    print("🔨 Rebuilding FTS5 index...")

    # Rebuild
    result = indexer.rebuild_index()

    # Get stats
    stats = store.get_stats()
    index_stats = indexer.get_index_stats()

    # Report
    print(f"\n{'='*60}")
    print("INDEX BUILD COMPLETE")
    print(f"{'='*60}")
    print(f"Items indexed: {result['indexed']}")
    print(f"Errors:        {len(result['errors'])}")
    print(f"Total items:   {result['total_items']}")
    print(f"\nKB Statistics:")
    print(f"  By domain: {stats['by_domain']}")
    print(f"  By type:   {stats['by_type']}")
    print(f"  By confidence: {stats['by_confidence']}")
    print(f"\nIndex status:")
    print(f"  Indexed:   {index_stats['indexed_items']}")
    print(f"  Total:     {index_stats['total_items']}")
    print(f"  Complete:  {index_stats['is_complete']}")
    print(f"{'='*60}")

    if result['errors']:
        print("\n⚠️  Errors encountered:")
        for err in result['errors']:
            print(f"  - {err['id']}: {err['error']}")
        sys.exit(1)
    else:
        print("\n✅ Index build successful!")
        sys.exit(0)


if __name__ == "__main__":
    main()
