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
    compute_site_signals,  # V42
)
from services.tertiaire_proofs import (  # V45
    PROOF_CATALOG, get_expected_proofs_for_efa, list_proofs_status,
)
from services.tertiaire_proof_catalog import (  # V50
    get_proof_types, get_issue_proof_mapping, get_proofs_for_issue,
)
from services.tertiaire_proof_templates import generate_proof_templates  # V50

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

    # V44: Dedup warning — check if site already has an active/draft EFA
    dedup_warning = None
    if inferred_site_id:
        existing_efas = db.query(TertiaireEfa).filter(
            TertiaireEfa.site_id == inferred_site_id,
            TertiaireEfa.deleted_at.is_(None),
            TertiaireEfa.statut.in_([EfaStatut.DRAFT, EfaStatut.ACTIVE]),
        ).all()
        if existing_efas:
            names = ", ".join(e.nom for e in existing_efas[:3])
            dedup_warning = f"Ce site a déjà {len(existing_efas)} EFA existante(s) : {names}"

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
    if dedup_warning:
        result["dedup_warning"] = dedup_warning
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


# ── Site Signals V42 ─────────────────────────────────────────────────────────

@router.get("/site-signals")
def site_signals(org_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """V42: Qualification des sites patrimoine vis-à-vis du Décret tertiaire."""
    return compute_site_signals(db, org_id)


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


# ── Proof catalog + status V45 ───────────────────────────────────────────────

@router.get("/proof-catalog")
def get_proof_catalog():
    """V45: Catalogue des preuves OPERAT attendues."""
    return {"proofs": list(PROOF_CATALOG.values()), "total": len(PROOF_CATALOG)}


@router.get("/efa/{efa_id}/proofs")
def get_efa_proofs(
    efa_id: int,
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """V45: Statut des preuves pour une EFA (expected/deposited/validated)."""
    efa = db.query(TertiaireEfa).filter(
        TertiaireEfa.id == efa_id,
        TertiaireEfa.deleted_at.is_(None),
    ).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")
    return list_proofs_status(db, efa_id, year)


class ProofLinkBody(BaseModel):
    kb_doc_id: str
    proof_type: str
    year: Optional[int] = None
    issue_code: Optional[str] = None


@router.post("/efa/{efa_id}/proofs/link", status_code=201)
def link_proof_to_efa(
    efa_id: int,
    body: ProofLinkBody,
    db: Session = Depends(get_db),
):
    """V45: Lie un document KB à une EFA comme preuve."""
    efa = db.query(TertiaireEfa).filter(
        TertiaireEfa.id == efa_id,
        TertiaireEfa.deleted_at.is_(None),
    ).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    # Dedup: check if artifact already exists
    existing = db.query(TertiaireProofArtifact).filter(
        TertiaireProofArtifact.efa_id == efa_id,
        TertiaireProofArtifact.kb_doc_id == body.kb_doc_id,
        TertiaireProofArtifact.type == body.proof_type,
    ).first()
    if existing:
        return {
            "id": existing.id,
            "status": "already_linked",
            "message": "Ce document est déjà lié à cette EFA",
        }

    import json
    artifact = TertiaireProofArtifact(
        efa_id=efa_id,
        type=body.proof_type,
        kb_doc_id=body.kb_doc_id,
        owner_role=efa.role_assujetti,
        tags_json=json.dumps({
            "year": body.year,
            "issue_code": body.issue_code,
            "proof_type": body.proof_type,
        }),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    return {
        "id": artifact.id,
        "status": "linked",
        "type": artifact.type,
        "kb_doc_id": artifact.kb_doc_id,
        "efa_id": efa_id,
    }


# ── Proof Catalog V2 (V50) ──────────────────────────────────────────────────

@router.get("/proofs/catalog")
def proof_catalog_v2():
    """V50: Catalogue enrichi des types de preuves OPERAT."""
    return get_proof_types()


@router.get("/proofs/issue-mapping")
def proof_issue_mapping():
    """V50: Mapping issue_code → preuves attendues."""
    return get_issue_proof_mapping()


@router.get("/issues/{issue_code}/proofs")
def issue_proofs(issue_code: str):
    """V50: Preuves attendues pour un code d'issue donné."""
    return get_proofs_for_issue(issue_code)


# ── Template generation V50 ─────────────────────────────────────────────────

class ProofTemplateBody(BaseModel):
    issue_code: str
    proof_types: List[str]
    action_id: Optional[int] = None


@router.post("/efa/{efa_id}/proofs/templates")
def create_proof_templates(
    efa_id: int,
    body: ProofTemplateBody,
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    """V50: Génère des modèles de preuves dans la Mémobox (draft)."""
    efa = db.query(TertiaireEfa).filter(
        TertiaireEfa.id == efa_id,
        TertiaireEfa.deleted_at.is_(None),
    ).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    return generate_proof_templates(
        efa_id=efa_id,
        year=year,
        issue_code=body.issue_code,
        proof_types=body.proof_types,
        action_id=body.action_id,
        efa_nom=efa.nom,
    )
