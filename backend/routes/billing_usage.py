"""
PROMEOS - Billing Usage Ventilation Routes
GET /api/billing/usage-ventilation/sites/{site_id}
    — ventile le dernier shadow bill du site par usage (estime via archetype)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access
from services.flex.archetype_resolver import resolve_archetype
from services.billing.usage_ventilation import ventile_shadow_bill_by_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing/usage-ventilation", tags=["Billing Usage Ventilation"])


@router.get("/sites/{site_id}")
def get_site_usage_ventilation(
    site_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    check_site_access(auth, site_id)
    """
    Ventile le dernier shadow bill du site par usage canonique.

    La ventilation est une estimation basee sur l'archetype du site et
    un profil de repartition sectoriel. Non mesuree.

    Returns:
        {
            "site_id": ...,
            "site_nom": ...,
            "archetype_code": "BUREAU_STANDARD",
            "period": {"start": ..., "end": ...},
            "total_kwh": ...,
            "by_usage": {"CVC_HVAC": {...}, "ECLAIRAGE": {...}, ...},
            "totals_check": {...},
            "method": "archetype_repartition",
            "confidence": "medium"
        }
    """
    from models.site import Site
    from models.energy_models import Meter

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} non trouve")

    # Derniere facture avec shadow bill calcule
    shadow_bill, period = _fetch_latest_shadow_bill(db, site_id)
    if not shadow_bill:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun shadow bill disponible pour le site {site_id}",
        )

    meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).first()
    archetype = resolve_archetype(db, site, meter)

    ventilation = ventile_shadow_bill_by_usage(shadow_bill, archetype)

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "period": period,
        **ventilation,
    }


def _fetch_latest_shadow_bill(db: Session, site_id: int) -> tuple[Optional[dict], Optional[dict]]:
    """
    Recupere la derniere facture du site et lance shadow_billing_v2 dessus.
    Retourne (shadow_bill_dict, period_dict) ou (None, None).
    """
    try:
        from sqlalchemy.orm import joinedload
        from models.billing_models import EnergyInvoice
        from services.billing_shadow_v2 import shadow_billing_v2
    except Exception as exc:
        logger.debug("billing v2 imports failed: %s", exc)
        return None, None

    try:
        invoice = (
            db.query(EnergyInvoice)
            .options(
                joinedload(EnergyInvoice.lines),
                joinedload(EnergyInvoice.contract),
            )
            .filter(EnergyInvoice.site_id == site_id)
            .order_by(EnergyInvoice.period_end.desc())
            .first()
        )
    except Exception as exc:
        logger.debug("shadow bill lookup failed for site %s: %s", site_id, exc)
        return None, None

    if not invoice:
        return None, None

    try:
        shadow_bill = shadow_billing_v2(invoice, invoice.lines, invoice.contract, db=db)
    except Exception as exc:
        logger.warning("shadow_billing_v2 failed for invoice %s: %s", invoice.id, exc)
        return None, None

    period = {
        "start": invoice.period_start.isoformat() if invoice.period_start else None,
        "end": invoice.period_end.isoformat() if invoice.period_end else None,
    }
    return shadow_bill, period
