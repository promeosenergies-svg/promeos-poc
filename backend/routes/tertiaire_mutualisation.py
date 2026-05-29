"""
PROMEOS S3 (2026-05-28) — Routes API « Groupe de structures ».

Namespace : /api/tertiaire/mutualisation

Sous-routes :
  POST   /groups                              — créer un groupe
  GET    /groups                              — lister mes groupes
  GET    /groups/{id}                         — détail
  POST   /groups/{id}/members                 — ajouter une EFA
  DELETE /groups/{id}/members/{efa_id}        — retirer une EFA
  PATCH  /groups/{id}/members/{efa_id}/rl     — valider/refuser le RL
  POST   /groups/{id}/redistribution          — enregistrer une redistribution
  POST   /groups/{id}/archive                 — archiver le groupe
  GET    /groups/{id}/export-table-1b         — export CSV Table 1B Annexe IV

Cross-check Légifrance : voir
docs/audits/crosscheck_legifrance_mutualisation_art14_2026_05_28.md

Aucun nouveau menu côté UI : ces endpoints sont consommés par la
section Mutualisation existante de /conformite (doctrine §6.2 hub unique).
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models import (
    GROUPE_STATUSES,
    GroupeStructures,
    GroupeStructuresMembre,
    RL_STATUSES,
    TertiaireEfa,
)
from services.iam_scope import get_effective_org_id
from services.tertiaire_groupe_structures_service import (
    MutualisationViolation,
    add_efa_to_groupe,
    archive_groupe,
    create_groupe,
    ensure_groupe_exportable,
    record_redistribution,
    remove_efa_from_groupe,
    set_groupe_status,
    set_representant_legal_status,
)

router = APIRouter(prefix="/api/tertiaire/mutualisation", tags=["Tertiaire / Mutualisation"])


# ─── Schemas ─────────────────────────────────────────────────────────────


class GroupeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organisation_id: int = Field(..., gt=0)
    nom: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=4000)


class GroupeStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_status: str


class MembreAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    efa_id: int = Field(..., gt=0)


class RLUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_status: str = Field(..., description="'validated' ou 'rejected'")
    validator_user_id: Optional[str] = Field(None, max_length=200)
    validation_note: Optional[str] = Field(None, max_length=2000)


class RedistributionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    donneuse_efa_id: int = Field(..., gt=0)
    jalon_annee: int = Field(..., ge=2030, le=2100)
    kwh_redistribues: float = Field(..., gt=0)
    surplus_disponible_kwh: float = Field(..., ge=0)
    note: Optional[str] = Field(None, max_length=2000)


class MembreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    efa_id: int
    site_id: Optional[int]
    representant_legal_status: str
    representant_legal_validated_at: Optional[datetime]
    validator_user_id: Optional[str]
    validation_note: Optional[str]


class GroupeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organisation_id: int
    nom: str
    description: Optional[str]
    status: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    membres: list[MembreOut] = Field(default_factory=list)


# ─── Helpers ─────────────────────────────────────────────────────────────


def _violation_to_http(exc: MutualisationViolation) -> HTTPException:
    """Map une violation métier vers 422 + payload PROMEOS standard."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": exc.code,
            "message": exc.message_fr,
            "hint": exc.hint,
            "source": "Article 14 arrêté 10/04/2020 modifié (R.174-31 + L.174-1 CCH)",
        },
    )


def _load_groupe(db: Session, group_id: int, org_id: int) -> GroupeStructures:
    g = (
        db.query(GroupeStructures)
        .filter(
            GroupeStructures.id == group_id,
            GroupeStructures.organisation_id == org_id,
            GroupeStructures.deleted_at.is_(None),
        )
        .first()
    )
    if g is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GROUPE_NOT_FOUND", "message": "Groupe introuvable ou hors organisation."},
        )
    return g


def _load_membre(db: Session, groupe: GroupeStructures, efa_id: int) -> GroupeStructuresMembre:
    m = (
        db.query(GroupeStructuresMembre)
        .filter(
            GroupeStructuresMembre.group_id == groupe.id,
            GroupeStructuresMembre.efa_id == efa_id,
            GroupeStructuresMembre.deleted_at.is_(None),
        )
        .first()
    )
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MEMBRE_NOT_FOUND", "message": "EFA non membre actif de ce groupe."},
        )
    return m


# ─── Endpoints ───────────────────────────────────────────────────────────


@router.post("/groups", response_model=GroupeOut, status_code=201)
def create_group(
    payload: GroupeCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée un nouveau groupe de structures (statut initial : draft)."""
    org_id = get_effective_org_id(auth, payload.organisation_id)
    try:
        groupe = create_groupe(
            db,
            organisation_id=org_id,
            nom=payload.nom,
            description=payload.description,
            created_by=(auth.user_email if auth and getattr(auth, "user_email", None) else None),
        )
        db.commit()
        db.refresh(groupe)
        return groupe
    except MutualisationViolation as e:
        db.rollback()
        raise _violation_to_http(e)


@router.get("/groups", response_model=list[GroupeOut])
def list_groups(
    org_id: int = Query(..., gt=0),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les groupes d'une organisation (actifs par défaut)."""
    org_id = get_effective_org_id(auth, org_id)
    q = (
        db.query(GroupeStructures)
        .filter(
            GroupeStructures.organisation_id == org_id,
            GroupeStructures.deleted_at.is_(None),
        )
        .order_by(GroupeStructures.created_at.desc())
    )
    if not include_archived:
        q = q.filter(GroupeStructures.status != "archived")
    return q.all()


@router.get("/groups/{group_id}", response_model=GroupeOut)
def get_group(
    group_id: int,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    org_id = get_effective_org_id(auth, org_id)
    return _load_groupe(db, group_id, org_id)


@router.patch("/groups/{group_id}/status", response_model=GroupeOut)
def update_status(
    group_id: int,
    payload: GroupeStatusUpdate,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    try:
        set_groupe_status(db, g, payload.new_status)
        db.commit()
        db.refresh(g)
        return g
    except MutualisationViolation as e:
        db.rollback()
        raise _violation_to_http(e)


@router.post("/groups/{group_id}/archive", response_model=GroupeOut)
def archive_group(
    group_id: int,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive un groupe et libère les EFA membres pour réintégration ailleurs."""
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    archive_groupe(db, g)
    db.commit()
    db.refresh(g)
    return g


# ─── Membres ─────────────────────────────────────────────────────────────


@router.post("/groups/{group_id}/members", response_model=MembreOut, status_code=201)
def add_member(
    group_id: int,
    payload: MembreAdd,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Ajoute une EFA au groupe (I3 — refus si déjà dans un autre groupe actif)."""
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    try:
        m = add_efa_to_groupe(db, g, payload.efa_id)
        db.commit()
        db.refresh(m)
        return m
    except MutualisationViolation as e:
        db.rollback()
        raise _violation_to_http(e)


@router.delete("/groups/{group_id}/members/{efa_id}", status_code=204)
def remove_member(
    group_id: int,
    efa_id: int,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    try:
        remove_efa_from_groupe(db, g, efa_id)
        db.commit()
    except MutualisationViolation as e:
        db.rollback()
        raise _violation_to_http(e)


@router.patch(
    "/groups/{group_id}/members/{efa_id}/rl",
    response_model=MembreOut,
)
def update_rl(
    group_id: int,
    efa_id: int,
    payload: RLUpdate,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour le statut de validation du représentant légal pour
    une EFA membre (Art. 14 §1 al.2 — solidarité opposable)."""
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    m = _load_membre(db, g, efa_id)
    try:
        set_representant_legal_status(
            db,
            m,
            new_status=payload.new_status,
            validator_user_id=payload.validator_user_id,
            validation_note=payload.validation_note,
        )
        db.commit()
        db.refresh(m)
        return m
    except MutualisationViolation as e:
        db.rollback()
        raise _violation_to_http(e)


# ─── Redistribution (Ledger I4 + I5) ─────────────────────────────────────


@router.post("/groups/{group_id}/redistribution", status_code=201)
def add_redistribution(
    group_id: int,
    payload: RedistributionCreate,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Enregistre une redistribution d'économies (I4 + I5)."""
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    try:
        entry = record_redistribution(
            db,
            g,
            donneuse_efa_id=payload.donneuse_efa_id,
            jalon_annee=payload.jalon_annee,
            kwh_redistribues=payload.kwh_redistribues,
            surplus_disponible_kwh=payload.surplus_disponible_kwh,
            note=payload.note,
        )
        db.commit()
        return {
            "id": entry.id,
            "group_id": entry.group_id,
            "donneuse_efa_id": entry.donneuse_efa_id,
            "jalon_annee": entry.jalon_annee,
            "kwh_redistribues": entry.kwh_redistribues,
            "note": entry.note,
        }
    except MutualisationViolation as e:
        db.rollback()
        raise _violation_to_http(e)


# ─── Export Table 1B Annexe IV (Chantier 3) ──────────────────────────────


# Colonnes de l'export. Le détail exact de la Table 1B Annexe IV est
# verbatim Légifrance — nous exposons ici le minimum viable (groupe +
# EFA + identifiants + statut RL + horodatage + source réglementaire),
# qui est ce que le DAF doit reporter au-dessus du formulaire OPERAT.
# Toute extension future colonne par colonne devra référencer l'Annexe IV.
_TABLE_1B_COLUMNS = [
    "groupe_id",
    "groupe_nom",
    "groupe_status",
    "efa_id",
    "efa_nom",
    "efa_org_id",
    "site_id",
    "representant_legal_status",
    "representant_legal_validated_at",
    "date_generation_iso",
    "source_reglementaire",
]


@router.get("/groups/{group_id}/export-table-1b")
def export_table_1b(
    group_id: int,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Export CSV du groupe au format Table 1B Annexe IV.

    Refuse l'export tant que TOUS les RL ne sont pas validés (Art. 14
    §1 al.2 — sans solidarité opposable, le groupe ne peut être déposé
    sur OPERAT comme une entité unique).
    """
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    try:
        ensure_groupe_exportable(g)
    except MutualisationViolation as e:
        raise _violation_to_http(e)

    now_iso = datetime.now(timezone.utc).isoformat()
    source_ref = "Article 14 arrêté 10/04/2020 modifié — Table 1B Annexe IV (R.174-31 + L.174-1 CCH)"

    # Construction du CSV
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(_TABLE_1B_COLUMNS)

    efa_ids = [m.efa_id for m in g.membres if m.deleted_at is None]
    efas = {e.id: e for e in db.query(TertiaireEfa).filter(TertiaireEfa.id.in_(efa_ids)).all()}

    for m in g.membres:
        if m.deleted_at is not None:
            continue
        efa = efas.get(m.efa_id)
        writer.writerow(
            [
                g.id,
                g.nom,
                g.status,
                m.efa_id,
                getattr(efa, "nom", ""),
                getattr(efa, "org_id", ""),
                m.site_id or "",
                m.representant_legal_status,
                (m.representant_legal_validated_at.isoformat() if m.representant_legal_validated_at else ""),
                now_iso,
                source_ref,
            ]
        )

    csv_bytes = buf.getvalue().encode("utf-8-sig")  # BOM pour Excel FR
    filename = f"groupe-structures-{g.id}-table-1b-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    # Note : la source réglementaire est portée par la colonne dédiée
    # `source_reglementaire` du CSV (verbatim avec em-dash). On ne la
    # remonte PAS en header HTTP car les en-têtes Starlette/Hyper sont
    # encodés en latin-1 (RFC 7230) et l'em-dash U+2014 lève
    # UnicodeEncodeError. Si un header est requis ultérieurement, il
    # devra utiliser un ASCII fallback ou encoding RFC 5987.
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
