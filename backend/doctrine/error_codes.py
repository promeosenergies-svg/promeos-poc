"""Standard d'erreur API PROMEOS Sol (§12.2 Doctrine).

Format obligatoire : {code, message, hint, correlation_id, scope}
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum


class ErrorCode(str, Enum):
    DATA_QUALITY_INCOMPLETE_PERIOD = "DATA_QUALITY_INCOMPLETE_PERIOD"
    DATA_QUALITY_MISSING_SOURCE = "DATA_QUALITY_MISSING_SOURCE"
    DATA_QUALITY_INCONSISTENT = "DATA_QUALITY_INCONSISTENT"
    AUTH_ORG_MISMATCH = "AUTH_ORG_MISMATCH"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"
    KPI_NOT_REGISTERED = "KPI_NOT_REGISTERED"
    REGULATION_VERSION_MISMATCH = "REGULATION_VERSION_MISMATCH"
    PATRIMOINE_NOT_FOUND = "PATRIMOINE_NOT_FOUND"
    BILLING_ANOMALY_UNRESOLVED = "BILLING_ANOMALY_UNRESOLVED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class StandardError:
    code: ErrorCode
    message: str
    hint: str
    correlation_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:16]}")
    scope: dict | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["code"] = self.code.value
        return d
