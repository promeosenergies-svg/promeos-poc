"""
PROMEOS — Contrats V2 (Cadre + Annexes) API Routes.
20 endpoints pour CRUD cadre/annexe, coherence, KPIs, events, import — org-scoped.
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
    SUPPLIERS_BY_CATEGORY,
    PRICING_MODELS,
    PRICING_MODELS_ELEC,
    PRICING_MODELS_GAZ,
    TARIFF_OPTIONS_BY_SEGMENT,
    PRICING_GRID_BY_TARIFF,
    CONTRACT_DURATIONS,
    # Reponses
    CadreKpisResponse,
    CadreResponse,
    SuppliersResponse,
    DeleteResponse,
    EventResponse,
    CoherenceCheckResponse,
    ImportCsvResponse,
)
from services import contract_v2_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts/v2", tags=["Contracts V2 – Cadre+Annexe"])


# ── helpers ───────────────────────────────────────────────────────────


def _check_cadre_org(db: Session, cadre_id: int, org_id: int):
    """Verify cadre belongs to org. Returns cadre dict or raises 404."""
    result = svc.get_cadre_for_org(db, cadre_id, org_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")
    return result


# ── Cadres ─────────────────────────────────────────────────────────────


@router.get("/cadres", response_model=list[CadreResponse])
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


@router.get("/cadres/kpis", response_model=CadreKpisResponse)
def portfolio_kpis(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """KPIs portefeuille contrats."""
    org_id = _get_org_id(request, auth, db)
    return svc.compute_portfolio_kpis(db, org_id)


@router.get("/cadres/expiring", response_model=list[CadreResponse])
def expiring_cadres(
    request: Request,
    days: int = Query(90, ge=1, le=365, description="Horizon en jours"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Contrats cadre expirant dans N jours (defaut 90)."""
    org_id = _get_org_id(request, auth, db)
    return svc.list_expiring(db, org_id, days=days)


@router.get("/cadres/suppliers", response_model=SuppliersResponse)
def suppliers_list():
    """Referentiels fournisseurs, modeles de prix, options tarifaires."""
    return {
        "suppliers": SUPPLIERS_CRE,
        "suppliers_by_category": SUPPLIERS_BY_CATEGORY,
        "pricing_models": PRICING_MODELS,
        "pricing_models_elec": PRICING_MODELS_ELEC,
        "pricing_models_gaz": PRICING_MODELS_GAZ,
        "tariff_options_by_segment": TARIFF_OPTIONS_BY_SEGMENT,
        "pricing_grid_by_tariff": PRICING_GRID_BY_TARIFF,
        "contract_durations": CONTRACT_DURATIONS,
    }


@router.get("/cadres/{cadre_id}", response_model=CadreResponse)
def get_cadre(
    cadre_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Detail cadre + annexes + pricing + events + coherence (org-scoped)."""
    org_id = _get_org_id(request, auth, db)
    return _check_cadre_org(db, cadre_id, org_id)


@router.post("/cadres", status_code=201, response_model=CadreResponse)
def create_cadre(
    data: CadreCreateSchema,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Query(None, description="Cle d'idempotence"),
):
    """Cree contrat cadre + N annexes + pricing. Supporte idempotency_key."""
    if idempotency_key:
        from models.billing_models import EnergyContract

        existing = (
            db.query(EnergyContract)
            .filter(
                EnergyContract.reference_fournisseur == idempotency_key,
                EnergyContract.is_cadre == True,  # noqa: E712
            )
            .first()
        )
        if existing:
            return svc.get_cadre(db, existing.id)
    return svc.create_cadre(db, data)


@router.patch("/cadres/{cadre_id}", response_model=CadreResponse)
def update_cadre(
    cadre_id: int,
    data: CadreUpdateSchema,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """MAJ partielle cadre (org-scoped)."""
    org_id = _get_org_id(request, auth, db)
    _check_cadre_org(db, cadre_id, org_id)
    result = svc.update_cadre(db, cadre_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")
    return result


@router.delete("/cadres/{cadre_id}", response_model=DeleteResponse)
def delete_cadre(
    cadre_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Soft-delete cadre + annexes (org-scoped)."""
    org_id = _get_org_id(request, auth, db)
    _check_cadre_org(db, cadre_id, org_id)
    ok = svc.delete_cadre(db, cadre_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")
    return {"status": "deleted", "cadre_id": cadre_id}


# ── Annexes ────────────────────────────────────────────────────────────


@router.get("/cadres/{cadre_id}/annexes/{annexe_id}")
def get_annexe(
    cadre_id: int,
    annexe_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Annexe + resolved pricing (org-scoped via cadre)."""
    org_id = _get_org_id(request, auth, db)
    _check_cadre_org(db, cadre_id, org_id)
    result = svc.get_annexe(db, annexe_id)
    if not result or result.get("cadre_id") != cadre_id:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    return result


@router.post("/cadres/{cadre_id}/annexes", status_code=201)
def create_annexe(
    cadre_id: int,
    data: AnnexeCreateSchema,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    idempotency_key: str | None = Query(None, description="Cle d'idempotence"),
):
    """Ajouter annexe a un cadre existant (org-scoped). Supporte idempotency_key."""
    org_id = _get_org_id(request, auth, db)
    _check_cadre_org(db, cadre_id, org_id)
    if idempotency_key:
        from models.contract_v2_models import ContractAnnexe

        existing = (
            db.query(ContractAnnexe)
            .filter(
                ContractAnnexe.contrat_cadre_id == cadre_id,
                ContractAnnexe.annexe_ref == idempotency_key,
            )
            .first()
        )
        if existing:
            return svc.get_annexe(db, existing.id)
    result = svc.create_annexe(db, cadre_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Contrat cadre non trouve")
    return result


@router.patch("/annexes/{annexe_id}")
def update_annexe(
    annexe_id: int,
    data: AnnexeUpdateSchema,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """MAJ annexe (org-scoped via cadre)."""
    org_id = _get_org_id(request, auth, db)
    # Verify annexe's cadre belongs to org
    existing = svc.get_annexe(db, annexe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    _check_cadre_org(db, existing["cadre_id"], org_id)
    result = svc.update_annexe(db, annexe_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    return result


@router.delete("/annexes/{annexe_id}", response_model=DeleteResponse)
def delete_annexe(
    annexe_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Soft-delete annexe (org-scoped via cadre)."""
    org_id = _get_org_id(request, auth, db)
    existing = svc.get_annexe(db, annexe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    _check_cadre_org(db, existing["cadre_id"], org_id)
    ok = svc.delete_annexe(db, annexe_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    return {"status": "deleted", "annexe_id": annexe_id}


# ── Site active contract ──────────────────────────────────────────────


@router.get("/site/{site_id}/active")
def site_active_contract(
    site_id: int,
    db: Session = Depends(get_db),
):
    """Contrat actif (annexe + cadre) pour un site donne."""
    result = svc.get_site_active_contract(db, site_id)
    if not result:
        raise HTTPException(status_code=404, detail="Aucun contrat actif pour ce site")
    return result


# ── Pricing resolve ───────────────────────────────────────────────────


@router.get("/annexes/{annexe_id}/pricing")
def pricing_resolve(
    annexe_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Resolve pricing cascade pour une annexe (override > cadre structured > cadre flat)."""
    org_id = _get_org_id(request, auth, db)
    existing = svc.get_annexe(db, annexe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    _check_cadre_org(db, existing["cadre_id"], org_id)
    return {"annexe_id": annexe_id, "pricing": existing.get("resolved_pricing", [])}


# ── Events ─────────────────────────────────────────────────────────────


@router.post("/cadres/{cadre_id}/events", status_code=201, response_model=EventResponse)
def add_event(
    cadre_id: int,
    data: EventSchema,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Ajouter evenement lifecycle au cadre (org-scoped)."""
    org_id = _get_org_id(request, auth, db)
    _check_cadre_org(db, cadre_id, org_id)

    from models.contract_v2_models import ContractEvent

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


@router.get("/cadres/{cadre_id}/coherence", response_model=CoherenceCheckResponse)
def coherence_check(
    cadre_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Check coherence R1-R16 (org-scoped)."""
    org_id = _get_org_id(request, auth, db)
    _check_cadre_org(db, cadre_id, org_id)
    results = svc.coherence_check(db, cadre_id)
    return {"cadre_id": cadre_id, "rules": results, "total": len(results)}


@router.get("/annexes/{annexe_id}/shadow-gap")
def shadow_gap(
    annexe_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Ecart shadow billing pour une annexe (org-scoped via cadre)."""
    org_id = _get_org_id(request, auth, db)
    existing = svc.get_annexe(db, annexe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Annexe non trouvee")
    _check_cadre_org(db, existing["cadre_id"], org_id)
    return svc.compute_shadow_gap(db, annexe_id)


# ── Import ─────────────────────────────────────────────────────────────


@router.post("/import/csv", response_model=ImportCsvResponse)
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
