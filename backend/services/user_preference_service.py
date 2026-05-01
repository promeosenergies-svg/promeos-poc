"""User preference service — Sprint Refonte Narrative dynamique Phase 1.4.

Service central pour lecture/écriture des préférences utilisateur (table
`user_preferences`). Évite le couplage `services/narrative` → `routes/`
(les services ne doivent pas importer les routes — anti-pattern layering).

## Phase 1.4 — typology_override

Gère l'override de la typologie auto-détectée par NAF. Décision Amine
2026-05-01 : la préférence est **globale par user** (pas scopée à l'org),
ce qui constitue un choix produit explicite — un user multi-org partage
son override entre toutes ses orgs (cf. ADR P1-1 Phase 2).

## Extensible

À terme : `narrative_style`, `push_threshold`, `email_digest_frequency`.
Chaque nouveau champ s'ajoutera dans `UserPreference` + helper dédié ici.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.4.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from doctrine.naf_to_typology import OrganizationTypology
from models import UserPreference


def get_or_create_user_preference(db: Session, user_id: int) -> UserPreference:
    """Récupère la préférence du user, ou la crée si inexistante.

    NB : ne commit pas — appelle `db.flush()` uniquement. Le caller
    décide quand commiter (transaction-friendly).

    Args:
        db: session SQLAlchemy.
        user_id: id du user (issu de get_current_user.id).

    Returns:
        UserPreference (existant ou nouveau).
    """
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

    Design choice (Amine 2026-05-01) : **global par user**. Un user
    multi-org partage son override entre toutes ses orgs. Si V2 multi-org
    nécessite un override scopé, ajouter `(user_id, org_id)` unique
    composite (ADR P1-1 Phase 2).

    Args:
        db: session SQLAlchemy.
        user_id: id du user.

    Returns:
        `OrganizationTypology` si override défini, None sinon.
        Jamais d'exception (user_id inexistant → None).
    """
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref is None:
        return None
    return pref.typology_override


__all__ = [
    "get_or_create_user_preference",
    "get_user_typology_override",
]
