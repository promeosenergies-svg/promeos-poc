"""
PROMEOS — Audit Report Service (Sprint 10.1)
Builds structured audit data from all briques, renders a multi-page B2B PDF.
"""
import io
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Organisation, Site, Batiment, Compteur,
    ComplianceFinding, ConsumptionInsight, BillingInsight,
    ActionItem, ActionSyncBatch,
    ActionSourceType, ActionStatus, InsightStatus,
    EnergyContract, EnergyInvoice,
    PurchaseScenarioResult, PurchaseRecoStatus,
    EntiteJuridique, Portefeuille,
)


# ========================================
# Step 1: Build audit report data (JSON)
# ========================================

def build_audit_report_data(db: Session, org_id: Optional[int] = None) -> dict:
    """
    Assemble toutes les donnees d'audit pour un rapport PDF.
    Retourne un dict JSON-serialisable.
    """
    # Resolve org
    if org_id:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
    else:
        org = db.query(Organisation).first()
    if not org:
        return {"error": "Aucune organisation trouvee"}

    org_id = org.id

    # Sites
    total_sites = db.query(Site).filter(Site.actif == True).count()
    total_surface = db.query(func.sum(Site.surface_m2)).filter(Site.actif == True).scalar() or 0

    # -- Section 1: Conformite --
    compliance = _build_compliance_section(db, org_id)

    # -- Section 2: Consommation --
    consumption = _build_consumption_section(db, org_id)

    # -- Section 3: Facturation --
    billing = _build_billing_section(db, org_id)

    # -- Section 4: Achats energie --
    purchase = _build_purchase_section(db, org_id)

    # -- Section 5: Plan d'action --
    actions = _build_actions_section(db, org_id)

    # -- Synthese executive --
    total_risk_eur = (
        (consumption.get("total_loss_eur") or 0) +
        (billing.get("total_loss_eur") or 0)
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "organisation": {
            "nom": org.nom,
            "type_client": org.type_client,
            "total_sites": total_sites,
            "total_surface_m2": round(total_surface),
        },
        "synthese": {
            "total_risk_eur": round(total_risk_eur, 2),
            "total_gain_potentiel_eur": round(actions.get("total_gain_eur") or 0, 2),
            "conformite_pct": compliance.get("conformite_pct", 0),
            "actions_open": actions.get("open", 0),
            "actions_total": actions.get("total", 0),
            "confidence": _compute_confidence(
                compliance.get("total_findings", 0),
                consumption.get("total_insights", 0),
                billing.get("total_insights", 0),
            ),
        },
        "compliance": compliance,
        "consumption": consumption,
        "billing": billing,
        "purchase": purchase,
        "actions": actions,
    }


def _get_site_ids(db: Session, org_id: int) -> list:
    """Resolve site IDs for an org (same pattern as action_hub_service)."""
    ej_ids = [r[0] for r in db.query(EntiteJuridique.id).filter(
        EntiteJuridique.organisation_id == org_id).all()]
    if not ej_ids:
        return []
    pf_ids = [r[0] for r in db.query(Portefeuille.id).filter(
        Portefeuille.entite_juridique_id.in_(ej_ids)).all()]
    if not pf_ids:
        return []
    return [r[0] for r in db.query(Site.id).filter(
        Site.portefeuille_id.in_(pf_ids), Site.actif == True).all()]


def _build_compliance_section(db: Session, org_id: int) -> dict:
    site_ids = _get_site_ids(db, org_id)
    if not site_ids:
        return {"total_findings": 0, "nok": 0, "ok": 0, "unknown": 0,
                "conformite_pct": 0, "top_findings": []}

    findings = db.query(ComplianceFinding).filter(
        ComplianceFinding.site_id.in_(site_ids)).all()

    nok = [f for f in findings if f.status == "NOK"]
    ok = [f for f in findings if f.status == "OK"]
    unknown = [f for f in findings if f.status == "UNKNOWN"]

    conformite_pct = round(len(ok) / len(findings) * 100) if findings else 0

    # Top 5 NOK findings by severity
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    nok_sorted = sorted(nok, key=lambda f: severity_rank.get(f.severity, 0), reverse=True)

    top_findings = []
    for f in nok_sorted[:5]:
        site = db.query(Site).filter(Site.id == f.site_id).first()
        top_findings.append({
            "rule_id": f.rule_id,
            "regulation": f.regulation,
            "severity": f.severity,
            "evidence": f.evidence,
            "site_nom": site.nom if site else "?",
            "deadline": f.deadline.isoformat() if f.deadline else None,
        })

    return {
        "total_findings": len(findings),
        "nok": len(nok),
        "ok": len(ok),
        "unknown": len(unknown),
        "conformite_pct": conformite_pct,
        "top_findings": top_findings,
    }


def _build_consumption_section(db: Session, org_id: int) -> dict:
    site_ids = _get_site_ids(db, org_id)
    if not site_ids:
        return {"total_insights": 0, "total_loss_eur": 0, "top_insights": []}

    insights = db.query(ConsumptionInsight).filter(
        ConsumptionInsight.site_id.in_(site_ids),
        ConsumptionInsight.estimated_loss_eur > 0,
    ).all()

    total_loss = sum(i.estimated_loss_eur or 0 for i in insights)

    # Top 5 by loss
    sorted_ins = sorted(insights, key=lambda i: i.estimated_loss_eur or 0, reverse=True)
    top_insights = []
    for ins in sorted_ins[:5]:
        site = db.query(Site).filter(Site.id == ins.site_id).first()
        top_insights.append({
            "type": ins.type,
            "severity": ins.severity,
            "message": ins.message,
            "estimated_loss_eur": round(ins.estimated_loss_eur or 0, 2),
            "site_nom": site.nom if site else "?",
        })

    return {
        "total_insights": len(insights),
        "total_loss_eur": round(total_loss, 2),
        "top_insights": top_insights,
    }


def _build_billing_section(db: Session, org_id: int) -> dict:
    site_ids = _get_site_ids(db, org_id)
    if not site_ids:
        return {"total_insights": 0, "total_loss_eur": 0, "top_insights": []}

    insights = db.query(BillingInsight).filter(
        BillingInsight.site_id.in_(site_ids),
        BillingInsight.insight_status != InsightStatus.FALSE_POSITIVE,
    ).all()

    total_loss = sum(i.estimated_loss_eur or 0 for i in insights)

    sorted_ins = sorted(insights, key=lambda i: i.estimated_loss_eur or 0, reverse=True)
    top_insights = []
    for ins in sorted_ins[:5]:
        site = db.query(Site).filter(Site.id == ins.site_id).first()
        top_insights.append({
            "type": ins.type,
            "severity": ins.severity,
            "message": ins.message,
            "estimated_loss_eur": round(ins.estimated_loss_eur or 0, 2),
            "site_nom": site.nom if site else "?",
        })

    return {
        "total_insights": len(insights),
        "total_loss_eur": round(total_loss, 2),
        "top_insights": top_insights,
    }


def _build_purchase_section(db: Session, org_id: int) -> dict:
    results = db.query(PurchaseScenarioResult).all()
    if not results:
        return {"total_scenarios": 0, "recommendation": None}

    recommended = next((r for r in results if r.is_recommended), None)

    rec = None
    if recommended:
        rec = {
            "strategy": recommended.strategy.value if recommended.strategy else None,
            "price_eur_per_kwh": recommended.price_eur_per_kwh,
            "total_annual_eur": recommended.total_annual_eur,
            "savings_vs_current_pct": recommended.savings_vs_current_pct,
        }

    return {
        "total_scenarios": len(results),
        "recommendation": rec,
    }


def _build_actions_section(db: Session, org_id: int) -> dict:
    items = db.query(ActionItem).filter(ActionItem.org_id == org_id).all()
    if not items:
        return {"total": 0, "open": 0, "in_progress": 0, "done": 0,
                "total_gain_eur": 0, "by_source": {}, "top_actions": []}

    open_count = sum(1 for a in items if a.status == ActionStatus.OPEN)
    in_progress = sum(1 for a in items if a.status == ActionStatus.IN_PROGRESS)
    done = sum(1 for a in items if a.status == ActionStatus.DONE)
    total_gain = sum(a.estimated_gain_eur or 0 for a in items if a.status != ActionStatus.DONE)

    by_source = {}
    for a in items:
        src = a.source_type.value if a.source_type else "unknown"
        by_source[src] = by_source.get(src, 0) + 1

    # Top 5 open by priority
    open_items = [a for a in items if a.status in (ActionStatus.OPEN, ActionStatus.IN_PROGRESS)]
    open_items.sort(key=lambda a: (a.priority or 5, str(a.due_date or "9999-12-31")))

    top_actions = []
    for a in open_items[:5]:
        top_actions.append({
            "title": a.title,
            "source_type": a.source_type.value if a.source_type else None,
            "priority": a.priority,
            "severity": a.severity,
            "estimated_gain_eur": a.estimated_gain_eur,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "owner": a.owner,
        })

    return {
        "total": len(items),
        "open": open_count,
        "in_progress": in_progress,
        "done": done,
        "total_gain_eur": round(total_gain, 2),
        "by_source": by_source,
        "top_actions": top_actions,
    }


def _compute_confidence(compliance_n: int, conso_n: int, billing_n: int) -> str:
    """Confidence flag based on data volume."""
    score = 0
    if compliance_n >= 5:
        score += 1
    if conso_n >= 2:
        score += 1
    if billing_n >= 2:
        score += 1
    if score >= 3:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


# ========================================
# Step 2: Render PDF with reportlab
# ========================================

def render_audit_pdf(data: dict) -> bytes:
    """
    Render a multi-page B2B audit PDF from structured data.
    Returns raw PDF bytes.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
    )

    # Colors (HexColor for style properties, hex strings for inline <font> tags)
    BLUE = HexColor("#2563EB")
    DARK = HexColor("#1F2937")
    GRAY = HexColor("#6B7280")
    LIGHT_BG = HexColor("#F3F4F6")
    RED = HexColor("#DC2626")
    GREEN = HexColor("#059669")
    ORANGE = HexColor("#D97706")
    WHITE = HexColor("#FFFFFF")

    # Hex strings for use in <font color='...'> tags (avoid ast.Str issue on Python 3.14)
    C_BLUE = "#2563EB"
    C_RED = "#DC2626"
    C_GREEN = "#059669"
    C_ORANGE = "#D97706"

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "AuditTitle", parent=styles["Title"],
        fontSize=22, textColor=BLUE, spaceAfter=4 * mm,
    )
    subtitle_style = ParagraphStyle(
        "AuditSubtitle", parent=styles["Normal"],
        fontSize=11, textColor=GRAY, spaceAfter=8 * mm,
    )
    h2_style = ParagraphStyle(
        "AuditH2", parent=styles["Heading2"],
        fontSize=14, textColor=DARK, spaceBefore=6 * mm, spaceAfter=3 * mm,
        borderWidth=0, borderColor=BLUE, borderPadding=0,
    )
    body_style = ParagraphStyle(
        "AuditBody", parent=styles["Normal"],
        fontSize=10, textColor=DARK, spaceAfter=2 * mm, leading=14,
    )
    small_style = ParagraphStyle(
        "AuditSmall", parent=styles["Normal"],
        fontSize=8, textColor=GRAY, spaceAfter=1 * mm,
    )
    bold_style = ParagraphStyle(
        "AuditBold", parent=body_style,
        fontName="Helvetica-Bold",
    )
    kpi_style = ParagraphStyle(
        "AuditKPI", parent=styles["Normal"],
        fontSize=18, fontName="Helvetica-Bold", textColor=BLUE,
        alignment=TA_CENTER, spaceAfter=1 * mm,
    )
    kpi_label_style = ParagraphStyle(
        "AuditKPILabel", parent=styles["Normal"],
        fontSize=9, textColor=GRAY, alignment=TA_CENTER, spaceAfter=0,
    )

    elements = []
    org = data.get("organisation", {})
    synth = data.get("synthese", {})

    # ========================================
    # Page 1: Cover + Synthese executive
    # ========================================
    elements.append(Spacer(1, 15 * mm))
    elements.append(Paragraph("PROMEOS", ParagraphStyle(
        "Logo", parent=styles["Normal"],
        fontSize=28, fontName="Helvetica-Bold", textColor=BLUE,
    )))
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph("Rapport d'audit energetique", title_style))
    elements.append(Paragraph(
        f"{org.get('nom', '?')} - {org.get('type_client', '?')} | "
        f"{org.get('total_sites', 0)} sites | {org.get('total_surface_m2', 0):,} m2",
        subtitle_style,
    ))
    elements.append(Paragraph(
        f"Date de generation : {data.get('generated_at', '?')[:10]}",
        small_style,
    ))
    elements.append(Spacer(1, 8 * mm))

    # Confidence badge
    conf = synth.get("confidence", "low")
    conf_hex = {"high": C_GREEN, "medium": C_ORANGE, "low": C_RED}.get(conf, "#6B7280")
    conf_label = {"high": "Elevee", "medium": "Moyenne", "low": "Faible"}.get(conf, "?")
    elements.append(Paragraph(
        f"Indice de confiance : <font color='{conf_hex}'><b>{conf_label}</b></font>",
        body_style,
    ))
    elements.append(Spacer(1, 6 * mm))

    # KPI cards as table
    kpi_data = [
        [
            _kpi_cell("Risque financier", f"{synth.get('total_risk_eur', 0):,.0f} EUR", RED, kpi_style, kpi_label_style),
            _kpi_cell("Gain potentiel", f"{synth.get('total_gain_potentiel_eur', 0):,.0f} EUR", GREEN, kpi_style, kpi_label_style),
            _kpi_cell("Conformite", f"{synth.get('conformite_pct', 0)}%", BLUE, kpi_style, kpi_label_style),
            _kpi_cell("Actions ouvertes", f"{synth.get('actions_open', 0)} / {synth.get('actions_total', 0)}", ORANGE, kpi_style, kpi_label_style),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[42 * mm] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    elements.append(kpi_table)

    # ========================================
    # Page 2: Conformite
    # ========================================
    elements.append(PageBreak())
    comp = data.get("compliance", {})
    elements.append(Paragraph("1. Conformite reglementaire", h2_style))
    elements.append(Paragraph(
        f"<b>{comp.get('total_findings', 0)}</b> points evalues | "
        f"<font color='{C_GREEN}'><b>{comp.get('ok', 0)}</b> OK</font> | "
        f"<font color='{C_RED}'><b>{comp.get('nok', 0)}</b> NOK</font> | "
        f"<font color='{C_ORANGE}'><b>{comp.get('unknown', 0)}</b> inconnus</font>",
        body_style,
    ))
    elements.append(Spacer(1, 4 * mm))

    top_findings = comp.get("top_findings", [])
    if top_findings:
        elements.append(Paragraph("Non-conformites prioritaires :", bold_style))
        elements.append(Spacer(1, 2 * mm))

        header = ["Regle", "Site", "Severite", "Echeance", "Constat"]
        rows = [header]
        for f in top_findings:
            rows.append([
                f.get("rule_id", "?"),
                _truncate(f.get("site_nom", "?"), 25),
                f.get("severity", "?"),
                f.get("deadline", "-"),
                _truncate(f.get("evidence", "?"), 40),
            ])
        t = _make_table(rows, [28 * mm, 38 * mm, 22 * mm, 22 * mm, 60 * mm])
        elements.append(t)
    else:
        elements.append(Paragraph("Aucune non-conformite detectee.", body_style))

    # ========================================
    # Page 3: Consommation + Facturation
    # ========================================
    elements.append(PageBreak())
    conso = data.get("consumption", {})
    elements.append(Paragraph("2. Diagnostics de consommation", h2_style))
    elements.append(Paragraph(
        f"<b>{conso.get('total_insights', 0)}</b> anomalies detectees | "
        f"Pertes estimees : <font color='{C_RED}'><b>{conso.get('total_loss_eur', 0):,.0f} EUR/an</b></font>",
        body_style,
    ))
    elements.append(Spacer(1, 3 * mm))

    top_conso = conso.get("top_insights", [])
    if top_conso:
        header = ["Type", "Site", "Severite", "Perte EUR/an", "Description"]
        rows = [header]
        for ins in top_conso:
            rows.append([
                ins.get("type", "?"),
                _truncate(ins.get("site_nom", "?"), 25),
                ins.get("severity", "?"),
                f"{ins.get('estimated_loss_eur', 0):,.0f}",
                _truncate(ins.get("message", "?"), 35),
            ])
        elements.append(_make_table(rows, [25 * mm, 35 * mm, 22 * mm, 25 * mm, 63 * mm]))
    else:
        elements.append(Paragraph("Aucune anomalie de consommation detectee.", body_style))

    elements.append(Spacer(1, 8 * mm))

    # Billing
    bill = data.get("billing", {})
    elements.append(Paragraph("3. Anomalies de facturation", h2_style))
    elements.append(Paragraph(
        f"<b>{bill.get('total_insights', 0)}</b> anomalies de facturation | "
        f"Ecart total : <font color='{C_RED}'><b>{bill.get('total_loss_eur', 0):,.0f} EUR</b></font>",
        body_style,
    ))
    elements.append(Spacer(1, 3 * mm))

    top_bill = bill.get("top_insights", [])
    if top_bill:
        header = ["Type", "Site", "Severite", "Ecart EUR", "Description"]
        rows = [header]
        for ins in top_bill:
            rows.append([
                ins.get("type", "?"),
                _truncate(ins.get("site_nom", "?"), 25),
                ins.get("severity", "?"),
                f"{ins.get('estimated_loss_eur', 0):,.0f}",
                _truncate(ins.get("message", "?"), 35),
            ])
        elements.append(_make_table(rows, [25 * mm, 35 * mm, 22 * mm, 25 * mm, 63 * mm]))
    else:
        elements.append(Paragraph("Aucune anomalie de facturation detectee.", body_style))

    # ========================================
    # Page 4: Achats + Plan d'action
    # ========================================
    elements.append(PageBreak())
    purch = data.get("purchase", {})
    elements.append(Paragraph("4. Achats energie", h2_style))
    if purch.get("recommendation"):
        rec = purch["recommendation"]
        elements.append(Paragraph(
            f"Strategie recommandee : <b>{rec.get('strategy', '?')}</b> | "
            f"Prix : {rec.get('price_eur_per_kwh', 0):.4f} EUR/kWh | "
            f"Budget annuel : {rec.get('total_annual_eur', 0):,.0f} EUR | "
            f"Economie : {rec.get('savings_vs_current_pct', 0):.1f}%",
            body_style,
        ))
    else:
        elements.append(Paragraph(
            f"{purch.get('total_scenarios', 0)} scenarios evalues. Aucune recommandation finalisee.",
            body_style,
        ))

    elements.append(Spacer(1, 8 * mm))

    # Plan d'action
    act = data.get("actions", {})
    elements.append(Paragraph("5. Plan d'action", h2_style))
    elements.append(Paragraph(
        f"<b>{act.get('total', 0)}</b> actions | "
        f"<font color='{C_ORANGE}'>{act.get('open', 0)} ouvertes</font> | "
        f"<font color='{C_BLUE}'>{act.get('in_progress', 0)} en cours</font> | "
        f"<font color='{C_GREEN}'>{act.get('done', 0)} terminees</font> | "
        f"Gain potentiel : <font color='{C_GREEN}'><b>{act.get('total_gain_eur', 0):,.0f} EUR</b></font>",
        body_style,
    ))
    elements.append(Spacer(1, 3 * mm))

    # By source
    by_source = act.get("by_source", {})
    if by_source:
        source_label = {
            "compliance": "Conformite", "consumption": "Consommation",
            "billing": "Facturation", "purchase": "Achats",
        }
        parts = [f"{source_label.get(k, k)}: {v}" for k, v in by_source.items()]
        elements.append(Paragraph(f"Repartition : {' | '.join(parts)}", body_style))
        elements.append(Spacer(1, 3 * mm))

    top_actions = act.get("top_actions", [])
    if top_actions:
        elements.append(Paragraph("Actions prioritaires :", bold_style))
        elements.append(Spacer(1, 2 * mm))
        header = ["Priorite", "Source", "Action", "Gain EUR", "Echeance", "Owner"]
        rows = [header]
        for a in top_actions:
            rows.append([
                f"P{a.get('priority', '?')}",
                a.get("source_type", "?"),
                _truncate(a.get("title", "?"), 35),
                f"{a.get('estimated_gain_eur', 0) or 0:,.0f}",
                a.get("due_date", "-") or "-",
                a.get("owner", "-") or "-",
            ])
        elements.append(_make_table(rows, [18 * mm, 25 * mm, 55 * mm, 22 * mm, 22 * mm, 28 * mm]))

    # Footer
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        "Ce rapport est genere automatiquement par PROMEOS. "
        "Les donnees refletent l'etat du systeme au moment de la generation.",
        small_style,
    ))

    # Build
    doc.build(elements, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buf.getvalue()


# ========================================
# Helpers
# ========================================

def _kpi_cell(label, value, color, kpi_style, label_style):
    """Build a KPI cell (value + label) as a list of Flowables."""
    from reportlab.platypus import Paragraph as P
    from reportlab.lib.styles import ParagraphStyle
    custom_kpi = ParagraphStyle("kpi_custom", parent=kpi_style, textColor=color)
    return [
        P(value, custom_kpi),
        P(label, label_style),
    ]


def _make_table(rows, col_widths):
    """Build a styled table from a list of rows (first row = header)."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Table, TableStyle

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BACKGROUND", (0, 1), (-1, -1), HexColor("#FFFFFF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), HexColor("#F9FAFB")]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
    ]))
    return t


def _truncate(text: str, max_len: int = 50) -> str:
    if not text:
        return "?"
    return text[:max_len] + "..." if len(text) > max_len else text


def _page_footer(canvas, doc):
    """Draw footer on every page."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#9CA3AF"))
    canvas.drawString(20 * mm, 10 * mm, "PROMEOS - Rapport d'audit energetique - Confidentiel")
    canvas.drawRightString(doc.pagesize[0] - 20 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()
