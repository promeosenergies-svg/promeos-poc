"""Canonical contract perimeter — links billing, contract, and site."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class ContractPerimeter(BaseModel):
    """Validates that a billing reference is consistent with contract and site."""

    site_id: int = Field(gt=0)
    contract_id: Optional[int] = Field(None, gt=0)
    energy_type: Optional[str] = Field(None, pattern="^(elec|gaz|reseau_chaleur|reseau_froid|fioul|bois|autre)$")
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class PerimeterCheckResult(BaseModel):
    """Result of a perimeter consistency check."""

    consistent: bool
    site_exists: bool
    contract_exists: Optional[bool] = None
    contract_matches_site: Optional[bool] = None
    contract_covers_period: Optional[bool] = None
    warnings: list = Field(default_factory=list)
