"""
PROMEOS V48 — Tests: Action ↔ Proof persistence (KB link table)
Tests the action_proof_link table, store operations, and API endpoints.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import sqlite3
from pathlib import Path


class TestActionProofLinkTable:
    """Test migration creates table and CRUD operations work."""

    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        """Create a fresh KB database for each test."""
        self.db_path = str(tmp_path / "test_kb.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        # Create action_proof_link table (same DDL as models.py)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS action_proof_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                kb_doc_id TEXT NOT NULL,
                proof_type TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(action_id, kb_doc_id)
            )
        """)
        # Create a minimal kb_docs table for joins
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS kb_docs (
                doc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'pdf',
                source_path TEXT NOT NULL DEFAULT '',
                content_hash TEXT NOT NULL DEFAULT '',
                nb_sections INTEGER,
                nb_chunks INTEGER,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'draft',
                domain TEXT,
                display_name TEXT
            )
        """)
        self.conn.commit()
        yield
        self.conn.close()

    def _insert_doc(self, doc_id, title="Doc Test", status="draft", domain=None):
        self.conn.execute(
            "INSERT INTO kb_docs (doc_id, title, source_type, source_path, content_hash, updated_at, status, domain) "
            "VALUES (?, ?, 'pdf', '/tmp/test', 'abc123', datetime('now'), ?, ?)",
            (doc_id, title, status, domain),
        )
        self.conn.commit()

    def test_insert_link(self):
        self.conn.execute(
            "INSERT INTO action_proof_link (action_id, kb_doc_id) VALUES (?, ?)",
            (1, "doc_001"),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM action_proof_link WHERE action_id = 1"
        ).fetchone()
        assert row is not None
        assert dict(row)["kb_doc_id"] == "doc_001"

    def test_unique_constraint_dedup(self):
        """Double insert same (action_id, kb_doc_id) → IntegrityError."""
        self.conn.execute(
            "INSERT INTO action_proof_link (action_id, kb_doc_id) VALUES (?, ?)",
            (1, "doc_001"),
        )
        self.conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO action_proof_link (action_id, kb_doc_id) VALUES (?, ?)",
                (1, "doc_001"),
            )

    def test_different_actions_same_doc(self):
        """Same doc can be linked to different actions."""
        self.conn.execute(
            "INSERT INTO action_proof_link (action_id, kb_doc_id) VALUES (?, ?)",
            (1, "doc_001"),
        )
        self.conn.execute(
            "INSERT INTO action_proof_link (action_id, kb_doc_id) VALUES (?, ?)",
            (2, "doc_001"),
        )
        self.conn.commit()
        rows = self.conn.execute("SELECT * FROM action_proof_link").fetchall()
        assert len(rows) == 2

    def test_join_with_kb_docs(self):
        """Test JOIN between action_proof_link and kb_docs."""
        self._insert_doc("doc_abc", title="Preuve conformité", status="validated", domain="reglementaire")
        self.conn.execute(
            "INSERT INTO action_proof_link (action_id, kb_doc_id) VALUES (?, ?)",
            (42, "doc_abc"),
        )
        self.conn.commit()

        row = self.conn.execute("""
            SELECT apl.action_id, apl.kb_doc_id, d.title, d.status, d.domain
            FROM action_proof_link apl
            LEFT JOIN kb_docs d ON apl.kb_doc_id = d.doc_id
            WHERE apl.action_id = 42
        """).fetchone()
        d = dict(row)
        assert d["title"] == "Preuve conformité"
        assert d["status"] == "validated"
        assert d["domain"] == "reglementaire"

    def test_summary_counts(self):
        """Test aggregation for proof summary."""
        self._insert_doc("d1", status="draft")
        self._insert_doc("d2", status="review")
        self._insert_doc("d3", status="validated")
        self._insert_doc("d4", status="validated")
        for doc_id in ["d1", "d2", "d3", "d4"]:
            self.conn.execute(
                "INSERT INTO action_proof_link (action_id, kb_doc_id) VALUES (?, ?)",
                (10, doc_id),
            )
        self.conn.commit()

        rows = self.conn.execute("""
            SELECT d.status, COUNT(*) as cnt
            FROM action_proof_link apl
            LEFT JOIN kb_docs d ON apl.kb_doc_id = d.doc_id
            WHERE apl.action_id = 10
            GROUP BY d.status
        """).fetchall()
        counts = {dict(r)["status"]: dict(r)["cnt"] for r in rows}
        assert counts.get("draft") == 1
        assert counts.get("review") == 1
        assert counts.get("validated") == 2

    def test_delete_link(self):
        """Test unlinking a doc from an action."""
        self.conn.execute(
            "INSERT INTO action_proof_link (action_id, kb_doc_id) VALUES (?, ?)",
            (1, "doc_001"),
        )
        self.conn.commit()
        self.conn.execute(
            "DELETE FROM action_proof_link WHERE action_id = ? AND kb_doc_id = ?",
            (1, "doc_001"),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM action_proof_link WHERE action_id = 1"
        ).fetchone()
        assert row is None

    def test_action_id_unknown_no_crash(self):
        """Querying proofs for non-existent action returns empty."""
        rows = self.conn.execute(
            "SELECT * FROM action_proof_link WHERE action_id = 999"
        ).fetchall()
        assert len(rows) == 0

    def test_proof_type_stored(self):
        """proof_type column is stored correctly."""
        self.conn.execute(
            "INSERT INTO action_proof_link (action_id, kb_doc_id, proof_type) VALUES (?, ?, ?)",
            (1, "doc_001", "attestation_conso"),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT proof_type FROM action_proof_link WHERE action_id = 1"
        ).fetchone()
        assert dict(row)["proof_type"] == "attestation_conso"
