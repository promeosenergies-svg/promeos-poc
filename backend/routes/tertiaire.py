"""
PROMEOS V39 — Routes Tertiaire / OPERAT
Namespace: /api/tertiaire
"""

from datetime import date, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access, get_effective_org_id

from database import get_db
from models import (
    TertiaireEfa,
    TertiaireEfaLink,
    TertiaireEfaBuilding,
    TertiaireResponsibility,
    TertiairePerimeterEvent,
    TertiaireDeclaration,
    TertiaireProofArtifact,
    TertiaireDataQualityIssue,
    EfaStatut,
    EfaRole,
    DeclarationStatus,
    PerimeterEventType,
    DataQualityIssueStatus,
    Site,
    Batiment,  # V41
    TertiaireEfaConsumption,
    not_deleted,
)
from services.tertiaire_service import (
    qualify_efa,
    run_controls,
    precheck_declaration,
    generate_operat_pack,
    get_tertiaire_dashboard,
    compute_site_signals,  # V42
)
from services.tertiaire_proofs import (  # V45
    PROOF_CATALOG,
    get_expected_proofs_for_efa,
    list_proofs_status,
)
from services.tertiaire_proof_catalog import (  # V50
    get_proof_types,
    get_issue_proof_mapping,
    get_proofs_for_issue,
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


# ── Site Signals response models (V42 / fix OpenAPI) ─────────────────────────

from typing import Any


class SiteSignalRuleApplied(BaseModel):
    code: str
    label_fr: str
    value: Any = None
    threshold: Any = None
    ok: bool = False


class SiteSignalCTA(BaseModel):
    label_fr: str
    to: str


class SiteSignalItem(BaseModel):
    site_id: int
    site_nom: str
    ville: Optional[str] = None
    surface_tertiaire_m2: Optional[float] = None
    nb_batiments: int = 0
    signal: str
    signal_version: Optional[str] = None
    data_complete: bool = False
    is_covered: bool = False
    efa_ids: List[int] = []
    missing_fields: Optional[List[str]] = None
    reasons_fr: Optional[List[str]] = None
    rules_applied: Optional[List[SiteSignalRuleApplied]] = None
    recommended_next_step: Optional[str] = None
    recommended_cta: Optional[SiteSignalCTA] = None


class SiteSignalCounts(BaseModel):
    assujetti_probable: int = 0
    a_verifier: int = 0
    non_concerne: int = 0


class SiteSignalsResponse(BaseModel):
    sites: List[SiteSignalItem]
    total_sites: int
    counts: SiteSignalCounts
    uncovered_probable: int = 0
    incomplete_data: int = 0
    top_missing_fields: Optional[dict] = None


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
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    statut: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    query = db.query(TertiaireEfa).filter(not_deleted(TertiaireEfa))
    if site_id:
        check_site_access(auth, site_id)
        query = query.filter(TertiaireEfa.site_id == site_id)
    elif org_id:
        effective_org_id = get_effective_org_id(auth, org_id)
        query = query.filter(TertiaireEfa.org_id == effective_org_id)
    if statut:
        query = query.filter(TertiaireEfa.statut == statut)
    efas = query.order_by(TertiaireEfa.created_at.desc()).all()
    return {"efas": [_efa_to_dict(e) for e in efas], "total": len(efas)}


@router.post("/efa", status_code=201)
def create_efa(
    body: EfaCreate, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    get_effective_org_id(auth, body.org_id)
    # V41: Validate buildings if provided
    batiment_lookup = {}
    if body.buildings:
        building_ids = [b.building_id for b in body.buildings]
        batiments = (
            db.query(Batiment)
            .filter(
                Batiment.id.in_(building_ids),
                not_deleted(Batiment),
            )
            .all()
        )
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
        existing_efas = (
            db.query(TertiaireEfa)
            .filter(
                TertiaireEfa.site_id == inferred_site_id,
                not_deleted(TertiaireEfa),
                TertiaireEfa.statut.in_([EfaStatut.DRAFT, EfaStatut.ACTIVE]),
            )
            .all()
        )
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
    efa = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.id == efa_id,
            not_deleted(TertiaireEfa),
        )
        .first()
    )
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    buildings = db.query(TertiaireEfaBuilding).filter(TertiaireEfaBuilding.efa_id == efa_id).all()
    resps = db.query(TertiaireResponsibility).filter(TertiaireResponsibility.efa_id == efa_id).all()
    events = (
        db.query(TertiairePerimeterEvent)
        .filter(TertiairePerimeterEvent.efa_id == efa_id)
        .order_by(TertiairePerimeterEvent.effective_date.desc())
        .all()
    )
    declarations = (
        db.query(TertiaireDeclaration)
        .filter(TertiaireDeclaration.efa_id == efa_id)
        .order_by(TertiaireDeclaration.year.desc())
        .all()
    )
    proofs = db.query(TertiaireProofArtifact).filter(TertiaireProofArtifact.efa_id == efa_id).all()
    issues = (
        db.query(TertiaireDataQualityIssue)
        .filter(
            TertiaireDataQualityIssue.efa_id == efa_id,
            TertiaireDataQualityIssue.status == DataQualityIssueStatus.OPEN,
        )
        .all()
    )
    links = (
        db.query(TertiaireEfaLink)
        .filter((TertiaireEfaLink.child_efa_id == efa_id) | (TertiaireEfaLink.parent_efa_id == efa_id))
        .all()
    )

    result = _efa_to_dict(efa)
    result["buildings"] = [_building_to_dict(b) for b in buildings]
    result["responsibilities"] = [_resp_to_dict(r) for r in resps]
    result["events"] = [_event_to_dict(e) for e in events]
    result["declarations"] = [
        {
            "id": d.id,
            "year": d.year,
            "status": d.status.value if d.status else None,
            "exported_pack_path": d.exported_pack_path,
        }
        for d in declarations
    ]
    result["proofs"] = [
        {"id": p.id, "type": p.type, "kb_doc_id": p.kb_doc_id, "file_path": p.file_path} for p in proofs
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
    efa = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.id == efa_id,
            not_deleted(TertiaireEfa),
        )
        .first()
    )
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
    efa = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.id == efa_id,
            not_deleted(TertiaireEfa),
        )
        .first()
    )
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    efa.soft_delete()
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
    return {
        "id": link.id,
        "child_efa_id": link.child_efa_id,
        "parent_efa_id": link.parent_efa_id,
        "reason": link.reason,
    }


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
    issue = db.query(TertiaireDataQualityIssue).filter(TertiaireDataQualityIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(404, "Issue introuvable")
    issue.status = DataQualityIssueStatus(body.status)
    db.commit()
    return _issue_to_dict(issue)


# ── Dashboard ────────────────────────────────────────────────────────────────


@router.get("/dashboard")
def dashboard(
    org_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    effective_org_id = get_effective_org_id(auth, org_id)
    if site_id:
        check_site_access(auth, site_id)
    return get_tertiaire_dashboard(db, effective_org_id, site_id=site_id)


# ── Site Signals V42 ─────────────────────────────────────────────────────────


@router.get("/site-signals", response_model=SiteSignalsResponse)
def site_signals(
    org_id: Optional[int] = Query(None, description="ID organisation (optionnel, filtre les sites)"),
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V42: Qualification des sites patrimoine vis-à-vis du Décret tertiaire."""
    effective_org_id = get_effective_org_id(auth, org_id)
    if site_id:
        check_site_access(auth, site_id)
    return compute_site_signals(db, effective_org_id, site_id=site_id)


# ── Catalog (patrimoine buildings for wizard) ────────────────────────────────


@router.get("/catalog")
def building_catalog(
    org_id: int = Query(1),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    org_id = get_effective_org_id(auth, org_id)
    """Sites + bâtiments pour le wizard EFA (scoped org)."""
    sites = (
        db.query(Site)
        .filter(
            not_deleted(Site),
        )
        .order_by(Site.nom)
        .all()
    )

    result = []
    for site in sites:
        bats = (
            db.query(Batiment)
            .filter(
                Batiment.site_id == site.id,
                not_deleted(Batiment),
            )
            .all()
        )
        result.append(
            {
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
            }
        )

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
    efa = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.id == efa_id,
            not_deleted(TertiaireEfa),
        )
        .first()
    )
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
    efa = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.id == efa_id,
            not_deleted(TertiaireEfa),
        )
        .first()
    )
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    # Dedup: check if artifact already exists
    existing = (
        db.query(TertiaireProofArtifact)
        .filter(
            TertiaireProofArtifact.efa_id == efa_id,
            TertiaireProofArtifact.kb_doc_id == body.kb_doc_id,
            TertiaireProofArtifact.type == body.proof_type,
        )
        .first()
    )
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
        tags_json=json.dumps(
            {
                "year": body.year,
                "issue_code": body.issue_code,
                "proof_type": body.proof_type,
            }
        ),
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
    efa = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.id == efa_id,
            not_deleted(TertiaireEfa),
        )
        .first()
    )
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


# ═══════════════════════════════════════════════════════════════════════
# OPERAT TRAJECTORY — consommation + trajectoire
# ═══════════════════════════════════════════════════════════════════════


class ConsumptionDeclareRequest(BaseModel):
    year: int
    kwh_total: float
    kwh_elec: Optional[float] = None
    kwh_gaz: Optional[float] = None
    kwh_reseau: Optional[float] = None
    is_reference: bool = False
    source: Optional[str] = None


@router.post("/efa/{efa_id}/consumption/declare")
def declare_efa_consumption(
    efa_id: int,
    body: ConsumptionDeclareRequest,
    request: Request = None,
    db: Session = Depends(get_db),
    auth=Depends(get_optional_auth),
):
    """Declare ou met a jour la consommation annuelle d'une EFA."""
    from services.operat_trajectory import declare_consumption
    from services.actor_resolver import resolve_actor

    _ = resolve_actor(auth, request, fallback="api_declare")  # noqa: F841 — pour future journalisation actor

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id, not_deleted(TertiaireEfa)).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    try:
        result = declare_consumption(
            db=db,
            efa_id=efa_id,
            year=body.year,
            kwh_total=body.kwh_total,
            kwh_elec=body.kwh_elec,
            kwh_gaz=body.kwh_gaz,
            kwh_reseau=body.kwh_reseau,
            is_reference=body.is_reference,
            source=body.source,
        )
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/efa/{efa_id}/targets/validate")
def validate_efa_trajectory(
    efa_id: int,
    year: int = Query(..., description="Annee d'observation"),
    db: Session = Depends(get_db),
):
    """Calcule la trajectoire OPERAT pour une EFA."""
    from services.operat_trajectory import validate_trajectory

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id, not_deleted(TertiaireEfa)).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    try:
        result = validate_trajectory(db, efa_id, year)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/efa/{efa_id}/consumption")
def get_efa_consumption_history(
    efa_id: int,
    db: Session = Depends(get_db),
):
    """Historique des consommations declarees pour une EFA."""
    from services.operat_trajectory import get_consumption_history

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id, not_deleted(TertiaireEfa)).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    return {"efa_id": efa_id, "consumptions": get_consumption_history(db, efa_id)}


@router.get("/efa/{efa_id}/proof-events")
def get_efa_proof_events(
    efa_id: int,
    db: Session = Depends(get_db),
):
    """Journal d'audit conformite pour une EFA (consommations, trajectoire, exports)."""
    from services.operat_trajectory import get_proof_events

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id, not_deleted(TertiaireEfa)).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    return {"efa_id": efa_id, "events": get_proof_events(db, efa_id)}


# ═══════════════════════════════════════════════════════════════════════
# NORMALISATION CLIMATIQUE
# ═══════════════════════════════════════════════════════════════════════


class NormalizeRequest(BaseModel):
    consumption_id: int
    dju_heating: Optional[float] = None
    dju_cooling: Optional[float] = None
    dju_reference: Optional[float] = None
    weather_data_source: str = "manual"


@router.post("/efa/{efa_id}/consumption/normalize")
def normalize_efa_consumption(
    efa_id: int,
    body: NormalizeRequest,
    db: Session = Depends(get_db),
):
    """Normalise climatiquement une consommation EFA (methode DJU)."""
    from services.operat_normalization import normalize_consumption

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id, not_deleted(TertiaireEfa)).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    try:
        result = normalize_consumption(
            db, body.consumption_id, body.dju_heating, body.dju_cooling, body.dju_reference, body.weather_data_source
        )
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/efa/{efa_id}/normalization-history")
def get_efa_normalization_history(
    efa_id: int,
    db: Session = Depends(get_db),
):
    """Historique de normalisation climatique pour une EFA."""
    from services.operat_normalization import get_normalization_history

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id, not_deleted(TertiaireEfa)).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    return {"efa_id": efa_id, "history": get_normalization_history(db, efa_id)}


class AutoNormalizeRequest(BaseModel):
    consumption_id: int
    code_postal: Optional[str] = None


@router.post("/efa/{efa_id}/consumption/auto-normalize")
def auto_normalize_efa_consumption(
    efa_id: int,
    body: AutoNormalizeRequest,
    request: Request = None,
    db: Session = Depends(get_db),
    auth=Depends(get_optional_auth),
):
    """Normalise automatiquement via le weather provider interne."""
    from services.operat_normalization import normalize_consumption
    from services.weather_provider import get_dju_for_year
    from services.actor_resolver import resolve_actor

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id, not_deleted(TertiaireEfa)).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    conso = db.query(TertiaireEfaConsumption).filter(TertiaireEfaConsumption.id == body.consumption_id).first()
    if not conso:
        raise HTTPException(404, "Consommation introuvable")

    # Resoudre le code postal depuis le site si pas fourni
    cp = body.code_postal
    if not cp and efa.site_id:
        site = db.query(Site).filter(Site.id == efa.site_id).first()
        if site:
            cp = site.code_postal
    if not cp:
        cp = "75001"  # Defaut Paris si inconnu

    # Obtenir les DJU via le weather provider
    weather = get_dju_for_year(cp, conso.year)

    actor = resolve_actor(auth, request, fallback="api_user")

    try:
        result = normalize_consumption(
            db,
            body.consumption_id,
            dju_heating=weather.dju_heating,
            dju_cooling=weather.dju_cooling,
            dju_reference=weather.dju_reference,
            weather_data_source=weather.provider,
        )
        db.commit()
        return {
            **result,
            "weather": {
                "provider": weather.provider,
                "source_ref": weather.source_ref,
                "source_verified": weather.source_verified,
                "climate_zone": weather.climate_zone,
                "confidence": weather.confidence,
                "warnings": weather.warnings,
            },
            "actor": actor,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── MUTUALISATION (simulateur inter-sites) ──────────────────────────────


@router.get("/mutualisation")
def get_mutualisation_simulation(
    org_id: int = Query(..., description="ID de l'organisation"),
    jalon: int = Query(2030, description="Jalon cible (2030, 2040 ou 2050)"),
    db: Session = Depends(get_db),
):
    """Simulation de mutualisation DT pour un portefeuille."""
    from services.tertiaire_mutualisation_service import compute_mutualisation

    if jalon not in (2030, 2040, 2050):
        raise HTTPException(400, "Jalon invalide (2030, 2040 ou 2050)")

    result = compute_mutualisation(db, org_id, jalon)
    return result.to_dict()


# ── MODULATION (simulateur dossier) ─────────────────────────────────────


class ModulationActionInput(BaseModel):
    label: str
    cout_eur: float
    economie_annuelle_kwh: float
    economie_annuelle_eur: float
    duree_vie_ans: int = 0


class ModulationConstraintInput(BaseModel):
    type: str  # technique | architecturale | economique
    description: str = ""
    actions: List[ModulationActionInput] = []


class ModulationSimulationInput(BaseModel):
    efa_id: int
    contraintes: List[ModulationConstraintInput]


@router.post("/modulation-simulation")
def post_modulation_simulation(
    body: ModulationSimulationInput,
    db: Session = Depends(get_db),
):
    """Simulation de modulation DT pour une EFA."""
    from services.tertiaire_modulation_service import simulate_modulation

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == body.efa_id, not_deleted(TertiaireEfa)).first()
    if not efa:
        raise HTTPException(404, "EFA introuvable")

    contraintes_dict = [c.model_dump() for c in body.contraintes]
    result = simulate_modulation(db, body.efa_id, contraintes_dict)
    return result.to_dict()


# ── DT Progress — Progression Décret Tertiaire ──────────────────────────

# Jalons officiels — Décret n°2019-771, art. R131-39 CCH
# Il n'existe PAS de jalon 2026 dans le texte réglementaire
_JALONS_OFFICIELS = [
    {"annee": 2030, "reduction_cible_pct": 40.0, "is_official": True, "source": "Décret n°2019-771 du 23/07/2019"},
    {"annee": 2040, "reduction_cible_pct": 50.0, "is_official": True, "source": "Décret n°2019-771 du 23/07/2019"},
    {"annee": 2050, "reduction_cible_pct": 60.0, "is_official": True, "source": "Décret n°2019-771 du 23/07/2019"},
]


def _compute_site_dt_progress(db: Session, site_id: int, annee: int, *, site=None) -> dict:
    """Calcule la progression DT pour un site en agregeant ses EFA actives.

    Delegue a operat_trajectory via dt_trajectory_service (SoT avec DJU).

    Args:
        site: optional pre-loaded Site object to avoid redundant query.
    """
    import datetime as _dt
    from services.dt_trajectory_service import compute_site_trajectory
    from services.operat_trajectory import validate_trajectory

    if site is None:
        site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {"error": "not_found", "site_id": site_id}

    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()

    if not site.tertiaire_area_m2 or site.tertiaire_area_m2 < 1000:
        return {
            "site_id": site_id,
            "site_nom": site.nom,
            "assujetti": False,
            "message": f"Surface assujettie {site.tertiaire_area_m2 or 0}m² < 1000m²",
            "source": "dt_trajectory_service",
            "computed_at": now_iso,
        }

    efas = db.query(TertiaireEfa).filter(TertiaireEfa.site_id == site_id, not_deleted(TertiaireEfa)).all()

    if not efas:
        return {
            "site_id": site_id,
            "site_nom": site.nom,
            "assujetti": True,
            "n_efa_actives": 0,
            "on_track": None,
            "reduction_pct": None,
            "message": "Aucune EFA active",
            "jalons_officiels": _JALONS_OFFICIELS,
            "source": "dt_trajectory_service",
            "computed_at": now_iso,
        }

    # Agreger les trajectoires via operat_trajectory (SoT avec DJU)
    efa_results = []
    for efa in efas:
        try:
            r = validate_trajectory(db, efa.id, annee)
            baseline = r.get("baseline") or {}
            current = r.get("current") or {}
            baseline_kwh = baseline.get("kwh")
            current_kwh = current.get("kwh")
            norm_kwh = current.get("normalized_kwh")
            effective_kwh = norm_kwh or current_kwh

            reduction = None
            if baseline_kwh and baseline_kwh > 0 and effective_kwh is not None:
                reduction = round((1 - effective_kwh / baseline_kwh) * 100, 1)

            efa_results.append(
                {
                    "efa_id": efa.id,
                    "efa_nom": efa.nom,
                    "conso_ref_kwh": baseline_kwh,
                    "conso_actuelle_kwh": current_kwh,
                    "conso_normalisee_kwh": norm_kwh,
                    "reduction_pct": reduction,
                    "on_track": r.get("final_status") == "on_track",
                    "status": r.get("final_status", "not_evaluable"),
                    "is_dju_applied": r.get("is_normalized", False),
                }
            )
        except Exception:
            pass

    if not efa_results:
        return {
            "site_id": site_id,
            "site_nom": site.nom,
            "assujetti": True,
            "n_efa_actives": len(efas),
            "on_track": None,
            "reduction_pct": None,
            "message": "Donnees insuffisantes pour calculer la trajectoire",
            "jalons_officiels": _JALONS_OFFICIELS,
            "source": "operat_trajectory",
            "computed_at": now_iso,
        }

    total_ref = sum(r["conso_ref_kwh"] or 0 for r in efa_results)
    total_act = sum(r["conso_actuelle_kwh"] or 0 for r in efa_results)
    total_norm = sum(r["conso_normalisee_kwh"] or 0 for r in efa_results if r["conso_normalisee_kwh"])
    is_dju = any(r["is_dju_applied"] for r in efa_results)
    reduction_agg = round((1 - total_act / total_ref) * 100, 1) if total_ref > 0 else None
    on_track_all = all(r["on_track"] for r in efa_results if r["on_track"] is not None)

    # Prochain jalon
    prochain_jalon = None
    for j in _JALONS_OFFICIELS:
        if annee <= j["annee"]:
            ecart = round((reduction_agg or 0) - j["reduction_cible_pct"], 1) if reduction_agg is not None else None
            prochain_jalon = {
                "annee": j["annee"],
                "reduction_cible_pct": j["reduction_cible_pct"],
                "reduction_actuelle_pct": reduction_agg,
                "ecart_pts": ecart,
                "on_track": ecart >= 0 if ecart is not None else None,
                "is_official": True,
            }
            break

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "assujetti": True,
        "n_efa_actives": len(efa_results),
        "conso_ref_kwh": round(total_ref, 0),
        "conso_actuelle_kwh": round(total_act, 0),
        "conso_normalisee_kwh": round(total_norm, 0) if is_dju else None,
        "reduction_pct": reduction_agg,
        "is_dju_applied": is_dju,
        "on_track": on_track_all,
        "prochain_jalon": prochain_jalon,
        "jalons_officiels": _JALONS_OFFICIELS,
        "detail_efa": efa_results,
        "source": "operat_trajectory",
        "computed_at": now_iso,
    }


@router.get("/sites/{site_id}/dt-progress")
def get_site_dt_progress(
    site_id: int,
    annee: int = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    check_site_access(auth, site_id)
    """Progression DT pour un site — agrégation de ses EFA actives.

    Délègue à operat_trajectory.validate_trajectory() (SoT avec DJU).
    Jalons officiels : -40% 2030 / -50% 2040 / -60% 2050.
    """
    import datetime as _dt

    if annee is None:
        annee = _dt.date.today().year

    result = _compute_site_dt_progress(db, site_id, annee)
    if result.get("error") == "not_found":
        raise HTTPException(404, f"Site {site_id} introuvable")
    return result


@router.get("/portfolio/{org_id}/dt-progress")
def get_portfolio_dt_progress(
    org_id: int,
    annee: int = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    get_effective_org_id(auth, org_id)
    """Vue multi-site trajectoire DT pour une organisation.

    Tri : off_track en premier (sites en retard prioritaires).
    Jalons officiels : -40% 2030 / -50% 2040 / -60% 2050.
    """
    import datetime as _dt

    if annee is None:
        annee = _dt.date.today().year

    from models import Portefeuille, EntiteJuridique, not_deleted as _nd

    sites = (
        _nd(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.tertiaire_area_m2 >= 1000)
        .all()
    )

    resultats = []
    n_on = n_off = n_nodata = 0

    for site in sites:
        progress = _compute_site_dt_progress(db, site.id, annee, site=site)
        on_track = progress.get("on_track")
        status = "on_track" if on_track is True else "off_track" if on_track is False else "no_data"
        if status == "on_track":
            n_on += 1
        elif status == "off_track":
            n_off += 1
        else:
            n_nodata += 1

        resultats.append(
            {
                "site_id": site.id,
                "site_nom": site.nom,
                "surface_m2": site.tertiaire_area_m2,
                "reduction_pct": progress.get("reduction_pct"),
                "on_track": on_track,
                "status": status,
                "prochain_jalon": progress.get("prochain_jalon"),
                "is_dju_applied": progress.get("is_dju_applied", False),
                "n_efa": progress.get("n_efa_actives", 0),
            }
        )

    # Tri : off_track → no_data → on_track
    order = {"off_track": 0, "no_data": 1, "on_track": 2}
    resultats.sort(key=lambda r: (order.get(r["status"], 3), -(r["reduction_pct"] or -999)))

    return {
        "org_id": org_id,
        "annee": annee,
        "n_sites_assujettis": len(sites),
        "n_on_track": n_on,
        "n_off_track": n_off,
        "n_no_data": n_nodata,
        "sites": resultats,
        "jalons_officiels": _JALONS_OFFICIELS,
        "source": "operat_trajectory",
        "computed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
