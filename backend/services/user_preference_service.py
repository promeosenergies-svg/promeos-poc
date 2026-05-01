"""User preference service — Sprint Refonte Narrative dynamique Phase 1.4 + 13.B.

Service central pour lecture/écriture des préférences utilisateur (table
`user_preferences`). Évite le couplage `services/narrative` → `routes/`
(les services ne doivent pas importer les routes — anti-pattern layering).

## Phase 1.4 — typology_override (global user)

Gère l'override de la typologie auto-détectée par NAF.

## Phase 13.B — Cross-org typology_override (audit final BL-7)

Migration vers (user_id, org_id) composite : un user multi-org peut
désormais avoir des overrides différents selon l'org active.

Ordre de priorité résolution :
  1. (user_id, current_org_id) → override scopé org spécifique
  2. (user_id, NULL) → override global user (rétrocompat Phase 1.4)
  3. None → auto-détection NAF reprend la main

## Extensible

À terme : `narrative_style`, `push_threshold`, `email_digest_frequency`.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.4 + audit final BL-7.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from doctrine.naf_to_typology import OrganizationTypology
from models import UserPreference


def get_or_create_user_preference(
    db: Session,
    user_id: int,
    org_id: Optional[int] = None,
) -> UserPreference:
    """Récupère la préférence du user (ou (user, org) si org_id fourni).

    Phase 13.B : `org_id=None` → override global (compat Phase 1.4).
    `org_id != None` → override scopé à l'org spécifique.

    NB : ne commit pas — appelle `db.flush()` uniquement.

    Args:
        db: session SQLAlchemy.
        user_id: id du user (issu de get_current_user.id).
        org_id: id org pour scope (None = override global).

    Returns:
        UserPreference (existant ou nouveau).
    """
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id, UserPreference.org_id == org_id).first()
    if pref is None:
        pref = UserPreference(user_id=user_id, org_id=org_id, typology_override=None)
        db.add(pref)
        db.flush()
    return pref


def get_user_typology_override(
    db: Session,
    user_id: int,
    org_id: Optional[int] = None,
) -> Optional[OrganizationTypology]:
    """Lit l'override typologie du user avec priorité cross-org (Phase 13.B).

    Ordre de priorité (audit final BL-7 closé) :
      1. (user_id, org_id) si org_id fourni et override scopé existe
      2. (user_id, NULL) override global user (rétrocompat Phase 1.4)
      3. None → caller retombe sur auto-détection NAF

    Args:
        db: session SQLAlchemy.
        user_id: id du user.
        org_id: id de l'org courante (None = lookup uniquement global).

    Returns:
        `OrganizationTypology` si override défini, None sinon.
        Jamais d'exception (user_id inexistant → None).
    """
    # 1. Phase 13.B — Priorité override scopé org si org_id fourni
    if org_id is not None:
        pref_org = (
            db.query(UserPreference)
            .filter(
                UserPreference.user_id == user_id,
                UserPreference.org_id == org_id,
            )
            .first()
        )
        if pref_org is not None and pref_org.typology_override is not None:
            return pref_org.typology_override

    # 2. Fallback override global user (org_id NULL — rétrocompat Phase 1.4)
    pref_global = (
        db.query(UserPreference).filter(UserPreference.user_id == user_id, UserPreference.org_id.is_(None)).first()
    )
    if pref_global is None:
        return None
    return pref_global.typology_override


__all__ = [
    "get_or_create_user_preference",
    "get_user_typology_override",
]
