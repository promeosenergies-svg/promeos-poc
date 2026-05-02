"""Pydantic schemas user_notification_preferences — Phase 2.C Sprint α-push.

Update partial pattern : tous les champs Optional dans
`UserNotificationPreferenceUpdate` + utilisation `model_dump(exclude_unset=True)`
côté handler pour appliquer uniquement les champs explicitement fournis
(cf. pattern repo `routes/patrimoine_crud.py:156`).

Validation `digest_channels` : MVP whitelist `{"email"}`. Forward-compat
SMS Phase 3 → ajouter `"sms"` à `_ALLOWED_CHANNELS`.

Réf : docs/audits/sprint_alpha_push_phase0_audit_20260502.md (Q2),
backend/models/user_notification_preference.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


_ALLOWED_CHANNELS = {"email"}  # MVP — SMS forward-compat Phase 3


class UserNotificationPreferenceResponse(BaseModel):
    """Réponse lecture — incluant defaults gracieux si aucune ligne DB.

    Quand l'utilisateur n'a jamais configuré ses préférences, le service
    retourne les valeurs par défaut + `created_at=None / updated_at=None`
    pour signaler "ligne non persistée".
    """

    digest_daily_enabled: bool
    digest_daily_locale: str
    digest_channels: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserNotificationPreferenceUpdate(BaseModel):
    """Update partial — tous champs Optional. Le service applique
    `model_dump(exclude_unset=True)` pour ne modifier que les champs
    explicitement fournis dans le PATCH.
    """

    digest_daily_enabled: Optional[bool] = None
    digest_daily_locale: Optional[str] = Field(
        None,
        max_length=16,
        description="Locale i18n future (défaut fr-FR)",
    )
    digest_channels: Optional[List[str]] = Field(
        None,
        description="Channels actifs — MVP {'email'}, forward-compat SMS Phase 3",
    )

    @field_validator("digest_channels")
    @classmethod
    def validate_channels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        if not v:
            raise ValueError("digest_channels must not be empty list (use null to skip)")
        invalid = [c for c in v if c not in _ALLOWED_CHANNELS]
        if invalid:
            raise ValueError(f"digest_channels invalid: {invalid}. Allowed: {sorted(_ALLOWED_CHANNELS)}")
        return v
