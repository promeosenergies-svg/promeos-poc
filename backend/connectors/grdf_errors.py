"""
PROMEOS Connectors — Exceptions typées pour GRDF ADICT
"""


class GrdfAdictError(Exception):
    """Erreur de base pour le connecteur GRDF ADICT."""

    def __init__(self, message: str, code: str | None = None, detail: dict | None = None):
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


class PceNotFoundError(GrdfAdictError):
    """PCE inconnu chez GRDF."""

    def __init__(self, pce: str, message: str = "PCE non trouvé"):
        super().__init__(message, code="PCE_NOT_FOUND", detail={"pce": pce})
        self.pce = pce


class PceNotAuthorizedError(GrdfAdictError):
    """Accès non autorisé au PCE (consentement manquant ou révoqué)."""

    def __init__(self, pce: str, message: str = "PCE non autorisé"):
        super().__init__(message, code="PCE_NOT_AUTHORIZED", detail={"pce": pce})
        self.pce = pce


class GrdfApiError(GrdfAdictError):
    """Erreur HTTP générique de l'API GRDF."""

    def __init__(self, status_code: int, body: str = ""):
        super().__init__(f"GRDF API HTTP {status_code}: {body[:200]}", code=f"HTTP_{status_code}")
        self.status_code = status_code
        self.body = body
