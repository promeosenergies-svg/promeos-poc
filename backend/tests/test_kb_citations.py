"""
PROMEOS KB — Tests for Citations + RuleCards
AC: tables created, insert/query OK, P5 compliance check works.
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.kb.models import KBDatabase
from app.kb.citations import (
    init_citations_schema,
    create_citation,
    get_citation,
    get_citations_by_doc,
    search_citations,
    create_rule_card,
    get_rule_card,
    get_rule_cards,
    add_citation_to_rule_card,
    get_rule_card_stats,
)


@pytest.fixture(scope="module")
def kb_db(tmp_path_factory):
    """Create a temporary KB database with citations schema."""
    tmp_dir = tmp_path_factory.mktemp("kb_test")
    db_path = str(tmp_dir / "test_kb.db")
    db = KBDatabase(db_path=db_path)
    db.connect()
    db.init_schema()
    init_citations_schema(db.conn)

    # Insert a test doc for FK references
    cursor = db.conn.cursor()
    cursor.execute("""
        INSERT INTO kb_docs (doc_id, title, source_type, source_path, content_hash, updated_at)
        VALUES ('test_doc_turpe6', 'TURPE 6 HTA-BT CRE', 'html', '/data/kb/raw/turpe6.html',
                'abc123', datetime('now'))
    """)
    cursor.execute("""
        INSERT INTO kb_docs (doc_id, title, source_type, source_path, content_hash, updated_at)
        VALUES ('test_doc_cta', 'CTA Arrete 2026', 'html', '/data/kb/raw/cta.html',
                'def456', datetime('now'))
    """)
    db.conn.commit()

    # Monkey-patch get_kb_db to return our test DB
    import app.kb.citations as citations_mod

    citations_mod.get_kb_db = lambda: db

    yield db
    db.close()


# ========================================
# Schema tests
# ========================================


def test_citations_table_exists(kb_db):
    """Table kb_citations created."""
    cursor = kb_db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kb_citations'")
    assert cursor.fetchone() is not None


def test_rule_cards_table_exists(kb_db):
    """Table kb_rule_cards created."""
    cursor = kb_db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kb_rule_cards'")
    assert cursor.fetchone() is not None


def test_junction_table_exists(kb_db):
    """Junction table kb_rule_card_citations created."""
    cursor = kb_db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kb_rule_card_citations'")
    assert cursor.fetchone() is not None


def test_doc_manifest_v2_columns(kb_db):
    """Enhanced doc columns added (source_org, doc_type, etc)."""
    cursor = kb_db.conn.cursor()
    cursor.execute("PRAGMA table_info(kb_docs)")
    columns = {row[1] for row in cursor.fetchall()}
    assert "source_org" in columns
    assert "doc_type" in columns
    assert "effective_from" in columns
    assert "effective_to" in columns
    assert "version_tag" in columns


# ========================================
# Citation CRUD tests
# ========================================


def test_create_citation(kb_db):
    """Create a citation and retrieve it."""
    cite = create_citation(
        doc_id="test_doc_turpe6",
        doc_title="TURPE 6 HTA-BT CRE",
        excerpt_text="Le tarif d'utilisation des reseaux publics d'electricite (TURPE) est fixe par la CRE.",
        pointer_section="Article 1",
        pointer_article="Art. L. 341-2",
        confidence="high",
    )
    assert cite["citation_id"].startswith("cite_test_doc_turpe6_")
    assert cite["doc_id"] == "test_doc_turpe6"
    assert cite["confidence"] == "high"
    assert len(cite["excerpt_hash"]) == 16


def test_get_citation(kb_db):
    """Retrieve citation by ID."""
    cite = create_citation(
        doc_id="test_doc_turpe6",
        doc_title="TURPE 6",
        excerpt_text="Composante de gestion annuelle fixe.",
        pointer_section="Section 2",
    )
    retrieved = get_citation(cite["citation_id"])
    assert retrieved is not None
    assert retrieved["excerpt_text"] == "Composante de gestion annuelle fixe."
    assert retrieved["pointer"]["section"] == "Section 2"


def test_get_citation_not_found(kb_db):
    """Non-existent citation returns None."""
    assert get_citation("cite_nonexistent_000000") is None


def test_get_citations_by_doc(kb_db):
    """Get all citations for a document."""
    citations = get_citations_by_doc("test_doc_turpe6")
    assert len(citations) >= 2


def test_search_citations(kb_db):
    """Search citations by text."""
    results = search_citations("TURPE")
    assert len(results) >= 1
    assert any("TURPE" in r["excerpt_text"] for r in results)


def test_citation_upsert_idempotent(kb_db):
    """Same excerpt on same doc produces same citation_id (upsert)."""
    text = "Identique excerpt pour test idempotence."
    cite1 = create_citation(doc_id="test_doc_turpe6", doc_title="T6", excerpt_text=text)
    cite2 = create_citation(doc_id="test_doc_turpe6", doc_title="T6", excerpt_text=text)
    assert cite1["citation_id"] == cite2["citation_id"]


# ========================================
# RuleCard CRUD tests
# ========================================


def test_create_rule_card_with_citations(kb_db):
    """Create a RuleCard linked to citations."""
    # First create citations
    cite1 = create_citation(
        doc_id="test_doc_turpe6",
        doc_title="TURPE 6",
        excerpt_text="Verification arithmetique : somme composantes = total HT.",
    )
    cite2 = create_citation(
        doc_id="test_doc_cta",
        doc_title="CTA 2026",
        excerpt_text="La CTA est assise sur la part fixe hors taxe du TURPE.",
    )

    card = create_rule_card(
        rule_card_id="RULE_ARITH_TOTAL_HT",
        name="Coherence somme composantes vs total HT",
        scope="both",
        category="invoice_structure",
        intent="Verifier que la somme des montants HT des composantes correspond au total HT facture.",
        formula_or_check="SUM(components.amount_ht) == invoice.total_ht (tolerance 0.01 EUR)",
        inputs_needed=["invoice.total_ht", "components[].amount_ht"],
        citation_ids=[cite1["citation_id"], cite2["citation_id"]],
        status="ACTIVE",
    )

    assert card is not None
    assert card["rule_card_id"] == "RULE_ARITH_TOTAL_HT"
    assert card["scope"] == "both"
    assert card["category"] == "invoice_structure"
    assert len(card["citations"]) == 2


def test_get_rule_card(kb_db):
    """Retrieve RuleCard with its citations."""
    card = get_rule_card("RULE_ARITH_TOTAL_HT")
    assert card is not None
    assert card["name"] == "Coherence somme composantes vs total HT"
    assert len(card["citations"]) == 2
    assert card["inputs_needed"] == ["invoice.total_ht", "components[].amount_ht"]


def test_get_rule_card_not_found(kb_db):
    """Non-existent RuleCard returns None."""
    assert get_rule_card("RULE_NONEXISTENT") is None


def test_create_rule_card_no_citations(kb_db):
    """RuleCard without citations (arithmetic rule — non-normative)."""
    card = create_rule_card(
        rule_card_id="RULE_TVA_ARITH",
        name="Verification calcul TVA",
        scope="both",
        category="vat",
        intent="Verifier que TVA = base * taux.",
        formula_or_check="amount_tva == amount_ht * tva_rate (tolerance 0.01 EUR)",
        inputs_needed=["amount_ht", "tva_rate", "amount_tva"],
    )
    assert card is not None
    assert len(card["citations"]) == 0


def test_list_rule_cards_by_scope(kb_db):
    """Filter RuleCards by scope."""
    cards = get_rule_cards(scope="both")
    assert len(cards) >= 2
    for c in cards:
        assert c["scope"] == "both"


def test_list_rule_cards_by_category(kb_db):
    """Filter RuleCards by category."""
    cards = get_rule_cards(category="vat")
    assert len(cards) >= 1
    assert cards[0]["category"] == "vat"


def test_add_citation_to_existing_rule_card(kb_db):
    """Add a citation to an existing rule card."""
    cite = create_citation(
        doc_id="test_doc_turpe6",
        doc_title="TURPE 6",
        excerpt_text="Citation ajoutee apres creation de la RuleCard.",
    )
    ok = add_citation_to_rule_card("RULE_TVA_ARITH", cite["citation_id"])
    assert ok is True

    card = get_rule_card("RULE_TVA_ARITH")
    assert len(card["citations"]) == 1


# ========================================
# Stats / P5 compliance tests
# ========================================


def test_rule_card_stats(kb_db):
    """Stats include P5 compliance indicator."""
    stats = get_rule_card_stats()
    assert stats["total_rule_cards"] >= 2
    assert stats["total_citations"] >= 3
    assert "by_status" in stats
    assert "by_scope" in stats
    assert "p5_compliant" in stats


def test_p5_rules_without_citations_detected(kb_db):
    """P5: create a normative rule without citation — detected."""
    create_rule_card(
        rule_card_id="RULE_ORPHAN_TEST",
        name="Regle orpheline (test P5)",
        scope="elec",
        category="tax",
        intent="Regle sans citation — doit etre detectee.",
        formula_or_check="N/A",
        status="NEEDS_REVIEW",
    )
    stats = get_rule_card_stats()
    assert stats["rules_without_citations"] >= 1
    # P5 not compliant because at least one rule has no citation
    # (the orphan + RULE_TVA_ARITH before we added a citation — but we did add one)
    # At least RULE_ORPHAN_TEST has none
    assert stats["rules_without_citations"] >= 1


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
