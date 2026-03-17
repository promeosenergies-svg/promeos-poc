"""Canonical ActionableIssue — unified signal format across all PROMEOS domains."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from enum import Enum


class IssueSeverity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class IssueDomain(str, Enum):
    compliance = "compliance"
    billing = "billing"
    purchase = "purchase"
    patrimoine = "patrimoine"


class ActionableIssue(BaseModel):
    issue_id: str = Field(description="Unique identifier: {domain}_{issue_code}_{site_id}")
    domain: IssueDomain
    severity: IssueSeverity
    site_id: int = Field(gt=0)
    site_name: Optional[str] = None
    contract_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    issue_code: str = Field(min_length=1, max_length=100)
    issue_label: str = Field(min_length=1, max_length=500)
    reason_codes: List[str] = Field(default_factory=list)
    estimated_impact_eur: Optional[float] = None
    recommended_action: Optional[str] = None
    traceable: bool = True
    status: str = Field(default="open", pattern="^(open|acknowledged|resolved|dismissed)$")


class ActionCenterResponse(BaseModel):
    total: int
    issues: List[ActionableIssue]
    domains: dict = Field(default_factory=dict, description="Count by domain")
    severities: dict = Field(default_factory=dict, description="Count by severity")
