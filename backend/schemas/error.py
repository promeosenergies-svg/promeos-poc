"""
PROMEOS — Standard API Error Contract.
Toutes les erreurs HTTP renvoient ce format uniforme.
"""

import uuid
from typing import Optional

from pydantic import BaseModel


class APIError(BaseModel):
    code: str  # e.g. "SITE_NOT_FOUND", "VALIDATION_ERROR"
    message: str
    hint: Optional[str] = None
    correlation_id: str = ""

    @classmethod
    def create(cls, code: str, message: str, hint: str = None):
        return cls(
            code=code,
            message=message,
            hint=hint,
            correlation_id=str(uuid.uuid4())[:8],
        )
