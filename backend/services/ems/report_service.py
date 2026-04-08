"""
PROMEOS — Report Service (EMS Tier 1)
Génération de rapports PDF par site (ReportLab).
"""

import io
import json
from datetime import date, datetime

from sqlalchemy.orm import Session

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


def _parse_kpis(snapshot) -> dict:
    """Extrait les KPIs JSON d'un MonitoringSnapshot."""
    if not snapshot or not snapshot.kpis_json:
        return {}
    try:
        raw = snapshot.kpis_json
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}


def generate_site_report(
    db: Session,
    site_id: int,
    period_start: date,
    period_end: date,
) -> bytes:
    """
    Génère un rapport PDF pour un site sur une période donnée.

    Contenu :
      - En-tête site (nom, type, adresse)
      - KPIs clés (consommation, score conformité, qualité données)
      - Résumé signature énergétique
      - Score qualité données par compteur
      - Pied de page avec date de génération

    Retourne les bytes du PDF.
    """
    from models import Site, MonitoringSnapshot
    from services.ems.data_quality_service import compute_data_quality

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} introuvable")

    # Données
    dq = compute_data_quality(db, site_id)
    snapshot = (
        db.query(MonitoringSnapshot)
        .filter(MonitoringSnapshot.site_id == site_id)
        .order_by(MonitoringSnapshot.id.desc())
        .first()
    )
    kpis = _parse_kpis(snapshot)

    # ── Construction PDF ────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="PromeosTitle",
            parent=styles["Title"],
            fontSize=18,
            textColor=HexColor("#1e40af"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PromeosH2",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=HexColor("#1e3a5f"),
            spaceBefore=16,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PromeosBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PromeosFooter",
            parent=styles["Normal"],
            fontSize=8,
            textColor=HexColor("#6b7280"),
            alignment=TA_CENTER,
        )
    )

    elements = []

    # ── En-tête ──
    elements.append(Paragraph("PROMEOS — Rapport Site", styles["PromeosTitle"]))
    elements.append(
        Paragraph(
            f"<b>{site.nom}</b> — {site.type.value if site.type else 'N/A'}",
            styles["PromeosBody"],
        )
    )
    if site.adresse:
        elements.append(
            Paragraph(
                f"{site.adresse}, {site.code_postal or ''} {site.ville or ''}",
                styles["PromeosBody"],
            )
        )
    elements.append(
        Paragraph(
            f"Période : {period_start.isoformat()} → {period_end.isoformat()}",
            styles["PromeosBody"],
        )
    )
    elements.append(Spacer(1, 0.5 * cm))

    # ── KPIs clés ──
    elements.append(Paragraph("Indicateurs clés", styles["PromeosH2"]))
    kpi_data = [
        ["Indicateur", "Valeur"],
        ["Consommation annuelle", f"{site.annual_kwh_total:,.0f} kWh" if site.annual_kwh_total else "N/A"],
        ["Surface", f"{site.surface_m2:,.0f} m²" if site.surface_m2 else "N/A"],
        [
            "Score conformité",
            f"{site.compliance_score_composite:.0f}/100" if site.compliance_score_composite else "N/A",
        ],
        ["Score qualité données", f"{dq['score_global']:.0f}/100 ({dq['status_global']})"],
    ]
    # Ajouter KPIs monitoring si disponibles
    if kpis.get("pmax_kw"):
        kpi_data.append(["Puissance max atteinte", f"{kpis['pmax_kw']:.0f} kW"])
    if kpis.get("load_factor"):
        kpi_data.append(["Facteur de charge", f"{kpis['load_factor']:.1%}"])

    kpi_table = Table(kpi_data, colWidths=[9 * cm, 7 * cm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e40af")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f9fafb"), HexColor("#ffffff")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.5 * cm))

    # ── Qualité données par compteur ──
    if dq["meters"]:
        elements.append(Paragraph("Qualité des données par compteur", styles["PromeosH2"]))
        dq_data = [["Compteur", "Dernière relève", "Trous", "Complétude %", "Score"]]
        for m in dq["meters"]:
            dq_data.append(
                [
                    m["name"],
                    m["last_reading"][:10] if m["last_reading"] else "Aucune",
                    str(m["gaps"]),
                    f"{m['completeness_pct']:.0f}%",
                    f"{m['score']}/100",
                ]
            )
        dq_table = Table(dq_data, colWidths=[4 * cm, 3.5 * cm, 2 * cm, 3 * cm, 3.5 * cm])
        dq_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#059669")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f0fdf4"), HexColor("#ffffff")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(dq_table)
        elements.append(Spacer(1, 0.5 * cm))

    # ── Pied de page ──
    elements.append(Spacer(1, 1 * cm))
    elements.append(
        Paragraph(
            f"Rapport généré par PROMEOS le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M UTC')}",
            styles["PromeosFooter"],
        )
    )

    doc.build(elements)
    return buf.getvalue()
