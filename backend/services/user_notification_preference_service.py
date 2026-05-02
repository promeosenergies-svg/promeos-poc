"""Service user_notification_preferences — Phase 2.C Sprint α-push.

CRUD + upsert avec defaults gracieux. Le service est l'unique chemin
canonique pour lire/écrire les préférences digest user-scoped (pas de
backref bidirectionnel `User.notification_preferences` — cf. modèle).

Pattern :
- `get_user_preferences(db, user_id)` → dict avec defaults si pas de ligne
- `upsert_user_preferences(db, user_id, updates)` → insert ou update
  selon présence ligne, retourne dict propre

Réf : docs/audits/sprint_alpha_push_phase0_audit_20260502.md (Q2),
backend/models/user_notification_preference.py.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from models.user_notification_preference import UserNotificationPreference


# Defaults gracieux — appliqués si aucune ligne DB (lecture)
# OU si nouvelle ligne créée (upsert).
DEFAULTS: dict[str, Any] = {
    "digest_daily_enabled": True,
    "digest_daily_locale": "fr-FR",
    "digest_channels": ["email"],
}


def get_user_preferences(db: Session, user_id: int) -> dict:
    """Retourne les préférences digest pour `user_id` ou les defaults.

    Defaults gracieux : si aucune ligne en DB, retourne les valeurs par
    défaut + `created_at=None / updated_at=None` pour signaler "non
    persisté".

    Pattern de défense en profondeur : `digest_channels` est cloné
    (list comprehension) pour éviter les mutations partagées du DEFAULTS
    global entre appels.
    """
    pref = db.query(UserNotificationPreference).filter_by(user_id=user_id).first()
    if pref is None:
        return {
            "digest_daily_enabled": DEFAULTS["digest_daily_enabled"],
            "digest_daily_locale": DEFAULTS["digest_daily_locale"],
            "digest_channels": list(DEFAULTS["digest_channels"]),
            "created_at": None,
            "updated_at": None,
        }
    return _to_dict(pref)


def upsert_user_preferences(
    db: Session,
    user_id: int,
    updates: dict[str, Any],
) -> dict:
    """Insert ou update les préférences digest pour `user_id`.

    Comportement :
    - Si aucune ligne : crée une nouvelle ligne avec DEFAULTS, puis
      applique `updates` par-dessus (qui peut être vide).
    - Si ligne existe : applique uniquement les champs présents dans
      `updates` (partial update via `model_dump(exclude_unset=True)`
      côté handler).

    Le service ne valide pas les valeurs — la validation est dans le
    schema Pydantic `UserNotificationPreferenceUpdate.field_validator`.

    Returns
    -------
    dict
        Préférences fraîches re-lues post-commit (cohérent avec response
        endpoint).
    """
    pref = db.query(UserNotificationPreference).filter_by(user_id=user_id).first()
    if pref is None:
        pref = UserNotificationPreference(
            user_id=user_id,
            digest_daily_enabled=DEFAULTS["digest_daily_enabled"],
            digest_daily_locale=DEFAULTS["digest_daily_locale"],
            digest_channels=list(DEFAULTS["digest_channels"]),
        )
        db.add(pref)

    # Partial update — n'applique que les champs présents
    _ALLOWED_FIELDS = {"digest_daily_enabled", "digest_daily_locale", "digest_channels"}
    for field, value in updates.items():
        if field in _ALLOWED_FIELDS:
            setattr(pref, field, value)

    db.commit()
    db.refresh(pref)
    return _to_dict(pref)


def _to_dict(pref: UserNotificationPreference) -> dict:
    """Sérialisation dict pour API response."""
    return {
        "digest_daily_enabled": pref.digest_daily_enabled,
        "digest_daily_locale": pref.digest_daily_locale,
        "digest_channels": list(pref.digest_channels) if pref.digest_channels else [],
        "created_at": pref.created_at,
        "updated_at": pref.updated_at,
    }
