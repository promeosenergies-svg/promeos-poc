"""
PROMEOS — Resolution d'actor pour audit-trail.

Extrait l'identite de l'acteur depuis le contexte de requete.
Actor n'est JAMAIS vide. Fallback explicite si non identifie.
"""

from typing import Optional


def resolve_actor(
    auth=None,
    request=None,
    fallback: str = "manual_unknown",
) -> str:
    """Resout l'actor depuis le contexte d'authentification ou de requete.

    Priorite :
    1. auth.email si disponible
    2. auth.user_id si disponible
    3. Header X-Actor si present
    4. fallback explicite (jamais vide)
    """
    # 1. Depuis le contexte auth
    if auth:
        if hasattr(auth, "email") and auth.email:
            return auth.email
        if hasattr(auth, "user_id") and auth.user_id:
            return f"user_{auth.user_id}"
        if hasattr(auth, "display_name") and auth.display_name:
            return auth.display_name

    # 2. Depuis le header de requete
    if request:
        actor_header = None
        if hasattr(request, "headers"):
            actor_header = request.headers.get("X-Actor")
        if actor_header:
            return actor_header

    # 3. Fallback — jamais vide
    return fallback or "system"
