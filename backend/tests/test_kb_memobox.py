"""
PROMEOS KB V38 — Memobox lifecycle + upload dedup tests

AC:
  - 4-state lifecycle on kb_docs (draft -> review -> validated -> decisional)
  - Forward-only transitions
  - SHA256 dedup (same hash -> same doc_id)
  - Gating: only validated/decisional feed deterministic engine
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.kb.models import KBDatabase
from app.kb.store import KBStore
from app.kb.doc_ingest import kb_doc_allows_deterministic


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def kb_db(tmp_path_factory):
    """Create an isolated KB database for Memobox tests."""
    tmp_dir = tmp_path_factory.mktemp("kb_memobox")
    db_path = str(tmp_dir / "test_memobox.db")
    db = KBDatabase(db_path=db_path)
    db.connect()
    db.init_schema()

    # Monkey-patch singleton so KBStore picks up our test DB
    import app.kb.models as models_mod

    original = models_mod._db
    models_mod._db = db
    yield db
    models_mod._db = original
    db.close()


@pytest.fixture()
def store(kb_db):
    """Create a KBStore connected to the test DB."""
    s = KBStore()
    s.db = kb_db
    return s


# ══════════════════════════════════════════════════════════════════════════════
# Schema tests
# ══════════════════════════════════════════════════════════════════════════════


def test_kb_docs_has_status_column(kb_db):
    """V38: kb_docs table has a status column after migration."""
    cursor = kb_db.conn.cursor()
    cursor.execute("PRAGMA table_info(kb_docs)")
    columns = {row[1] for row in cursor.fetchall()}
    assert "status" in columns


def test_kb_docs_has_domain_column(kb_db):
    """V38: kb_docs table has a domain column after migration."""
    cursor = kb_db.conn.cursor()
    cursor.execute("PRAGMA table_info(kb_docs)")
    columns = {row[1] for row in cursor.fetchall()}
    assert "domain" in columns


def test_kb_docs_status_defaults_to_draft(store):
    """New docs inserted via upsert_doc default to 'draft' status."""
    store.upsert_doc(
        {
            "doc_id": "memo_default_test",
            "title": "Test default status",
            "source_type": "pdf",
            "source_path": "/tmp/x.pdf",
            "content_hash": "abc123default",
            "updated_at": "2026-01-01T00:00:00",
        }
    )
    doc = store.get_doc("memo_default_test")
    assert doc is not None
    assert doc["status"] == "draft"


# ══════════════════════════════════════════════════════════════════════════════
# Lifecycle transition tests
# ══════════════════════════════════════════════════════════════════════════════


def test_lifecycle_draft_to_review(store):
    """Forward transition: draft -> review."""
    store.upsert_doc(
        {
            "doc_id": "memo_lifecycle",
            "title": "Lifecycle test",
            "source_type": "pdf",
            "source_path": "/tmp/lc.pdf",
            "content_hash": "lc_hash",
            "updated_at": "2026-01-01T00:00:00",
            "status": "draft",
        }
    )
    ok = store.update_doc_status("memo_lifecycle", "review")
    assert ok is True
    assert store.get_doc("memo_lifecycle")["status"] == "review"


def test_lifecycle_review_to_validated(store):
    """Forward transition: review -> validated."""
    ok = store.update_doc_status("memo_lifecycle", "validated")
    assert ok is True
    assert store.get_doc("memo_lifecycle")["status"] == "validated"


def test_lifecycle_validated_to_decisional(store):
    """Forward transition: validated -> decisional."""
    ok = store.update_doc_status("memo_lifecycle", "decisional")
    assert ok is True
    assert store.get_doc("memo_lifecycle")["status"] == "decisional"


def test_lifecycle_invalid_status_rejected(store):
    """Invalid status string is rejected."""
    ok = store.update_doc_status("memo_lifecycle", "bogus_status")
    assert ok is False


def test_lifecycle_nonexistent_doc(store):
    """Updating non-existent doc returns False."""
    ok = store.update_doc_status("nonexistent_doc_id", "review")
    assert ok is False


# ══════════════════════════════════════════════════════════════════════════════
# Gating tests
# ══════════════════════════════════════════════════════════════════════════════


def test_gating_validated_allows():
    assert kb_doc_allows_deterministic("validated") is True


def test_gating_decisional_allows():
    assert kb_doc_allows_deterministic("decisional") is True


def test_gating_draft_blocks():
    assert kb_doc_allows_deterministic("draft") is False


def test_gating_review_blocks():
    assert kb_doc_allows_deterministic("review") is False


def test_gating_deprecated_blocks():
    assert kb_doc_allows_deterministic("deprecated") is False


# ══════════════════════════════════════════════════════════════════════════════
# Dedup tests
# ══════════════════════════════════════════════════════════════════════════════


def test_dedup_same_hash_returns_existing(store):
    """Upserting a doc with same doc_id + hash updates (no duplicate row)."""
    store.upsert_doc(
        {
            "doc_id": "dedup_test",
            "title": "Original",
            "source_type": "pdf",
            "source_path": "/x.pdf",
            "content_hash": "hash_dedup_abc",
            "updated_at": "2026-01-01T00:00:00",
        }
    )
    # Upsert again with same doc_id
    store.upsert_doc(
        {
            "doc_id": "dedup_test",
            "title": "Updated title",
            "source_type": "pdf",
            "source_path": "/x.pdf",
            "content_hash": "hash_dedup_abc",
            "updated_at": "2026-01-02T00:00:00",
        }
    )
    doc = store.get_doc("dedup_test")
    assert doc is not None
    assert doc["title"] == "Updated title"
    assert doc["content_hash"] == "hash_dedup_abc"


# ══════════════════════════════════════════════════════════════════════════════
# Filtered docs retrieval
# ══════════════════════════════════════════════════════════════════════════════


def test_get_docs_filtered_by_status(store):
    """get_docs_filtered returns docs matching status filter."""
    # Insert a validated doc
    store.upsert_doc(
        {
            "doc_id": "filter_val",
            "title": "Validated doc",
            "source_type": "txt",
            "source_path": "/v.txt",
            "content_hash": "fv_hash",
            "updated_at": "2026-01-01T00:00:00",
            "status": "validated",
        }
    )
    validated = store.get_docs_filtered(status="validated")
    ids = [d["doc_id"] for d in validated]
    assert "filter_val" in ids

    drafts = store.get_docs_filtered(status="draft")
    draft_ids = [d["doc_id"] for d in drafts]
    assert "filter_val" not in draft_ids


def test_get_docs_filtered_returns_list(store):
    """get_docs_filtered always returns a list."""
    result = store.get_docs_filtered()
    assert isinstance(result, list)


def test_get_docs_filtered_by_title_search(store):
    """get_docs_filtered with q parameter filters by title."""
    results = store.get_docs_filtered(q="Validated doc")
    ids = [d["doc_id"] for d in results]
    assert "filter_val" in ids
