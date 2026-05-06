"""
PROMEOS — Bill Intelligence routes (Sprint C-5 Phase 5.1, ADR-013).

Endpoint org-scopé `GET /api/bill-intelligence/anomalies` exposant les anomalies de
facturation détectées par `services/bill_intelligence/anomaly_detector.py`.

Filtres : code (R19/R20), severity (critical/warning/info), resolved (bool).
Sprint C-7 Phase 7.7 Lot D : Literal Enum validation + pagination + KPI agrégat.

Org-scoping cardinal via `resolve_org_id` + JOIN chain
EnergyInvoice → Site → Portefeuille → EntiteJuridique.organisation_id.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models import BillAnomaly, EnergyInvoice, EntiteJuridique, Portefeuille, Site
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/bill-intelligence", tags=["Bill Intelligence"])


# Sprint C-7 Phase 7.7 Lot D — D-Sprint-C7-BillAnomaly-Endpoint-Enum-Validation-001 P2 :
# Literal types contraignent FastAPI à valider les query params côté entrée
# (422 sur valeur hors enum vs 200 silencieux avec liste vide auparavant).
BillAnomalyCode = Literal["R19", "R20"]
BillAnomalySeverity = Literal["critical", "warning", "info"]


@router.get("/anomalies")
def list_bill_anomalies(
    request: Request,
    code: Optional[BillAnomalyCode] = Query(
        None,
        description="Filtre par code (R19=VNU dormant, R20=capacité variance)",
    ),
    severity: Optional[BillAnomalySeverity] = Query(
        None,
        description="Filtre par sévérité (critical, warning, info)",
    ),
    resolved: Optional[bool] = Query(
        None,
        description="True = anomalies résolues, False = ouvertes, None = toutes",
    ),
    period_start: Optional[date] = Query(
        None,
        description="Sprint C-7 Phase 7.7 Lot D : filtre invoice.period_start >= date",
    ),
    period_end: Optional[date] = Query(
        None,
        description="Sprint C-7 Phase 7.7 Lot D : filtre invoice.period_end <= date",
    ),
    limit: int = Query(50, ge=1, le=200, description="Pagination — max 200 par page"),
    offset: int = Query(0, ge=0, description="Pagination — offset"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les anomalies de facturation org-scopées + KPI agrégé.

    Filtrage cardinal :
    - `code` : R19 (VNU dormant), R20 (capacité variance) — Literal validé 422
    - `severity` : critical / warning / info — Literal validé 422
    - `resolved` : True (résolues) / False (ouvertes) / None (toutes)
    - `period_start` / `period_end` : filtres date sur EnergyInvoice
    - `limit` / `offset` : pagination (1-200 / 0+)

    Sprint C-7 Phase 7.7 Lot D nouvelles fonctionnalités :
    - D-Sprint-C7-BillAnomaly-Endpoint-Enum-Validation-001 : Literal validation 422
    - D-Sprint-C7-BillAnomaly-Endpoint-Pagination-001 : limit/offset + filtres date
    - D-Sprint-C7-BillIntelligence-KPI-Aggregate-001 : KPI total_economie_potentielle_eur

    Sécurité : strict org-scoping via JOIN chain
    BillAnomaly → EnergyInvoice → Site → Portefeuille → EntiteJuridique.organisation_id.
    Soft-deleted exclues automatiquement (`BillAnomaly.deleted_at IS NULL`).
    """
    org_id = resolve_org_id(request, auth, db)

    # Sprint C-8 Phase 8.1 — D-Audit-Phase7-KPI-Mutation-Coherence-003 fix (P1-CR-003) :
    # base org-scopée SANS filtres user (pour KPI canonique stable cross-vues).
    # Avant fix : KPI était calculé sur base_q déjà filtrée par code/severity/resolved/period →
    # si filtre `code=R20`, KPI R19 = 0 trompeur. Maintenant : KPI canonical (org-scope only).
    org_scope_q = (
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

    base_q = org_scope_q

    if code:
        base_q = base_q.filter(BillAnomaly.code == code)
    if severity:
        base_q = base_q.filter(BillAnomaly.severity == severity)
    if resolved is True:
        base_q = base_q.filter(BillAnomaly.resolved_at.isnot(None))
    elif resolved is False:
        base_q = base_q.filter(BillAnomaly.resolved_at.is_(None))
    if period_start:
        base_q = base_q.filter(EnergyInvoice.period_start >= period_start)
    if period_end:
        base_q = base_q.filter(EnergyInvoice.period_end <= period_end)

    # KPI cardinal canonique Phase 8.1 : SUM(actual_value) R19 NON RÉSOLUES sur org_scope_q
    # (vs base_q user-filtered avant Phase 8.1). Différenciateur CFO :
    # montant VNU dormant cumulé ACTIONNABLE (resolved_at IS NULL).
    # bill-intelligence audit deep recommandation : exclusion résolues = montant à reclaim restant.
    kpi_total_economie_eur = (
        org_scope_q.filter(
            BillAnomaly.code == "R19",
            BillAnomaly.resolved_at.is_(None),
        )
        .with_entities(func.coalesce(func.sum(BillAnomaly.actual_value), 0.0))
        .scalar()
    )

    total_count = base_q.count()
    anomalies = base_q.order_by(BillAnomaly.detected_at.desc()).limit(limit).offset(offset).all()

    return {
        "count": len(anomalies),
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "kpi_total_economie_potentielle_eur": float(kpi_total_economie_eur or 0.0),
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
