"""
PROMEOS Bill Intelligence — FastAPI Router
Endpoints pour import, audit, shadow billing, rapport.
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path

router = APIRouter(prefix="/api/bill", tags=["Bill Intelligence"])


# ========================================
# Pydantic models
# ========================================

class InvoiceImportRequest(BaseModel):
    json_content: str  # raw JSON string


class AuditRequest(BaseModel):
    invoice_id: str


class BatchAuditRequest(BaseModel):
    invoice_ids: Optional[List[str]] = None  # None = all demo


# ========================================
# Endpoints
# ========================================

@router.get("/demo/invoices")
def list_demo_invoices():
    """List available demo invoices."""
    from .parsers.json_parser import list_demo_invoices
    files = list_demo_invoices()
    return {"invoices": files, "count": len(files)}


@router.get("/demo/invoices/{filename}")
def get_demo_invoice(filename: str):
    """Parse and return a demo invoice."""
    from .parsers.json_parser import parse_json_file
    demo_dir = Path(__file__).resolve().parent.parent.parent / "data" / "invoices" / "demo"
    fpath = demo_dir / filename
    if not fpath.exists():
        raise HTTPException(status_code=404, detail=f"Demo invoice {filename} not found")
    try:
        invoice = parse_json_file(str(fpath))
        return invoice.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)[:200]}")


@router.post("/import")
def import_invoice(request: InvoiceImportRequest):
    """Import a JSON invoice and parse it."""
    from .parsers.json_parser import parse_json_invoice
    try:
        invoice = parse_json_invoice(request.json_content)
        return {"status": "imported", "invoice": invoice.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import error: {str(e)[:200]}")


@router.post("/audit/{invoice_id}")
def audit_invoice_endpoint(invoice_id: str):
    """
    Audit a demo invoice: run 20 V0 rules + shadow billing L1.
    Returns full audit report.
    """
    from .parsers.json_parser import parse_json_file
    from .engine import full_pipeline

    demo_dir = Path(__file__).resolve().parent.parent.parent / "data" / "invoices" / "demo"

    # Find invoice file
    candidates = list(demo_dir.glob(f"*{invoice_id}*"))
    if not candidates:
        # Try all files, match by invoice_id inside
        for f in demo_dir.glob("*.json"):
            try:
                inv = parse_json_file(str(f))
                if inv.invoice_id == invoice_id:
                    candidates = [f]
                    break
            except Exception:
                continue

    if not candidates:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    try:
        invoice = parse_json_file(str(candidates[0]))
        report = full_pipeline(invoice)
        return {
            "status": "audited",
            "invoice_id": report.invoice_id,
            "coverage_level": report.coverage_level,
            "total_anomalies": report.total_anomalies,
            "critical_anomalies": report.critical_anomalies,
            "potential_savings_eur": report.potential_savings_eur,
            "anomalies": report.anomalies,
            "shadow": report.shadow,
            "explain_log": report.explain_log,
            "engine_version": report.engine_version,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit error: {str(e)[:200]}")


@router.post("/audit-all")
def audit_all_demo():
    """Audit all demo invoices. Returns summary."""
    from .parsers.json_parser import load_all_demo_invoices
    from .engine import full_pipeline

    invoices = load_all_demo_invoices()
    results = []
    for inv in invoices:
        try:
            report = full_pipeline(inv)
            results.append({
                "invoice_id": report.invoice_id,
                "coverage_level": report.coverage_level,
                "total_anomalies": report.total_anomalies,
                "critical_anomalies": report.critical_anomalies,
                "potential_savings_eur": report.potential_savings_eur,
                "energy_type": inv.energy_type.value,
                "supplier": inv.supplier,
                "total_ttc": inv.total_ttc,
            })
        except Exception as e:
            results.append({"invoice_id": inv.invoice_id, "error": str(e)[:200]})

    total_savings = sum(r.get("potential_savings_eur", 0) or 0 for r in results)
    total_anomalies = sum(r.get("total_anomalies", 0) for r in results)

    return {
        "status": "ok",
        "invoices_audited": len(results),
        "total_anomalies": total_anomalies,
        "total_potential_savings_eur": round(total_savings, 2),
        "results": results,
    }


@router.get("/report/{invoice_id}", response_class=HTMLResponse)
def get_report_html(invoice_id: str):
    """Generate HTML audit report for an invoice."""
    from .parsers.json_parser import parse_json_file
    from .engine import full_pipeline, report_to_html

    demo_dir = Path(__file__).resolve().parent.parent.parent / "data" / "invoices" / "demo"
    candidates = list(demo_dir.glob(f"*{invoice_id}*"))

    if not candidates:
        for f in demo_dir.glob("*.json"):
            try:
                from .parsers.json_parser import parse_json_file as pjf
                inv = pjf(str(f))
                if inv.invoice_id == invoice_id:
                    candidates = [f]
                    break
            except Exception:
                continue

    if not candidates:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")

    invoice = parse_json_file(str(candidates[0]))
    report = full_pipeline(invoice)
    html = report_to_html(report)
    return HTMLResponse(content=html)


@router.get("/anomalies/csv", response_class=PlainTextResponse)
def export_anomalies_csv():
    """Export all anomalies from all demo invoices as CSV."""
    from .parsers.json_parser import load_all_demo_invoices
    from .engine import audit_invoice, anomalies_to_csv

    invoices = load_all_demo_invoices()
    all_csv_parts = []

    # Header
    all_csv_parts.append(
        "invoice_id;anomaly_id;type;severity;message;component;expected;actual;difference;rule_card_id"
    )

    for inv in invoices:
        inv = audit_invoice(inv)
        for a in inv.anomalies:
            d = a.to_dict()
            row = ";".join([
                str(inv.invoice_id),
                str(d.get("anomaly_id", "")),
                str(d.get("anomaly_type", "")),
                str(d.get("severity", "")),
                str(d.get("message", "")).replace(";", ","),
                str(d.get("component_type", "") or ""),
                str(d.get("expected_value", "") or ""),
                str(d.get("actual_value", "") or ""),
                str(d.get("difference", "") or ""),
                str(d.get("rule_card_id", "")),
            ])
            all_csv_parts.append(row)

    return PlainTextResponse(
        content="\n".join(all_csv_parts),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anomalies_promeos.csv"},
    )


@router.get("/rules")
def list_audit_rules():
    """List all V0 audit rules."""
    from .rules.audit_rules_v0 import ALL_RULES
    return {
        "rules": [
            {"id": r[0], "name": r[1], "function": r[2].__name__}
            for r in ALL_RULES
        ],
        "count": len(ALL_RULES),
        "engine_version": "0.1.0-poc",
    }


@router.get("/coverage")
def get_coverage():
    """Get coverage dashboard data for all demo invoices."""
    from .parsers.json_parser import load_all_demo_invoices
    from .engine import full_pipeline

    invoices = load_all_demo_invoices()
    by_level = {"L0": 0, "L1": 0, "L2": 0, "L3": 0}
    by_energy = {"elec": 0, "gaz": 0}
    total_ht = 0.0
    total_anomalies = 0

    for inv in invoices:
        report = full_pipeline(inv)
        by_level[report.coverage_level] = by_level.get(report.coverage_level, 0) + 1
        by_energy[inv.energy_type.value] = by_energy.get(inv.energy_type.value, 0) + 1
        total_ht += inv.total_ht or 0
        total_anomalies += report.total_anomalies

    return {
        "total_invoices": len(invoices),
        "by_level": by_level,
        "by_energy": by_energy,
        "total_ht_eur": round(total_ht, 2),
        "total_anomalies": total_anomalies,
        "coverage_percent": {
            "L0": round(by_level["L0"] / max(len(invoices), 1) * 100, 1),
            "L1": round(by_level["L1"] / max(len(invoices), 1) * 100, 1),
            "L2": round(by_level["L2"] / max(len(invoices), 1) * 100, 1),
            "L3": round(by_level["L3"] / max(len(invoices), 1) * 100, 1),
        },
    }


@router.get("/timeline")
def get_timeline(
    site_id: Optional[int] = Query(None, description="Filter by site_id"),
    energy: Optional[str] = Query(None, description="Filter by energy type (elec/gaz)"),
    start_year: int = Query(2023, description="Start year"),
    start_month: int = Query(1, description="Start month"),
    end_year: int = Query(2024, description="End year"),
    end_month: int = Query(12, description="End month"),
):
    """
    Timeline 24 mois: affiche les slots mensuels avec gaps et overlaps.
    Groupes par (site_id, energy_type).
    """
    from .parsers.json_parser import load_all_demo_invoices
    from .engine import audit_invoice
    from .timeline import build_timeline

    invoices = load_all_demo_invoices()

    # Filter
    if site_id is not None:
        invoices = [i for i in invoices if i.site_id == site_id]
    if energy is not None:
        invoices = [i for i in invoices if i.energy_type.value == energy]

    # Audit each invoice for anomaly counts
    audited = []
    for inv in invoices:
        inv = audit_invoice(inv)
        audited.append(inv)

    timelines = build_timeline(
        audited,
        start_year=start_year, start_month=start_month,
        end_year=end_year, end_month=end_month,
    )

    total_gaps = sum(len(t.gaps) for t in timelines)
    total_overlaps = sum(len(t.overlaps) for t in timelines)

    return {
        "status": "ok",
        "timelines_count": len(timelines),
        "total_gaps": total_gaps,
        "total_overlaps": total_overlaps,
        "timelines": [t.to_dict() for t in timelines],
    }


@router.get("/dashboard")
def get_dashboard():
    """
    Dashboard coverage L0-L3 avec KPIs agregees.
    """
    from .parsers.json_parser import load_all_demo_invoices
    from .timeline import build_coverage_dashboard

    invoices = load_all_demo_invoices()
    dashboard = build_coverage_dashboard(invoices)
    return {"status": "ok", **dashboard}


@router.get("/pdf/templates")
def list_pdf_templates():
    """List available PDF parser templates."""
    from .parsers.pdf_parser import list_templates
    templates = list_templates()
    return {"templates": templates, "count": len(templates)}


@router.post("/pdf/parse")
def parse_pdf_text_endpoint(request: InvoiceImportRequest):
    """
    Parse extracted PDF text into an Invoice.
    Accepts raw text (as extracted from a PDF) and auto-detects the template.
    """
    from .parsers.pdf_parser import parse_pdf_text
    try:
        invoice = parse_pdf_text(request.json_content)
        return {"status": "parsed", "invoice": invoice.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)[:200]}")
