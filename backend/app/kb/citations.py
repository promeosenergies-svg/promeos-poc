"""
PROMEOS KB — Citations
Structure de citation obligatoire pour toute regle normative.
Chaque Citation pointe vers un document KB + un pointeur (page/section/article).

Regle P5 : aucune "rule" normative sans au moins 1 Citation.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from .models import get_kb_db


# ========================================
# Schema extension
# ========================================

def init_citations_schema(conn: sqlite3.Connection):
    """Create citations + rule_cards tables if they don't exist."""
    cursor = conn.cursor()

    # Citations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_citations (
            citation_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            doc_title TEXT NOT NULL,
            pointer_page TEXT,
            pointer_section TEXT,
            pointer_article TEXT,
            pointer_table TEXT,
            pointer_line_range TEXT,
            excerpt_text TEXT NOT NULL,
            excerpt_hash TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'medium',
            created_at TEXT DEFAULT (datetime('now')),

            CHECK (confidence IN ('high', 'medium', 'low')),
            CHECK (length(excerpt_text) <= 1000),
            FOREIGN KEY (doc_id) REFERENCES kb_docs(doc_id) ON DELETE CASCADE
        )
    """)

    # Rule Cards table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_rule_cards (
            rule_card_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            scope TEXT NOT NULL,
            category TEXT NOT NULL,
            intent TEXT NOT NULL,
            inputs_needed_json TEXT NOT NULL DEFAULT '[]',
            formula_or_check TEXT NOT NULL,
            effective_from TEXT,
            effective_to TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),

            CHECK (scope IN ('elec', 'gas', 'both')),
            CHECK (category IN (
                'tax', 'network', 'invoice_structure', 'vat',
                'period', 'prorata', 'penalty', 'subscription',
                'consumption', 'capacity', 'reactive', 'other'
            )),
            CHECK (status IN ('ACTIVE', 'NEEDS_REVIEW', 'OUT_OF_SCOPE_POC', 'DEPRECATED'))
        )
    """)

    # Junction table: rule_card ↔ citations (M:N)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_rule_card_citations (
            rule_card_id TEXT NOT NULL,
            citation_id TEXT NOT NULL,
            PRIMARY KEY (rule_card_id, citation_id),
            FOREIGN KEY (rule_card_id) REFERENCES kb_rule_cards(rule_card_id) ON DELETE CASCADE,
            FOREIGN KEY (citation_id) REFERENCES kb_citations(citation_id) ON DELETE CASCADE
        )
    """)

    # Enhanced doc manifest (v2 columns — additive migration)
    for col_def in [
        ("source_org", "TEXT"),
        ("doc_type", "TEXT"),
        ("published_date", "TEXT"),
        ("effective_from", "TEXT"),
        ("effective_to", "TEXT"),
        ("version_tag", "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE kb_docs ADD COLUMN {col_def[0]} {col_def[1]}")
        except sqlite3.OperationalError:
            pass  # column already exists

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_doc ON kb_citations(doc_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_confidence ON kb_citations(confidence)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rule_cards_scope ON kb_rule_cards(scope)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rule_cards_category ON kb_rule_cards(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rule_cards_status ON kb_rule_cards(status)")

    conn.commit()


# ========================================
# Citation CRUD
# ========================================

def _make_excerpt_hash(text: str) -> str:
    """SHA-256 of the excerpt text for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _make_citation_id(doc_id: str, excerpt_hash: str) -> str:
    """Deterministic citation ID from doc + excerpt."""
    return f"cite_{doc_id}_{excerpt_hash}"


def create_citation(
    doc_id: str,
    doc_title: str,
    excerpt_text: str,
    pointer_page: Optional[str] = None,
    pointer_section: Optional[str] = None,
    pointer_article: Optional[str] = None,
    pointer_table: Optional[str] = None,
    pointer_line_range: Optional[str] = None,
    confidence: str = "medium",
) -> Dict[str, Any]:
    """
    Create a citation pointing to a KB document.
    Returns the citation dict with generated ID + hash.
    """
    db = get_kb_db()
    if not db.conn:
        db.connect()

    excerpt_text = excerpt_text.strip()[:1000]
    excerpt_hash = _make_excerpt_hash(excerpt_text)
    citation_id = _make_citation_id(doc_id, excerpt_hash)
    now = datetime.now(timezone.utc).isoformat()

    cursor = db.conn.cursor()
    cursor.execute("""
        INSERT INTO kb_citations (
            citation_id, doc_id, doc_title,
            pointer_page, pointer_section, pointer_article,
            pointer_table, pointer_line_range,
            excerpt_text, excerpt_hash, retrieved_at, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(citation_id) DO UPDATE SET
            doc_title=excluded.doc_title,
            pointer_page=excluded.pointer_page,
            pointer_section=excluded.pointer_section,
            pointer_article=excluded.pointer_article,
            pointer_table=excluded.pointer_table,
            pointer_line_range=excluded.pointer_line_range,
            excerpt_text=excluded.excerpt_text,
            excerpt_hash=excluded.excerpt_hash,
            retrieved_at=excluded.retrieved_at,
            confidence=excluded.confidence
    """, (
        citation_id, doc_id, doc_title,
        pointer_page, pointer_section, pointer_article,
        pointer_table, pointer_line_range,
        excerpt_text, excerpt_hash, now, confidence,
    ))
    db.conn.commit()

    return {
        "citation_id": citation_id,
        "doc_id": doc_id,
        "doc_title": doc_title,
        "pointer": {
            "page": pointer_page,
            "section": pointer_section,
            "article": pointer_article,
            "table": pointer_table,
            "line_range": pointer_line_range,
        },
        "excerpt_text": excerpt_text,
        "excerpt_hash": excerpt_hash,
        "retrieved_at": now,
        "confidence": confidence,
    }


def get_citation(citation_id: str) -> Optional[Dict[str, Any]]:
    """Get a citation by ID."""
    db = get_kb_db()
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM kb_citations WHERE citation_id = ?", (citation_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return _row_to_citation(dict(row))


def get_citations_by_doc(doc_id: str) -> List[Dict[str, Any]]:
    """Get all citations for a document."""
    db = get_kb_db()
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT * FROM kb_citations WHERE doc_id = ? ORDER BY created_at",
        (doc_id,)
    )
    return [_row_to_citation(dict(row)) for row in cursor.fetchall()]


def search_citations(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search citations by excerpt text (LIKE match)."""
    db = get_kb_db()
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT * FROM kb_citations WHERE excerpt_text LIKE ? ORDER BY retrieved_at DESC LIMIT ?",
        (f"%{query}%", limit)
    )
    return [_row_to_citation(dict(row)) for row in cursor.fetchall()]


def _row_to_citation(row: dict) -> Dict[str, Any]:
    """Convert DB row to citation dict."""
    return {
        "citation_id": row["citation_id"],
        "doc_id": row["doc_id"],
        "doc_title": row["doc_title"],
        "pointer": {
            "page": row.get("pointer_page"),
            "section": row.get("pointer_section"),
            "article": row.get("pointer_article"),
            "table": row.get("pointer_table"),
            "line_range": row.get("pointer_line_range"),
        },
        "excerpt_text": row["excerpt_text"],
        "excerpt_hash": row["excerpt_hash"],
        "retrieved_at": row["retrieved_at"],
        "confidence": row["confidence"],
    }


# ========================================
# RuleCard CRUD
# ========================================

def create_rule_card(
    rule_card_id: str,
    name: str,
    scope: str,
    category: str,
    intent: str,
    formula_or_check: str,
    inputs_needed: Optional[List[str]] = None,
    effective_from: Optional[str] = None,
    effective_to: Optional[str] = None,
    citation_ids: Optional[List[str]] = None,
    status: str = "ACTIVE",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a RuleCard linked to citations.
    P5 enforcement: normative rules must have >= 1 citation.
    """
    db = get_kb_db()
    if not db.conn:
        db.connect()

    now = datetime.now(timezone.utc).isoformat()
    inputs_json = json.dumps(inputs_needed or [])

    cursor = db.conn.cursor()
    cursor.execute("""
        INSERT INTO kb_rule_cards (
            rule_card_id, name, scope, category, intent,
            inputs_needed_json, formula_or_check,
            effective_from, effective_to, status, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(rule_card_id) DO UPDATE SET
            name=excluded.name,
            scope=excluded.scope,
            category=excluded.category,
            intent=excluded.intent,
            inputs_needed_json=excluded.inputs_needed_json,
            formula_or_check=excluded.formula_or_check,
            effective_from=excluded.effective_from,
            effective_to=excluded.effective_to,
            status=excluded.status,
            notes=excluded.notes,
            updated_at=excluded.updated_at
    """, (
        rule_card_id, name, scope, category, intent,
        inputs_json, formula_or_check,
        effective_from, effective_to, status, notes, now,
    ))

    # Link citations
    if citation_ids:
        for cid in citation_ids:
            cursor.execute("""
                INSERT OR IGNORE INTO kb_rule_card_citations (rule_card_id, citation_id)
                VALUES (?, ?)
            """, (rule_card_id, cid))

    db.conn.commit()

    return get_rule_card(rule_card_id)


def get_rule_card(rule_card_id: str) -> Optional[Dict[str, Any]]:
    """Get a RuleCard by ID, including its citations."""
    db = get_kb_db()
    cursor = db.conn.cursor()

    cursor.execute("SELECT * FROM kb_rule_cards WHERE rule_card_id = ?", (rule_card_id,))
    row = cursor.fetchone()
    if not row:
        return None

    card = dict(row)
    card["inputs_needed"] = json.loads(card.pop("inputs_needed_json", "[]"))

    # Fetch linked citations
    cursor.execute("""
        SELECT c.* FROM kb_citations c
        JOIN kb_rule_card_citations rc ON c.citation_id = rc.citation_id
        WHERE rc.rule_card_id = ?
        ORDER BY c.retrieved_at
    """, (rule_card_id,))

    card["citations"] = [_row_to_citation(dict(r)) for r in cursor.fetchall()]
    return card


def get_rule_cards(
    scope: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List RuleCards with optional filters."""
    db = get_kb_db()
    cursor = db.conn.cursor()

    query = "SELECT rule_card_id FROM kb_rule_cards WHERE 1=1"
    params = []

    if scope:
        query += " AND scope = ?"
        params.append(scope)
    if category:
        query += " AND category = ?"
        params.append(category)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    ids = [row[0] for row in cursor.fetchall()]

    return [get_rule_card(rid) for rid in ids]


def add_citation_to_rule_card(rule_card_id: str, citation_id: str) -> bool:
    """Link an existing citation to a rule card."""
    db = get_kb_db()
    cursor = db.conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO kb_rule_card_citations (rule_card_id, citation_id)
            VALUES (?, ?)
        """, (rule_card_id, citation_id))
        db.conn.commit()
        return True
    except sqlite3.Error:
        return False


def validate_citation_proof(citation: Dict[str, Any]) -> bool:
    """
    P5: A citation is valid if it has doc_id, at least one pointer field,
    and a non-empty excerpt_hash.
    """
    if not citation.get("doc_id"):
        return False
    if not citation.get("excerpt_hash"):
        return False
    pointer = citation.get("pointer", {})
    if not any(pointer.get(k) for k in ("page", "section", "article", "table", "line_range")):
        return False
    return True


def enforce_p5_status() -> Dict[str, Any]:
    """
    P5 enforcement: set all normative RuleCards without valid citations
    to NEEDS_REVIEW status. Returns enforcement summary.
    """
    db = get_kb_db()
    if not db.conn:
        db.connect()
    cursor = db.conn.cursor()

    # Find rule cards without any citation
    cursor.execute("""
        SELECT rc.rule_card_id, rc.status FROM kb_rule_cards rc
        WHERE NOT EXISTS (
            SELECT 1 FROM kb_rule_card_citations rcc
            WHERE rcc.rule_card_id = rc.rule_card_id
        ) AND rc.status = 'ACTIVE'
    """)
    uncited = cursor.fetchall()
    downgraded = []

    for row in uncited:
        cursor.execute(
            "UPDATE kb_rule_cards SET status = 'NEEDS_REVIEW', updated_at = ? WHERE rule_card_id = ?",
            (datetime.now(timezone.utc).isoformat(), row[0]),
        )
        downgraded.append(row[0])

    # Also validate existing citations — cards where all citations are invalid
    cursor.execute("""
        SELECT DISTINCT rc.rule_card_id FROM kb_rule_cards rc
        JOIN kb_rule_card_citations rcc ON rc.rule_card_id = rcc.rule_card_id
        WHERE rc.status = 'ACTIVE'
    """)
    for row in cursor.fetchall():
        card = get_rule_card(row[0])
        if card and card.get("citations"):
            all_invalid = all(not validate_citation_proof(c) for c in card["citations"])
            if all_invalid:
                cursor.execute(
                    "UPDATE kb_rule_cards SET status = 'NEEDS_REVIEW', updated_at = ? WHERE rule_card_id = ?",
                    (datetime.now(timezone.utc).isoformat(), row[0]),
                )
                downgraded.append(row[0])

    db.conn.commit()
    return {"downgraded_count": len(downgraded), "downgraded_ids": downgraded}


def get_active_rule_card_ids() -> set:
    """Return set of rule_card_ids with status=ACTIVE (citation-backed)."""
    db = get_kb_db()
    if not db.conn:
        db.connect()
    cursor = db.conn.cursor()

    try:
        cursor.execute("SELECT rule_card_id FROM kb_rule_cards WHERE status = 'ACTIVE'")
        return {row[0] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        return set()


def get_citations_for_rule(rule_card_id: str) -> List[Dict[str, Any]]:
    """Get all valid citations for a rule card."""
    card = get_rule_card(rule_card_id)
    if not card:
        return []
    return [c for c in card.get("citations", []) if validate_citation_proof(c)]


def get_rule_card_stats() -> Dict[str, Any]:
    """Get statistics on rule cards and citations."""
    db = get_kb_db()
    cursor = db.conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM kb_rule_cards")
    total_rules = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM kb_citations")
    total_citations = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM kb_rule_cards GROUP BY status")
    by_status = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT scope, COUNT(*) FROM kb_rule_cards GROUP BY scope")
    by_scope = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT category, COUNT(*) FROM kb_rule_cards GROUP BY category")
    by_category = {row[0]: row[1] for row in cursor.fetchall()}

    # Rules without citations (P5 violation check)
    cursor.execute("""
        SELECT COUNT(*) FROM kb_rule_cards rc
        WHERE NOT EXISTS (
            SELECT 1 FROM kb_rule_card_citations rcc
            WHERE rcc.rule_card_id = rc.rule_card_id
        )
    """)
    rules_without_citations = cursor.fetchone()[0]

    return {
        "total_rule_cards": total_rules,
        "total_citations": total_citations,
        "by_status": by_status,
        "by_scope": by_scope,
        "by_category": by_category,
        "rules_without_citations": rules_without_citations,
        "p5_compliant": rules_without_citations == 0,
    }
