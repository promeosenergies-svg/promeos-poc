"""Ingest referential snapshots into KB documents."""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.kb.doc_ingest import ingest_referential_snapshots

result = ingest_referential_snapshots()
print(f"Total: {result['total']}")
print(f"Ingested: {result['ingested']}")
print(f"Already ingested: {result['already_ingested']}")
print()
for d in result.get("details", []):
    status = d["status"]
    doc_id = d["doc_id"]
    extra = f" ({d.get('nb_chunks', '?')} chunks, {d.get('word_count', '?')} words)" if status == "ingested" else ""
    print(f"  [{status:20s}] {doc_id}{extra}")
