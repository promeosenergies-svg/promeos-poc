"""
PROMEOS KB — Document Ingestion
Ingest raw documents (HTML/TXT/MD) into KB with manifest, chunking, and FTS indexing.
Supports importing from referential snapshots.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from .models import get_kb_db
from .store import KBStore
from .citations import init_citations_schema

# Paths
DATA_KB_RAW = Path(__file__).resolve().parent.parent.parent / "data" / "kb" / "raw"
DATA_KB_NORMALIZED = Path(__file__).resolve().parent.parent.parent / "data" / "kb" / "normalized"

# Chunk settings
MAX_CHUNK_WORDS = 300
CHUNK_OVERLAP_WORDS = 50


def _sha256(content: str) -> str:
    """SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def kb_doc_allows_deterministic(doc_status: str) -> bool:
    """
    V38 Gating: only validated or decisional docs may feed deterministic rules.
    Draft and review docs are excluded from the apply engine.
    """
    return doc_status in ("validated", "decisional")


def _extract_text_from_html(html: str) -> str:
    """Simple HTML to text (reuse normalize_text if available, fallback to regex)."""
    try:
        from scripts.referential.normalize_text import html_to_markdown
        return html_to_markdown(html)
    except ImportError:
        # Fallback: strip tags with regex
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


def _extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pymupdf. Returns markdown-style text."""
    import pymupdf  # lazy import — only needed for PDF ingestion

    doc = pymupdf.open(file_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"## Page {i + 1}\n\n{text.strip()}")
    doc.close()
    return "\n\n---\n\n".join(pages)


def _chunk_text(text: str, max_words: int = MAX_CHUNK_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> List[Dict[str, Any]]:
    """Split text into overlapping chunks."""
    words = text.split()
    if len(words) <= max_words:
        return [{
            "chunk_index": 0,
            "text": text,
            "word_count": len(words),
        }]

    chunks = []
    i = 0
    idx = 0
    while i < len(words):
        chunk_words = words[i:i + max_words]
        chunk_text = " ".join(chunk_words)
        chunks.append({
            "chunk_index": idx,
            "text": chunk_text,
            "word_count": len(chunk_words),
        })
        i += max_words - overlap
        idx += 1

    return chunks


def ingest_document(
    doc_id: str,
    title: str,
    file_path: str,
    source_org: str = "unknown",
    doc_type: str = "html",
    published_date: Optional[str] = None,
    effective_from: Optional[str] = None,
    effective_to: Optional[str] = None,
    version_tag: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest a raw document into KB.
    Steps:
    1. Read file
    2. Extract text (HTML → text or passthrough)
    3. Compute hash
    4. Chunk text
    5. Store doc metadata + chunks in DB
    6. Save normalized text to data/kb/normalized/

    Returns ingestion result dict.
    """
    db = get_kb_db()
    if not db.conn:
        db.connect()
    init_citations_schema(db.conn)
    store = KBStore()

    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "doc_id": doc_id, "message": f"File not found: {file_path}"}

    # Read file
    raw_content = path.read_text(encoding="utf-8", errors="replace")
    content_hash = _sha256(raw_content)

    # Check if already ingested with same hash
    existing = store.get_doc(doc_id)
    if existing and existing.get("content_hash") == content_hash:
        return {
            "status": "already_ingested",
            "doc_id": doc_id,
            "content_hash": content_hash,
            "message": "Document unchanged (same hash)",
        }

    # Extract text
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        source_type = "pdf"
        extracted_text = _extract_text_from_pdf(str(path))
    elif suffix in (".html", ".htm"):
        source_type = "html"
        extracted_text = _extract_text_from_html(raw_content)
    else:
        source_type = "txt"
        extracted_text = raw_content

    # Chunk
    chunks = _chunk_text(extracted_text)

    # Save normalized text
    DATA_KB_NORMALIZED.mkdir(parents=True, exist_ok=True)
    norm_path = DATA_KB_NORMALIZED / f"{doc_id}.md"
    norm_path.write_text(extracted_text, encoding="utf-8")

    # Store doc metadata
    now = datetime.now(timezone.utc).isoformat()
    doc_record = {
        "doc_id": doc_id,
        "title": title,
        "source_type": source_type,
        "source_path": str(file_path),
        "content_hash": content_hash,
        "nb_sections": 1,
        "nb_chunks": len(chunks),
        "updated_at": now,
        "status": "draft",
        "meta": {
            "source_org": source_org,
            "doc_type": doc_type,
            "published_date": published_date,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "version_tag": version_tag,
            "notes": notes,
            "word_count": sum(c["word_count"] for c in chunks),
        },
    }
    store.upsert_doc(doc_record)

    # Update enhanced manifest columns
    cursor = db.conn.cursor()
    cursor.execute("""
        UPDATE kb_docs SET source_org=?, doc_type=?, published_date=?,
            effective_from=?, effective_to=?, version_tag=?
        WHERE doc_id=?
    """, (source_org, doc_type, published_date, effective_from, effective_to, version_tag, doc_id))

    # Store chunks (delete old ones first)
    cursor.execute("DELETE FROM kb_chunks WHERE doc_id = ?", (doc_id,))
    for chunk in chunks:
        chunk_id = f"{doc_id}_chunk_{chunk['chunk_index']:04d}"
        store.upsert_chunk({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "section_path": None,
            "anchor": None,
            "text": chunk["text"],
            "word_count": chunk["word_count"],
            "chunk_index": chunk["chunk_index"],
        })

    db.conn.commit()

    return {
        "status": "ingested",
        "doc_id": doc_id,
        "title": title,
        "content_hash": content_hash,
        "source_org": source_org,
        "doc_type": doc_type,
        "nb_chunks": len(chunks),
        "word_count": sum(c["word_count"] for c in chunks),
        "normalized_path": str(norm_path),
    }


def ingest_referential_snapshots() -> Dict[str, Any]:
    """
    Ingest all existing referential snapshots as KB documents.
    Each snapshot's raw.html becomes a KB doc.
    """
    snapshots_dir = Path(__file__).resolve().parent.parent / "referential" / "snapshots"
    if not snapshots_dir.exists():
        return {"status": "no_snapshots_dir", "ingested": 0}

    results = []
    for source_dir in sorted(snapshots_dir.iterdir()):
        if not source_dir.is_dir():
            continue

        # Find latest snapshot date
        date_dirs = sorted([d for d in source_dir.iterdir() if d.is_dir()])
        if not date_dirs:
            continue

        latest = date_dirs[-1]
        raw_html = latest / "raw.html"
        metadata_json = latest / "metadata.json"

        if not raw_html.exists():
            continue

        # Read metadata
        meta = {}
        if metadata_json.exists():
            meta = json.loads(metadata_json.read_text(encoding="utf-8"))

        doc_id = source_dir.name
        title = meta.get("title", doc_id)
        source_org = meta.get("authority", "unknown")

        result = ingest_document(
            doc_id=doc_id,
            title=title,
            file_path=str(raw_html),
            source_org=source_org,
            doc_type="deliberation" if "cre" in doc_id else "arrete",
            published_date=meta.get("fetched_at_utc", "")[:10],
            effective_from=meta.get("fetched_at_utc", "")[:10],
            notes=f"Auto-ingested from referential snapshot {latest.name}",
        )
        results.append(result)

    ingested = sum(1 for r in results if r["status"] == "ingested")
    already = sum(1 for r in results if r["status"] == "already_ingested")

    return {
        "status": "ok",
        "total": len(results),
        "ingested": ingested,
        "already_ingested": already,
        "details": results,
    }


def search_doc_chunks(query: str, doc_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search document chunks by text (LIKE match on chunks).
    Returns chunks with doc metadata for citation creation.
    """
    db = get_kb_db()
    cursor = db.conn.cursor()

    if doc_id:
        cursor.execute("""
            SELECT c.*, d.title as doc_title, d.source_org, d.doc_type
            FROM kb_chunks c
            JOIN kb_docs d ON c.doc_id = d.doc_id
            WHERE c.doc_id = ? AND c.text LIKE ?
            ORDER BY c.chunk_index
            LIMIT ?
        """, (doc_id, f"%{query}%", limit))
    else:
        cursor.execute("""
            SELECT c.*, d.title as doc_title, d.source_org, d.doc_type
            FROM kb_chunks c
            JOIN kb_docs d ON c.doc_id = d.doc_id
            WHERE c.text LIKE ?
            ORDER BY d.doc_id, c.chunk_index
            LIMIT ?
        """, (f"%{query}%", limit))

    results = []
    for row in cursor.fetchall():
        r = dict(row)
        results.append({
            "chunk_id": r["chunk_id"],
            "doc_id": r["doc_id"],
            "doc_title": r.get("doc_title", ""),
            "source_org": r.get("source_org", ""),
            "doc_type": r.get("doc_type", ""),
            "section_path": r.get("section_path"),
            "text": r["text"],
            "word_count": r.get("word_count", 0),
            "chunk_index": r.get("chunk_index", 0),
        })

    return results
