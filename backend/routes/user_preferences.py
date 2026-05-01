"""User preferences endpoints — Sprint Refonte Narrative dynamique Phase 1.4.

Endpoint `PUT /api/user/preferences/typology` pour permettre à un user de
surcharger la typologie auto-détectée par NAF.

Body :
  {
    "typology": "grand_groupe_tertiaire" | "commerce" | "etablissement_recevant_public" | null
  }

`typology = null` → reset l'override (retour à l'auto-détection NAF).

Auth : `get_current_user` (strict — l'utilisateur doit être authentifié pour
sauvegarder ses propres préférences). En DEMO_MODE, l'auth est lenient via
`get_optional_auth` ailleurs ; ici on exige user identifié pour cohérence
des préférences (pas de "préférence anonyme").

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.4.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from doctrine.naf_to_typology import OrganizationTypology
from middleware.auth import get_current_user
from models import User, UserPreference

router = APIRouter(prefix="/api/user", tags=["user-preferences"])


# ─── Schemas ───────────────────────────────────────────────────────────────


class TypologyOverrideRequest(BaseModel):
    """Body pour PUT /api/user/preferences/typology.

    `typology = null` → reset (auto-détection NAF reprend la main).
    """

    typology: Optional[OrganizationTypology] = None


class TypologyOverrideResponse(BaseModel):
    user_id: int
    typology_override: Optional[OrganizationTypology]


# ─── Helpers ────────────────────────────────────────────────────────────────


def get_or_create_user_preference(db: Session, user_id: int) -> UserPreference:
    """Récupère la préférence du user, ou la crée si inexistante."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref is None:
        pref = UserPreference(user_id=user_id, typology_override=None)
        db.add(pref)
        db.flush()
    return pref


def get_user_typology_override(db: Session, user_id: int) -> Optional[OrganizationTypology]:
    """Lit l'override typologie du user (None si pas d'override ou pas de préférence).

    Utilisé par `typology_resolver.resolve_typology_for_scope` pour respecter
    la préférence user avant calcul auto-détection NAF.
    """
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref is None:
        return None
    return pref.typology_override


# ─── Routes ─────────────────────────────────────────────────────────────────


@router.get("/preferences/typology", response_model=TypologyOverrideResponse)
def get_typology_preference(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupère l'override typologie courant pour le user authentifié."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    typology_override = pref.typology_override if pref else None
    return TypologyOverrideResponse(user_id=user.id, typology_override=typology_override)


@router.put("/preferences/typology", response_model=TypologyOverrideResponse)
def put_typology_preference(
    payload: TypologyOverrideRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Surcharge la typologie auto-détectée pour le user authentifié.

    Phase 1.4 — permet à un CFO d'une org mixte (auto-détectée GRAND_GROUPE)
    de forcer une autre typologie pour ses narratives. `typology = null`
    reset l'override (retour auto-détection NAF).

    Note : si l'override = UNKNOWN, on rejette pour éviter de figer un
    fallback générique (UNKNOWN doit toujours rester un état transitoire,
    pas une préférence active).
    """
    if payload.typology == OrganizationTypology.UNKNOWN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("typology=UNKNOWN n'est pas une valeur d'override valide. Pour reset l'override, utilisez null."),
        )

    pref = get_or_create_user_preference(db, user.id)
    pref.typology_override = payload.typology
    db.commit()
    db.refresh(pref)
    return TypologyOverrideResponse(
        user_id=user.id,
        typology_override=pref.typology_override,
    )
