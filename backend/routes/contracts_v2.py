"""
PROMEOS — Contrats V2 (Cadre + Annexes) API Routes.
17 endpoints pour CRUD cadre/annexe, coherence, KPIs, events, import.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from routes.patrimoine import _get_org_id
from schemas.contract_v2_schemas import (
    AnnexeCreateSchema,
    AnnexeUpdateSchema,
    CadreCreateSchema,
    CadreUpdateSchema,
    EventSchema,
    SUPPLIERS_CRE,
    PRICING_MODELS,
)
from services import contract_v2_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts/v2", tags=["Contracts V2 – Cadre+Annexe"])


# ── Cadres ─────────────────────────────────────────────────────────────


@router.get("/cadres")
def list_cadres(
    request: Request,
    status: Optional[str] = Query(None),
    energy_type: Optional[str] = Query(None),
    supplier: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste contrats cadre avec annexes et KPIs."""
    org_id = _get_org_id(request, auth, db)
    return svc.list_cadres(db, org_id, status=status, energy_type=energy_type, supplier=supplier, search=search)


@router.get("/cadres/kpis")
def portfolio_kpis(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """KPIs portefeuille contrats."""
    org_id = _get_org_id(request, auth, db)
    return svc.compute_portfolio_kpis(db, org_id)


@router.get("/cadres/suppliers")
def suppliers_list():
    """Liste fournisseurs CRE T4 2025."""
    return {"suppliers": SUPPLIERS_CRE, "pricing_models": PRICING_MODELS}


@router.get("/cadres/{cadre_id}")
def get_cadre(
    cadre_id: int,
    db: Session = Depends(get_db),
):
    """Detail cadre + annexes + pricing + events + coherence."""
    result = svc.get_cadre(db, cadre_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")
    return result


@router.post("/cadres", status_code=201)
def create_cadre(
    data: CadreCreateSchema,
    db: Session = Depends(get_db),
):
    """Cree contrat cadre + N annexes + pricing."""
    return svc.create_cadre(db, data)


@router.patch("/cadres/{cadre_id}")
def update_cadre(
    cadre_id: int,
    data: CadreUpdateSchema,
    db: Session = Depends(get_db),
):
    """MAJ partielle cadre."""
    result = svc.update_cadre(db, cadre_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")
    return result


@router.delete("/cadres/{cadre_id}")
def delete_cadre(
    cadre_id: int,
    db: Session = Depends(get_db),
):
    """Soft-delete cadre + annexes."""
    ok = svc.delete_cadre(db, cadre_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")
    return {"status": "deleted", "cadre_id": cadre_id}


# ── Annexes ────────────────────────────────────────────────────────────


@router.get("/cadres/{cadre_id}/annexes/{annexe_id}")
def get_annexe(
    cadre_id: int,
    annexe_id: int,
    db: Session = Depends(get_db),
):
    """Annexe + resolved pricing (merge cadre + override)."""
    result = svc.get_annexe(db, annexe_id)
    if not result or result.get("cadre_id") != cadre_id:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    return result


@router.post("/cadres/{cadre_id}/annexes", status_code=201)
def create_annexe(
    cadre_id: int,
    data: AnnexeCreateSchema,
    db: Session = Depends(get_db),
):
    """Ajouter annexe a un cadre existant."""
    result = svc.create_annexe(db, cadre_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")
    return result


@router.patch("/annexes/{annexe_id}")
def update_annexe(
    annexe_id: int,
    data: AnnexeUpdateSchema,
    db: Session = Depends(get_db),
):
    """MAJ annexe."""
    result = svc.update_annexe(db, annexe_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    return result


@router.delete("/annexes/{annexe_id}")
def delete_annexe(
    annexe_id: int,
    db: Session = Depends(get_db),
):
    """Soft-delete annexe."""
    ok = svc.delete_annexe(db, annexe_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    return {"status": "deleted", "annexe_id": annexe_id}


# ── Events ─────────────────────────────────────────────────────────────


@router.post("/cadres/{cadre_id}/events", status_code=201)
def add_event(
    cadre_id: int,
    data: EventSchema,
    db: Session = Depends(get_db),
):
    """Ajouter evenement lifecycle au cadre."""
    from models.contract_v2_models import ContractEvent
    from models.billing_models import EnergyContract

    cadre = (
        db.query(EnergyContract)
        .filter(
            EnergyContract.id == cadre_id,
            EnergyContract.is_cadre == True,  # noqa: E712
        )
        .first()
    )
    if not cadre:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")

    event = ContractEvent(
        contract_id=cadre_id,
        event_type=data.event_type,
        event_date=data.event_date,
        description=data.description,
        meta_json=data.meta_json,
    )
    db.add(event)
    db.commit()
    return {"id": event.id, "event_type": event.event_type, "event_date": str(event.event_date)}


# ── Analyses ───────────────────────────────────────────────────────────


@router.get("/cadres/{cadre_id}/coherence")
def coherence_check(
    cadre_id: int,
    db: Session = Depends(get_db),
):
    """Check coherence 12 regles."""
    results = svc.coherence_check(db, cadre_id)
    return {"cadre_id": cadre_id, "rules": results, "total": len(results)}


@router.get("/annexes/{annexe_id}/shadow-gap")
def shadow_gap(
    annexe_id: int,
    db: Session = Depends(get_db),
):
    """Ecart shadow billing pour une annexe."""
    return svc.compute_shadow_gap(db, annexe_id)


# ── Import ─────────────────────────────────────────────────────────────


@router.post("/import/csv")
async def import_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Import CSV/Excel multi-lignes avec auto-groupement cadre+annexes."""
    org_id = _get_org_id(request, auth, db)
    content = (await file.read()).decode("utf-8-sig")
    return svc.import_csv(db, org_id, content)


@router.get("/import/template")
def import_template():
    """Template CSV pour import contrats."""
    from fastapi.responses import PlainTextResponse

    header = "supplier,contract_ref,energy_type,start_date,end_date,site_id,annexe_ref,tariff_option,subscribed_power_kva,segment_enedis"
    example = "EDF Entreprises,CADRE-2026-001,elec,2026-07-01,2029-06-30,1,ANX-001,hp_hc,108,C5"
    return PlainTextResponse(
        content=f"{header}\n{example}\n",
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=promeos_contrats_template.csv"},
    )
