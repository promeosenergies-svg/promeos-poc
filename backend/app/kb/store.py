"""
PROMEOS KB - Store (CRUD operations)
Database operations for KB items, docs, chunks
"""
import json
import sqlite3
from typing import List, Dict, Any, Optional
from .models import get_kb_db


class KBStore:
    """Knowledge Base storage operations"""

    def __init__(self):
        self.db = get_kb_db()

    def upsert_item(self, item: Dict[str, Any]) -> bool:
        """
        Insert or update a KB item
        Returns True if successful
        """
        try:
            cursor = self.db.conn.cursor()

            # Serialize JSON fields
            tags_json = json.dumps(item.get("tags", {}))
            scope_json = json.dumps(item.get("scope", {})) if item.get("scope") else None
            logic_json = json.dumps(item.get("logic", {})) if item.get("logic") else None
            sources_json = json.dumps(item.get("sources", []))

            # Status: default to 'validated' for backward compat
            status = item.get("status", "validated")

            cursor.execute("""
                INSERT INTO kb_items (
                    id, type, domain, title, summary, content_md,
                    tags_json, scope_json, logic_json, sources_json,
                    updated_at, confidence, status, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type=excluded.type,
                    domain=excluded.domain,
                    title=excluded.title,
                    summary=excluded.summary,
                    content_md=excluded.content_md,
                    tags_json=excluded.tags_json,
                    scope_json=excluded.scope_json,
                    logic_json=excluded.logic_json,
                    sources_json=excluded.sources_json,
                    updated_at=excluded.updated_at,
                    confidence=excluded.confidence,
                    status=excluded.status,
                    priority=excluded.priority
            """, (
                item["id"],
                item["type"],
                item["domain"],
                item["title"],
                item["summary"],
                item.get("content_md", ""),
                tags_json,
                scope_json,
                logic_json,
                sources_json,
                item["updated_at"],
                item["confidence"],
                status,
                item.get("priority", 3)
            ))

            self.db.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"Error upserting KB item {item.get('id')}: {e}")
            return False

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get KB item by ID"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM kb_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()

        if row:
            return self._row_to_dict(row)
        return None

    def get_items(
        self,
        domain: Optional[str] = None,
        type_filter: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get KB items with optional filters"""
        cursor = self.db.conn.cursor()

        query = "SELECT * FROM kb_items WHERE 1=1"
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY priority ASC, updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def update_item_status(self, item_id: str, status: str, confidence: Optional[str] = None) -> bool:
        """Update status (and optionally confidence) of a KB item"""
        try:
            cursor = self.db.conn.cursor()
            if confidence:
                cursor.execute(
                    "UPDATE kb_items SET status = ?, confidence = ?, updated_at = datetime('now') WHERE id = ?",
                    (status, confidence, item_id)
                )
            else:
                cursor.execute(
                    "UPDATE kb_items SET status = ?, updated_at = datetime('now') WHERE id = ?",
                    (status, item_id)
                )
            self.db.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating status for {item_id}: {e}")
            return False

    def delete_item(self, item_id: str) -> bool:
        """Delete KB item"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM kb_items WHERE id = ?", (item_id,))
            self.db.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting KB item {item_id}: {e}")
            return False

    def count_items(self, domain: Optional[str] = None, status: Optional[str] = None) -> int:
        """Count KB items"""
        cursor = self.db.conn.cursor()
        query = "SELECT COUNT(*) FROM kb_items WHERE 1=1"
        params = []
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if status:
            query += " AND status = ?"
            params.append(status)
        cursor.execute(query, params)
        return cursor.fetchone()[0]

    def upsert_doc(self, doc: Dict[str, Any]) -> bool:
        """Insert or update HTML doc metadata"""
        try:
            cursor = self.db.conn.cursor()

            meta_json = json.dumps(doc.get("meta", {}))

            status = doc.get("status", "draft")

            cursor.execute("""
                INSERT INTO kb_docs (
                    doc_id, title, source_type, source_path, content_hash,
                    nb_sections, nb_chunks, updated_at, meta_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    title=excluded.title,
                    source_type=excluded.source_type,
                    source_path=excluded.source_path,
                    content_hash=excluded.content_hash,
                    nb_sections=excluded.nb_sections,
                    nb_chunks=excluded.nb_chunks,
                    updated_at=excluded.updated_at,
                    meta_json=excluded.meta_json,
                    status=excluded.status
            """, (
                doc["doc_id"],
                doc["title"],
                doc["source_type"],
                doc["source_path"],
                doc["content_hash"],
                doc.get("nb_sections", 0),
                doc.get("nb_chunks", 0),
                doc["updated_at"],
                meta_json,
                status,
            ))

            self.db.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"Error upserting doc {doc.get('doc_id')}: {e}")
            return False

    def get_doc(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get doc metadata"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM kb_docs WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()

        if row:
            return self._row_to_dict(row)
        return None

    # V38: Memobox lifecycle management

    VALID_DOC_STATUSES = {"draft", "review", "validated", "decisional", "deprecated"}

    def update_doc_status(self, doc_id: str, new_status: str) -> bool:
        """Update lifecycle status of a KB document."""
        if new_status not in self.VALID_DOC_STATUSES:
            return False
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "UPDATE kb_docs SET status = ?, updated_at = datetime('now') WHERE doc_id = ?",
                (new_status, doc_id),
            )
            self.db.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating doc status for {doc_id}: {e}")
            return False

    def get_docs_filtered(
        self,
        status: Optional[str] = None,
        domain: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get KB docs with optional status/domain/text filters."""
        cursor = self.db.conn.cursor()
        query = "SELECT * FROM kb_docs WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if q:
            query += " AND title LIKE ?"
            params.append(f"%{q}%")
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def upsert_chunk(self, chunk: Dict[str, Any]) -> bool:
        """Insert or update a chunk"""
        try:
            cursor = self.db.conn.cursor()

            cursor.execute("""
                INSERT INTO kb_chunks (
                    chunk_id, doc_id, section_path, anchor, text, word_count, chunk_index
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    doc_id=excluded.doc_id,
                    section_path=excluded.section_path,
                    anchor=excluded.anchor,
                    text=excluded.text,
                    word_count=excluded.word_count,
                    chunk_index=excluded.chunk_index
            """, (
                chunk["chunk_id"],
                chunk["doc_id"],
                chunk.get("section_path"),
                chunk.get("anchor"),
                chunk["text"],
                chunk.get("word_count", 0),
                chunk.get("chunk_index", 0)
            ))

            self.db.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"Error upserting chunk {chunk.get('chunk_id')}: {e}")
            return False

    def get_chunks_by_doc(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a doc"""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM kb_chunks WHERE doc_id = ? ORDER BY chunk_index",
            (doc_id,)
        )
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dict and parse JSON fields"""
        d = dict(row)

        # Parse JSON fields if present
        if "tags_json" in d and d["tags_json"]:
            d["tags"] = json.loads(d["tags_json"])
            del d["tags_json"]

        if "scope_json" in d and d["scope_json"]:
            d["scope"] = json.loads(d["scope_json"])
            del d["scope_json"]

        if "logic_json" in d and d["logic_json"]:
            d["logic"] = json.loads(d["logic_json"])
            del d["logic_json"]

        if "sources_json" in d and d["sources_json"]:
            d["sources"] = json.loads(d["sources_json"])
            del d["sources_json"]

        if "meta_json" in d and d["meta_json"]:
            d["meta"] = json.loads(d["meta_json"])
            del d["meta_json"]

        return d

    def get_stats(self) -> Dict[str, Any]:
        """Get KB statistics"""
        cursor = self.db.conn.cursor()

        # Total items
        cursor.execute("SELECT COUNT(*) FROM kb_items")
        total_items = cursor.fetchone()[0]

        # By domain
        cursor.execute("SELECT domain, COUNT(*) FROM kb_items GROUP BY domain")
        by_domain = {row[0]: row[1] for row in cursor.fetchall()}

        # By type
        cursor.execute("SELECT type, COUNT(*) FROM kb_items GROUP BY type")
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # By confidence
        cursor.execute("SELECT confidence, COUNT(*) FROM kb_items GROUP BY confidence")
        by_confidence = {row[0]: row[1] for row in cursor.fetchall()}

        # By status
        cursor.execute("SELECT status, COUNT(*) FROM kb_items GROUP BY status")
        by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Total docs
        cursor.execute("SELECT COUNT(*) FROM kb_docs")
        total_docs = cursor.fetchone()[0]

        # Total chunks
        cursor.execute("SELECT COUNT(*) FROM kb_chunks")
        total_chunks = cursor.fetchone()[0]

        return {
            "total_items": total_items,
            "by_domain": by_domain,
            "by_type": by_type,
            "by_confidence": by_confidence,
            "by_status": by_status,
            "total_docs": total_docs,
            "total_chunks": total_chunks
        }
