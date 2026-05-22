"""M2-6.B.pdf — Génération PDF COMEX (ReportLab).

Phase 1 audit M2-6.B.pdf : WeasyPrint indisponible (Cairo/Pango absent
brew, lib non installée). ReportLab 4.4.10 disponible. Décision Q22=C :
ReportLab seul.

Trace `M3-PDF-WEASYPRINT-MIGRATION` backlog : migration possible vers
HTML→PDF (meilleure fidélité Sol Q20=C) si l'installation Cairo/Pango +
WeasyPrint est faite sur l'environnement pilote.

Contenu (Q21=B summary + table items, Q23=A format full FR strict) :
  1. Header Sol (brun #3d2e1c sur crème #faf6ed) : titre + org + date
  2. Phrase complétude cardinale (cohérente EditorialNarrativeBlock .bis) :
     « N actions sur M portent un impact estimé : Z € »
  3. Synthèse 4 cards : P0/P1 (count + sum €) · Sans responsable · Bloqués · Preuvés
  4. Détail des actions : table N lignes (titre, priorité, état, domaine, impact)
  5. Footer note « Document indicatif, hors éléments non estimés »

Source unique chiffres : `ActionCenterItemRepository.get_summary()` (extension
M2-6.B.backend). Jamais recalculé côté PDF — la doctrine est respectée
côté backend de la même façon que `SG_AC_V4_MONEY_01` la pin côté FE.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from models.v4.action_center_items import ActionCenterItem
from repositories.action_center_item_v4_repository import ActionCenterItemRepository
from utils.format_euros import format_euros_full

logger = logging.getLogger(__name__)

# ── Palette Sol (cohérent maquette Sophie Marin M2-5.12) ─────────────
_SOL_BROWN_DARK = colors.HexColor("#3d2e1c")
_SOL_BROWN_MID = colors.HexColor("#6b5a4a")
_SOL_BROWN_LIGHT = colors.HexColor("#8a7869")
_SOL_CREAM = colors.HexColor("#faf6ed")
_SOL_CREAM_LIGHT = colors.HexColor("#faf8f2")
_SOL_ACCENT = colors.HexColor("#c9a875")


class PdfExportError(Exception):
    """Erreur métier génération PDF."""


def _completude_phrase(summary: dict) -> str:
    """Phrase cardinale cohérente avec EditorialNarrativeBlock M2-6.B.frontend.bis.

    Grammaire FR Académie : 0 et 1 → singulier ; ≥2 → pluriel.
    """
    n_known = int(summary.get("items_with_impact_known") or 0)
    n_total = int(summary.get("items_total") or 0)
    total_eur = format_euros_full(summary.get("sums_eur_total") or 0)

    is_singular = n_known <= 1
    action_word = "action" if is_singular else "actions"
    verb_word = "porte" if is_singular else "portent"

    return f"<b>{n_known}</b> {action_word} sur <b>{n_total}</b> {verb_word} un impact estimé : <b>{total_eur}</b>"


def _build_summary_cards_table(summary: dict) -> Table:
    """Section Synthèse : 4 cards (counts + sum € pour P0/P1)."""
    count_p0 = int(summary.get("count_p0") or 0)
    count_p1 = int(summary.get("count_p1") or 0)
    sums_by_priority = summary.get("sums_eur_by_priority") or {}
    sum_p0_p1 = float(sums_by_priority.get("P0") or 0) + float(sums_by_priority.get("P1") or 0)

    cards = [
        {
            "count": str(count_p0 + count_p1),
            "label": "DÉCISIONS P0/P1",
            "sum_eur": format_euros_full(sum_p0_p1) if sum_p0_p1 > 0 else "",
        },
        {
            "count": str(int(summary.get("count_without_owner") or 0)),
            "label": "SANS RESPONSABLE",
            "sum_eur": "",
        },
        {
            "count": str(int(summary.get("count_at_risk") or 0)),
            "label": "BLOQUÉS",
            "sum_eur": "",
        },
        {
            "count": str(int(summary.get("count_secured") or 0)),
            "label": "PREUVÉS",
            "sum_eur": "",
        },
    ]

    # Chaque card est une mini-table empilée verticalement (count / label / sum).
    card_style = ParagraphStyle(
        "CardStyle",
        fontName="Courier-Bold",
        fontSize=16,
        textColor=_SOL_BROWN_DARK,
        leading=18,
    )
    label_style = ParagraphStyle(
        "LabelStyle",
        fontName="Helvetica",
        fontSize=7,
        textColor=_SOL_BROWN_MID,
        leading=9,
    )
    sum_style = ParagraphStyle(
        "SumStyle",
        fontName="Courier",
        fontSize=9,
        textColor=_SOL_BROWN_MID,
        leading=11,
    )

    row = []
    for card in cards:
        cell_content = [
            Paragraph(card["count"], card_style),
            Spacer(1, 2),
            Paragraph(card["label"], label_style),
        ]
        if card["sum_eur"]:
            cell_content.append(Spacer(1, 2))
            cell_content.append(Paragraph(card["sum_eur"], sum_style))
        row.append(cell_content)

    table = Table([row], colWidths=[42 * mm] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _SOL_CREAM),
                ("BOX", (0, 0), (-1, -1), 0.5, _SOL_ACCENT),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, _SOL_ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _build_items_table(items: list[ActionCenterItem]) -> Table:
    """Détail des actions : table avec colonne « Impact estimé » à droite."""
    cell_style = ParagraphStyle(
        "ItemCell",
        fontName="Helvetica",
        fontSize=8.5,
        textColor=_SOL_BROWN_DARK,
        leading=10,
    )

    header = ["TITRE", "PRIORITÉ", "ÉTAT", "DOMAINE", "IMPACT ESTIMÉ"]
    data: list[list] = [header]

    for item in items:
        title = (item.title or "")[:80]
        data.append(
            [
                Paragraph(title, cell_style),
                item.priority_bracket or "—",
                item.lifecycle_state or "—",
                item.domain or "—",
                format_euros_full(item.estimated_impact_euros),
            ]
        )

    col_widths = [70 * mm, 18 * mm, 22 * mm, 26 * mm, 32 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), _SOL_BROWN_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), _SOL_CREAM),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, 0), 6),
                ("RIGHTPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 5),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                # Body
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 1), (-1, -1), _SOL_BROWN_DARK),
                ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
                ("FONTNAME", (-1, 1), (-1, -1), "Courier"),
                ("VALIGN", (0, 1), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 1), (-1, -1), 6),
                ("RIGHTPADDING", (0, 1), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _SOL_CREAM_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e8dfd0")),
            ]
        )
    )
    return table


def _on_page(canvas, doc, *, org_name: str, generated_at: str) -> None:
    """Header + footer Sol-fidèle (Q20=C) sur chaque page."""
    canvas.saveState()
    page_width, page_height = A4

    # ─── Header : logo PROMEOS + org + date ───
    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(_SOL_BROWN_DARK)
    canvas.drawString(18 * mm, page_height - 15 * mm, "PROMEOS")
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(_SOL_BROWN_MID)
    canvas.drawRightString(
        page_width - 18 * mm,
        page_height - 15 * mm,
        f"{org_name} · {generated_at}",
    )
    # Filet accent crème sous header
    canvas.setStrokeColor(_SOL_ACCENT)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, page_height - 18 * mm, page_width - 18 * mm, page_height - 18 * mm)

    # ─── Footer : URL + mention + pagination ───
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_SOL_BROWN_LIGHT)
    canvas.drawString(18 * mm, 12 * mm, "promeos.io · Document indicatif")
    canvas.drawRightString(
        page_width - 18 * mm,
        12 * mm,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def _list_items_org_scoped(db: Session, org_id: int) -> list[ActionCenterItem]:
    """Liste tous les items de l'org, ordonnés par priority_score DESC.

    Org-scopé via `_apply_scope` du repo (fail-closed IS3).
    """
    from sqlalchemy import select

    repo = ActionCenterItemRepository(db)
    stmt = repo._apply_scope(select(ActionCenterItem)).order_by(ActionCenterItem.priority_score.desc().nullslast())
    return list(db.execute(stmt).scalars().all())


def generate_comex_pdf(db: Session, org_id: int, org_name: str) -> bytes:
    """Génère le PDF COMEX pour l'org_id. Returns: bytes PDF (magic `%PDF`).

    Args:
        db : SQLAlchemy session (le contexte org doit être posé via
            `populate_org_context` AVANT l'appel — fail-closed sinon).
        org_id : id de l'org (récupéré via `current_org_id()` côté handler).
        org_name : nom org pour header PDF + filename (depuis `Organisation.nom`).

    Raises:
        PdfExportError : si la génération ReportLab échoue (DB locked, OOM…).
    """
    try:
        repo = ActionCenterItemRepository(db)
        summary = repo.get_summary()  # source unique chiffres — pas de recalcul ici
        items = _list_items_org_scoped(db, org_id)

        return _render_with_reportlab(summary, items, org_name)
    except Exception as exc:
        logger.exception("generate_comex_pdf failed for org_id=%d : %s", org_id, exc)
        raise PdfExportError(f"Erreur génération PDF : {exc}") from exc


def _render_with_reportlab(summary: dict, items: list[ActionCenterItem], org_name: str) -> bytes:
    """Layout ReportLab Sol-fidèle minimaliste."""
    buffer = BytesIO()
    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=28 * mm,
        bottomMargin=20 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title="PROMEOS — Export COMEX",
        author="PROMEOS",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleSol",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=_SOL_BROWN_DARK,
        leading=22,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleSol",
        fontName="Helvetica-Oblique",
        fontSize=9.5,
        textColor=_SOL_BROWN_MID,
        leading=12,
        spaceAfter=14,
    )
    completude_style = ParagraphStyle(
        "Completude",
        fontName="Helvetica",
        fontSize=11,
        textColor=_SOL_BROWN_DARK,
        leading=14,
        leftIndent=10,
        spaceBefore=4,
        spaceAfter=14,
        backColor=_SOL_CREAM,
        borderColor=_SOL_ACCENT,
        borderWidth=0,
        borderPadding=8,
    )
    h2_style = ParagraphStyle(
        "H2Sol",
        fontName="Helvetica-Bold",
        fontSize=11.5,
        textColor=_SOL_BROWN_DARK,
        leading=14,
        spaceBefore=14,
        spaceAfter=6,
    )
    footer_note_style = ParagraphStyle(
        "FooterNote",
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        textColor=_SOL_BROWN_LIGHT,
        leading=10,
        spaceBefore=14,
    )

    n_total = int(summary.get("items_total") or 0)

    elements = [
        Paragraph("Centre d'action — Export COMEX", title_style),
        Paragraph(f"{org_name} · {generated_at}", subtitle_style),
        Paragraph(_completude_phrase(summary), completude_style),
        Paragraph("Synthèse", h2_style),
        _build_summary_cards_table(summary),
        Spacer(1, 6),
        Paragraph(f"Détail des actions ({n_total})", h2_style),
        _build_items_table(items),
        Paragraph(
            "Montants indicatifs issus de l'agrégat backend PROMEOS, hors "
            "éléments non estimés. Sémantique de comptage et de somme : voir "
            "<i>docs/produit/semantique_cfo_sums_counts.md</i>.",
            footer_note_style,
        ),
    ]

    def _draw_page(canvas, doc_local):
        _on_page(canvas, doc_local, org_name=org_name, generated_at=generated_at)

    doc.build(elements, onFirstPage=_draw_page, onLaterPages=_draw_page)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ── Helper public pour les tests (fallback explicite) ─────────────────


def get_pdf_backend() -> str:
    """Renvoie le backend PDF actif. MV3 : `'reportlab'` (WeasyPrint indispo)."""
    return "reportlab"
