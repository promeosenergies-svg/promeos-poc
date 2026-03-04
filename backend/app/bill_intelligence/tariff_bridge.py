"""
PROMEOS Bill Intelligence — Tariff Reference Bridge
Import referential tariff snapshots into KB and create L2-min RuleCards.

This module bridges the referential tarifs (app/referential/snapshots/)
with the KB citation system, enabling shadow billing L2 (component-level).
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent / "referential" / "snapshots"


def _excerpt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _find_latest_snapshot(source_id: str) -> Optional[Path]:
    """Find the most recent snapshot directory for a source_id."""
    source_dir = SNAPSHOTS_DIR / source_id
    if not source_dir.exists():
        return None
    dates = sorted(source_dir.iterdir(), reverse=True)
    return dates[0] if dates else None


def import_tariff_references_to_kb() -> Dict[str, Any]:
    """
    Import TURPE/CTA referential snapshots into KB as documents + citations.
    Creates KBDocuments from extracted.md and citations from key excerpts.
    Returns summary of ingested documents.
    """
    from ..kb.models import get_kb_db
    from ..kb.citations import (
        init_citations_schema,
        create_citation,
        create_rule_card,
    )

    db = get_kb_db()
    if not db.conn:
        db.connect()
    db.init_schema()
    init_citations_schema(db.conn)

    cursor = db.conn.cursor()
    ingested_docs = []
    created_citations = []

    # Target sources for L2-min (TURPE + CTA)
    target_sources = [
        "cre_turpe6_hta_bt_2024_08",
        "cre_turpe6_hta_bt_2025_02",
        "cre_turpe7_hta_bt_decision_2025",
    ]

    for source_id in target_sources:
        snapshot_dir = _find_latest_snapshot(source_id)
        if not snapshot_dir:
            continue

        meta_path = snapshot_dir / "metadata.json"
        md_path = snapshot_dir / "extracted.md"

        if not meta_path.exists() or not md_path.exists():
            continue

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        content = md_path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        doc_id = f"ref_{source_id}"
        doc_title = meta.get("description", source_id)
        now = datetime.now(timezone.utc).isoformat()

        # Upsert KB document
        cursor.execute(
            """
            INSERT INTO kb_docs (doc_id, title, source_type, source_path, content_hash, nb_sections, nb_chunks, updated_at, meta_json)
            VALUES (?, ?, 'md', ?, ?, 1, 1, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                title=excluded.title, content_hash=excluded.content_hash,
                updated_at=excluded.updated_at, meta_json=excluded.meta_json
        """,
            (
                doc_id,
                doc_title,
                str(md_path),
                content_hash,
                now,
                json.dumps(meta, ensure_ascii=False),
            ),
        )
        ingested_docs.append(doc_id)

        # Create citation for this document
        excerpt = content[:500].strip() if content else "Document tarif referentiel"
        cite = create_citation(
            doc_id=doc_id,
            doc_title=doc_title,
            excerpt_text=excerpt,
            pointer_section="grille_tarifaire",
            pointer_page="1",
            confidence="medium",
        )
        created_citations.append(cite["citation_id"])

    db.conn.commit()

    # Create 2 L2-min RuleCards backed by these citations
    rule_cards_created = _create_l2_min_rule_cards(created_citations)

    return {
        "ingested_docs": len(ingested_docs),
        "doc_ids": ingested_docs,
        "citations_created": len(created_citations),
        "citation_ids": created_citations,
        "rule_cards_created": rule_cards_created,
    }


def _create_l2_min_rule_cards(citation_ids: List[str]) -> List[str]:
    """Create 2 L2-min RuleCards with valid citations."""
    from ..kb.citations import create_rule_card

    cards = []

    # RuleCard 1: TURPE composante gestion — verification du montant fixe
    rc1 = create_rule_card(
        rule_card_id="RC_L2_TURPE_GESTION",
        name="TURPE composante de gestion (fixe mensuel)",
        scope="elec",
        category="network",
        intent="Verifier que la composante de gestion TURPE correspond aux grilles CRE en vigueur",
        formula_or_check="turpe_fixe.amount_ht == grille_cre.composante_gestion_mensuel",
        inputs_needed=["turpe_fixe.amount_ht", "puissance_souscrite_kva", "segment_tarifaire"],
        effective_from="2024-08-01",
        status="ACTIVE",
        citation_ids=citation_ids,
        notes="L2-min: verification composante gestion TURPE vs grille CRE. Source: referentiel tarifs.",
    )
    if rc1:
        cards.append(rc1["rule_card_id"])

    # RuleCard 2: CTA — verification du taux
    rc2 = create_rule_card(
        rule_card_id="RC_L2_CTA_TAUX",
        name="CTA taux reglementaire",
        scope="both",
        category="tax",
        intent="Verifier que la CTA est calculee au taux reglementaire en vigueur",
        formula_or_check="cta.amount_ht == part_fixe_acheminement * taux_cta_reglementaire",
        inputs_needed=["cta.amount_ht", "turpe_fixe.amount_ht", "taux_cta"],
        effective_from="2024-01-01",
        status="ACTIVE",
        citation_ids=citation_ids,
        notes="L2-min: verification CTA vs taux reglementaire. Source: referentiel tarifs.",
    )
    if rc2:
        cards.append(rc2["rule_card_id"])

    return cards


def get_l2_rule_card_ids() -> List[str]:
    """Return list of L2 RuleCard IDs that are ACTIVE."""
    try:
        from ..kb.citations import get_active_rule_card_ids

        active = get_active_rule_card_ids()
        return [rid for rid in active if rid.startswith("RC_L2_")]
    except Exception:
        return []
