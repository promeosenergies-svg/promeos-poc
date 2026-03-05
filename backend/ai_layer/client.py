"""
PROMEOS AI - Client IA (live Claude API + fallback stub)
Calls Claude API when AI_API_KEY is configured, otherwise returns stubs.
"""

import logging
import os

import httpx

_logger = logging.getLogger("promeos.ai")

AI_API_KEY = os.environ.get("AI_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-4-5-20250929")
_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class AIClient:
    """Client IA Claude. Stub si pas de clé API."""

    def __init__(self):
        self.api_key = os.environ.get("AI_API_KEY") or AI_API_KEY
        self.model = os.environ.get("AI_MODEL") or AI_MODEL
        self.stub_mode = not self.api_key

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        """
        Appel synchrone API Claude.
        En stub mode: retourne un placeholder.
        """
        if self.stub_mode:
            return (
                f"[AI Stub Mode] Analyse non disponible. "
                f"Configurez AI_API_KEY pour activer l'IA.\n\n"
                f"Prompt: {user_prompt[:100]}..."
            )

        try:
            return _call_claude_sync(
                self.api_key, self.model, system_prompt, user_prompt, max_tokens
            )
        except Exception as exc:
            _logger.warning("AI call failed, falling back to stub: %s", exc)
            return (
                f"[AI Fallback] L'appel IA a échoué ({type(exc).__name__}). "
                f"Résultat stub retourné.\n\n"
                f"Prompt: {user_prompt[:100]}..."
            )

    async def acomplete(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        """
        Appel asynchrone API Claude.
        En stub mode: retourne un placeholder.
        """
        if self.stub_mode:
            return (
                f"[AI Stub Mode] Analyse non disponible. "
                f"Configurez AI_API_KEY pour activer l'IA.\n\n"
                f"Prompt: {user_prompt[:100]}..."
            )

        try:
            return await _call_claude_async(
                self.api_key, self.model, system_prompt, user_prompt, max_tokens
            )
        except Exception as exc:
            _logger.warning("AI async call failed, falling back to stub: %s", exc)
            return (
                f"[AI Fallback] L'appel IA a échoué ({type(exc).__name__}). "
                f"Résultat stub retourné.\n\n"
                f"Prompt: {user_prompt[:100]}..."
            )


def _call_claude_sync(api_key: str, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    """Synchronous Claude API call via httpx."""
    resp = httpx.post(
        _API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


async def _call_claude_async(api_key: str, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    """Asynchronous Claude API call via httpx."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


# Singleton
_client = None


def get_client() -> AIClient:
    global _client
    if _client is None:
        _client = AIClient()
    return _client
