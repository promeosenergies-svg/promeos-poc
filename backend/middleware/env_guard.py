"""Environment guard — defense in depth pour endpoints sensibles (M2-3.A).

Bloque l'exécution d'endpoints sensibles (seed, reset, debug) en environnement
de production, même pour un admin authentifié. Defense-in-depth contre tout
accident d'opérateur ou erreur de configuration.

Variable d'env consommée : `PROMEOS_ENV` (avec fallback sur DEMO_MODE legacy).

Allowlist des environnements non-prod (où l'endpoint est autorisé) :
- dev / development : développement local
- demo : démo client
- staging : pré-prod
- test / testing : exécution tests CI

Si PROMEOS_ENV est absent ou ∉ allowlist → considéré comme prod → 403.

Note : DEMO_MODE=true est respecté comme signal non-prod (legacy compat) si
PROMEOS_ENV n'est pas défini. Ne pas inverser la logique pour préserver le
comportement existant des seeds en démo.

Source : Sprint M2-3.A (audit Phase 1 gap A2 — consumption_diagnostic seed-demo).
Cohérent avec ADR-027 §4-6 (defense in depth) + critère #6 audit M2-2 (Q13-B).
"""

import os

from fastapi import HTTPException, status

NON_PROD_ENVS = frozenset({"dev", "development", "demo", "staging", "test", "testing"})


def _resolve_env() -> str:
    """Résout l'environnement courant.

    Priorité :
    1. PROMEOS_ENV (canonique)
    2. ENVIRONMENT (fallback générique)
    3. DEMO_MODE=true → 'demo' (legacy compat)
    4. fallback 'production' (par défaut sûr)
    """
    env = os.environ.get("PROMEOS_ENV") or os.environ.get("ENVIRONMENT")
    if env:
        return env.lower().strip()

    # Legacy : si DEMO_MODE=true, considérer comme 'demo' (non-prod)
    demo_mode = os.environ.get("PROMEOS_DEMO_MODE", "false").lower() == "true"
    if demo_mode:
        return "demo"

    return "production"  # default safe : prod si non spécifié


def require_non_prod_env() -> None:
    """FastAPI dependency : bloque l'exécution en environnement de production.

    Usage :
        @router.post("/seed-demo")
        def seed_demo(
            ...,
            _env_guard: None = Depends(require_non_prod_env),  # defense in depth
        ):
            ...

    Raises:
        HTTPException(403, ENV_NOT_ALLOWED) si PROMEOS_ENV ∉ NON_PROD_ENVS.
    """
    env = _resolve_env()
    if env not in NON_PROD_ENVS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ENV_NOT_ALLOWED",
                "message": "This endpoint is disabled in production",
                "hint": (
                    "Seed/reset endpoints are restricted to dev/demo/staging "
                    "environments. Set PROMEOS_ENV to one of: " + ", ".join(sorted(NON_PROD_ENVS))
                ),
                "current_env": env,
            },
        )
