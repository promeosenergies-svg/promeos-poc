"""Org context for V4 repositories (IS11 cardinal · fail-closed).

Un `ContextVar` porte l'`org_id` courant à travers le cycle de vie de la requête.
Peuplé par la dependency `populate_org_context` (consomme le JWT payload M2-3.B).
Lu par `BaseRepositoryV4._apply_scope()` pour filtrer automatiquement les queries.

Sémantique FAIL-CLOSED :
- `current_org_id()` appelé hors d'un contexte peuplé → lève `NoOrgContextError`.
- Cela force chaque appelant V4 à être dans une requête HTTP passée par
  `populate_org_context`, OU à set le contexte explicitement (tests/scripts).
- Contraste avec le legacy `services/iam_scope.py` (helpers fonctionnels mais
  *oubliables* — un dev peut écrire une route sans appeler `apply_org_filter`).
  Ici, oublier le scoping = exception immédiate, pas une fuite silencieuse.

╔═══════════════════════════════════════════════════════════════════════════╗
║ ✅  DETTE JWT/UUID RÉSOLUE — M2-4.1 (ADR-009 Option D)                      ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ Historique : M2-3.C avait un mismatch — le JWT legacy porte `org_id` INT    ║
║ (`Organisation.id` Integer PK) tandis que les 8 models V4 utilisaient       ║
║ `organisation_id` UUID. La chaîne JWT → BaseRepositoryV4 ne bouclait pas.   ║
║                                                                             ║
║ M2-4.1 (ADR-009 Option D · avenant ADR-025/029 A1) a migré les 8 models V4  ║
║ vers `organisation_id` Integer FK `organisations(id)` — identifiant org     ║
║ PARTAGÉ legacy↔V4. Le JWT `org_id: int` alimente désormais le ContextVar    ║
║ directement, sans transformation ni mapping.                                ║
║                                                                             ║
║ Le `ContextVar` est typé `Optional[int]` (cohérent avec le type DB réel).   ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

from contextvars import ContextVar, Token
from typing import Optional, Union

from fastapi import Depends, HTTPException, status

from middleware.auth import get_jwt_payload  # M2-3.B helper JWT-only


class NoOrgContextError(RuntimeError):
    """Levée quand `current_org_id()` est appelée hors d'un contexte peuplé.

    Fail-closed : un repository V4 qui n'a pas de contexte org ne peut pas
    deviner le tenant — il refuse de tourner plutôt que de fuiter cross-org.
    """


# Type-agnostic : porte n'importe quel identifiant org sérialisé en str
# (int legacy aujourd'hui, UUID V4 demain — cf. dette ci-dessus).
_current_org_id: ContextVar[Optional[int]] = ContextVar("current_org_id", default=None)


def current_org_id() -> int:
    """Retourne l'org_id courant. FAIL-CLOSED : lève si non défini.

    Returns:
        int : identifiant org courant (Integer FK `organisations.id`, partagé
        legacy↔V4 depuis M2-4.1 — ADR-009 Option D).

    Raises:
        NoOrgContextError : si appelée hors d'un contexte peuplé.
    """
    org_id = _current_org_id.get()
    if org_id is None:
        raise NoOrgContextError(
            "current_org_id() appelée hors d'un contexte org peuplé. "
            "Vérifier que la route dépend de `populate_org_context` "
            "(ou set le contexte explicitement via `set_org_context()` "
            "dans les tests/scripts)."
        )
    return org_id


def set_org_context(org_id: Union[int, str]) -> Token:
    """Set le contexte org. Retourne un token pour reset.

    Usage : middleware/dependency en contexte HTTP, ET tests/scripts.

    Args:
        org_id : identifiant org. Accepte int OU str (cast `int()` interne pour
        rétro-compat des tests ; le contexte stocke toujours un int).

    Returns:
        Token : à passer à `reset_org_context()` pour restaurer l'état précédent.

    Raises:
        ValueError : si `org_id` n'est pas convertible en int.
    """
    return _current_org_id.set(int(org_id))


def reset_org_context(token: Token) -> None:
    """Reset le contexte org via un token retourné par `set_org_context()`."""
    _current_org_id.reset(token)


async def populate_org_context(
    payload: Optional[dict] = Depends(get_jwt_payload),
):
    """FastAPI dependency : extrait `org_id` du JWT et peuple le ContextVar.

    Sémantique FAIL-VISIBLE (≠ fail-silencieux du legacy) :

    - **JWT présent + org_id présent** : peuple le contexte pour la durée de la
      requête, puis reset en `finally` (propre, pas de fuite cross-requête).

    - **JWT présent + org_id ABSENT** : lève HTTP 403 `ORG_ID_MISSING`. Un token
      valide mais sans claim `org_id` est une anomalie d'émission — on refuse
      bruyamment plutôt que de laisser un repo V4 lever `NoOrgContextError`
      plus loin (erreur 500 opaque).

    - **DEMO_MODE (payload=None)** : NE peuple PAS le contexte. Un repo V4 appelé
      dans ce cas lèvera `NoOrgContextError`. C'est INTENTIONNEL et c'est la
      ligne de séparation V4 ↔ legacy : une démo V4 qui casse révèle un seed mal
      calibré (le seed doit faire `set_org_context(demo_org_id)` explicite).
      On ne masque pas le problème par un bypass org silencieux.

    M2-4.1 (ADR-009 Option D) : le JWT `org_id: int` alimente directement le
    ContextVar typé `int`. `BaseRepositoryV4` filtre sur `organisation_id`
    Integer FK — le type matche de bout en bout, sans mapping.
    """
    if payload is None:
        # DEMO_MODE : pas de JWT, pas de contexte. Laissé tel quel (fail-visible
        # côté repo si appelé). Voir docstring.
        yield
        return

    org_id_raw = payload.get("org_id")
    if not org_id_raw:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORG_ID_MISSING",
                "message": "JWT does not carry an org_id claim",
                "hint": "Re-issue the token via /api/auth/login or /api/auth/switch-org",
            },
        )

    try:
        org_id = int(org_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORG_ID_INVALID",
                "message": f"org_id must be an integer, got {type(org_id_raw).__name__}",
                "hint": "JWT org_id claim must be the legacy Organisation.id (Integer)",
            },
        )

    token = set_org_context(org_id)
    try:
        yield
    finally:
        reset_org_context(token)
