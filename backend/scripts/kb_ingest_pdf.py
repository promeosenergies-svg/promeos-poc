"""
PROMEOS KB - PDF Ingestion CLI
Ingest regulatory PDF documents into the Knowledge Base.
Uses pymupdf for text extraction, then feeds into the existing
chunking + FTS5 pipeline (doc_ingest.ingest_document).

Usage:
  # Single file
  python backend/scripts/kb_ingest_pdf.py --input decret_tertiaire.pdf --doc-id decret-tertiaire-2019

  # Directory (all PDFs)
  python backend/scripts/kb_ingest_pdf.py --input docs/kb/sources/ --source-org CRE

  # With metadata
  python backend/scripts/kb_ingest_pdf.py --input arrete.pdf --doc-id arrete-2024 \
      --title "Arrete du 10 avril 2024" --source-org "JORF" --doc-type arrete \
      --published-date 2024-04-10
"""
import sys
import os
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.kb.doc_ingest import ingest_document


def _slugify(name: str) -> str:
    """Generate a doc_id from a filename."""
    slug = name.lower().replace(" ", "-").replace("_", "-")
    # Remove accents (basic)
    for a, b in [("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("â", "a"),
                 ("ô", "o"), ("û", "u"), ("ù", "u"), ("î", "i"), ("ï", "i"),
                 ("ç", "c")]:
        slug = slug.replace(a, b)
    # Keep only alphanumeric + hyphens
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
    # Collapse multiple hyphens
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def ingest_single(
    file_path: Path,
    doc_id: str,
    title: str | None = None,
    source_org: str = "unknown",
    doc_type: str = "reglementaire",
    published_date: str | None = None,
) -> dict:
    """Ingest a single PDF file."""
    if not title:
        title = file_path.stem.replace("_", " ").replace("-", " ").title()

    result = ingest_document(
        doc_id=doc_id,
        title=title,
        file_path=str(file_path),
        source_org=source_org,
        doc_type=doc_type,
        published_date=published_date,
        notes=f"Ingested from PDF: {file_path.name}",
    )
    return result


def ingest_directory(
    dir_path: Path,
    source_org: str = "unknown",
    doc_type: str = "reglementaire",
) -> list[dict]:
    """Ingest all PDFs in a directory."""
    pdf_files = sorted(dir_path.glob("**/*.pdf"))
    if not pdf_files:
        print(f"  Aucun PDF trouve dans {dir_path}")
        return []

    results = []
    for pdf in pdf_files:
        doc_id = _slugify(pdf.stem)
        print(f"  [{len(results)+1}/{len(pdf_files)}] {pdf.name} -> {doc_id}")
        result = ingest_single(pdf, doc_id=doc_id, source_org=source_org, doc_type=doc_type)
        results.append(result)
        status = result.get("status", "?")
        chunks = result.get("nb_chunks", 0)
        words = result.get("word_count", 0)
        if status == "ingested":
            print(f"         OK  {chunks} chunks, {words} mots")
        elif status == "already_ingested":
            print(f"         SKIP  deja ingere (meme hash)")
        else:
            print(f"         {status}: {result.get('message', '')}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Ingerer des PDF reglementaires dans la KB PROMEOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/kb_ingest_pdf.py --input decret.pdf --doc-id decret-2019
  python scripts/kb_ingest_pdf.py --input docs/kb/sources/ --source-org CRE
  python scripts/kb_ingest_pdf.py --input arrete.pdf --doc-id arr-2024 --title "Arrete 2024" --doc-type arrete
        """,
    )
    parser.add_argument("--input", required=True, help="Chemin vers un fichier PDF ou un dossier")
    parser.add_argument("--doc-id", help="ID unique du document (auto-genere si dossier)")
    parser.add_argument("--title", help="Titre du document (auto-detecte si absent)")
    parser.add_argument("--source-org", default="unknown", help="Organisation source (CRE, JORF, ADEME...)")
    parser.add_argument("--doc-type", default="reglementaire", help="Type de document (reglementaire, deliberation, arrete, guide)")
    parser.add_argument("--published-date", help="Date de publication (YYYY-MM-DD)")

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Erreur: '{args.input}' n'existe pas")
        sys.exit(1)

    print()
    print("=" * 60)
    print("PROMEOS KB — Ingestion PDF")
    print("=" * 60)

    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            print(f"Erreur: '{input_path.name}' n'est pas un PDF")
            sys.exit(1)

        doc_id = args.doc_id or _slugify(input_path.stem)
        print(f"Fichier:  {input_path.name}")
        print(f"Doc ID:   {doc_id}")
        print()

        result = ingest_single(
            input_path,
            doc_id=doc_id,
            title=args.title,
            source_org=args.source_org,
            doc_type=args.doc_type,
            published_date=args.published_date,
        )

        print(f"Statut:      {result['status']}")
        if result["status"] == "ingested":
            print(f"Chunks:      {result['nb_chunks']}")
            print(f"Mots:        {result['word_count']}")
            print(f"Hash:        {result['content_hash'][:16]}...")
            print(f"Normalise:   {result.get('normalized_path', '-')}")
        elif result["status"] == "already_ingested":
            print("Document deja ingere avec le meme contenu (hash identique)")
        else:
            print(f"Message: {result.get('message', '-')}")

    elif input_path.is_dir():
        print(f"Dossier:     {input_path}")
        print(f"Source org:  {args.source_org}")
        print(f"Doc type:    {args.doc_type}")
        print()

        results = ingest_directory(input_path, source_org=args.source_org, doc_type=args.doc_type)

        ingested = sum(1 for r in results if r["status"] == "ingested")
        skipped = sum(1 for r in results if r["status"] == "already_ingested")
        errors = sum(1 for r in results if r["status"] not in ("ingested", "already_ingested"))
        total_chunks = sum(r.get("nb_chunks", 0) for r in results if r["status"] == "ingested")
        total_words = sum(r.get("word_count", 0) for r in results if r["status"] == "ingested")

        print()
        print(f"Total PDF:   {len(results)}")
        print(f"Ingeres:     {ingested} ({total_chunks} chunks, {total_words} mots)")
        print(f"Deja en KB:  {skipped}")
        if errors:
            print(f"Erreurs:     {errors}")

    print()
    print("=" * 60)
    print("Ingestion terminee.")
    print()
    print("Prochaines etapes:")
    print("  1. Verifier les chunks: python scripts/kb_build_index.py")
    print("  2. Rechercher: python -c \"from app.kb.doc_ingest import search_doc_chunks; print(search_doc_chunks('decret'))\"")
    print("  3. Creer des KB items YAML a partir des chunks: docs/kb/drafts/")
    print()


if __name__ == "__main__":
    main()
