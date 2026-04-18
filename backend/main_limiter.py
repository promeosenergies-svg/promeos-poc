"""Slowapi Limiter — single source of truth.

Instance unique utilisée par `main.py` (app.state.limiter + exception handler)
ET par les routes qui décorent leurs endpoints (`@limiter.limit(...)`).

**Important** : pour que le rate limit soit effectif derrière un reverse proxy
(nginx, Cloudflare, ALB), uvicorn doit être démarré avec :

    uvicorn main:app --proxy-headers --forwarded-allow-ips=<trusted_proxy_ip>

et le proxy doit **strip le header X-Forwarded-For entrant** (sinon un client
peut spoofer son IP). Sans ça, `get_remote_address` retourne l'IP du proxy
(constant) → toute la planète partage le même bucket (dégradation globale,
pas une faille). En dev / test, pas de reverse proxy → vraie IP client → OK.

Module isolé pour éviter le cycle d'import `main.py` ↔ `routes/*`.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
