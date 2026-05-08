"""
PROMEOS — Phase I3 : export PDF dashboard conformité (Marie DAF comité).

Persona Marie DAF cardinal Phase I3 : présentation comité 25 sites bailleur
avec exposition financière chiffrée + pending + countdown urgency par framework.

Réutilise reportlab (déjà dans requirements via audit_report_service.py).
Pattern : page de garde + tableau récap headlines + tableau détaillé sites
+ section Audit SMÉ + footer réglementaire.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any


def _format_eur(value: Any) -> str:
    """Format chiffre EUR FR avec séparateurs (ou '—' si None)."""
    if value is None:
        return "—"
    try:
        return f"{int(round(float(value))):,}".replace(",", " ") + " €"
    except (TypeError, ValueError):
        return "—"


def _urgency_color(level: str) -> str:
    """Mapping urgency → couleur hex (cohérent UI Sol)."""
    return {
        "OVERDUE": "#7F1D1D",
        "CRITICAL": "#DC2626",
        "HIGH": "#D97706",
        "MEDIUM": "#2563EB",
        "LOW": "#059669",
    }.get(level, "#6B7280")


def _compliant_label(compliant: Any, has_assujetti: bool = True) -> str:
    """Compliant tri-state → label FR pour comité."""
    if compliant is True:
        return "✓ Conforme"
    if compliant is False:
        return "✗ Non conforme"
    if compliant is None and has_assujetti:
        return "⚠ En attente"
    return "—"


def render_compliance_dashboard_pdf(dashboard_data: dict, org_nom: str = "PROMEOS") -> bytes:
    """Rend le dashboard conformité Marie DAF en PDF prêt à présenter au comité.

    Args:
        dashboard_data: dict retourné par `build_compliance_dashboard_marie_daf`
        org_nom: nom organisation (pour page de garde)

    Returns:
        bytes PDF (utilisable en `Response(content=bytes, media_type="application/pdf")`)
    """
    from reportlab.lib.colors import HexColor
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

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    DARK = HexColor("#1F2937")
    GRAY = HexColor("#6B7280")
    LIGHT_BG = HexColor("#F3F4F6")
    BORDER = HexColor("#E5E7EB")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=18,
        textColor=DARK,
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=DARK,
        spaceBefore=12,
        spaceAfter=6,
    )
    p_style = ParagraphStyle("P", parent=styles["Normal"], fontSize=9, textColor=DARK, leading=12)
    p_small = ParagraphStyle("PSmall", parent=styles["Normal"], fontSize=7, textColor=GRAY, leading=9)

    elements = []

    # ── Page de garde ────────────────────────────────────────────────────────
    elements.append(Paragraph(f"Tableau de bord conformité — {org_nom}", h1))
    elements.append(
        Paragraph(
            f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} · PROMEOS",
            p_small,
        )
    )
    elements.append(Spacer(1, 8))

    # ── Headlines ────────────────────────────────────────────────────────────
    headlines = dashboard_data.get("headlines", {})
    elements.append(Paragraph("Synthèse globale", h2))

    headline_rows = [
        ["Indicateur", "Valeur"],
        ["Sites suivis", str(headlines.get("total_sites", 0))],
        ["Sites non conformes", str(headlines.get("non_compliant_count", 0))],
        [
            "Exposition pénalités confirmées",
            _format_eur(headlines.get("total_exposure_certain_eur", 0)),
        ],
        [
            "Exposition pending (à évaluer)",
            _format_eur(headlines.get("total_exposure_pending_max_eur", 0)),
        ],
        [
            "Frameworks en attente",
            str(headlines.get("pending_frameworks_count", 0)),
        ],
        [
            "Prochaine échéance (jours)",
            str(headlines.get("next_deadline_days") or "—"),
        ],
    ]
    headline_tbl = Table(headline_rows, colWidths=[80 * mm, 80 * mm])
    headline_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), DARK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(headline_tbl)

    # ── Sites détail ─────────────────────────────────────────────────────────
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Détail par site (5 frameworks)", h2))

    sites = dashboard_data.get("sites", [])
    if sites:
        site_rows = [["Site", "DT", "BACS", "APER", "OPERAT", "DPE", "Exposition"]]
        for s in sites:
            fw_by_name = {fw["framework"]: fw for fw in s.get("frameworks", [])}
            row = [
                Paragraph(s.get("nom", "—"), p_style),
                _compliant_label(
                    fw_by_name.get("DT", {}).get("compliant"),
                    fw_by_name.get("DT", {}).get("assujetti", False),
                ),
                _compliant_label(
                    fw_by_name.get("BACS", {}).get("compliant"),
                    fw_by_name.get("BACS", {}).get("assujetti", False),
                ),
                _compliant_label(
                    fw_by_name.get("APER", {}).get("compliant"),
                    fw_by_name.get("APER", {}).get("assujetti", False),
                ),
                _compliant_label(
                    fw_by_name.get("OPERAT", {}).get("compliant"),
                    fw_by_name.get("OPERAT", {}).get("assujetti", True),
                ),
                _compliant_label(
                    fw_by_name.get("DPE", {}).get("compliant"),
                    fw_by_name.get("DPE", {}).get("assujetti", False),
                ),
                _format_eur(s.get("exposure_certain_eur", 0)),
            ]
            site_rows.append(row)
        site_tbl = Table(site_rows, colWidths=[40 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 30 * mm])
        site_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ]
            )
        )
        elements.append(site_tbl)

    # ── Audit SMÉ par EJ ─────────────────────────────────────────────────────
    audit_sme = dashboard_data.get("audit_sme", [])
    if audit_sme:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Audit SMÉ — Loi DDADUE 2025-391 art. 8", h2))
        rows = [["Entité juridique", "Déclencheur 2,75 GWh", "ISO 50001 valide", "Obligation active"]]
        for a in audit_sme:
            rows.append(
                [
                    Paragraph(a.get("nom", "—"), p_style),
                    "✓" if a.get("triggered") else "—",
                    "✓ Exempté" if a.get("iso_50001_valide") else "—",
                    "⚠ À auditer" if a.get("obligation_active") else "✓ OK",
                ]
            )
        sme_tbl = Table(rows, colWidths=[55 * mm, 35 * mm, 35 * mm, 35 * mm])
        sme_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(sme_tbl)

    # ── Footer réglementaire ─────────────────────────────────────────────────
    elements.append(Spacer(1, 14))
    elements.append(
        Paragraph(
            "Sources réglementaires : Décret 2019-771 (DT) · Décret 2020-887 (BACS) · "
            "Loi 2023-175 art. 40 (APER) · Décret 2019-771 art. R131-39 CCH (OPERAT) · "
            "Art. L. 134-3-1 CCH + Décret 2020-1610 (DPE) · Loi DDADUE 2025-391 art. 8 (Audit SMÉ).",
            p_small,
        )
    )

    doc.build(elements)
    return buf.getvalue()
