"""
PROMEOS KB - Indexer (FTS5 full-text search)
Build and rebuild FTS5 index for KB items
"""

import json
from typing import List, Dict, Any
from .models import get_kb_db
from .store import KBStore


class KBIndexer:
    """FTS5 indexer for KB items"""

    def __init__(self):
        self.db = get_kb_db()
        self.store = KBStore()

    def rebuild_index(self) -> Dict[str, Any]:
        """
        Rebuild FTS5 index from kb_items table
        Returns stats about indexing operation
        """
        cursor = self.db.conn.cursor()

        # Clear existing FTS index
        cursor.execute("DELETE FROM kb_fts")

        # Get all items
        cursor.execute("SELECT * FROM kb_items")
        rows = cursor.fetchall()

        indexed_count = 0
        errors = []

        for row in rows:
            try:
                # Parse JSON fields
                tags = json.loads(row["tags_json"]) if row["tags_json"] else {}
                sources = json.loads(row["sources_json"]) if row["sources_json"] else []

                # Flatten tags for search
                tags_text = self._flatten_tags(tags)

                # Extract source labels for search
                sources_text = " ".join([s.get("label", "") for s in sources])

                # Insert into FTS
                cursor.execute(
                    """
                    INSERT INTO kb_fts (id, title, summary, content_md, tags_text, sources_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (row["id"], row["title"], row["summary"], row["content_md"] or "", tags_text, sources_text),
                )

                indexed_count += 1

            except Exception as e:
                errors.append({"id": row["id"], "error": str(e)})

        self.db.conn.commit()

        return {"indexed": indexed_count, "errors": errors, "total_items": len(rows)}

    def search(
        self,
        query: str,
        domain: str = None,
        type_filter: str = None,
        tags: Dict[str, List[str]] = None,
        include_drafts: bool = False,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Full-text search with FTS5 + filters
        Returns ranked results with highlights

        Args:
            include_drafts: If False (default), only validated items returned.
                           If True, drafts are included in search results.
        """
        cursor = self.db.conn.cursor()

        # Build FTS query
        fts_query = query.strip()
        if not fts_query:
            fts_query = "*"  # Match all if empty

        # Base query with FTS5 search
        sql = """
            SELECT
                kb_items.*,
                kb_fts.rank AS score
            FROM kb_fts
            JOIN kb_items ON kb_items.id = kb_fts.id
            WHERE kb_fts MATCH ?
        """
        params = [fts_query]

        # GUARD: exclude drafts by default
        if not include_drafts:
            sql += " AND kb_items.status = 'validated'"

        # Add domain filter
        if domain:
            sql += " AND kb_items.domain = ?"
            params.append(domain)

        # Add type filter
        if type_filter:
            sql += " AND kb_items.type = ?"
            params.append(type_filter)

        # Add tag filters (AND logic across categories)
        if tags:
            for category, values in tags.items():
                if values:
                    # Check if any tag value matches (OR within category)
                    tag_conditions = " OR ".join([f"kb_items.tags_json LIKE ?" for _ in values])
                    sql += f" AND ({tag_conditions})"
                    params.extend([f'%"{val}"%' for val in values])

        # Order by FTS rank + priority
        sql += " ORDER BY kb_items.priority ASC, kb_fts.rank LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # Convert rows to dicts and parse JSON
        results = []
        for row in rows:
            item = self.store._row_to_dict(row)
            item["score"] = row["score"] if "score" in row.keys() else 0
            results.append(item)

        return results

    def _flatten_tags(self, tags: Dict[str, List[str]]) -> str:
        """Flatten tags dict to space-separated string for FTS"""
        parts = []
        for category, values in tags.items():
            if isinstance(values, list):
                parts.extend(values)
            else:
                parts.append(str(values))
        return " ".join(parts)

    def get_index_stats(self) -> Dict[str, Any]:
        """Get FTS index statistics"""
        cursor = self.db.conn.cursor()

        # Count indexed items
        cursor.execute("SELECT COUNT(*) FROM kb_fts")
        indexed_count = cursor.fetchone()[0]

        # Count total items
        cursor.execute("SELECT COUNT(*) FROM kb_items")
        total_count = cursor.fetchone()[0]

        # Check if index is complete
        is_complete = indexed_count == total_count

        return {
            "indexed_items": indexed_count,
            "total_items": total_count,
            "is_complete": is_complete,
            "missing": total_count - indexed_count,
        }
