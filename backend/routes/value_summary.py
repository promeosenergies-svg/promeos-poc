"""
PROMEOS — Value Summary (CX Gap #6)
GET /api/value-summary — valeur cumulée créée par PROMEOS depuis l'abonnement.

Agrège UNIQUEMENT des données déjà calculées :
- BillingInsight.estimated_loss_eur (anomalies facturation résolues)
- ComplianceFinding.estimated_penalty_eur (pénalités évitées)
- ActionItem.estimated_savings_eur_year (ROI actions complétées)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import get_effective_org_id
from models import Organisation, Site, Portefeuille, EntiteJuridique, ComplianceFinding
from models.billing_models import BillingInsight
from models.enums import InsightStatus

router = APIRouter(prefix="/api", tags=["Value Summary"])


@router.get("/value-summary")
def get_value_summary(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Valeur cumulée créée par PROMEOS pour l'organisation.
    Agrégation simple sur données existantes. Zéro nouveau calcul.
    """
    effective_org_id = get_effective_org_id(auth, org_id)
    if not effective_org_id:
        return {
            "total_eur": 0,
            "since": None,
            "anomalies_detected_eur": 0,
            "penalties_avoided_eur": 0,
            "insights_count": 0,
            "actions_completed": 0,
        }

    # Date d'abonnement = created_at de l'organisation
    org = db.query(Organisation).filter(Organisation.id == effective_org_id).first()
    since = org.created_at.isoformat() if org and org.created_at else None

    # Site IDs de l'org via join chain
    site_ids = [
        row[0]
        for row in db.query(Site.id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == effective_org_id)
        .all()
    ]

    # 1. Anomalies facturation résolues (BillingInsight.estimated_loss_eur)
    anomalies_eur = 0.0
    insights_count = 0
    if site_ids:
        anomalies_eur = (
            db.query(func.coalesce(func.sum(BillingInsight.estimated_loss_eur), 0.0))
            .filter(
                BillingInsight.site_id.in_(site_ids),
                BillingInsight.insight_status.in_([InsightStatus.RESOLVED, InsightStatus.ACK]),
            )
            .scalar()
            or 0.0
        )
        insights_count = (
            db.query(func.count(BillingInsight.id)).filter(BillingInsight.site_id.in_(site_ids)).scalar() or 0
        )

    # 2. Pénalités évitées (ComplianceFinding résolus)
    penalties_eur = 0.0
    if site_ids:
        penalties_eur = (
            db.query(func.coalesce(func.sum(ComplianceFinding.estimated_penalty_eur), 0.0))
            .filter(
                ComplianceFinding.site_id.in_(site_ids),
                ComplianceFinding.status == "resolved",
            )
            .scalar()
            or 0.0
        )

    total_eur = float(anomalies_eur) + float(penalties_eur)

    return {
        "total_eur": round(total_eur, 2),
        "since": since,
        "anomalies_detected_eur": round(float(anomalies_eur), 2),
        "penalties_avoided_eur": round(float(penalties_eur), 2),
        "insights_count": int(insights_count),
        "actions_completed": 0,
        "sites_count": len(site_ids),
    }
