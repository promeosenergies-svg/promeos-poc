"""
PROMEOS Connectors — Exceptions typées pour Enedis Data Connect
"""


class EnedisDataConnectError(Exception):
    """Erreur de base pour le connecteur Enedis Data Connect."""

    def __init__(self, message: str, code: str | None = None, detail: dict | None = None):
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


class ConsentExpiredError(EnedisDataConnectError):
    """Le consentement du client a expiré (ADAM-ERR0025)."""

    def __init__(self, prm: str, message: str = "Consentement expiré"):
        super().__init__(message, code="ADAM-ERR0025", detail={"prm": prm})
        self.prm = prm


class ConsentRevokedError(EnedisDataConnectError):
    """Le consentement du client a été révoqué."""

    def __init__(self, prm: str, message: str = "Consentement révoqué"):
        super().__init__(message, code="CONSENT_REVOKED", detail={"prm": prm})
        self.prm = prm


class PrmNotFoundError(EnedisDataConnectError):
    """PRM inconnu chez Enedis (ADAM-ERR0069)."""

    def __init__(self, prm: str, message: str = "PRM non trouvé"):
        super().__init__(message, code="ADAM-ERR0069", detail={"prm": prm})
        self.prm = prm


class TokenInvalidError(EnedisDataConnectError):
    """Token invalide ou expiré (ADAM-ERR0031)."""

    def __init__(self, message: str = "Token invalide"):
        super().__init__(message, code="ADAM-ERR0031")


class RateLimitError(EnedisDataConnectError):
    """Limite de débit dépassée (HTTP 429)."""

    def __init__(self, retry_after: int | None = None):
        msg = f"Rate limit — retry après {retry_after}s" if retry_after else "Rate limit atteint"
        super().__init__(msg, code="RATE_LIMIT")
        self.retry_after = retry_after


class EnedisApiError(EnedisDataConnectError):
    """Erreur HTTP générique de l'API Enedis."""

    def __init__(self, status_code: int, body: str = ""):
        super().__init__(f"Enedis API HTTP {status_code}: {body[:200]}", code=f"HTTP_{status_code}")
        self.status_code = status_code
        self.body = body
