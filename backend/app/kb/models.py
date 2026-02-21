"""
PROMEOS KB - Database Models
SQLite schema for Knowledge Base items, FTS5 index, and HTML docs
"""
import sqlite3
from pathlib import Path
from typing import Optional


class KBDatabase:
    """
    KB Database manager
    Uses SQLite with FTS5 for full-text search
    """

    def __init__(self, db_path: str = "data/kb.db"):
        """Initialize KB database connection"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def init_schema(self):
        """Create tables if they don't exist"""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        # Main KB items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_items (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                domain TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                content_md TEXT,
                tags_json TEXT NOT NULL,
                scope_json TEXT,
                logic_json TEXT,
                sources_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                confidence TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'validated',
                priority INTEGER DEFAULT 3,
                created_at TEXT DEFAULT (datetime('now')),

                CHECK (type IN ('rule', 'knowledge', 'checklist', 'calc')),
                CHECK (domain IN ('reglementaire', 'usages', 'acc', 'facturation', 'flex')),
                CHECK (confidence IN ('high', 'medium', 'low')),
                CHECK (status IN ('draft', 'validated', 'deprecated')),
                CHECK (priority BETWEEN 1 AND 5)
            )
        """)

        # Migration: add status column if missing (existing databases)
        try:
            cursor.execute("SELECT status FROM kb_items LIMIT 1")
        except Exception:
            cursor.execute("ALTER TABLE kb_items ADD COLUMN status TEXT NOT NULL DEFAULT 'validated'")

        # FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
                id UNINDEXED,
                title,
                summary,
                content_md,
                tags_text,
                sources_text,
                tokenize = 'porter unicode61'
            )
        """)

        # HTML documents table (for ingested docs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_docs (
                doc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                nb_sections INTEGER,
                nb_chunks INTEGER,
                updated_at TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                meta_json TEXT,

                CHECK (source_type IN ('html', 'pdf', 'md', 'txt'))
            )
        """)

        # HTML chunks table (optional, for sourcing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                section_path TEXT,
                anchor TEXT,
                text TEXT NOT NULL,
                word_count INTEGER,
                chunk_index INTEGER,

                FOREIGN KEY (doc_id) REFERENCES kb_docs(doc_id) ON DELETE CASCADE
            )
        """)

        # V38: Memobox lifecycle + domain columns for kb_docs
        # V40.1: display_name — human-friendly label for generated docs
        for col_name, col_def in [
            ("status", "TEXT DEFAULT 'draft'"),
            ("domain", "TEXT"),
            ("used_by_modules", "TEXT"),
            ("display_name", "TEXT"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE kb_docs ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass  # column already exists

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_items_domain ON kb_items(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_items_type ON kb_items(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_items_confidence ON kb_items(confidence)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_items_priority ON kb_items(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_items_status ON kb_items(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc ON kb_chunks(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_docs_status ON kb_docs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_docs_domain ON kb_docs(domain)")

        self.conn.commit()
        return True

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


# Singleton instance
_db = None


def get_kb_db() -> KBDatabase:
    """Get or create KB database singleton"""
    global _db
    if _db is None:
        _db = KBDatabase()
        _db.connect()
        _db.init_schema()
    return _db
