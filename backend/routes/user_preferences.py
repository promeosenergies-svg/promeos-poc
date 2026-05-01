"""User preferences endpoints — Sprint Refonte Narrative dynamique Phase 1.4.

Endpoint `PUT /api/user/preferences/typology` pour permettre à un user de
surcharger la typologie auto-détectée par NAF.

Body :
  {
    "typology": "grand_groupe_tertiaire" | "commerce" | "etablissement_recevant_public" | null
  }

`typology = null` → reset l'override (retour à l'auto-détection NAF).

## Auth

`get_current_user` (strict — l'utilisateur doit être authentifié pour
sauvegarder ses propres préférences). En DEMO_MODE, l'auth est lenient via
`get_optional_auth` ailleurs ; ici on exige user identifié pour cohérence
des préférences (pas de "préférence anonyme").

## Layering

Cette route est **HTTP only** : la logique métier (lecture/écriture DB)
vit dans `services/user_preference_service.py`. Les autres modules qui
ont besoin de lire l'override (ex: `typology_resolver`) doivent importer
le service, **pas** cette route — règle layering PROMEOS (services ne
doivent pas dépendre de routes).

## Design choice cross-org

L'override est **global par user** (pas scopé à l'org). Un user multi-org
partage son override entre toutes ses orgs. Choix produit explicite Amine
2026-05-01 : la typologie est une perception personnelle du user, pas une
caractéristique de l'org. Si V2 multi-org nécessite un override scopé,
ADR P1-1 Phase 2 (cf service docstring).

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
from models import User
from services.user_preference_service import (
    get_or_create_user_preference,
    get_user_typology_override,
)

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


# ─── Routes ─────────────────────────────────────────────────────────────────


@router.get("/preferences/typology", response_model=TypologyOverrideResponse)
def get_typology_preference(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Récupère l'override typologie courant pour le user authentifié.

    Si aucune préférence enregistrée → `typology_override = null`.
    """
    typology_override = get_user_typology_override(db, user.id)
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
