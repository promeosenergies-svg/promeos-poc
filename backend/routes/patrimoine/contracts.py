"""
PROMEOS - Patrimoine Contract routes.
Contract CRUD.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import (
    EntiteJuridique,
    Portefeuille,
    Site,
    EnergyContract,
    BillingEnergyType,
    ContractIndexation,
    ContractStatus,
)
from middleware.auth import get_optional_auth, AuthContext
from routes.billing import check_contract_overlap

from routes.patrimoine._helpers import (
    _get_org_id,
    _load_site_with_org_check,
    _load_contract_with_org_check,
    _serialize_contract,
    ContractCreateRequest,
    ContractUpdateRequest,
)

router = APIRouter(tags=["Patrimoine"])


# ========================================
# Contract CRUD (WORLD CLASS)
# ========================================


@router.get("/contracts")
def list_contracts(
    request: Request,
    site_id: Optional[int] = None,
    energy_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List energy contracts with filters — scoped to org."""
    org_id = _get_org_id(request, auth, db)
    q = (
        db.query(EnergyContract)
        .join(Site, EnergyContract.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    if site_id is not None:
        q = q.filter(EnergyContract.site_id == site_id)
    if energy_type:
        q = q.filter(EnergyContract.energy_type == energy_type)
    total = q.count()
    contracts = q.offset(skip).limit(limit).all()
    return {"total": total, "contracts": [_serialize_contract(ct) for ct in contracts]}


@router.post("/contracts")
def create_contract(
    request: Request,
    body: ContractCreateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create a new energy contract."""
    org_id = _get_org_id(request, auth, db)
    site = _load_site_with_org_check(db, body.site_id, org_id)

    try:
        et = BillingEnergyType(body.energy_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Type energie invalide: {body.energy_type}")

    # V96 — parse optional enums
    offer_idx = None
    if body.offer_indexation:
        try:
            offer_idx = ContractIndexation(body.offer_indexation)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Indexation invalide: {body.offer_indexation}")
    ct_status = None
    if body.contract_status:
        try:
            ct_status = ContractStatus(body.contract_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut contrat invalide: {body.contract_status}")

    ct = EnergyContract(
        site_id=body.site_id,
        energy_type=et,
        supplier_name=body.supplier_name,
        start_date=date.fromisoformat(body.start_date) if body.start_date else None,
        end_date=date.fromisoformat(body.end_date) if body.end_date else None,
        price_ref_eur_per_kwh=body.price_ref_eur_per_kwh,
        fixed_fee_eur_per_month=body.fixed_fee_eur_per_month,
        notice_period_days=body.notice_period_days,
        auto_renew=body.auto_renew,
        offer_indexation=offer_idx,
        price_granularity=body.price_granularity,
        renewal_alert_days=body.renewal_alert_days,
        contract_status=ct_status,
        # V-registre
        reference_fournisseur=body.reference_fournisseur,
        date_signature=date.fromisoformat(body.date_signature) if body.date_signature else None,
        conditions_particulieres=body.conditions_particulieres,
        document_url=body.document_url,
    )
    db.add(ct)
    db.flush()
    # V-registre: rattacher les delivery points
    if body.delivery_point_ids:
        from models import DeliveryPoint as DP

        dps = db.query(DP).filter(DP.id.in_(body.delivery_point_ids), DP.site_id == body.site_id).all()
        ct.delivery_points = dps
    db.commit()
    db.refresh(ct)
    return _serialize_contract(ct)


@router.patch("/contracts/{contract_id}")
def update_contract(
    contract_id: int,
    request: Request,
    body: ContractUpdateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Update an energy contract (partial update)."""
    org_id = _get_org_id(request, auth, db)
    ct = _load_contract_with_org_check(db, contract_id, org_id)

    updates = body.model_dump(exclude_unset=True)

    # V-registre: handle delivery_point_ids separately
    dp_ids = updates.pop("delivery_point_ids", None)
    if dp_ids is not None:
        from models import DeliveryPoint as DP

        dps = db.query(DP).filter(DP.id.in_(dp_ids), DP.site_id == ct.site_id).all()
        ct.delivery_points = dps

    # Apply field values (parse dates + V96 enums + V-registre dates)
    for field, value in updates.items():
        if field in ("start_date", "end_date", "date_signature") and value is not None:
            value = date.fromisoformat(value)
        elif field == "offer_indexation" and value is not None:
            try:
                value = ContractIndexation(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Indexation invalide: {value}")
        elif field == "contract_status" and value is not None:
            try:
                value = ContractStatus(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Statut contrat invalide: {value}")
        setattr(ct, field, value)

    # If dates changed, check for overlap with other contracts
    if "start_date" in updates or "end_date" in updates:
        overlap = check_contract_overlap(
            db,
            ct.site_id,
            ct.energy_type,
            ct.start_date,
            ct.end_date,
            exclude_id=ct.id,
        )
        if overlap:
            raise HTTPException(
                status_code=409,
                detail=f"Chevauchement avec le contrat #{overlap.id} "
                f"({overlap.supplier_name}, "
                f"{overlap.start_date or '...'} → {overlap.end_date or '...'})",
            )

    db.commit()
    return {"updated": list(updates.keys()), **_serialize_contract(ct)}


@router.delete("/contracts/{contract_id}")
def delete_contract(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Delete an energy contract."""
    org_id = _get_org_id(request, auth, db)
    ct = _load_contract_with_org_check(db, contract_id, org_id)
    db.delete(ct)
    db.commit()
    return {"detail": f"Contrat {contract_id} supprime"}
