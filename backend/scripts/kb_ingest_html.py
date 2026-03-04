"""
PROMEOS KB - HTML Ingestion CLI
Usage: python backend/scripts/kb_ingest_html.py --input <path> --doc-id <DOC_ID> [options]
"""

import sys
import os
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.kb.ingest_html import HTMLIngestionPipeline


def main():
    parser = argparse.ArgumentParser(description="Ingest HTML documentation into KB")
    parser.add_argument("--input", required=True, help="Path to HTML file/folder/zip")
    parser.add_argument("--doc-id", required=True, help="Unique document ID")
    parser.add_argument("--title", help="Document title (auto-detect if not provided)")
    parser.add_argument("--updated-at", help="ISO date (YYYY-MM-DD)")
    parser.add_argument("--auto-import", type=bool, default=False, help="Auto-import generated drafts to DB")

    args = parser.parse_args()

    # Validate input path exists
    if not Path(args.input).exists():
        print(f"❌ Error: Input path '{args.input}' does not exist")
        sys.exit(1)

    # Run ingestion pipeline
    pipeline = HTMLIngestionPipeline()

    try:
        report = pipeline.ingest(
            input_path=args.input,
            doc_id=args.doc_id,
            title=args.title,
            updated_at=args.updated_at,
            auto_import=args.auto_import,
        )

        if "error" in report:
            print(f"❌ Error: {report['error']}")
            sys.exit(1)

        # Print report
        print("\n" + "=" * 60)
        print("HTML INGESTION REPORT")
        print("=" * 60)
        print(f"Document ID:    {report['doc_id']}")
        print(f"Title:          {report['title']}")
        print(f"Content Hash:   {report['content_hash']}")
        print(f"Sections:       {report['nb_sections']}")
        print(f"Chunks:         {report['nb_chunks']}")
        print(f"YAML Drafts:    {report['nb_drafts']}")
        print("\nOutput paths:")
        for key, path in report["paths"].items():
            print(f"  {key:12} → {path}")
        print("=" * 60)
        print("\n✅ Ingestion complete!")
        print("\nNext steps:")
        print("  1. Review generated drafts in docs/kb/drafts/")
        print("  2. Upgrade confidence + refine tags/logic")
        print("  3. Run: python backend/scripts/kb_seed_import.py --include-drafts")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
