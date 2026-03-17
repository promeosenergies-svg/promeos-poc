"""PROMEOS — Pydantic Schemas"""

from .error import APIError  # noqa: F401
from .patrimoine_schemas import (  # noqa: F401
    QuickCreateSiteRequest,
    QuickCreateSiteResponse,
    SiteUpdateRequest,
    ContractCreateRequest,
)
