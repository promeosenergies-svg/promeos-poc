"""
PROMEOS RegOps - Domain schemas (dataclasses)
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Finding:
    regulation: str
    rule_id: str
    status: str
    severity: str
    confidence: str
    legal_deadline: Optional[date]
    trigger_condition: str
    config_params_used: dict
    inputs_used: list[str]
    missing_inputs: list[str]
    explanation: str
    category: str = "obligation"  # "obligation" (DT/BACS/APER) or "incentive" (CEE)


@dataclass
class Action:
    action_code: str
    label: str
    priority_score: float
    urgency_reason: str
    owner_role: str
    effort: str
    roi_hint: Optional[str] = None
    cee_p6_hints: Optional[dict] = None
    is_ai_suggestion: bool = False


@dataclass
class SiteSummary:
    site_id: int
    global_status: str
    compliance_score: float
    next_deadline: Optional[date]
    findings: list[Finding] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    deterministic_version: str = ""
    confidence_score: float = 0.0
    scoring_profile_id: str = ""
