"""
PROMEOS Bill Intelligence — Engine
Pipeline: parse → audit → shadow → reconcile → report.
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .domain import (
    Invoice,
    InvoiceAnomaly,
    ShadowResult,
    AuditReport,
    InvoiceStatus,
    ShadowLevel,
    AnomalySeverity,
)
from .rules.audit_rules_v0 import run_all_rules, ALL_RULES
from .parsers.json_parser import parse_json_file, parse_json_invoice, load_all_demo_invoices

ENGINE_VERSION = "0.1.0-poc"


def _check_l2_availability() -> bool:
    """Check if L2-min RuleCards are available in KB."""
    try:
        from .tariff_bridge import get_l2_rule_card_ids

        return len(get_l2_rule_card_ids()) > 0
    except Exception:
        return False


def _enrich_anomalies_with_citations(anomalies: List[InvoiceAnomaly]) -> List[InvoiceAnomaly]:
    """
    P5: attach KB citations to anomalies when their rule_card_id
    maps to a citation-backed RuleCard in the KB.
    Gracefully returns unmodified anomalies if KB is unavailable.
    """
    try:
        from ..kb.citations import get_citations_for_rule

        for anom in anomalies:
            if anom.rule_card_id and not anom.citations:
                try:
                    cites = get_citations_for_rule(anom.rule_card_id)
                    if cites:
                        anom.citations = cites
                except Exception:
                    pass
    except Exception:
        pass
    return anomalies


def audit_invoice(invoice: Invoice) -> Invoice:
    """
    Run all V0 audit rules on an invoice.
    Sets shadow_level to L1 (partial shadow) after audit.
    """
    anomalies = run_all_rules(invoice)
    anomalies = _enrich_anomalies_with_citations(anomalies)
    invoice.anomalies = anomalies
    invoice.status = InvoiceStatus.AUDITED
    invoice.audit_timestamp = datetime.now(timezone.utc).isoformat()
    invoice.engine_version = ENGINE_VERSION

    # Determine shadow level
    l2_available = _check_l2_availability()
    if l2_available:
        invoice.shadow_level = ShadowLevel.L1_PARTIAL
        invoice.why_not_higher = (
            "L2-min: grilles TURPE/CTA presentes dans la KB. L2 complet necessite offre fournisseur + contrat."
        )
    elif anomalies:
        invoice.shadow_level = ShadowLevel.L1_PARTIAL
        invoice.why_not_higher = "Audit L1 (arithmetique + TVA + coherences). L2 necessite grilles TURPE dans la KB."
    else:
        invoice.shadow_level = ShadowLevel.L1_PARTIAL
        invoice.why_not_higher = "Aucune anomalie L1. L2 necessite grilles tarifaires dans la KB."

    return invoice


def shadow_billing_l1(invoice: Invoice) -> ShadowResult:
    """
    Shadow billing L1 : recalcul partiel (arithmetique + TVA).
    Recalcule les totaux a partir des composantes.
    """
    shadow_components = []
    shadow_total_ht = 0.0
    shadow_total_tva = 0.0
    explain = []

    for comp in invoice.components:
        shadow_comp = {
            "component_type": comp.component_type.value,
            "label": comp.label,
            "amount_ht_original": comp.amount_ht,
            "amount_ht_shadow": None,
            "tva_rate_original": comp.tva_rate,
            "tva_rate_shadow": None,
            "tva_amount_shadow": None,
        }

        # Recalcul amount_ht si qty + prix dispo
        if comp.quantity is not None and comp.unit_price is not None:
            shadow_ht = round(comp.quantity * comp.unit_price, 2)
            shadow_comp["amount_ht_shadow"] = shadow_ht
            if comp.amount_ht is not None and abs(shadow_ht - comp.amount_ht) > 0.02:
                explain.append(f"{comp.label}: recalcul HT {shadow_ht:.2f} vs facture {comp.amount_ht:.2f}")
        elif comp.amount_ht is not None:
            shadow_comp["amount_ht_shadow"] = comp.amount_ht
            shadow_ht = comp.amount_ht
        else:
            shadow_ht = 0.0
            shadow_comp["amount_ht_shadow"] = 0.0

        # Skip TVA summary lines
        from .domain import ComponentType

        if comp.component_type in (ComponentType.TVA_REDUITE, ComponentType.TVA_NORMALE):
            shadow_components.append(shadow_comp)
            continue

        shadow_total_ht += shadow_ht

        # Recalcul TVA
        from .rules.audit_rules_v0 import COMPONENTS_TVA_REDUITE, TVA_REDUITE, TVA_NORMALE

        expected_rate = TVA_REDUITE if comp.component_type in COMPONENTS_TVA_REDUITE else TVA_NORMALE
        shadow_comp["tva_rate_shadow"] = expected_rate
        shadow_tva = round(shadow_ht * expected_rate / 100, 2)
        shadow_comp["tva_amount_shadow"] = shadow_tva
        shadow_total_tva += shadow_tva

        if comp.tva_rate is not None and abs(comp.tva_rate - expected_rate) > 0.01:
            explain.append(f"{comp.label}: TVA corrigee {comp.tva_rate}% → {expected_rate}%")

        shadow_components.append(shadow_comp)

    shadow_total_ttc = round(shadow_total_ht + shadow_total_tva, 2)
    shadow_total_ht = round(shadow_total_ht, 2)

    delta_ht = round(shadow_total_ht - (invoice.total_ht or 0), 2)
    delta_ttc = round(shadow_total_ttc - (invoice.total_ttc or 0), 2)
    delta_percent = round(delta_ttc / (invoice.total_ttc or 1) * 100, 2) if invoice.total_ttc else None

    if not explain:
        explain.append("Aucun ecart detecte au niveau L1")

    return ShadowResult(
        invoice_id=invoice.invoice_id,
        shadow_level=ShadowLevel.L1_PARTIAL,
        shadow_total_ht=shadow_total_ht,
        shadow_total_ttc=shadow_total_ttc,
        shadow_components=shadow_components,
        delta_ht=delta_ht,
        delta_ttc=delta_ttc,
        delta_percent=delta_percent,
        explain=explain,
        why_not_higher=(
            "L2-min: grilles TURPE/CTA presentes. L2 complet necessite offre fournisseur."
            if _check_l2_availability()
            else "L2 necessite grilles TURPE/ATRD dans la KB"
        ),
        rule_cards_used=[f"RULE_{r[0]}" for r in ALL_RULES],
        engine_version=ENGINE_VERSION,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


def full_pipeline(invoice: Invoice) -> AuditReport:
    """
    Pipeline complet : audit → shadow L1 → report.
    """
    # Step 1: Audit
    invoice = audit_invoice(invoice)

    # Step 2: Shadow billing L1
    shadow = shadow_billing_l1(invoice)

    # Step 3: Build report
    critical_count = sum(1 for a in invoice.anomalies if a.severity == AnomalySeverity.CRITICAL)
    error_count = sum(1 for a in invoice.anomalies if a.severity == AnomalySeverity.ERROR)

    # Estimate savings from TVA errors
    tva_savings = sum(
        abs(a.difference or 0)
        for a in invoice.anomalies
        if a.anomaly_type.value in ("tva_error", "arithmetic_error") and a.difference
    )

    # Allocation summary by concept
    concept_totals: Dict[str, float] = {}
    for comp in invoice.components:
        if comp.allocation:
            cid = comp.allocation.concept_id
            concept_totals[cid] = concept_totals.get(cid, 0.0) + (comp.amount_ht or 0.0)

    report = AuditReport(
        invoice_id=invoice.invoice_id,
        invoice=invoice.to_dict(),
        shadow=shadow.to_dict(),
        anomalies=[a.to_dict() for a in invoice.anomalies],
        coverage_level=shadow.shadow_level.value,
        total_anomalies=len(invoice.anomalies),
        critical_anomalies=critical_count,
        potential_savings_eur=round(tva_savings, 2) if tva_savings > 0 else None,
        explain_log=shadow.explain,
        generated_at=datetime.now(timezone.utc).isoformat(),
        engine_version=ENGINE_VERSION,
        concept_allocations={k: round(v, 2) for k, v in concept_totals.items()},
    )

    return report


def anomalies_to_csv(anomalies: List[Dict[str, Any]], invoice_id: str = "") -> str:
    """Export anomalies to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "invoice_id",
            "anomaly_id",
            "type",
            "severity",
            "message",
            "component",
            "expected",
            "actual",
            "difference",
            "rule_card_id",
        ]
    )
    for a in anomalies:
        writer.writerow(
            [
                invoice_id,
                a.get("anomaly_id", ""),
                a.get("anomaly_type", ""),
                a.get("severity", ""),
                a.get("message", ""),
                a.get("component_type", ""),
                a.get("expected_value", ""),
                a.get("actual_value", ""),
                a.get("difference", ""),
                a.get("rule_card_id", ""),
            ]
        )
    return output.getvalue()


def _build_kb_evidence_html(anomalies: List[Dict[str, Any]]) -> str:
    """Build KB Evidence HTML block showing citations backing each rule."""
    cited_rules = {}
    uncited_rules = set()
    for a in anomalies:
        rule_id = a.get("rule_card_id", "")
        cites = a.get("citations", [])
        if cites:
            cited_rules[rule_id] = cites
        elif rule_id:
            uncited_rules.add(rule_id)

    if not cited_rules and not uncited_rules:
        return '<p style="color:#6b7280">Aucune regle normative KB utilisee. Les 20 regles V0 sont des controles arithmetiques universels.</p>'

    html_parts = []
    if cited_rules:
        html_parts.append(
            "<table><tr><th>Regle</th><th>Document</th><th>Section</th><th>Extrait</th><th>Confiance</th></tr>"
        )
        for rule_id, cites in cited_rules.items():
            for c in cites:
                ptr = c.get("pointer", {})
                section = ptr.get("section") or ptr.get("article") or ptr.get("page") or "-"
                excerpt = (
                    (c.get("excerpt_text", "")[:80] + "...")
                    if len(c.get("excerpt_text", "")) > 80
                    else c.get("excerpt_text", "")
                )
                html_parts.append(
                    f'<tr><td style="font-family:monospace">{rule_id}</td><td>{c.get("doc_title", "")}</td><td>{section}</td><td style="font-size:0.85em">{excerpt}</td><td>{c.get("confidence", "")}</td></tr>'
                )
        html_parts.append("</table>")

    if uncited_rules:
        html_parts.append(
            f'<div class="explain">Regles sans citation KB (P5 non verifiable): {", ".join(sorted(uncited_rules))}</div>'
        )

    return "\n".join(html_parts)


def report_to_html(report: AuditReport) -> str:
    """Generate HTML report from AuditReport."""
    inv = report.invoice
    shadow = report.shadow or {}
    anomalies = report.anomalies

    severity_colors = {
        "critical": "#dc2626",
        "error": "#ea580c",
        "warning": "#ca8a04",
        "info": "#2563eb",
    }

    anomaly_rows = ""
    for a in anomalies:
        color = severity_colors.get(a.get("severity", "info"), "#6b7280")
        anomaly_rows += f"""
        <tr>
            <td style="color:{color};font-weight:bold">{a.get("severity", "").upper()}</td>
            <td>{a.get("anomaly_type", "")}</td>
            <td>{a.get("message", "")}</td>
            <td>{a.get("component_type", "") or "-"}</td>
            <td>{a.get("expected_value", "") or "-"}</td>
            <td>{a.get("actual_value", "") or "-"}</td>
            <td>{a.get("difference", "") or "-"}</td>
            <td style="font-family:monospace;font-size:0.8em">{a.get("rule_card_id", "")}</td>
        </tr>"""

    component_rows = ""
    for c in inv.get("components", []):
        alloc = c.get("allocation") or {}
        concept = alloc.get("concept_id", "-")
        conf = alloc.get("confidence")
        conf_str = f"{conf:.0%}" if conf is not None else "-"
        rules_str = ", ".join(alloc.get("matched_rules", [])) or "-"
        component_rows += f"""
        <tr>
            <td>{c.get("component_type", "")}</td>
            <td>{c.get("label", "")}</td>
            <td>{c.get("quantity", "") or "-"}</td>
            <td>{c.get("unit", "") or "-"}</td>
            <td>{c.get("unit_price", "") or "-"}</td>
            <td>{c.get("amount_ht", "") or "-"}</td>
            <td>{c.get("tva_rate", "") or "-"}%</td>
            <td>{c.get("tva_amount", "") or "-"}</td>
            <td style="font-weight:bold">{concept}</td>
            <td>{conf_str}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>PROMEOS Bill Intelligence — Rapport Audit {inv.get("invoice_id", "")}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f9fafb; }}
        h1 {{ color: #1e40af; border-bottom: 3px solid #1e40af; padding-bottom: 10px; }}
        h2 {{ color: #1e3a5f; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; background: white; }}
        th {{ background: #1e40af; color: white; padding: 10px; text-align: left; }}
        td {{ border: 1px solid #e5e7eb; padding: 8px; }}
        tr:nth-child(even) {{ background: #f3f4f6; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .card {{ background: white; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
        .card .value {{ font-size: 2em; font-weight: bold; color: #1e40af; }}
        .card .label {{ color: #6b7280; font-size: 0.9em; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold; }}
        .badge-l0 {{ background: #e5e7eb; color: #374151; }}
        .badge-l1 {{ background: #dbeafe; color: #1e40af; }}
        .badge-l2 {{ background: #d1fae5; color: #065f46; }}
        .explain {{ background: #fffbeb; border-left: 4px solid #f59e0b; padding: 10px 15px; margin: 10px 0; }}
        footer {{ margin-top: 40px; padding-top: 10px; border-top: 1px solid #e5e7eb; color: #9ca3af; font-size: 0.85em; }}
    </style>
</head>
<body>
    <h1>PROMEOS Bill Intelligence — Rapport d'Audit</h1>

    <div class="summary">
        <div class="card">
            <div class="value">{inv.get("invoice_id", "")}</div>
            <div class="label">Facture</div>
        </div>
        <div class="card">
            <div class="value">{inv.get("total_ttc", "N/A")} EUR</div>
            <div class="label">Total TTC</div>
        </div>
        <div class="card">
            <div class="value">{report.total_anomalies}</div>
            <div class="label">Anomalies</div>
        </div>
        <div class="card">
            <div class="value"><span class="badge badge-{report.coverage_level.lower()}">{report.coverage_level}</span></div>
            <div class="label">Niveau Couverture</div>
        </div>
    </div>

    <h2>Informations generales</h2>
    <table>
        <tr><th>Champ</th><th>Valeur</th></tr>
        <tr><td>Fournisseur</td><td>{inv.get("supplier", "")}</td></tr>
        <tr><td>Energie</td><td>{inv.get("energy_type", "")}</td></tr>
        <tr><td>Contrat</td><td>{inv.get("contract_ref", "") or "-"}</td></tr>
        <tr><td>PDL/PCE</td><td>{inv.get("pdl_pce", "") or "-"}</td></tr>
        <tr><td>Periode</td><td>{inv.get("period_start", "")} → {inv.get("period_end", "")}</td></tr>
        <tr><td>Consommation</td><td>{inv.get("conso_kwh", "") or "-"} kWh</td></tr>
        <tr><td>Total HT</td><td>{inv.get("total_ht", "") or "-"} EUR</td></tr>
        <tr><td>Total TVA</td><td>{inv.get("total_tva", "") or "-"} EUR</td></tr>
        <tr><td>Total TTC</td><td>{inv.get("total_ttc", "") or "-"} EUR</td></tr>
    </table>

    <h2>Composantes ({inv.get("nb_components", 0)})</h2>
    <table>
        <tr><th>Type</th><th>Label</th><th>Qty</th><th>Unite</th><th>PU</th><th>HT</th><th>TVA%</th><th>TVA</th><th>Concept</th><th>Conf.</th></tr>
        {component_rows}
    </table>

    <h2>Allocation par concept</h2>
    <table>
        <tr><th>Concept</th><th>Montant HT (EUR)</th></tr>
        {"".join(f"<tr><td>{k}</td><td>{v:.2f}</td></tr>" for k, v in sorted(report.concept_allocations.items()))}
    </table>

    <h2>Anomalies ({report.total_anomalies})</h2>
    {"<p>Aucune anomalie detectee.</p>" if not anomalies else ""}
    {"<table><tr><th>Severite</th><th>Type</th><th>Message</th><th>Composante</th><th>Attendu</th><th>Reel</th><th>Ecart</th><th>Regle</th></tr>" + anomaly_rows + "</table>" if anomalies else ""}

    <h2>Shadow Billing</h2>
    <table>
        <tr><th>Champ</th><th>Facture</th><th>Shadow</th><th>Ecart</th></tr>
        <tr><td>Total HT</td><td>{inv.get("total_ht", "")}</td><td>{shadow.get("shadow_total_ht", "")}</td><td>{shadow.get("delta_ht", "")}</td></tr>
        <tr><td>Total TTC</td><td>{inv.get("total_ttc", "")}</td><td>{shadow.get("shadow_total_ttc", "")}</td><td>{shadow.get("delta_ttc", "")}</td></tr>
        <tr><td>Ecart %</td><td colspan="3">{shadow.get("delta_percent", "")}%</td></tr>
    </table>

    <h2>Explications</h2>
    {"".join(f'<div class="explain">{e}</div>' for e in report.explain_log)}

    {f'<h2>Economies potentielles</h2><p style="font-size:1.5em;color:#065f46;font-weight:bold">{report.potential_savings_eur} EUR</p>' if report.potential_savings_eur else ""}

    <h2>KB Evidence (P5)</h2>
    {_build_kb_evidence_html(anomalies)}

    <footer>
        <p>PROMEOS Bill Intelligence v{ENGINE_VERSION} — Genere le {report.generated_at or ""}</p>
        <p>20 regles d'audit V0 executees — Niveau {report.coverage_level}</p>
    </footer>
</body>
</html>"""

    return html
