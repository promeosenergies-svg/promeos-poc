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

# Sprint S4 (2026-05-29) — PDF Table 1B + deadline status.
from services.tertiaire_mutualisation_pdf import (
    MutualisationPdfError,
    generate_table_1b_pdf,
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


# ─── S4 — Export PDF Table 1B Annexe IV ────────────────────────────────


@router.get("/groups/{group_id}/export-table-1b.pdf")
def export_table_1b_pdf(
    group_id: int,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Sprint S4 — Export PDF du groupe au format Table 1B Annexe IV.

    Mêmes garde-fous que l'export CSV (refus si I2 violé). En plus, le
    PDF inclut un hash SHA256 d'opposabilité du contenu (recalculable
    par un contrôleur ADEME à partir des données déposées).
    """
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    try:
        ensure_groupe_exportable(g)
    except MutualisationViolation as e:
        raise _violation_to_http(e)
    try:
        pdf_bytes, export_hash = generate_table_1b_pdf(db, g)
    except MutualisationPdfError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PDF_RENDER_ERROR", "message": str(e)},
        )
    filename = f"groupe-structures-{g.id}-table-1b-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Hash": export_hash,
        },
    )


# ─── S4 — Demande de validation représentant légal via Centre d'Action ──


@router.post(
    "/groups/{group_id}/members/{efa_id}/request-validation",
    status_code=status.HTTP_201_CREATED,
)
def request_rl_validation(
    group_id: int,
    efa_id: int,
    response: Response,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Sprint S4 — Crée une action « Demander validation représentant légal »
    dans le Centre d'Action V4 pour cette EFA membre.

    Réutilise le endpoint upsert-by-external-ref livré S2 (idempotent
    + CLOSED non ressuscité). Si la demande existe déjà, on renvoie
    l'action existante (pas de doublon).

    Pour S4 : pas d'envoi d'email réel — le canal canonique est le
    Centre d'Action V4. L'envoi email Brevo pourra être branché en S5+
    via le service `email_provider.py`.

    Sprint S4.1 hotfix (2026-05-29) : HTTP code aligné REST strict
    - 201 Created si nouvelle action créée
    - 200 OK si action existante retournée (idempotent)
    - 409 sur RL_ALREADY_VALIDATED ou EXTERNAL_REF_CLOSED
    """
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    m = _load_membre(db, g, efa_id)
    if m.representant_legal_status == "validated":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RL_ALREADY_VALIDATED",
                "message": "Le représentant légal a déjà validé cette EFA.",
            },
        )
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    efa_nom = getattr(efa, "nom", f"EFA #{efa_id}")

    # Délégation upsert NBA (Sprint S2) — idempotent par external_ref.
    from middleware.org_context import reset_org_context, set_org_context
    from repositories.action_center_item_v4_repository import (
        ActionCenterItemRepository,
    )

    external_ref = f"conformite:rl_validation:{efa_id}:{group_id}"
    source_url = f"/conformite?regulation=dt&mutualisation_group={group_id}"
    org_token = set_org_context(org_id)
    repo = ActionCenterItemRepository(db)
    try:
        existing = repo.find_by_external_ref(external_ref)
        if existing is not None:
            if existing.lifecycle_state == "closed":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "EXTERNAL_REF_CLOSED",
                        "message": (
                            "Une demande de validation RL antérieure a été clôturée "
                            "pour cette EFA — elle ne peut être ressuscitée. Si la "
                            "demande doit être relancée, archivez puis recréez le "
                            "groupe pour signer une nouvelle instance."
                        ),
                    },
                )
            # S4.1 — idempotent : action existante → bascule 201→200.
            response.status_code = status.HTTP_200_OK
            return {
                "id": str(existing.id),
                "external_ref": existing.external_ref,
                "kind": existing.kind,
                "status": "existing",
            }
        item = repo.create(
            kind="action",
            title=f"Demander validation représentant légal — {efa_nom}",
            description=(
                f"Le groupe « {g.nom} » nécessite la validation du représentant "
                f"légal de l'EFA « {efa_nom} » pour devenir opposable au contrôle "
                "décennal ADEME (Art. 14 §1 al.2 de l'arrêté 10/04/2020 modifié)."
            ),
            domain="conformite",
            external_ref=external_ref,
            source_url=source_url,
            priority_bracket="P2",
            priority_score=50.0,
            score_stale=True,
        )
        db.commit()
        return {
            "id": str(item.id),
            "external_ref": item.external_ref,
            "kind": item.kind,
            "status": "created",
        }
    finally:
        reset_org_context(org_token)


# ─── S4 — Statut échéance contrôle ADEME (R.174-31) ────────────────────


# Échéances cardinales R.174-31 : vérification ADEME au 31/12 de l'année
# qui suit chaque jalon (cross-check Légifrance livré S3, Phase 0 §4).
_DEADLINES = [
    {"jalon": 2030, "deadline": "2031-12-31"},
    {"jalon": 2040, "deadline": "2041-12-31"},
    {"jalon": 2050, "deadline": "2051-12-31"},
]


@router.get("/groups/{group_id}/deadline-status")
def get_deadline_status(
    group_id: int,
    org_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Sprint S4 — Renvoie la prochaine échéance ADEME + statut du groupe
    + action recommandée.

    Source : Article R.174-31 du Code de la construction et de l'habitation
    (vérification au 31/12/2031, 2041, 2051 au plus tard) — confirmé
    Phase 0 cross-check S3.
    """
    org_id = get_effective_org_id(auth, org_id)
    g = _load_groupe(db, group_id, org_id)
    now = datetime.now(timezone.utc)
    next_d = None
    for d in _DEADLINES:
        deadline_dt = datetime.fromisoformat(d["deadline"] + "T23:59:59+00:00")
        if deadline_dt > now:
            next_d = {**d, "days_remaining": (deadline_dt - now).days}
            break

    actives = [m for m in g.membres if m.deleted_at is None]
    rl_validated = sum(1 for m in actives if m.representant_legal_status == "validated")
    opposable = bool(actives) and rl_validated == len(actives) and g.status != "archived"

    # Action recommandée FR claire (priorité forte > faible).
    if g.status == "archived":
        action = "Groupe archivé — créez un nouveau groupe pour préparer la prochaine échéance."
    elif not actives:
        action = "Ajoutez au moins une EFA au groupe avant l'échéance."
    elif rl_validated < len(actives):
        missing = len(actives) - rl_validated
        action = (
            f"Collectez {missing} validation(s) représentant légal manquante(s) "
            "(Art. 14 §1 al.2) — sans solidarité opposable, le groupe ne pourra "
            "pas être déposé."
        )
    elif next_d and next_d["days_remaining"] < 365:
        action = (
            f"Échéance ADEME dans {next_d['days_remaining']} jours — préparez "
            "le dépôt OPERAT dès l'ouverture du module mutualisation."
        )
    else:
        action = "Groupe opposable — surveillez l'ouverture du module OPERAT mutualisation ADEME."

    return {
        "group_id": g.id,
        "group_status": g.status,
        "n_members_active": len(actives),
        "n_rl_validated": rl_validated,
        "opposable": opposable,
        "next_deadline": next_d,
        "action_recommandee_fr": action,
        "source_reglementaire": (
            "Article R.174-31 CCH (vérification ADEME au 31/12/2031, 2041, 2051) + Article 14 arrêté 10/04/2020 modifié"
        ),
    }
