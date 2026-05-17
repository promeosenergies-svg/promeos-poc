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
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from database import get_db
from middleware.org_context import populate_org_context
from middleware.rbac import require_v4_role
from models.v4.action_center_items import ActionCenterItem
from models.v4.enums import Role
from repositories.action_blocker_repository import ActionBlockerRepository
from repositories.action_center_item_v4_repository import ActionCenterItemRepository
from repositories.action_event_log_repository import ActionEventLogRepository
from repositories.action_evidence_repository import ActionEvidenceRepository
from repositories.action_link_repository import ActionLinkRepository
from routes.v4.dependencies import verify_parent_item_access
from schemas.v4.action_center import (
    ActionBlockerListResponse,
    ActionCenterItemCreate,
    ActionCenterItemListResponse,
    ActionCenterItemResponse,
    ActionEventLogListResponse,
    ActionEvidenceListResponse,
    ActionLinkListResponse,
)

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
async def create_action_center_item(
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
async def list_action_center_items(
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
async def get_action_center_item(
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
async def list_item_events(
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
async def list_item_evidences(
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
async def list_item_blockers(
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
async def list_item_links(
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
