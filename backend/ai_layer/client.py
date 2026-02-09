"""
PROMEOS AI - Client IA (stub mode if no API key)
"""
import os


class AIClient:
    """Client IA OpenAI-compatible. Stub si pas de cle API."""

    def __init__(self):
        self.api_key = os.environ.get("AI_API_KEY")
        self.model = os.environ.get("AI_MODEL", "claude-sonnet-4-5-20250929")
        self.stub_mode = not self.api_key

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Appel API IA.
        En stub mode: retourne un placeholder.
        """
        if self.stub_mode:
            return f"[AI Stub Mode] Analyse non disponible. Configurez AI_API_KEY pour activer l'IA.\n\nPrompt: {user_prompt[:100]}..."

        # TODO: Real API call (httpx POST to api.anthropic.com)
        # For now, return stub even if key present
        return f"[AI Mock] Response for: {user_prompt[:50]}..."


# Singleton
_client = None


def get_client() -> AIClient:
    global _client
    if _client is None:
        _client = AIClient()
    return _client
