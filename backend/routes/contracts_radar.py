"""
PROMEOS — V99 Contract Renewal Radar Routes
Grand public endpoints for DAF/Direction Achats.
"""

import hashlib
from datetime import date, timedelta, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from routes.patrimoine import _get_org_id, _load_contract_with_org_check
from models import ActionItem, ActionSourceType, ActionStatus, EnergyContract

router = APIRouter(prefix="/api/contracts", tags=["Contract Radar"])


# ── Schemas ──────────────────────────────────────────────────────────


class ScenarioActionCreate(BaseModel):
    scenario: str  # "A", "B", or "C"


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/radar")
def get_contract_radar(
    request: Request,
    portfolio_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    days: int = Query(90, ge=30, le=365),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Portfolio-level renewal radar for DAF/Direction Achats."""
    from services.contract_radar_service import compute_contract_radar

    org_id = _get_org_id(request, auth, db)
    return compute_contract_radar(db, org_id, portfolio_id=portfolio_id, site_id=site_id, horizon_days=days)


@router.get("/{contract_id}/purchase-scenarios")
def get_purchase_scenarios(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """3 simple purchase scenarios for a contract.

    ⚠️ DÉPRÉCIÉ — Utilise des facteurs prix fixes.
    Préférer POST /api/purchase/compute/{site_id} pour les scénarios market-based.
    """
    from services.purchase_scenarios_service import compute_purchase_scenarios

    org_id = _get_org_id(request, auth, db)
    _load_contract_with_org_check(db, contract_id, org_id)
    result = compute_purchase_scenarios(db, contract_id)
    result["_deprecated"] = (
        "Ce endpoint utilise des facteurs prix fixes (demo). "
        "Utilisez POST /api/purchase/compute/{site_id} pour les scenarios market-based."
    )
    return result


@router.post("/{contract_id}/actions/from-scenario")
def create_actions_from_scenario(
    contract_id: int,
    body: ScenarioActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create 3-5 PROMEOS actions from a purchase scenario."""
    if body.scenario not in ("A", "B", "C"):
        raise HTTPException(status_code=400, detail="Scénario doit être A, B ou C")

    from services.purchase_scenarios_service import compute_purchase_scenarios

    org_id = _get_org_id(request, auth, db)
    ct = _load_contract_with_org_check(db, contract_id, org_id)

    scenario_data = compute_purchase_scenarios(db, contract_id)
    scenario = next((s for s in scenario_data["scenarios"] if s["id"] == body.scenario), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    created = []
    for i, action_text in enumerate(scenario["recommended_actions"]):
        idem_key = hashlib.sha256(f"v99:{contract_id}:{body.scenario}:{i}".encode()).hexdigest()[:32]

        existing = db.query(ActionItem).filter(ActionItem.idempotency_key == idem_key).first()
        if existing:
            created.append({"id": existing.id, "title": existing.title, "status": "existing"})
            continue

        # Due date: end_date - notice_period, or end_date - 30 if past
        due = None
        if ct.end_date:
            notice = ct.notice_period_days or 90
            due = ct.end_date - timedelta(days=notice)
            if due < date.today():
                due = ct.end_date - timedelta(days=30)
                if due < date.today():
                    due = date.today() + timedelta(days=14)

        item = ActionItem(
            org_id=org_id,
            site_id=ct.site_id,
            source_type=ActionSourceType.PURCHASE,
            source_id=f"v99:contract:{contract_id}:scenario:{body.scenario}",
            source_key=f"v99:{contract_id}:{body.scenario}:{i}",
            title=action_text,
            rationale=f"Scénario « {scenario['label']} » pour contrat {ct.supplier_name}",
            priority=2,
            severity="medium",
            due_date=due,
            status=ActionStatus.OPEN,
            idempotency_key=idem_key,
            evidence_required=False,
            category="finance",
        )
        db.add(item)
        db.flush()
        created.append({"id": item.id, "title": item.title, "status": "created"})

    db.commit()
    return {
        "contract_id": contract_id,
        "scenario": body.scenario,
        "scenario_label": scenario["label"],
        "actions_created": len([a for a in created if a["status"] == "created"]),
        "actions_existing": len([a for a in created if a["status"] == "existing"]),
        "actions": created,
    }


@router.get("/{contract_id}/scenario-summary")
def get_scenario_summary(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """1-page printable summary of 3 scenarios for a contract."""
    from services.purchase_scenarios_service import compute_purchase_scenarios

    org_id = _get_org_id(request, auth, db)
    ct = _load_contract_with_org_check(db, contract_id, org_id)
    scenarios = compute_purchase_scenarios(db, contract_id)

    site = ct.site
    return {
        "contract_id": contract_id,
        "site_id": ct.site_id,
        "site_name": site.nom if site else f"Site {ct.site_id}",
        "supplier_name": ct.supplier_name,
        "end_date": ct.end_date.isoformat() if ct.end_date else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenarios": scenarios["scenarios"],
    }
