"""
PROMEOS — Phase G : endpoints REST persona dashboards (Marie DAF + Jean-Marc CFO).

Pattern Phase E IDOR cardinal : `resolve_org_id` + scope_org_id propagé aux services.

3 endpoints cardinaux :
- GET /api/persona/marie-daf/compliance-dashboard — tableau bord conformité multi-sites
- GET /api/persona/cfo/billing-anomalies-summary — synthèse anomalies factures
- GET /api/persona/cfo/expiring-contracts — alertes fin contrat J-180 (configurable)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models import Organisation, not_deleted
from services.persona_dashboard_service import (
    build_billing_anomalies_summary_cfo,
    build_compliance_dashboard_marie_daf,
    get_contract_price_benchmark,
    list_expiring_contracts,
)
from services.persona_pdf_export import render_compliance_dashboard_pdf
from services.scope_utils import resolve_org_id


router = APIRouter(prefix="/api/persona", tags=["Persona Dashboards"])


@router.get("/marie-daf/compliance-dashboard")
def get_marie_daf_compliance_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Phase G G1 — Tableau de bord conformité multi-sites (persona Marie DAF).

    Retourne pour chaque site les statuts des 4 frameworks (DT/BACS/APER/OPERAT)
    avec deadlines countdown + sanctions provisionnées + déclencheur Audit SMÉ
    par EJ. Pattern Phase E IDOR cardinal.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    return build_compliance_dashboard_marie_daf(db, scope_org_id)


@router.get("/cfo/billing-anomalies-summary")
def get_cfo_billing_anomalies_summary(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Phase G G2.1 — Synthèse anomalies factures (persona Jean-Marc CFO).

    Retourne le total OPEN + breakdown sévérité + top 5 anomalies les plus
    impactantes (montant). Pattern Phase E IDOR cardinal.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    return build_billing_anomalies_summary_cfo(db, scope_org_id)


@router.get("/cfo/expiring-contracts")
def get_cfo_expiring_contracts(
    request: Request,
    horizon_days: int = Query(180, ge=30, le=365, description="Horizon alerte (défaut J-180)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Phase G G2.2 — Contrats expirant dans `horizon_days` (persona CFO).

    Pattern Phase E IDOR cardinal. Default J-180 = cible cardinale Jean-Marc
    pour anticiper renégociation post-ARENH 2026.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    return list_expiring_contracts(db, scope_org_id, horizon_days=horizon_days)


@router.get("/marie-daf/compliance-dashboard.pdf")
def get_marie_daf_compliance_dashboard_pdf(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Phase I3 — Export PDF dashboard conformité Marie DAF (présentation comité).

    Génère un PDF A4 (page de garde + headlines + tableau 5 frameworks par site
    + Audit SMÉ par EJ + footer réglementaire) à partir du dashboard JSON.
    Pattern Phase E IDOR cardinal.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    dashboard = build_compliance_dashboard_marie_daf(db, scope_org_id)
    org = db.query(Organisation).filter(Organisation.id == scope_org_id, not_deleted(Organisation)).first()
    org_nom = org.nom if org else "PROMEOS"
    pdf_bytes = render_compliance_dashboard_pdf(dashboard, org_nom=org_nom)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="conformite_{scope_org_id}_'
                f'{__import__("datetime").datetime.now().strftime("%Y%m%d")}.pdf"'
            )
        },
    )


@router.get("/cfo/contract-price-benchmark")
def get_cfo_contract_price_benchmark(
    request: Request,
    horizon_days: int = Query(180, ge=30, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Phase H6 — Comparateur prix marché vs prix contractuel (Jean-Marc CFO MVP).

    Pour chaque contrat expirant dans `horizon_days`, compare prix contractuel
    €/MWh vs forward EPEX/EEX baseload calendar Y+1 (zone FR) + chiffre delta
    annuel basé sur consommation historique.

    Sans données marché disponibles → `benchmark_status='no_market_data'`.
    Pattern Phase E IDOR cardinal.
    """
    scope_org_id = resolve_org_id(request, auth, db)
    return get_contract_price_benchmark(db, scope_org_id, horizon_days=horizon_days)
