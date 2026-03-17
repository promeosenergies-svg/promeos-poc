"""
PROMEOS - Patrimoine Billing routes.
Payment rules CRUD + reconciliation endpoints.
"""

import csv
import io
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import (
    EntiteJuridique,
    Portefeuille,
    Site,
    PaymentRule,
    PaymentRuleLevel,
)
from middleware.auth import get_optional_auth, AuthContext

from routes.patrimoine._helpers import (
    _get_org_id,
    _check_portfolio_belongs_to_org,
    _load_site_with_org_check,
    _load_contract_with_org_check,
    _serialize_payment_rule,
    _resolve_payment_rule,
    PaymentRuleCreateRequest,
    PaymentRuleBulkApplyRequest,
    ReconciliationFixRequest,
)

router = APIRouter(tags=["Patrimoine"])


# ========================================
# V96: Payment Rules CRUD
# ========================================


@router.get("/payment-rules")
def list_payment_rules(
    request: Request,
    level: Optional[str] = None,
    portefeuille_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List payment rules — scoped to org."""
    org_id = _get_org_id(request, auth, db)
    q = (
        db.query(PaymentRule)
        .join(EntiteJuridique, PaymentRule.invoice_entity_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    if level:
        try:
            q = q.filter(PaymentRule.level == PaymentRuleLevel(level))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Niveau invalide: {level}")
    if portefeuille_id is not None:
        q = q.filter(PaymentRule.portefeuille_id == portefeuille_id)
    rules = q.all()
    return {"rules": [_serialize_payment_rule(pr) for pr in rules]}


@router.post("/payment-rules")
def create_payment_rule(
    request: Request,
    body: PaymentRuleCreateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create or upsert a payment rule at any level."""
    org_id = _get_org_id(request, auth, db)

    try:
        lvl = PaymentRuleLevel(body.level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Niveau invalide: {body.level}")

    # Validate entity belongs to org
    ej = (
        db.query(EntiteJuridique)
        .filter(
            EntiteJuridique.id == body.invoice_entity_id,
            EntiteJuridique.organisation_id == org_id,
        )
        .first()
    )
    if not ej:
        raise HTTPException(status_code=404, detail="Entite juridique facturee non trouvee")

    if body.payer_entity_id:
        pej = (
            db.query(EntiteJuridique)
            .filter(
                EntiteJuridique.id == body.payer_entity_id,
                EntiteJuridique.organisation_id == org_id,
            )
            .first()
        )
        if not pej:
            raise HTTPException(status_code=404, detail="Entite juridique payeuse non trouvee")

    # Validate scope target
    if lvl == PaymentRuleLevel.PORTEFEUILLE and body.portefeuille_id:
        _check_portfolio_belongs_to_org(db, body.portefeuille_id, org_id)
    elif lvl == PaymentRuleLevel.SITE and body.site_id:
        _load_site_with_org_check(db, body.site_id, org_id)
    elif lvl == PaymentRuleLevel.CONTRAT and body.contract_id:
        _load_contract_with_org_check(db, body.contract_id, org_id)

    # Upsert: check for existing rule at same scope
    existing = (
        db.query(PaymentRule)
        .filter(
            PaymentRule.level == lvl,
            PaymentRule.portefeuille_id == body.portefeuille_id,
            PaymentRule.site_id == body.site_id,
            PaymentRule.contract_id == body.contract_id,
        )
        .first()
    )

    if existing:
        existing.invoice_entity_id = body.invoice_entity_id
        existing.payer_entity_id = body.payer_entity_id
        existing.cost_center = body.cost_center
        db.commit()
        return _serialize_payment_rule(existing)

    pr = PaymentRule(
        level=lvl,
        portefeuille_id=body.portefeuille_id,
        site_id=body.site_id,
        contract_id=body.contract_id,
        invoice_entity_id=body.invoice_entity_id,
        payer_entity_id=body.payer_entity_id,
        cost_center=body.cost_center,
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return _serialize_payment_rule(pr)


@router.put("/payment-rules/{rule_id}")
def update_payment_rule(
    rule_id: int,
    request: Request,
    body: PaymentRuleCreateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Update an existing payment rule."""
    org_id = _get_org_id(request, auth, db)
    pr = db.query(PaymentRule).filter(PaymentRule.id == rule_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail=f"Regle {rule_id} non trouvee")

    # Check org ownership via invoice entity
    ej = (
        db.query(EntiteJuridique)
        .filter(
            EntiteJuridique.id == pr.invoice_entity_id,
            EntiteJuridique.organisation_id == org_id,
        )
        .first()
    )
    if not ej:
        raise HTTPException(status_code=404, detail=f"Regle {rule_id} non trouvee")

    pr.invoice_entity_id = body.invoice_entity_id
    pr.payer_entity_id = body.payer_entity_id
    pr.cost_center = body.cost_center
    db.commit()
    return _serialize_payment_rule(pr)


@router.delete("/payment-rules/{rule_id}")
def delete_payment_rule(
    rule_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Delete a payment rule."""
    org_id = _get_org_id(request, auth, db)
    pr = db.query(PaymentRule).filter(PaymentRule.id == rule_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail=f"Regle {rule_id} non trouvee")

    ej = (
        db.query(EntiteJuridique)
        .filter(
            EntiteJuridique.id == pr.invoice_entity_id,
            EntiteJuridique.organisation_id == org_id,
        )
        .first()
    )
    if not ej:
        raise HTTPException(status_code=404, detail=f"Regle {rule_id} non trouvee")

    db.delete(pr)
    db.commit()
    return {"detail": f"Regle {rule_id} supprimee"}


@router.post("/payment-rules/apply-bulk")
def apply_payment_rules_bulk(
    request: Request,
    body: PaymentRuleBulkApplyRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Apply payment rule to N sites atomically."""
    org_id = _get_org_id(request, auth, db)

    ej = (
        db.query(EntiteJuridique)
        .filter(
            EntiteJuridique.id == body.invoice_entity_id,
            EntiteJuridique.organisation_id == org_id,
        )
        .first()
    )
    if not ej:
        raise HTTPException(status_code=404, detail="Entite juridique non trouvee")

    db.begin_nested()  # SAVEPOINT
    created = 0
    for sid in body.site_ids:
        _load_site_with_org_check(db, sid, org_id)
        existing = (
            db.query(PaymentRule)
            .filter(
                PaymentRule.level == PaymentRuleLevel.SITE,
                PaymentRule.site_id == sid,
            )
            .first()
        )
        if existing:
            existing.invoice_entity_id = body.invoice_entity_id
            existing.payer_entity_id = body.payer_entity_id
            existing.cost_center = body.cost_center
        else:
            db.add(
                PaymentRule(
                    level=PaymentRuleLevel.SITE,
                    site_id=sid,
                    invoice_entity_id=body.invoice_entity_id,
                    payer_entity_id=body.payer_entity_id,
                    cost_center=body.cost_center,
                )
            )
            created += 1

    db.commit()
    return {"applied": len(body.site_ids), "created": created}


@router.get("/sites/{site_id}/payment-info")
def get_site_payment_info(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Resolve effective payment rule for a site (contrat > site > portefeuille)."""
    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)

    pr = _resolve_payment_rule(db, site_id)
    if not pr:
        return {"resolved": False, "rule": None, "source_level": None}

    # Load entity names
    inv_ej = db.get(EntiteJuridique, pr.invoice_entity_id)
    pay_ej = db.get(EntiteJuridique, pr.payer_entity_id) if pr.payer_entity_id else None

    return {
        "resolved": True,
        "source_level": pr.level.value if pr.level else None,
        "rule": _serialize_payment_rule(pr),
        "invoice_entity_name": inv_ej.nom if inv_ej else None,
        "payer_entity_name": pay_ej.nom if pay_ej else None,
    }


# ========================================
# V96: Reconciliation endpoints
# ========================================


@router.get("/sites/{site_id}/reconciliation")
def get_site_reconciliation(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """3-way reconciliation for a single site."""
    from services.reconciliation_service import reconcile_site

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)
    return reconcile_site(db, site_id)


@router.get("/portfolio/reconciliation")
def get_portfolio_reconciliation(
    request: Request,
    portefeuille_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Aggregate reconciliation across all sites in scope."""
    from services.reconciliation_service import reconcile_portfolio

    org_id = _get_org_id(request, auth, db)
    if portefeuille_id:
        _check_portfolio_belongs_to_org(db, portefeuille_id, org_id)
    return reconcile_portfolio(db, org_id, portefeuille_id)


# ========================================
# V97: Resolution Engine endpoints
# ========================================


@router.post("/sites/{site_id}/reconciliation/fix")
def apply_reconciliation_fix(
    site_id: int,
    request: Request,
    body: ReconciliationFixRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V97: Apply a 1-click fix for a reconciliation check."""
    from services.reconciliation_service import (
        fix_create_delivery_point,
        fix_extend_contract,
        fix_adjust_contract_dates,
        fix_align_energy_type,
        fix_create_payment_rule,
    )

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)

    params = body.params or {}
    applied_by = auth.user_email if auth and hasattr(auth, "user_email") else None

    FIXERS = {
        "create_delivery_point": fix_create_delivery_point,
        "extend_contract": fix_extend_contract,
        "adjust_contract_dates": fix_adjust_contract_dates,
        "align_energy_type": fix_align_energy_type,
        "create_payment_rule": fix_create_payment_rule,
    }

    fixer = FIXERS.get(body.action)
    if not fixer:
        raise HTTPException(status_code=400, detail=f"Action inconnue: {body.action}")

    db.begin_nested()
    result = fixer(db, site_id, **params, applied_by=applied_by)
    db.commit()

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"ok": True, "action": body.action, "result": result}


@router.get("/sites/{site_id}/reconciliation/history")
def get_reconciliation_fix_history(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V97: Get audit trail for reconciliation fixes on a site."""
    from services.reconciliation_service import get_fix_logs

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)
    return {"site_id": site_id, "logs": get_fix_logs(db, site_id)}


@router.get("/sites/{site_id}/reconciliation/evidence")
def get_reconciliation_evidence(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V97 Phase 4: Get evidence pack (JSON) for a site's reconciliation."""
    from services.reconciliation_service import get_evidence_pack

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)
    return get_evidence_pack(db, site_id)


@router.get("/sites/{site_id}/reconciliation/evidence/summary")
def get_reconciliation_evidence_summary(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V98: Get 1-page evidence summary for a site's reconciliation."""
    from services.reconciliation_service import get_evidence_summary

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)
    return get_evidence_summary(db, site_id)


@router.get("/sites/{site_id}/reconciliation/evidence/csv")
def get_reconciliation_evidence_csv(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V97 Phase 4: Export evidence pack as CSV."""
    from services.reconciliation_service import get_evidence_pack

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)
    pack = get_evidence_pack(db, site_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["check_id", "label_fr", "status", "reason_fr", "suggestion_fr"])
    for check in pack["reconciliation"]["checks"]:
        writer.writerow(
            [
                check["id"],
                check["label_fr"],
                check["status"],
                check["reason_fr"],
                check.get("suggestion_fr", ""),
            ]
        )
    writer.writerow([])
    writer.writerow(["fix_id", "check_id", "action", "status_before", "status_after", "applied_by", "applied_at"])
    for log in pack["fix_history"]:
        writer.writerow(
            [
                log["id"],
                log["check_id"],
                log["action"],
                log["status_before"],
                log["status_after"],
                log.get("applied_by", ""),
                log.get("applied_at", ""),
            ]
        )

    content = output.getvalue()
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=evidence_site_{site_id}.csv"},
    )


@router.get("/portfolio/reconciliation/evidence/csv")
def get_portfolio_evidence_csv(
    request: Request,
    portefeuille_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V97 Phase 4: Export portfolio reconciliation summary as CSV."""
    from services.reconciliation_service import reconcile_portfolio

    org_id = _get_org_id(request, auth, db)
    if portefeuille_id:
        _check_portfolio_belongs_to_org(db, portefeuille_id, org_id)
    data = reconcile_portfolio(db, org_id, portefeuille_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["site_id", "nom", "status", "score"])
    for s in data["sites"]:
        writer.writerow([s["site_id"], s["nom"], s["status"], s["score"]])
    writer.writerow([])
    writer.writerow(["stat", "value"])
    for k, v in data["stats"].items():
        writer.writerow([k, v])

    content = output.getvalue()
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio_reconciliation.csv"},
    )
