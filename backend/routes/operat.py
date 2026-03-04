"""
PROMEOS — OPERAT Export routes (Chantier 2)
POST /api/operat/export          — generate OPERAT CSV and return as download
POST /api/operat/export/preview  — preview export data (JSON)
POST /api/operat/export/validate — validate before export (errors + warnings)
"""

from typing import Optional, List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.operat_export_service import generate_operat_csv, log_operat_export, validate_operat_export

router = APIRouter(prefix="/api/operat", tags=["operat-export"])


class ExportRequest(BaseModel):
    org_id: int
    year: int
    efa_ids: Optional[List[int]] = None


@router.post("/export")
def export_operat_csv(
    body: ExportRequest,
    db: Session = Depends(get_db),
):
    """Generate OPERAT-compatible CSV for download."""
    csv_content = generate_operat_csv(db, body.org_id, body.year, body.efa_ids)

    # Audit log
    efa_count = csv_content.count("\n") - 1  # minus header
    log_operat_export(db, body.org_id, body.year, max(0, efa_count))

    filename = f"OPERAT_export_{body.org_id}_{body.year}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export/preview")
def preview_operat_export(
    body: ExportRequest,
    db: Session = Depends(get_db),
):
    """Preview OPERAT export data without downloading (returns JSON)."""
    csv_content = generate_operat_csv(db, body.org_id, body.year, body.efa_ids)
    lines = csv_content.strip().split("\n")
    header = lines[0].split(";") if lines else []
    rows = []
    for line in lines[1:]:
        vals = line.split(";")
        rows.append(dict(zip(header, vals)))
    return {
        "year": body.year,
        "efa_count": len(rows),
        "columns": header,
        "rows": rows,
    }


@router.post("/export/validate")
def validate_export(
    body: ExportRequest,
    db: Session = Depends(get_db),
):
    """Validate OPERAT export data — returns errors (blocking) + warnings."""
    return validate_operat_export(db, body.org_id, body.year, body.efa_ids)
