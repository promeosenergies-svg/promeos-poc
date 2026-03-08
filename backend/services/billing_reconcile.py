"""
PROMEOS — Auto-reconciliation compteur/facture apres import (Step 9 B3).
Appelle reconcile_metered_billed et cree un BillingInsight si ecart > 10%.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import BillingInsight, InsightStatus, EnergyInvoice, Site

logger = logging.getLogger(__name__)


def auto_reconcile_after_import(
    db: Session,
    site_id: int,
    period_start: Optional[date],
    period_end: Optional[date],
) -> Optional[dict]:
    """
    Rapprochement automatique compteur/facture apres import.
    - Appelle reconcile_metered_billed
    - Si ecart > 10%, cree un BillingInsight type="reconciliation_mismatch"
    - Idempotent : ne cree pas de doublon pour meme site + periode
    - Ne leve jamais d'exception (try/except) pour ne pas bloquer l'import
    """
    if not period_start or not period_end:
        return None

    try:
        from services.consumption_unified_service import reconcile_metered_billed

        result = reconcile_metered_billed(db, site_id, period_start, period_end)

        if result.get("status") == "insufficient_data":
            return {"status": "insufficient_data", "site_id": site_id}

        delta_pct = result.get("delta_pct")
        if delta_pct is None:
            return {"status": "no_delta", "site_id": site_id}

        if abs(delta_pct) <= 10:
            return {"status": "aligned", "site_id": site_id, "delta_pct": delta_pct}

        # Ecart > 10% — verifier idempotence (pas de doublon)
        period_tag = f"{period_start.isoformat()}_{period_end.isoformat()}"
        existing = (
            db.query(BillingInsight)
            .filter(
                BillingInsight.site_id == site_id,
                BillingInsight.type == "reconciliation_mismatch",
                BillingInsight.message.contains(period_tag),
            )
            .first()
        )
        if existing:
            return {
                "status": "already_exists",
                "site_id": site_id,
                "insight_id": existing.id,
            }

        severity = "high" if abs(delta_pct) > 20 else "medium"
        metered = result.get("metered_kwh", 0)
        billed = result.get("billed_kwh", 0)

        message = (
            f"Ecart de {abs(delta_pct):.1f}% entre compteur ({metered:.0f} kWh) "
            f"et facture ({billed:.0f} kWh) sur la periode {period_tag}. "
            f"Verifiez les releves ou la facture."
        )

        insight = BillingInsight(
            site_id=site_id,
            type="reconciliation_mismatch",
            severity=severity,
            message=message,
            estimated_loss_eur=None,
            insight_status=InsightStatus.OPEN,
        )
        db.add(insight)
        db.flush()

        logger.info(
            "Reconciliation mismatch site=%s period=%s delta=%.1f%% → insight #%s",
            site_id,
            period_tag,
            delta_pct,
            insight.id,
        )

        return {
            "status": "mismatch_created",
            "site_id": site_id,
            "insight_id": insight.id,
            "delta_pct": delta_pct,
            "severity": severity,
        }

    except Exception as e:
        logger.warning("auto_reconcile_after_import failed site=%s: %s", site_id, str(e)[:200])
        return {"status": "error", "site_id": site_id, "error": str(e)[:200]}
