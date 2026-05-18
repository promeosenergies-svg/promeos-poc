"""Slowapi Limiter — single source of truth.

Instance unique utilisée par `main.py` (app.state.limiter + exception handler)
ET par les routes qui décorent leurs endpoints (`@limiter.limit(...)`).

Clé de quota (M2-4.6) : `user:<sub>` si le JWT est décodable, sinon
`ip:<adresse>`. Un endpoint anonyme (ex. public_diagnostic) retombe sur l'IP —
comportement identique à l'ancien `get_remote_address`.

Désactivation : env `PROMEOS_RATE_LIMIT_ENABLED=false` (posée par les tests, le
limiter est `enabled=False` → aucun quota appliqué). Défaut prod = activé.
Migration Redis (multi-instance) différée M3+.

**Reverse proxy** : pour que le rate limit soit effectif derrière nginx /
Cloudflare / ALB, uvicorn doit tourner avec `--proxy-headers
--forwarded-allow-ips=<trusted_proxy>` et le proxy doit **strip le header
X-Forwarded-For entrant** (sinon un client spoofe son IP). Sans ça,
`get_remote_address` retourne l'IP du proxy → bucket partagé (dégradation
globale, pas une faille). En dev / test, pas de proxy → vraie IP → OK.

Module isolé pour éviter le cycle d'import `main.py` ↔ `routes/*`.
"""

from __future__ import annotations

import os

from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

RATE_LIMIT_ENABLED = os.environ.get("PROMEOS_RATE_LIMIT_ENABLED", "true").lower() == "true"


def rate_limit_key(request: Request) -> str:
    """Clé de quota : `user:<sub>` si le JWT est décodable, sinon `ip:<adresse>`.

    Défensif : toute erreur de décodage (token absent/expiré/forgé) retombe sur
    l'IP sans lever — le rate limiting ne doit jamais casser une requête.
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            try:
                from services.iam_service import decode_token

                sub = decode_token(token).get("sub")
                if sub:
                    return f"user:{sub}"
            except Exception:
                pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=rate_limit_key,
    enabled=RATE_LIMIT_ENABLED,
    default_limits=[],
    storage_uri="memory://",
    # headers_enabled volontairement OFF : `headers_enabled=True` exigerait un
    # paramètre `response: Response` sur CHAQUE endpoint décoré (slowapi y
    # injecte les headers X-RateLimit-*). Les 14 endpoints V4 ne l'ont pas tous.
    # Le `Retry-After` du 429 est fourni par `rate_limit_exceeded_handler`.
)

# ── Quotas V4 (M2-4.6) — 5 catégories ────────────────────────────────
QUOTA_READ_V4 = "120/minute"  # GET — browsing confortable
QUOTA_WRITE_V4 = "60/minute"  # POST/PATCH non-upload — modifications réfléchies
QUOTA_UPLOAD_V4 = "10/minute"  # POST /evidences — I/O lourd + magic bytes
QUOTA_VERIFY_V4 = "30/minute"  # PATCH /evidences/{id}/verify — action explicite
QUOTA_FALLBACK_V4 = "100/minute"  # filet de sécurité endpoints non catégorisés


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Réponse 429 au format PROMEOS (`{code, message, hint, retry_after}`).

    Tous les quotas sont par minute → `retry_after` fixe à 60 s (cohérent ;
    une précision fine est différée, cf. M2-4.6 surprise #5).
    """
    retry_after = 60
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
        content={
            "detail": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests",
                "hint": f"Retry after {retry_after} seconds",
                "retry_after": retry_after,
            }
        },
    )
