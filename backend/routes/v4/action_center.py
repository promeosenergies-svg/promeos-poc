"""M2-4.2 — endpoints `/api/v4/action-center/items` (TEMPLATE).

3 endpoints livrés — premier endpoint V4 complet bout-en-bout :
- POST   /items            — création, support Idempotency-Key
- GET    /items            — liste paginée (offset/limit)
- GET    /items/{item_id}  — item unique (404 sur cross-org, pas de leak)

⚠️ Ce fichier est le TEMPLATE. Les 9 endpoints restants (M2-4.3 + M2-4.4)
reproduisent les mêmes patterns :
- `response_model` sur chaque route (anti V66 RC2)
- `populate_org_context` + `require_v4_role` sur chaque route (defense in depth)
- Repository org-scopé uniquement, jamais de `db.query()` direct (anti V66 RC1)
- Erreurs structurées `{code, message, hint}` (cf. schemas/error.py::APIError)
- 404 sur cross-org, jamais 403 (pas de fuite d'existence — anti-leak)
- Pagination native sur les listes (offset/limit, max 200)
- Idempotency-Key sur les POST (anti V66 RC4)
"""

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from main_limiter import (
    QUOTA_READ_V4,
    QUOTA_UPLOAD_V4,
    QUOTA_VERIFY_V4,
    QUOTA_WRITE_V4,
    limiter,
)
from sqlalchemy.orm import Session

from database import get_db
from middleware.org_context import current_org_id, populate_org_context
from middleware.rbac import require_v4_role
from models.v4.action_center_items import ActionCenterItem
from models.v4.enums import LifecycleState, Role
from repositories.action_blocker_repository import ActionBlockerRepository
from repositories.action_center_item_v4_repository import ActionCenterItemRepository
from repositories.action_event_log_repository import ActionEventLogRepository
from repositories.action_evidence_repository import ActionEvidenceRepository
from repositories.action_link_repository import ActionLinkRepository
from routes.v4.dependencies import assert_parent_item_in_scope, verify_parent_item_access
from schemas.v4.action_center import (
    ActionBlockerListResponse,
    ActionBlockerResponse,
    ActionCenterItemCreate,
    ActionCenterItemListResponse,
    ActionCenterItemResponse,
    ActionCenterItemUpdate,
    ActionEventLogListResponse,
    ActionEvidenceListResponse,
    ActionEvidenceResponse,
    ActionLinkCreate,
    ActionLinkListResponse,
    ActionLinkResponse,
    BlockerCreate,
    BlockerResolveRequest,
    EvidenceVerifyRequest,
    LifecycleTransitionRequest,
)
from services.v4.file_validation import validate_file_upload
from services.v4.lifecycle_validator import validate_lifecycle_transition
from services.v4.link_target_validator import verify_link_target

router = APIRouter(prefix="/api/v4/action-center", tags=["V4 Action Center"])

# Priorité = axe DÉRIVÉ (scoring R1-R6, Sprint M2-5), pas une saisie utilisateur.
# À la création, on pose un placeholder neutre + score_stale=True : le service
# PriorityScoring (M2-5) recalculera bracket + score réels.
_PLACEHOLDER_PRIORITY_BRACKET = "P2"
_PLACEHOLDER_PRIORITY_SCORE = 50.0


def _hash_payload(payload: ActionCenterItemCreate) -> str:
    """SHA256 hex du payload — sert au contrôle de conflit d'idempotence.

    Un même Idempotency-Key rejoué avec un payload sémantiquement différent
    produit un hash différent → 409 (cf. POST). Ajouter un champ au schema
    change le hash : c'est voulu (payload différent = requête différente).
    """
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ════════════════════════════════════════════════════════════════════
# POST /items — création avec idempotence
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/items",
    response_model=ActionCenterItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_WRITE_V4)
async def create_action_center_item(
    request: Request,
    payload: ActionCenterItemCreate,
    response: Response,
    idempotency_key: Annotated[
        Optional[str],
        Header(alias="Idempotency-Key", description="UUID v4 — rend le POST rejouable"),
    ] = None,
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.USER, Role.ADMIN)),
):
    """Crée un ActionCenterItem dans l'org du contexte courant.

    Header `Idempotency-Key` (optionnel, UUID v4) :
    - absent          → création standard (201).
    - présent, inédit → création standard, clé enregistrée (201).
    - présent, déjà vu, même payload → renvoie l'item précédent (200, pas 201).
    - présent, déjà vu, payload différent → 409 IDEMPOTENCY_CONFLICT.

    `organisation_id` est forcé par le repository depuis le contexte (jamais
    dans le body). `priority_*` est posé en placeholder (scoring M2-5).
    """
    repo = ActionCenterItemRepository(db)
    payload_hash: Optional[str] = None

    if idempotency_key is not None:
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "IDEMPOTENCY_KEY_INVALID",
                    "message": "Idempotency-Key must be a valid UUID",
                    "hint": "Generate one with uuid.uuid4()",
                },
            )
        payload_hash = _hash_payload(payload)
        existing = repo.find_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.idempotency_payload_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "IDEMPOTENCY_CONFLICT",
                        "message": "Idempotency-Key reused with a different payload",
                        "hint": "Use a fresh UUID, or resend the identical payload",
                    },
                )
            # Même clé + même payload → rejeu sûr : on renvoie l'item existant.
            response.status_code = status.HTTP_200_OK
            return existing

    item = repo.create(
        **payload.model_dump(),
        priority_bracket=_PLACEHOLDER_PRIORITY_BRACKET,
        priority_score=_PLACEHOLDER_PRIORITY_SCORE,
        score_stale=True,
        idempotency_key=idempotency_key,
        idempotency_payload_hash=payload_hash,
    )
    db.commit()
    return item


# ════════════════════════════════════════════════════════════════════
# GET /items — liste paginée
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/items",
    response_model=ActionCenterItemListResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_READ_V4)
async def list_action_center_items(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.VIEWER, Role.USER, Role.ADMIN)),
):
    """Liste paginée des ActionCenterItems de l'org courante (org-scopé)."""
    repo = ActionCenterItemRepository(db)
    items, total = repo.list_paginated(offset=offset, limit=limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


# ════════════════════════════════════════════════════════════════════
# GET /items/{item_id} — item unique (404 sur cross-org)
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/items/{item_id}",
    response_model=ActionCenterItemResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_READ_V4)
async def get_action_center_item(
    request: Request,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.VIEWER, Role.USER, Role.ADMIN)),
):
    """Récupère un ActionCenterItem par id.

    404 sur accès cross-org (pas 403 — pas de fuite d'existence) : le repository
    fail-closed filtre par `organisation_id`, donc une requête cross-org renvoie
    naturellement None → 404 ici.
    """
    repo = ActionCenterItemRepository(db)
    item = repo.get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ITEM_NOT_FOUND",
                "message": f"ActionCenterItem {item_id} not found",
                "hint": "Check the id, or your access scope",
            },
        )
    return item


# ════════════════════════════════════════════════════════════════════
# Sous-ressources en lecture (M2-4.3 — rollout du template)
# ════════════════════════════════════════════════════════════════════
#
# Les 4 handlers ci-dessous ont une structure identique : c'est une
# duplication contrôlée et VOLONTAIRE. Toute factorisation par
# méta-programmation est refusée — 4 fonctions courtes et auditables valent
# mieux qu'un générique imreviewable. Seules varient : la sous-ressource
# (repository + response_model) et la docstring.
#
# `verify_parent_item_access` (dependency) résout l'item parent org-scopé →
# 404 ITEM_NOT_FOUND si absent ou cross-org, avant toute requête sous-ressource.


@router.get(
    "/items/{item_id}/events",
    response_model=ActionEventLogListResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_READ_V4)
async def list_item_events(
    request: Request,
    item_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.VIEWER, Role.USER, Role.ADMIN)),
):
    """Liste paginée des events de l'item (audit trail), triée occurred_at DESC.

    404 ITEM_NOT_FOUND si l'item n'existe pas ou est cross-org.
    """
    items, total = ActionEventLogRepository(db).list_by_item_id(item_id, offset=offset, limit=limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get(
    "/items/{item_id}/evidences",
    response_model=ActionEvidenceListResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_READ_V4)
async def list_item_evidences(
    request: Request,
    item_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.VIEWER, Role.USER, Role.ADMIN)),
):
    """Liste paginée des evidences de l'item, triée uploaded_at DESC.

    SÉCURITÉ : `storage_uri` n'est jamais renvoyé (cf. ActionEvidenceResponse).
    """
    items, total = ActionEvidenceRepository(db).list_by_item_id(item_id, offset=offset, limit=limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get(
    "/items/{item_id}/blockers",
    response_model=ActionBlockerListResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_READ_V4)
async def list_item_blockers(
    request: Request,
    item_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.VIEWER, Role.USER, Role.ADMIN)),
):
    """Liste paginée des blockers de l'item, triée added_at DESC.

    Le modèle ActionBlocker n'a pas de colonne `severity` — tri simple.
    """
    items, total = ActionBlockerRepository(db).list_by_item_id(item_id, offset=offset, limit=limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get(
    "/items/{item_id}/links",
    response_model=ActionLinkListResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_READ_V4)
async def list_item_links(
    request: Request,
    item_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.VIEWER, Role.USER, Role.ADMIN)),
):
    """Liste paginée des liens de l'item (vers d'autres modules), triée created_at DESC."""
    items, total = ActionLinkRepository(db).list_by_item_id(item_id, offset=offset, limit=limit)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


# ════════════════════════════════════════════════════════════════════
# Endpoints write/admin (M2-4.4)
# ════════════════════════════════════════════════════════════════════
#
# Discipline : chaque endpoint qui modifie le métier persiste sa modif ET son
# audit event dans LA MÊME transaction — un seul `db.commit()` en fin de
# handler. Toute exception avant ce commit (validation, échec d'écriture de
# l'event) → pas de commit → rollback au close de session : atomicité garantie
# sans try/except explicite.
#
# Acteur des events : `_actor_uuid` dérive un UUID5 déterministe du `sub` (user
# id INT du JWT legacy). `ActionEventLog.actor_id` / `Evidence.uploaded_by` /
# `ActionBlocker.added_by` sont des UUID — la dette JWT/UUID n'a été résolue que
# pour `organisation_id` (M2-4.1). Le user_id int reste tracé dans event_payload.

_V4_ACTOR_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "promeos:v4:actor")


def _actor_uuid(auth: Optional[dict]) -> Optional[uuid.UUID]:
    """UUID5 déterministe de l'acteur depuis le `sub` du JWT (None si pas de JWT)."""
    sub = (auth or {}).get("sub")
    return None if sub is None else uuid.uuid5(_V4_ACTOR_NAMESPACE, str(sub))


def _write_v4_event(
    db: Session,
    *,
    action_item_id: uuid.UUID,
    event_type: str,
    auth: Optional[dict],
    payload: dict,
) -> None:
    """Écrit un ActionEventLog (audit trail). Respecte `chk_actor_consistency`."""
    actor_id = _actor_uuid(auth)
    role = (auth or {}).get("role")
    body = dict(payload)
    body["actor_user_id"] = (auth or {}).get("sub")
    ActionEventLogRepository(db).create(
        action_item_id=action_item_id,
        event_type=event_type,
        actor_type="user" if actor_id is not None else "system",
        actor_id=actor_id,
        actor_role=role[:20] if role else None,
        event_payload=body,
        correlation_id=uuid.uuid4(),
    )


# ── PATCH /items/{id} — update cosmétique (sans event) ───────────────


@router.patch(
    "/items/{item_id}",
    response_model=ActionCenterItemResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_WRITE_V4)
async def update_action_center_item(
    request: Request,
    item_id: uuid.UUID,
    payload: ActionCenterItemUpdate,
    parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.USER, Role.ADMIN)),
):
    """Met à jour les champs cosmétiques (title/description/domain).

    Pas d'audit event : IL8 ne trace que les transitions lifecycle ; un edit
    cosmétique n'est pas dans les 16 event_types doctrine. `updated_at` suffit.
    Body vide → no-op idempotent (200, item inchangé).
    """
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        return parent
    updated = ActionCenterItemRepository(db).update(parent, **fields)
    db.commit()
    db.refresh(updated)
    return updated


# ── PATCH /items/{id}/lifecycle — transition d'état ──────────────────


@router.patch(
    "/items/{item_id}/lifecycle",
    response_model=ActionCenterItemResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_WRITE_V4)
async def transition_item_lifecycle(
    request: Request,
    item_id: uuid.UUID,
    payload: LifecycleTransitionRequest,
    parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    auth=Depends(require_v4_role(Role.USER, Role.ADMIN)),
):
    """Transitionne le cycle de vie de l'item. Écrit un event `state_changed`.

    Valide contre la matrice doctrine V4 (5 états · closed terminal). closure_reason
    requise SSI cible `closed` ; les valeurs system-only sont refusées en 422.
    """
    old_state = parent.lifecycle_state
    validate_lifecycle_transition(old_state, payload.new_state, payload.closure_reason)

    # chk_closure_consistency : closed ⇒ closed_at + closure_reason NOT NULL.
    fields: dict = {"lifecycle_state": payload.new_state.value}
    if payload.new_state == LifecycleState.CLOSED:
        fields["closure_reason"] = payload.closure_reason.value
        fields["closed_at"] = datetime.now(UTC)

    updated = ActionCenterItemRepository(db).update(parent, **fields)
    _write_v4_event(
        db,
        action_item_id=item_id,
        event_type="state_changed",
        auth=auth,
        payload={
            "old_state": str(old_state),
            "new_state": payload.new_state.value,
            "closure_reason": payload.closure_reason.value if payload.closure_reason else None,
            "comment": payload.comment,
        },
    )
    db.commit()
    db.refresh(updated)
    return updated


# ── POST /items/{id}/evidences — upload multipart ────────────────────


@router.post(
    "/items/{item_id}/evidences",
    response_model=ActionEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_UPLOAD_V4)
async def upload_item_evidence(
    request: Request,
    item_id: uuid.UUID,
    file: UploadFile = File(...),
    description: Annotated[Optional[str], Form()] = None,
    parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    auth=Depends(require_v4_role(Role.USER, Role.ADMIN)),
):
    """Upload d'une evidence. Magic bytes validés. Écrit un event `evidence_added`.

    SÉCURITÉ : `storage_uri` n'est jamais renvoyé (ActionEvidenceResponse).
    Stockage filesystem par org (`PROMEOS_EVIDENCE_STORAGE_PATH`).
    """
    content = await file.read()
    safe_filename = validate_file_upload(
        content=content,
        declared_content_type=file.content_type or "",
        declared_filename=file.filename or "unnamed",
    )

    org_id = current_org_id()
    storage_root = os.environ.get("PROMEOS_EVIDENCE_STORAGE_PATH", "./storage/evidences")
    storage_dir = os.path.join(storage_root, f"org_{org_id}")
    os.makedirs(storage_dir, exist_ok=True)
    evidence_id = uuid.uuid4()
    storage_path = os.path.join(storage_dir, f"{evidence_id}_{safe_filename}")
    with open(storage_path, "wb") as handle:
        handle.write(content)

    evidence = ActionEvidenceRepository(db).create(
        id=evidence_id,
        action_item_id=item_id,
        mime_type=file.content_type,
        file_size_bytes=len(content),
        storage_uri=f"fs://{storage_path}",
        original_filename=safe_filename,
        description=description,
        uploaded_by=_actor_uuid(auth),
    )
    _write_v4_event(
        db,
        action_item_id=item_id,
        event_type="evidence_added",
        auth=auth,
        payload={
            "evidence_id": str(evidence_id),
            "filename": safe_filename,
            "size_bytes": len(content),
            "mime_type": file.content_type,
        },
    )
    db.commit()
    db.refresh(evidence)
    return evidence


# ── PATCH /evidences/{id}/verify ─────────────────────────────────────


@router.patch(
    "/evidences/{evidence_id}/verify",
    response_model=ActionEvidenceResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_VERIFY_V4)
async def verify_item_evidence(
    request: Request,
    evidence_id: uuid.UUID,
    payload: EvidenceVerifyRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_v4_role(Role.USER, Role.ADMIN)),
):
    """Vérifie une evidence (ADR-029 : sémantique par timestamps, pas d'enum status).

    Verify-only (pas de reject). Écrit un event `evidence_verified`.
    409 si déjà vérifiée. Auto-verify (uploader == verifier) autorisée et tracée.
    """
    repo = ActionEvidenceRepository(db)
    evidence = repo.get(evidence_id)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "EVIDENCE_NOT_FOUND",
                "message": f"Evidence {evidence_id} not found",
                "hint": "Check the id, or your access scope",
            },
        )
    # M2-5.9 — défense en profondeur : l'item parent doit appartenir à l'org du
    # caller. L'evidence l'est déjà (repo org-scopé) ; ce check uniformise
    # verify/resolve avec les 5 autres sous-ressources et garde contre une
    # incohérence evidence.organisation_id ≠ parent.organisation_id.
    assert_parent_item_in_scope(db, evidence.action_item_id)
    if evidence.verified_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EVIDENCE_ALREADY_VERIFIED",
                "message": "Evidence already verified",
                # M2-5.9 — pas de timestamp dans le hint (CWE-209 info-disclosure).
            },
        )

    now = datetime.now(UTC)
    expires_at = payload.expires_at or (now + timedelta(days=90))
    verifier = _actor_uuid(auth)
    is_auto_verified = verifier is not None and evidence.uploaded_by == verifier

    # chk_evidence_verified_consistency : verified_at/by + expires_at tous NOT NULL.
    updated = repo.update(
        evidence,
        verified_at=now,
        verified_by=verifier,
        expires_at=expires_at,
    )
    _write_v4_event(
        db,
        action_item_id=evidence.action_item_id,
        event_type="evidence_verified",
        auth=auth,
        payload={
            "evidence_id": str(evidence_id),
            "auto_verified": is_auto_verified,
            "expires_at": expires_at.isoformat(),
            "comment": payload.comment,
        },
    )
    db.commit()
    db.refresh(updated)
    return updated


# ── POST /items/{id}/blockers ────────────────────────────────────────


@router.post(
    "/items/{item_id}/blockers",
    response_model=ActionBlockerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_WRITE_V4)
async def add_item_blocker(
    request: Request,
    item_id: uuid.UUID,
    payload: BlockerCreate,
    parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    auth=Depends(require_v4_role(Role.USER, Role.ADMIN)),
):
    """Ajoute un blocker à l'item. Écrit un event `blocker_added`."""
    blocker = ActionBlockerRepository(db).create(
        item_id=item_id,
        blocker_type=payload.blocker_type.value,
        justification=payload.justification,
        expected_resolution_at=payload.expected_resolution_at,
        added_by=_actor_uuid(auth),
    )
    _write_v4_event(
        db,
        action_item_id=item_id,
        event_type="blocker_added",
        auth=auth,
        payload={"blocker_id": str(blocker.id), "blocker_type": payload.blocker_type.value},
    )
    db.commit()
    db.refresh(blocker)
    return blocker


# ── PATCH /blockers/{id}/resolve ─────────────────────────────────────


@router.patch(
    "/blockers/{blocker_id}/resolve",
    response_model=ActionBlockerResponse,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_WRITE_V4)
async def resolve_item_blocker(
    request: Request,
    blocker_id: uuid.UUID,
    payload: BlockerResolveRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_v4_role(Role.USER, Role.ADMIN)),
):
    """Résout un blocker. Écrit un event `blocker_removed`. 409 si déjà résolu."""
    repo = ActionBlockerRepository(db)
    blocker = repo.get(blocker_id)
    if blocker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BLOCKER_NOT_FOUND",
                "message": f"Blocker {blocker_id} not found",
                "hint": "Check the id, or your access scope",
            },
        )
    # M2-5.9 — défense en profondeur : item parent dans l'org du caller
    # (cf. verify_item_evidence — uniformisation des writes V4).
    assert_parent_item_in_scope(db, blocker.item_id)
    if blocker.resolved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BLOCKER_ALREADY_RESOLVED",
                "message": "Blocker already resolved",
                # M2-5.9 — pas de timestamp dans le hint (CWE-209).
            },
        )
    updated = repo.update(
        blocker,
        resolved_at=datetime.now(UTC),
        resolved_by=_actor_uuid(auth),
    )
    _write_v4_event(
        db,
        action_item_id=blocker.item_id,
        event_type="blocker_removed",
        auth=auth,
        payload={"blocker_id": str(blocker_id), "resolution_comment": payload.resolution_comment},
    )
    db.commit()
    db.refresh(updated)
    return updated


# ── POST /items/{id}/links — création de lien polymorphe (sans event) ─


@router.post(
    "/items/{item_id}/links",
    response_model=ActionLinkResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(populate_org_context)],
)
@limiter.limit(QUOTA_WRITE_V4)
async def create_item_link(
    request: Request,
    item_id: uuid.UUID,
    payload: ActionLinkCreate,
    parent: ActionCenterItem = Depends(verify_parent_item_access),
    db: Session = Depends(get_db),
    _rbac=Depends(require_v4_role(Role.USER, Role.ADMIN)),
):
    """Crée un lien de l'item vers une cible polymorphe.

    `verify_link_target` valide AVANT création : 404 si cross-org, 501 si le
    module cible n'est pas encore implémenté. Pas d'audit event (`link_created`
    hors des 16 event_types doctrine).
    """
    verify_link_target(payload.target_module, payload.target_id, db)
    link = ActionLinkRepository(db).create(
        item_id=item_id,
        link_type=payload.link_type,
        target_module=payload.target_module.value,
        target_id=payload.target_id,
        relation=payload.relation,
    )
    db.commit()
    db.refresh(link)
    return link
