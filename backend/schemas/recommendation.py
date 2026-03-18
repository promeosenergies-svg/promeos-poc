"""Canonical recommendation schema for PROMEOS prescriptive layer."""

from pydantic import BaseModel, Field
from typing import Optional, List


class Recommendation(BaseModel):
    recommendation_id: str
    issue_id: Optional[str] = None
    action_id: Optional[int] = None
    scope: str = Field(description="executive|portfolio|site")
    domain: str
    site_id: Optional[int] = None
    site_name: Optional[str] = None
    recommended_action: str
    why_now: str
    estimated_impact_eur: Optional[float] = None
    urgency_score: float = Field(ge=0, le=100, description="Higher = more urgent")
    risk_score: float = Field(ge=0, le=100, description="Higher = more risky")
    confidence_score: float = Field(ge=0, le=100, description="Higher = more confident")
    effort_score: Optional[float] = Field(None, ge=0, le=100, description="Higher = more effort")
    decision_score: float = Field(ge=0, le=100, description="Composite: higher = act now")
    blockers: List[str] = Field(default_factory=list)
    traceable: bool = True


class RecommendationSummary(BaseModel):
    total: int
    by_scope: dict
    by_domain: dict
    avg_decision_score: Optional[float] = None
    top_5: List[dict]
