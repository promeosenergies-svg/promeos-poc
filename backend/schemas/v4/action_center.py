"""M2-4.2 — Schemas Pydantic des endpoints /api/v4/action-center/items.

Discipline (anti-patterns V66 intégrés nativement) :
- `response_model` sur chaque endpoint (RC2) — les modèles de réponse vivent ici.
- `extra="forbid"` sur les requests → un payload avec un champ inconnu est
  rejeté en 422 dès la couche schema (defense in depth avec le repo).
- Enums Python V4, jamais de strings magiques.
- `organisation_id` JAMAIS dans un request body : forcé par `BaseRepositoryV4`
  depuis le contexte org. Il est en revanche exposé en réponse (pas dans l'URL,
  donc pas de fuite d'énumération).

Erreurs : format PROMEOS standard `{code, message, hint, correlation_id}` —
cf. `schemas/error.py::APIError`. Les routes lèvent des `HTTPException` dont le
`detail` suit ce dict (pas de modèle d'erreur dédié dupliqué ici).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.v4.enums import Kind, LifecycleState, PriorityBracket


# ── Request ──────────────────────────────────────────────────────────


class ActionCenterItemCreate(BaseModel):
    """Body de POST /api/v4/action-center/items.

    `priority_*` et `lifecycle_state` sont absents par design :
    - la priorité est DÉRIVÉE (scoring R1-R6, Sprint M2-5) — pas une saisie user ;
      à la création, la route pose un placeholder + `score_stale=True`.
    - `lifecycle_state` démarre toujours à `new` (server_default).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Kind
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    domain: Optional[str] = Field(None, max_length=30)


# ── Responses ────────────────────────────────────────────────────────


class ActionCenterItemResponse(BaseModel):
    """Réponse d'un item unique (POST / GET by id)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organisation_id: int  # exposé OK : dérivé du contexte, jamais dans l'URL
    kind: Kind
    title: str
    description: Optional[str]
    domain: Optional[str]
    lifecycle_state: LifecycleState
    priority_bracket: PriorityBracket
    priority_score: float
    score_stale: bool
    created_at: datetime
    updated_at: datetime


class ActionCenterItemListResponse(BaseModel):
    """Réponse de GET /api/v4/action-center/items — liste paginée."""

    items: list[ActionCenterItemResponse]
    total: int
    offset: int
    limit: int
