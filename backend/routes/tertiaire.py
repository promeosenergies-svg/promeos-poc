"""
PROMEOS V39 — Routes Tertiaire / OPERAT
Namespace: /api/tertiaire
"""
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    TertiaireEfa, TertiaireEfaLink, TertiaireEfaBuilding,
    TertiaireResponsibility, TertiairePerimeterEvent,
    TertiaireDeclaration, TertiaireProofArtifact, TertiaireDataQualityIssue,
    EfaStatut, EfaRole, DeclarationStatus, PerimeterEventType,
    DataQualityIssueStatus,
    Site, Batiment,  # V41
)
from services.tertiaire_service import (
    qualify_efa, run_controls, precheck_declaration,
    generate_operat_pack, get_tertiaire_dashboard,
)

router = APIRouter(prefix="/api/tertiaire", tags=["Tertiaire / OPERAT"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class BuildingWithUsage(BaseModel):
    building_id: int
    usage_label: str


class EfaCreate(BaseModel):
    org_id: int
    site_id: Optional[int] = None
    nom: str
    role_assujetti: str = "proprietaire"
    reporting_start: Optional[str] = None
    reporting_end: Optional[str] = None
    notes: Optional[str] = None
    buildings: Optional[List[BuildingWithUsage]] = None  # V41


class EfaUpdate(BaseModel):
    nom: Optional[str] = None
    statut: Optional[str] = None
    role_assujetti: Optional[str] = None
    reporting_start: Optional[str] = None
    reporting_end: Optional[str] = None
    notes: Optional[str] = None


class BuildingAssoc(BaseModel):
    building_id: Optional[int] = None
    usage_label: Optional[str] = None
    surface_m2: Optional[float] = None


class ResponsibilityCreate(BaseModel):
    role: str
    entity_type: Optional[str] = None
    entity_value: Optional[str] = None
    contact_email: Optional[str] = None
    scope_json: Optional[str] = None


class PerimeterEventCreate(BaseModel):
    type: str
    effective_date: str
    description: Optional[str] = None
    justification: Optional[str] = None


class EfaLinkCreate(BaseModel):
    parent_efa_id: int
    reason: str


class IssueStatusUpdate(BaseModel):
    status: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _efa_to_dict(efa: TertiaireEfa) -> dict:
    return {
        "id": efa.id,
        "org_id": efa.org_id,
        "site_id": efa.site_id,
        "nom": efa.nom,
        "statut": efa.statut.value if efa.statut else None,
        "role_assujetti": efa.role_assujetti.value if efa.role_assujetti else None,
        "reporting_start": str(efa.reporting_start) if efa.reporting_start else None,
        "reporting_end": str(efa.reporting_end) if efa.reporting_end else None,
        "closed_at": str(efa.closed_at) if efa.closed_at else None,
        "notes": efa.notes,
        "created_at": str(efa.created_at) if efa.created_at else None,
    }


def _building_to_dict(b: TertiaireEfaBuilding) -> dict:
    return {
        "id": b.id,
        "efa_id": b.efa_id,
        "building_id": b.building_id,
        "usage_label": b.usage_label,
        "surface_m2": b.surface_m2,
    }


def _resp_to_dict(r: TertiaireResponsibility) -> dict:
    return {
        "id": r.id,
        "efa_id": r.efa_id,
        "role": r.role.value if r.role else None,
        "entity_type": r.entity_type,
        "entity_value": r.entity_value,
        "contact_email": r.contact_email,
    }


def _event_to_dict(e: TertiairePerimeterEvent) -> dict:
    return {
        "id": e.id,
        "efa_id": e.efa_id,
        "type": e.type.value if e.type else None,
        "effective_date": str(e.effective_date) if e.effective_date else None,
        "description": e.description,
        "justification": e.justification,
    }


def _issue_to_dict(i: TertiaireDataQualityIssue) -> dict:
    return {
        "id": i.id,
        "efa_id": i.efa_id,
        "year": i.year,
        "code": i.code,
        "severity": i.severity.value if i.severity else None,
        "message_fr": i.message_fr,
        "impact_fr": i.impact_fr,
        "action_fr": i.action_fr,
        "status": i.status.value if i.status else None,
        "proof_required_json": i.proof_required_json,
        "proof_owner_role": i.proof_owner_role,
    }


# ── CRUD EFA ─────────────────────────────────────────────────────────────────

@router.get("/efa")
def list_efas(
    org_id: Optional[int] = Query(None),
    statut: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(TertiaireEfa).filter(TertiaireEfa.deleted_at.is_(None))
    if org_id:
        query = query.filter(TertiaireEfa.org_id == org_id)
    if statut:
        query = query.filter(TertiaireEfa.statut == statut)
    efas = query.order_by(TertiaireEfa.created_at.desc()).all()
    return {"efas": [_efa_to_dict(e) for e in efas], "total": len(efas)}


@router.post("/efa", status_code=201)
def create_efa(body: EfaCreate, db: Session = Depends(get_db)):
    # V41: Validate buildings if provided
    batiment_lookup = {}
    if body.buildings:
        building_ids = [b.building_id for b in body.buildings]
        batiments = db.query(Batiment).filter(
            Batiment.id.in_(building_ids),
            Batiment.deleted_at.is_(None),
        ).all()
        found_ids = {b.id for b in batiments}
        missing = set(building_ids) - found_ids
        if missing:
            raise HTTPException(404, f"Bâtiment(s) introuvable(s) : {sorted(missing)}")
        batiment_lookup = {b.id: b for b in batiments}

    # Infer site_id from first building if not provided
    inferred_site_id = body.site_id
    if not inferred_site_id and batiment_lookup:
        first_bat = batiment_lookup[body.buildings[0].building_id]
        inferred_site_id = first_bat.site_id

    efa = TertiaireEfa(
        org_id=body.org_id,
        site_id=inferred_site_id,
        nom=body.nom,
        statut=EfaStatut.DRAFT,
        role_assujetti=EfaRole(body.role_assujetti),
        reporting_start=date.fromisoformat(body.reporting_start) if body.reporting_start else None,
        reporting_end=date.fromisoformat(body.reporting_end) if body.reporting_end else None,
        notes=body.notes,
    )
    db.add(efa)
    db.flush()  # get efa.id for building rows

    # V41: Create building associations with snapshotted surface
    created_buildings = []
    if body.buildings and batiment_lookup:
        for bw in body.buildings:
            bat = batiment_lookup[bw.building_id]
            assoc = TertiaireEfaBuilding(
                efa_id=efa.id,
                building_id=bw.building_id,
                usage_label=bw.usage_label,
                surface_m2=bat.surface_m2,  # snapshot from patrimoine
            )
            db.add(assoc)
            created_buildings.append(assoc)

    db.commit()
    db.refresh(efa)

    result = _efa_to_dict(efa)
    if created_buildings:
        result["buildings"] = [_building_to_dict(b) for b in created_buildings]
    return result


@router.get("/efa/{efa_id}")
def get_efa(efa_id: int, db: Session = Depends(get_db)):
    efa = db.query(TertiaireEfa).filter(
        TertiaireEfa.id == efa_id,
        TertiaireEfa.deleted_at.is_(None),
    ).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    buildings = db.query(TertiaireEfaBuilding).filter(
        TertiaireEfaBuilding.efa_id == efa_id
    ).all()
    resps = db.query(TertiaireResponsibility).filter(
        TertiaireResponsibility.efa_id == efa_id
    ).all()
    events = db.query(TertiairePerimeterEvent).filter(
        TertiairePerimeterEvent.efa_id == efa_id
    ).order_by(TertiairePerimeterEvent.effective_date.desc()).all()
    declarations = db.query(TertiaireDeclaration).filter(
        TertiaireDeclaration.efa_id == efa_id
    ).order_by(TertiaireDeclaration.year.desc()).all()
    proofs = db.query(TertiaireProofArtifact).filter(
        TertiaireProofArtifact.efa_id == efa_id
    ).all()
    issues = db.query(TertiaireDataQualityIssue).filter(
        TertiaireDataQualityIssue.efa_id == efa_id,
        TertiaireDataQualityIssue.status == DataQualityIssueStatus.OPEN,
    ).all()
    links = db.query(TertiaireEfaLink).filter(
        (TertiaireEfaLink.child_efa_id == efa_id) | (TertiaireEfaLink.parent_efa_id == efa_id)
    ).all()

    result = _efa_to_dict(efa)
    result["buildings"] = [_building_to_dict(b) for b in buildings]
    result["responsibilities"] = [_resp_to_dict(r) for r in resps]
    result["events"] = [_event_to_dict(e) for e in events]
    result["declarations"] = [
        {
            "id": d.id, "year": d.year,
            "status": d.status.value if d.status else None,
            "exported_pack_path": d.exported_pack_path,
        }
        for d in declarations
    ]
    result["proofs"] = [
        {"id": p.id, "type": p.type, "kb_doc_id": p.kb_doc_id, "file_path": p.file_path}
        for p in proofs
    ]
    result["open_issues"] = [_issue_to_dict(i) for i in issues]
    result["links"] = [
        {"id": l.id, "child_efa_id": l.child_efa_id, "parent_efa_id": l.parent_efa_id, "reason": l.reason}
        for l in links
    ]
    result["qualification"] = qualify_efa(db, efa_id)
    return result


@router.patch("/efa/{efa_id}")
def update_efa(efa_id: int, body: EfaUpdate, db: Session = Depends(get_db)):
    efa = db.query(TertiaireEfa).filter(
        TertiaireEfa.id == efa_id,
        TertiaireEfa.deleted_at.is_(None),
    ).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    if body.nom is not None:
        efa.nom = body.nom
    if body.statut is not None:
        efa.statut = EfaStatut(body.statut)
    if body.role_assujetti is not None:
        efa.role_assujetti = EfaRole(body.role_assujetti)
    if body.reporting_start is not None:
        efa.reporting_start = date.fromisoformat(body.reporting_start)
    if body.reporting_end is not None:
        efa.reporting_end = date.fromisoformat(body.reporting_end)
    if body.notes is not None:
        efa.notes = body.notes

    db.commit()
    db.refresh(efa)
    return _efa_to_dict(efa)


@router.delete("/efa/{efa_id}")
def delete_efa(efa_id: int, db: Session = Depends(get_db)):
    efa = db.query(TertiaireEfa).filter(
        TertiaireEfa.id == efa_id,
        TertiaireEfa.deleted_at.is_(None),
    ).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    from datetime import datetime
    efa.deleted_at = datetime.utcnow()
    db.commit()
    return {"status": "deleted", "efa_id": efa_id}


# ── Buildings ────────────────────────────────────────────────────────────────

@router.post("/efa/{efa_id}/buildings", status_code=201)
def add_building(efa_id: int, body: BuildingAssoc, db: Session = Depends(get_db)):
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    assoc = TertiaireEfaBuilding(
        efa_id=efa_id,
        building_id=body.building_id,
        usage_label=body.usage_label,
        surface_m2=body.surface_m2,
    )
    db.add(assoc)
    db.commit()
    db.refresh(assoc)
    return _building_to_dict(assoc)


# ── Responsibilities ─────────────────────────────────────────────────────────

@router.post("/efa/{efa_id}/responsibilities", status_code=201)
def add_responsibility(efa_id: int, body: ResponsibilityCreate, db: Session = Depends(get_db)):
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    resp = TertiaireResponsibility(
        efa_id=efa_id,
        role=EfaRole(body.role),
        entity_type=body.entity_type,
        entity_value=body.entity_value,
        contact_email=body.contact_email,
        scope_json=body.scope_json,
    )
    db.add(resp)
    db.commit()
    db.refresh(resp)
    return _resp_to_dict(resp)


# ── Perimeter events ─────────────────────────────────────────────────────────

@router.post("/efa/{efa_id}/events", status_code=201)
def add_event(efa_id: int, body: PerimeterEventCreate, db: Session = Depends(get_db)):
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    event = TertiairePerimeterEvent(
        efa_id=efa_id,
        type=PerimeterEventType(body.type),
        effective_date=date.fromisoformat(body.effective_date),
        description=body.description,
        justification=body.justification,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _event_to_dict(event)


# ── EFA links ────────────────────────────────────────────────────────────────

@router.post("/efa/{efa_id}/links", status_code=201)
def add_efa_link(efa_id: int, body: EfaLinkCreate, db: Session = Depends(get_db)):
    child = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    parent = db.query(TertiaireEfa).filter(TertiaireEfa.id == body.parent_efa_id).first()
    if not child or not parent:
        raise HTTPException(404, "EFA introuvable (child ou parent)")

    link = TertiaireEfaLink(
        child_efa_id=efa_id,
        parent_efa_id=body.parent_efa_id,
        reason=body.reason,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"id": link.id, "child_efa_id": link.child_efa_id, "parent_efa_id": link.parent_efa_id, "reason": link.reason}


# ── Controls & Precheck ──────────────────────────────────────────────────────

@router.post("/efa/{efa_id}/controls")
def run_efa_controls(efa_id: int, year: int = Query(None), db: Session = Depends(get_db)):
    issues = run_controls(db, efa_id, year)
    return {"efa_id": efa_id, "year": year, "issues": issues, "total": len(issues)}


@router.post("/efa/{efa_id}/precheck")
def precheck_efa(efa_id: int, year: int = Query(...), db: Session = Depends(get_db)):
    result = precheck_declaration(db, efa_id, year)
    if result.get("status") == "not_found":
        raise HTTPException(404, "EFA introuvable")
    return result


# ── Export pack ──────────────────────────────────────────────────────────────

@router.post("/efa/{efa_id}/export-pack")
def export_pack(efa_id: int, year: int = Query(...), db: Session = Depends(get_db)):
    result = generate_operat_pack(db, efa_id, year)
    if result.get("status") == "not_found":
        raise HTTPException(404, "EFA introuvable")
    return result


# ── Issues management ────────────────────────────────────────────────────────

@router.get("/issues")
def list_issues(
    efa_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(TertiaireDataQualityIssue)
    if efa_id:
        query = query.filter(TertiaireDataQualityIssue.efa_id == efa_id)
    if status:
        query = query.filter(TertiaireDataQualityIssue.status == status)
    if severity:
        query = query.filter(TertiaireDataQualityIssue.severity == severity)
    issues = query.order_by(TertiaireDataQualityIssue.created_at.desc()).all()
    return {"issues": [_issue_to_dict(i) for i in issues], "total": len(issues)}


@router.patch("/issues/{issue_id}")
def update_issue_status(issue_id: int, body: IssueStatusUpdate, db: Session = Depends(get_db)):
    issue = db.query(TertiaireDataQualityIssue).filter(
        TertiaireDataQualityIssue.id == issue_id
    ).first()
    if not issue:
        raise HTTPException(404, "Issue introuvable")
    issue.status = DataQualityIssueStatus(body.status)
    db.commit()
    return _issue_to_dict(issue)


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(org_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    return get_tertiaire_dashboard(db, org_id)


# ── Catalog (patrimoine buildings for wizard) ────────────────────────────────

@router.get("/catalog")
def building_catalog(
    org_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Sites + bâtiments pour le wizard EFA (scoped org)."""
    sites = db.query(Site).filter(
        Site.actif.is_(True),
        Site.deleted_at.is_(None),
    ).order_by(Site.nom).all()

    result = []
    for site in sites:
        bats = db.query(Batiment).filter(
            Batiment.site_id == site.id,
            Batiment.deleted_at.is_(None),
        ).all()
        result.append({
            "site_id": site.id,
            "site_nom": site.nom,
            "ville": site.ville,
            "batiments": [
                {
                    "id": b.id,
                    "nom": b.nom,
                    "surface_m2": b.surface_m2,
                    "annee_construction": b.annee_construction,
                }
                for b in bats
            ],
        })

    return {
        "sites": result,
        "total_buildings": sum(len(s["batiments"]) for s in result),
    }
