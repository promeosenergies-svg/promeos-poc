"""Route REST /api/v1/users/me/* — Phase 2.C Sprint α-push.

Endpoints self-service utilisateur courant. Le user_id est **toujours**
résolu via `get_current_user` (token JWT) — pas de support `user_id`
dans body / path param (SG_USER_PREFS_03 : isolation user-tenant).

Endpoints livrés Phase 2.C :
- `GET  /api/v1/users/me/notification-preferences`
  → préférences digest user (defaults gracieux si pas de ligne)
- `PATCH /api/v1/users/me/notification-preferences`
  → partial update (model_dump(exclude_unset=True))

Réf : docs/audits/sprint_alpha_push_phase0_audit_20260502.md (Q2),
backend/services/user_notification_preference_service.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_current_user
from models import User
from schemas.user_notification_preference import (
    UserNotificationPreferenceResponse,
    UserNotificationPreferenceUpdate,
)
from services.user_notification_preference_service import (
    get_user_preferences,
    upsert_user_preferences,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get(
    "/me/notification-preferences",
    response_model=UserNotificationPreferenceResponse,
)
def get_my_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserNotificationPreferenceResponse:
    """Lecture self-service des préférences digest de l'utilisateur courant.

    Defaults gracieux si aucune ligne DB :
    `digest_daily_enabled=True, digest_daily_locale='fr-FR',
    digest_channels=['email'], created_at=None, updated_at=None`.
    """
    prefs = get_user_preferences(db, current_user.id)
    return UserNotificationPreferenceResponse(**prefs)


@router.patch(
    "/me/notification-preferences",
    response_model=UserNotificationPreferenceResponse,
)
def patch_my_notification_preferences(
    body: UserNotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserNotificationPreferenceResponse:
    """Update partial des préférences digest. user_id pris de auth token,
    JAMAIS du body (SG_USER_PREFS_03 isolation).

    Crée la ligne au premier appel (upsert), puis update partiel sur
    les appels suivants. Validation Pydantic appliquée en amont
    (digest_channels whitelist, digest_daily_locale max_length).
    """
    updates = body.model_dump(exclude_unset=True)
    prefs = upsert_user_preferences(db, current_user.id, updates)
    return UserNotificationPreferenceResponse(**prefs)
