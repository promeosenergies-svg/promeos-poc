"""
PROMEOS KB - FastAPI Router
API endpoints for KB management, search, and apply.
Hardened with input validation, payload limits, and proper error handling.
"""
import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any

from .store import KBStore
from .indexer import KBIndexer
from .service import KBService

# --- Constants ---
MAX_SEARCH_QUERY_LENGTH = 500
MAX_SITE_CONTEXT_KEYS = 100
MAX_SEARCH_LIMIT = 100
MAX_LIST_LIMIT = 1000
VALID_STATUSES = {"draft", "validated", "deprecated"}
VALID_DOMAINS = {"reglementaire", "usages", "acc", "facturation", "flex"}
VALID_TYPES = {"rule", "knowledge", "checklist", "calc"}

# V38: Memobox lifecycle
VALID_DOC_STATUSES = {"draft", "review", "validated", "decisional", "deprecated"}
DOC_TRANSITION_RULES = {
    "draft": {"review"},
    "review": {"validated", "draft"},
    "validated": {"decisional", "deprecated"},
    "decisional": {"deprecated"},
    "deprecated": set(),
}
MAX_UPLOAD_SIZE_MB = 10
VALID_UPLOAD_SUFFIXES = {".pdf", ".html", ".htm", ".md", ".txt"}


# Pydantic models with validation
class SearchRequest(BaseModel):
    q: str
    domain: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[Dict[str, List[str]]] = None
    include_drafts: bool = False
    limit: int = 20

    @field_validator("q")
    @classmethod
    def validate_query(cls, v):
        if len(v) > MAX_SEARCH_QUERY_LENGTH:
            raise ValueError(f"Query too long (max {MAX_SEARCH_QUERY_LENGTH} chars)")
        return v.strip()

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if v < 1 or v > MAX_SEARCH_LIMIT:
            raise ValueError(f"Limit must be 1-{MAX_SEARCH_LIMIT}")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if v is not None and v not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain '{v}' (allowed: {VALID_DOMAINS})")
        return v


class ApplyRequest(BaseModel):
    site_context: Dict[str, Any]
    domain: Optional[str] = None
    allow_drafts: bool = False  # HARD RULE: False by default

    @field_validator("site_context")
    @classmethod
    def validate_context(cls, v):
        if len(v) > MAX_SITE_CONTEXT_KEYS:
            raise ValueError(f"site_context too large (max {MAX_SITE_CONTEXT_KEYS} keys)")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if v is not None and v not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain '{v}' (allowed: {VALID_DOMAINS})")
        return v


# Create router
router = APIRouter(prefix="/api/kb", tags=["Knowledge Base"])

# Singleton services
store = KBStore()
indexer = KBIndexer()
service = KBService()


@router.get("/ping")
def kb_ping():
    """Health check for KB FTS5 engine."""
    return {"ok": True, "engine": "kb_fts5"}


@router.get("/items")
def list_items(
    domain: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="Filter by status: draft|validated|deprecated"),
    include_drafts: bool = Query(False, description="Include draft items (default: False, only validated)"),
    limit: int = Query(100, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(0, ge=0)
):
    """
    List KB items with optional filters.
    By default, only validated items are returned.
    """
    # Validate status parameter
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status '{status}' (allowed: {VALID_STATUSES})")

    # Validate domain parameter
    if domain and domain not in VALID_DOMAINS:
        raise HTTPException(status_code=400, detail=f"Invalid domain '{domain}' (allowed: {VALID_DOMAINS})")

    # Validate type parameter
    if type and type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type '{type}' (allowed: {VALID_TYPES})")

    try:
        status_filter = status
        if not status_filter and not include_drafts:
            status_filter = "validated"

        items = store.get_items(
            domain=domain,
            type_filter=type,
            status=status_filter,
            limit=limit,
            offset=offset
        )
        total = store.count_items(domain=domain, status=status_filter)

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)[:200]}")


@router.get("/items/{item_id}")
def get_item(item_id: str):
    """Get single KB item by ID"""
    if len(item_id) > 200:
        raise HTTPException(status_code=400, detail="Item ID too long")

    item = store.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"KB item {item_id} not found")
    return item


@router.post("/search")
def search_items(request: SearchRequest):
    """Full-text search KB items with FTS5. Drafts excluded by default."""
    try:
        results = indexer.search(
            query=request.q,
            domain=request.domain,
            type_filter=request.type,
            tags=request.tags,
            include_drafts=request.include_drafts,
            limit=request.limit
        )

        return {
            "query": request.q,
            "results": results,
            "count": len(results),
            "include_drafts": request.include_drafts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)[:200]}")


@router.post("/apply")
def apply_kb(request: ApplyRequest):
    """
    Apply KB items to site_context (deterministic evaluation).
    HARD RULE: allow_drafts=False by default — only validated items used for decisions.
    """
    try:
        result = service.apply(
            site_context=request.site_context,
            domain=request.domain,
            allow_drafts=request.allow_drafts
        )

        # Add guard metadata to response
        result["guards"] = {
            "allow_drafts": request.allow_drafts,
            "mode": "exploration" if request.allow_drafts else "decisional"
        }

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apply error: {str(e)[:200]}")


@router.get("/stats")
def get_stats():
    """Get KB statistics including status breakdown"""
    try:
        kb_stats = store.get_stats()
        index_stats = indexer.get_index_stats()

        return {
            "kb": kb_stats,
            "index": index_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)[:200]}")


@router.get("/docs")
def list_docs(
    status: Optional[str] = Query(None, description="Filter by lifecycle status"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    q: Optional[str] = Query(None, description="Search title"),
):
    """List ingested documents with optional filters."""
    try:
        docs = store.get_docs_filtered(status=status, domain=domain, q=q)
        return {"docs": docs, "total": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docs error: {str(e)[:200]}")


# V38: Memobox upload + lifecycle endpoints

class DocStatusRequest(BaseModel):
    status: str


@router.post("/upload")
async def upload_doc(
    file: UploadFile = File(...),
    title: str = Query(..., description="Titre du document"),
    domain: Optional[str] = Query(None, description="Domaine KB"),
    doc_type: str = Query("pdf", description="Type de document"),
    action_id: Optional[int] = Query(None, description="V48: lier automatiquement à une action"),
):
    """
    Upload a document to the Memobox (KB).
    Accepts PDF, HTML, MD, TXT files up to 10 MB.
    Dedup by SHA256 checksum — identical content returns existing ref.
    """
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux (max {MAX_UPLOAD_SIZE_MB} Mo)",
        )

    suffix = Path(file.filename).suffix.lower() if file.filename else ".txt"
    if suffix not in VALID_UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Type non supporte: {suffix}. Acceptes: {VALID_UPLOAD_SUFFIXES}",
        )

    content_hash = hashlib.sha256(contents).hexdigest()
    doc_id = f"upload_{content_hash[:12]}"

    # Dedup: if same hash already ingested, return existing ref
    existing = store.get_doc(doc_id)
    if existing and existing.get("content_hash") == content_hash:
        resp = {
            "status": "already_exists",
            "doc_id": doc_id,
            "content_hash": content_hash,
            "message": "Document avec contenu identique deja present",
        }
        # V48: still link to action even if doc already exists
        if action_id is not None:
            try:
                link_result = store.link_doc_to_action(action_id, doc_id)
                resp["action_link"] = link_result.get("status")
            except Exception:
                resp["action_link"] = "error"
        return resp

    # Save raw file
    raw_dir = Path(__file__).resolve().parent.parent.parent / "data" / "kb" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    file_path = raw_dir / f"{doc_id}{suffix}"
    file_path.write_bytes(contents)

    # Ingest via existing pipeline
    from .doc_ingest import ingest_document

    result = ingest_document(
        doc_id=doc_id,
        title=title,
        file_path=str(file_path),
        source_org="upload",
        doc_type=doc_type,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Erreur ingestion"))

    # Set domain if provided
    if domain:
        cursor = store.db.conn.cursor()
        cursor.execute("UPDATE kb_docs SET domain = ? WHERE doc_id = ?", (domain, doc_id))
        store.db.conn.commit()

    result["domain"] = domain

    # V48: Auto-link doc to action if action_id provided
    if action_id is not None:
        try:
            link_result = store.link_doc_to_action(action_id, doc_id)
            result["action_link"] = link_result.get("status")
        except Exception:
            result["action_link"] = "error"

    return result


@router.post("/docs/{doc_id}/status")
def change_doc_status(doc_id: str, request: DocStatusRequest):
    """
    Change lifecycle status of a KB document.
    Enforces forward-only transitions: draft->review->validated->decisional.
    """
    if len(doc_id) > 200:
        raise HTTPException(status_code=400, detail="Doc ID trop long")

    doc = store.get_doc(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} introuvable")

    current_status = doc.get("status", "draft")
    new_status = request.status

    if new_status not in VALID_DOC_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Statut invalide: {new_status}. Autorises: {VALID_DOC_STATUSES}",
        )

    allowed = DOC_TRANSITION_RULES.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Transition interdite: {current_status} -> {new_status}. Autorises: {allowed}",
        )

    ok = store.update_doc_status(doc_id, new_status)
    if not ok:
        raise HTTPException(status_code=500, detail="Echec mise a jour statut")

    return {
        "doc_id": doc_id,
        "previous_status": current_status,
        "new_status": new_status,
    }


@router.get("/docs/{doc_id}")
def get_doc(doc_id: str):
    """Get HTML document metadata + chunks"""
    if len(doc_id) > 200:
        raise HTTPException(status_code=400, detail="Doc ID too long")

    doc = store.get_doc(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    chunks = store.get_chunks_by_doc(doc_id)

    return {
        "doc": doc,
        "chunks": chunks,
        "nb_chunks": len(chunks)
    }


# ========================================
# Bill Intelligence KB endpoints (T3-KB → T5-KB)
# ========================================

class IngestRequest(BaseModel):
    doc_id: str
    title: str
    file_path: str
    source_org: str = "unknown"
    doc_type: str = "html"
    published_date: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    version_tag: Optional[str] = None
    notes: Optional[str] = None


class ExtractRuleRequest(BaseModel):
    rule_card_id: str
    name: str
    scope: str  # elec | gas | both
    category: str  # tax | network | invoice_structure | vat | ...
    intent: str
    formula_or_check: str
    inputs_needed: List[str] = []
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    citation_ids: List[str] = []
    status: str = "ACTIVE"
    notes: Optional[str] = None


class DocSearchRequest(BaseModel):
    q: str
    doc_id: Optional[str] = None
    limit: int = 10


@router.post("/ingest")
def ingest_doc(request: IngestRequest):
    """
    Ingest a raw document into KB.
    Creates doc manifest + chunks + normalized text.
    """
    try:
        from .doc_ingest import ingest_document
        result = ingest_document(
            doc_id=request.doc_id,
            title=request.title,
            file_path=request.file_path,
            source_org=request.source_org,
            doc_type=request.doc_type,
            published_date=request.published_date,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            version_tag=request.version_tag,
            notes=request.notes,
        )
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest error: {str(e)[:200]}")


@router.post("/ingest-referential")
def ingest_referential():
    """
    Auto-ingest all referential snapshots as KB documents.
    Idempotent: skips already-ingested docs with same hash.
    """
    try:
        from .doc_ingest import ingest_referential_snapshots
        return ingest_referential_snapshots()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest error: {str(e)[:200]}")


@router.post("/reindex")
def reindex_kb():
    """Rebuild FTS5 index for all KB items."""
    try:
        result = indexer.rebuild_index()
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindex error: {str(e)[:200]}")


@router.post("/search-docs")
def search_docs(request: DocSearchRequest):
    """
    Search KB document chunks (full-text).
    Returns candidate chunks for citation creation.
    """
    try:
        from .doc_ingest import search_doc_chunks
        results = search_doc_chunks(
            query=request.q,
            doc_id=request.doc_id,
            limit=request.limit,
        )
        return {
            "query": request.q,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)[:200]}")


@router.post("/extract-rule")
def extract_rule(request: ExtractRuleRequest):
    """
    Create a RuleCard from selected citations.
    P5: normative rules MUST have >= 1 citation.
    """
    try:
        from .citations import create_rule_card
        card = create_rule_card(
            rule_card_id=request.rule_card_id,
            name=request.name,
            scope=request.scope,
            category=request.category,
            intent=request.intent,
            formula_or_check=request.formula_or_check,
            inputs_needed=request.inputs_needed,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            citation_ids=request.citation_ids,
            status=request.status,
            notes=request.notes,
        )
        if not card:
            raise HTTPException(status_code=500, detail="Failed to create RuleCard")
        return card
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extract-rule error: {str(e)[:200]}")


@router.get("/rule-cards")
def list_rule_cards(
    scope: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """List RuleCards with optional filters."""
    try:
        from .citations import get_rule_cards
        cards = get_rule_cards(scope=scope, category=category, status=status, limit=limit)
        return {"rule_cards": cards, "count": len(cards)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule cards error: {str(e)[:200]}")


@router.get("/rule-cards/{rule_card_id}")
def get_rule_card_endpoint(rule_card_id: str):
    """Get a RuleCard by ID with its citations."""
    from .citations import get_rule_card
    card = get_rule_card(rule_card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"RuleCard {rule_card_id} not found")
    return card


@router.get("/citations/{doc_id}")
def list_citations_for_doc(doc_id: str):
    """List all citations for a document."""
    from .citations import get_citations_by_doc
    citations = get_citations_by_doc(doc_id)
    return {"doc_id": doc_id, "citations": citations, "count": len(citations)}


@router.get("/rule-card-stats")
def rule_card_stats_endpoint():
    """Get rule card + citation statistics including P5 compliance."""
    from .citations import get_rule_card_stats
    return get_rule_card_stats()


# Export router
__all__ = ["router"]
