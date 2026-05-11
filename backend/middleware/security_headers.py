"""
PROMEOS — Security Headers Middleware (Phase L36.5 audit fix PROMEOS-SEC-2026-025).

Inject les headers HTTP de sécurité OWASP recommandés sur chaque réponse :
- `X-Frame-Options: DENY`              — anti-clickjacking
- `X-Content-Type-Options: nosniff`    — anti MIME-sniff
- `Strict-Transport-Security`          — anti downgrade HTTPS (en prod uniquement)
- `Referrer-Policy: strict-origin-when-cross-origin` — minimisation referrer leak
- `Content-Security-Policy: default-src 'self'` — anti-XSS basique (élargie en
  dev pour permettre Vite HMR + lazy chunks).

Phase L36.5 contexte : Reviewer #3 security-auditor L35 a flag l'absence totale
de security headers comme bloqueur Medium pré-pilot externe (CWE-1021).

ASGI-natif (pas de FastAPI middleware obligatoire), pattern aligné sur
RequestContextMiddleware.
"""

from __future__ import annotations

import os


class SecurityHeadersMiddleware:
    """ASGI middleware : inject security headers OWASP sur chaque HTTP response."""

    def __init__(self, app):
        self.app = app
        # En dev : HSTS désactivé + CSP relaxée pour Vite HMR/lazy chunks
        self._is_prod = os.environ.get("PROMEOS_ENV", "dev").lower() == "production"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Anti-clickjacking (toujours)
                headers.append((b"x-frame-options", b"DENY"))
                # Anti MIME-sniff (toujours)
                headers.append((b"x-content-type-options", b"nosniff"))
                # Referrer minimisation (toujours)
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                # HSTS uniquement en prod (sinon casse dev local HTTP)
                if self._is_prod:
                    headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
                # CSP : 'self' en prod, relaxé en dev pour Vite HMR/lazy chunks +
                # connexion WS Vite + sources fonts/img du repo
                if self._is_prod:
                    headers.append(
                        (
                            b"content-security-policy",
                            b"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'",
                        )
                    )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
