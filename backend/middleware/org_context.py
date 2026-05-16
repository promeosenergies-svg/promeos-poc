"""M2-3.C — Org context for V4 repositories (IS11 cardinal · fail-closed).

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
║ ⚠️  DETTE ARCHITECTURE — CÂBLAGE JWT → V4 UUID (à résoudre Sprint M2-4)     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ Le JWT legacy porte `org_id` au format INTEGER (cf. iam_service.py          ║
║ `create_access_token(org_id: int)` · `Organisation.id` Integer PK).         ║
║ Les 8 models V4 (`backend/models/v4/`) utilisent `organisation_id` UUID.    ║
║                                                                             ║
║ → `populate_org_context` extrait `org_id` du JWT et le set tel quel (str).  ║
║   Tant que le JWT porte un INT et que les V4 models filtrent sur UUID,      ║
║   la chaîne réelle JWT → BaseRepositoryV4 N'EST PAS BOUCLÉE en production.   ║
║                                                                             ║
║ → M2-3.C livre le PATTERN testé en isolation (tests unit set le contexte    ║
║   directement avec des org_id str/UUID, sans JWT).                          ║
║ → M2-4 doit trancher : (a) JWT V4 porte un UUID organisation, OU            ║
║   (b) table de mapping org INT ↔ UUID, OU (c) V4 models migrent vers        ║
║   Integer FK organisations.id. Décision d'architecture hors M2-3.C.         ║
║                                                                             ║
║ Cette dette est mentionnée en 3 endroits (traçabilité) :                    ║
║   1. ce docstring                                                           ║
║   2. le message du commit M2-3.C                                            ║
║   3. SECURITY.md (à produire M2-3.D)                                        ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

from contextvars import ContextVar, Token
from typing import Optional

from fastapi import Depends, HTTPException, status

from middleware.auth import get_jwt_payload  # M2-3.B helper JWT-only


class NoOrgContextError(RuntimeError):
    """Levée quand `current_org_id()` est appelée hors d'un contexte peuplé.

    Fail-closed : un repository V4 qui n'a pas de contexte org ne peut pas
    deviner le tenant — il refuse de tourner plutôt que de fuiter cross-org.
    """


# Type-agnostic : porte n'importe quel identifiant org sérialisé en str
# (int legacy aujourd'hui, UUID V4 demain — cf. dette ci-dessus).
_current_org_id: ContextVar[Optional[str]] = ContextVar("current_org_id", default=None)


def current_org_id() -> str:
    """Retourne l'org_id courant. FAIL-CLOSED : lève si non défini.

    Returns:
        str : identifiant org courant (type-agnostic — int-as-str ou UUID-as-str).

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


def set_org_context(org_id: str) -> Token:
    """Set le contexte org. Retourne un token pour reset.

    Usage : middleware/dependency en contexte HTTP, ET tests/scripts.

    Args:
        org_id : identifiant org (sérialisé en str).

    Returns:
        Token : à passer à `reset_org_context()` pour restaurer l'état précédent.
    """
    return _current_org_id.set(str(org_id))


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
      calibré (le seed doit faire `set_org_context("demo-org-id")` explicite).
      On ne masque pas le problème par un bypass org silencieux.

    ⚠️ DETTE (cf. docstring module) : tant que le JWT porte `org_id` INT et que
    les V4 models filtrent sur `organisation_id` UUID, la valeur peuplée ici
    n'est PAS directement utilisable par `BaseRepositoryV4` en production.
    Câblage réel = Sprint M2-4.
    """
    if payload is None:
        # DEMO_MODE : pas de JWT, pas de contexte. Laissé tel quel (fail-visible
        # côté repo si appelé). Voir docstring.
        yield
        return

    org_id = payload.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORG_ID_MISSING",
                "message": "JWT does not carry an org_id claim",
                "hint": "Re-issue the token via /api/auth/login or /api/auth/switch-org",
            },
        )

    token = set_org_context(str(org_id))
    try:
        yield
    finally:
        reset_org_context(token)
