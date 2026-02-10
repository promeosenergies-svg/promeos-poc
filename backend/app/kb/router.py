"""
PROMEOS KB - FastAPI Router
API endpoints for KB management, search, and apply.
Hardened with input validation, payload limits, and proper error handling.
"""
from fastapi import APIRouter, HTTPException, Query
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
def list_docs():
    """List ingested HTML documents"""
    try:
        cursor = store.db.conn.cursor()
        cursor.execute("SELECT * FROM kb_docs ORDER BY updated_at DESC")
        rows = cursor.fetchall()

        docs = [store._row_to_dict(row) for row in rows]

        return {
            "docs": docs,
            "total": len(docs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docs error: {str(e)[:200]}")


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


# Export router
__all__ = ["router"]
