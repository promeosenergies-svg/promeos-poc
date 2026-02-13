"""
PROMEOS KB - Batch HTML Ingestion
Ingere tous les fichiers HTML d'un dossier via le pipeline KB existant.

Usage: python backend/scripts/kb_ingest_batch.py --input-dir <path>
"""
import sys
import os
import re
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.kb.ingest_html import HTMLIngestionPipeline


# Mapping: filename pattern → (doc_id, title)
FILE_MAP = {
    "decret_bacs_promeos_complet": ("BACS_COMPLET", "Decret BACS - Synthese PROMEOS complete"),
    "synthese_decret_tertiaire_PROMEOS": ("DT_SYNTHESE", "Decret Tertiaire - Synthese PROMEOS"),
    "LOI APER": ("LOI_APER", "Loi APER - Acceleration Production Energies Renouvelables"),
    "cret BACS": ("BACS_SEUILS", "Decret BACS - Seuils, dates, exemptions"),
    "cret tertiaire": ("DT_OPERAT_2026", "Decret Tertiaire / OPERAT - Obligations 2026"),
    "glementation PROMEOS": ("REGL_PROMEOS", "Reglementation PROMEOS - Vue d'ensemble"),
    "ANALYSE MARCH": ("MARCHE_ENERGIE_2025", "Analyse marche energie France-Europe 2025"),
    "ANALYSE STRATEGIQUE": ("STRATEGIE_NEBCO", "Analyse strategique NEBCO"),
    "Autoconsommation Collective": ("ACC_FRANCE", "Autoconsommation Collective en France"),
    "Flexibilit": ("FLEX_EFFACEMENT", "Flexibilite et Effacement en France 2025-2026"),
    "Post-ARENH": ("POST_ARENH_2026", "Post-ARENH 2026"),
    "Stockage": ("STOCKAGE_ACC", "Stockage et Autoconsommation Collective"),
    "tat 2025": ("LEVIERS_MARCHE_2025", "Etat 2025, Leviers de Marche et Plan de Simplification"),
    "Veille march": ("VEILLE_MARCHE", "Veille marche energie"),
    "Semaine 52": ("VEILLE_S52_2025", "Semaine 52 2025 - Veille Marche Energie PROMEOS"),
    "21 f": ("ARRETE_ACC_2025", "Arrete 21 fevrier 2025 - ACC 5MW/10MW"),
    "Sans titre": ("MISC_SANS_TITRE", "Document sans titre"),
}


def match_file(filename: str) -> tuple:
    """Match a filename to its (doc_id, title) from FILE_MAP."""
    for pattern, (doc_id, title) in FILE_MAP.items():
        if pattern in filename:
            return doc_id, title
    # Fallback: generate from filename
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', filename.split('.')[0])[:30]
    return clean.upper(), filename.split('.')[0]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch ingest HTML files into KB")
    parser.add_argument("--input-dir", required=True, help="Directory containing HTML files")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"Error: '{input_dir}' is not a directory")
        sys.exit(1)

    html_files = sorted(input_dir.glob("*.html"))
    if not html_files:
        print(f"Error: No HTML files found in '{input_dir}'")
        sys.exit(1)

    print(f"Found {len(html_files)} HTML files to ingest\n")

    pipeline = HTMLIngestionPipeline()
    results = []

    for i, html_file in enumerate(html_files, 1):
        doc_id, title = match_file(html_file.name)
        print(f"\n{'='*60}")
        print(f"[{i}/{len(html_files)}] {doc_id}")
        print(f"  File:  {html_file.name}")
        print(f"  Title: {title}")
        print(f"{'='*60}")

        try:
            report = pipeline.ingest(
                input_path=str(html_file),
                doc_id=doc_id,
                title=title,
                updated_at="2026-02-11",
            )
            if "error" in report:
                print(f"  ERROR: {report['error']}")
                results.append((doc_id, title, "ERROR", report['error']))
            else:
                print(f"  OK: {report['nb_sections']} sections, {report['nb_chunks']} chunks, {report['nb_drafts']} drafts")
                results.append((doc_id, title, "OK", report))
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            results.append((doc_id, title, "EXCEPTION", str(e)))

    # Summary
    print(f"\n\n{'='*60}")
    print("BATCH INGESTION SUMMARY")
    print(f"{'='*60}")
    print(f"{'Doc ID':<25} {'Status':<8} {'Sections':>8} {'Chunks':>8} {'Drafts':>8}")
    print("-" * 65)

    total_sections = 0
    total_chunks = 0
    total_drafts = 0
    ok_count = 0

    for doc_id, title, status, data in results:
        if status == "OK":
            ok_count += 1
            s = data['nb_sections']
            c = data['nb_chunks']
            d = data['nb_drafts']
            total_sections += s
            total_chunks += c
            total_drafts += d
            print(f"{doc_id:<25} {'OK':<8} {s:>8} {c:>8} {d:>8}")
        else:
            print(f"{doc_id:<25} {'FAIL':<8} {'':>8} {'':>8} {'':>8}  ({data})")

    print("-" * 65)
    print(f"{'TOTAL':<25} {ok_count}/{len(results):<6} {total_sections:>8} {total_chunks:>8} {total_drafts:>8}")
    print(f"\nDrafts saved to: docs/kb/drafts/")
    print(f"Sources saved to: docs/sources/html/")


if __name__ == "__main__":
    main()
