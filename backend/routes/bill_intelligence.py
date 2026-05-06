"""
PROMEOS — Bill Intelligence routes (Sprint C-5 Phase 5.1, ADR-013).

Endpoint org-scopé `GET /api/bill-intelligence/anomalies` exposant les anomalies de
facturation détectées par `services/bill_intelligence/anomaly_detector.py`.

Filtres : code (R19/R20), severity (critical/warning/info), resolved (bool).

Org-scoping cardinal via `resolve_org_id` + JOIN chain
EnergyInvoice → Site → Portefeuille → EntiteJuridique.organisation_id.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models import BillAnomaly, EnergyInvoice, EntiteJuridique, Portefeuille, Site
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/bill-intelligence", tags=["Bill Intelligence"])


@router.get("/anomalies")
def list_bill_anomalies(
    request: Request,
    code: Optional[str] = Query(None, description="Filtre par code (R19, R20, ...)"),
    severity: Optional[str] = Query(None, description="Filtre par sévérité (critical, warning, info)"),
    resolved: Optional[bool] = Query(None, description="True = anomalies résolues, False = ouvertes, None = toutes"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les anomalies de facturation org-scopées.

    Filtrage cardinal :
    - `code` : R19 (VNU dormant), R20 (capacité variance), R21+ futurs
    - `severity` : critical / warning / info
    - `resolved` : True (résolues) / False (ouvertes) / None (toutes)

    Sécurité : strict org-scoping via JOIN chain
    BillAnomaly → EnergyInvoice → Site → Portefeuille → EntiteJuridique.organisation_id.
    Soft-deleted exclues automatiquement (`BillAnomaly.deleted_at IS NULL`).
    """
    org_id = resolve_org_id(request, auth, db)

    q = (
        db.query(BillAnomaly)
        .join(EnergyInvoice, BillAnomaly.invoice_id == EnergyInvoice.id)
        .join(Site, EnergyInvoice.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(
            EntiteJuridique.organisation_id == org_id,
            BillAnomaly.deleted_at.is_(None),
        )
    )

    if code:
        q = q.filter(BillAnomaly.code == code)
    if severity:
        q = q.filter(BillAnomaly.severity == severity)
    if resolved is True:
        q = q.filter(BillAnomaly.resolved_at.isnot(None))
    elif resolved is False:
        q = q.filter(BillAnomaly.resolved_at.is_(None))

    anomalies = q.order_by(BillAnomaly.detected_at.desc()).all()

    return {
        "count": len(anomalies),
        "anomalies": [
            {
                "id": a.id,
                "invoice_id": a.invoice_id,
                "code": a.code,
                "severity": a.severity,
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "resolution_note": a.resolution_note,
                "threshold_value": float(a.threshold_value) if a.threshold_value is not None else None,
                "actual_value": float(a.actual_value) if a.actual_value is not None else None,
                "details": a.details_json,
            }
            for a in anomalies
        ],
    }
