"""
PROMEOS RegOps - Scoring module (S2 — DEPRECIE pour le score principal)

⚠️ Ce module N'EST PAS la source de verite pour le score global.
La SoT est : engine.py → compliance_score_service (S1) → RegAssessment.compliance_score

Ce module est conserve pour :
- Logique de dedup, clamp, et profiling reutilisable
- Tests de hardening du scoring
- Usage potentiel futur pour score_explain detaille

Les poids dans scoring_profile.json sont alignes avec regs.yaml (0.45/0.30/0.25)
depuis la Phase 2 DT (03/04/2026).

Source canonique poids :
- Sans Audit/SME : DT 45% / BACS 30% / APER 25% (regs.yaml)
- Avec Audit/SME : DT 39% / BACS 28% / APER 17% / AUDIT 16% (engine.py)
"""

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from .schemas import Finding


# Cache for scoring profile
_profile_cache = {}


@dataclass
class ScoringPenalty:
    regulation: str
    rule_id: str
    severity: str
    amount: float
    reason: str
    evidence_refs: list[str] = field(default_factory=list)
    suppressed: bool = False
    suppressed_by: str = ""


@dataclass
class ScoreResult:
    score: float
    confidence_score: float
    penalties: list[ScoringPenalty] = field(default_factory=list)
    suppressed_penalties: list[ScoringPenalty] = field(default_factory=list)
    profile_id: str = ""
    profile_version: str = ""


def load_scoring_profile() -> dict:
    """Load scoring_profile.json (cached)."""
    if _profile_cache:
        return _profile_cache

    profile_path = Path(__file__).parent / "config" / "scoring_profile.json"
    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)

    _profile_cache.update(profile)
    return _profile_cache


def _severity_rank(severity: str) -> int:
    """Rank severities for dedup comparison."""
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity.lower(), 0)


def _status_rank(status: str) -> int:
    """Rank statuses for dedup comparison."""
    return {
        "NON_COMPLIANT": 4,
        "UNKNOWN": 3,
        "AT_RISK": 2,
        "EXEMPTION_POSSIBLE": 1,
        "COMPLIANT": 0,
        "OUT_OF_SCOPE": 0,
    }.get(status, 0)


def _dedup_findings(findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
    """
    Dedup by (regulation, rule_id). Keep most severe per group.
    Returns (unique_findings, suppressed_findings).
    """
    groups: dict[tuple, list[Finding]] = {}
    for f in findings:
        key = (f.regulation, f.rule_id)
        groups.setdefault(key, []).append(f)

    unique = []
    suppressed = []

    for group in groups.values():
        if len(group) == 1:
            unique.append(group[0])
        else:
            group.sort(
                key=lambda f: (_severity_rank(f.severity), _status_rank(f.status)),
                reverse=True,
            )
            unique.append(group[0])
            suppressed.extend(group[1:])

    return unique, suppressed


def _compute_urgency(legal_deadline: Optional[date], profile: dict) -> float:
    """Compute urgency factor from deadline and profile."""
    if not legal_deadline:
        return 1.0

    days = (legal_deadline - date.today()).days
    uw = profile.get("urgency_weights_days", {})

    if days <= 0:
        return uw.get("0", 1.0)
    elif days <= 90:
        return uw.get("90", 0.8)
    elif days <= 180:
        return uw.get("180", 0.6)
    elif days <= 365:
        return uw.get("365", 0.4)
    else:
        return uw.get("730", 0.2)


def compute_regops_score(
    findings: list[Finding],
    dq_coverage_pct: float = 100.0,
    profile: dict = None,
) -> ScoreResult:
    """
    Compute RegOps compliance score with dedup, clamp, and profiling.

    1. Filter out COMPLIANT/OUT_OF_SCOPE
    2. Dedup by (regulation, rule_id) — keep most severe
    3. Compute weighted penalty per finding
    4. Normalize and clamp to [0, 100]
    5. Compute confidence_score from dq_coverage_pct
    """
    if profile is None:
        profile = load_scoring_profile()

    # 1. Filter
    active = [f for f in findings if f.status not in ("OUT_OF_SCOPE", "COMPLIANT")]

    # 2. Dedup
    unique, suppressed = _dedup_findings(active)

    # 3. Compute penalties
    penalties = []
    total_weight = 0.0
    weighted_sum = 0.0

    reg_weights = profile.get("regulation_weights", {})
    sev_mults = profile.get("severity_multipliers", {})
    conf_mults = profile.get("confidence_multipliers", {})
    status_pens = profile.get("status_penalties", {})

    for f in unique:
        reg_w = reg_weights.get(f.regulation, 1.0)
        sev_m = sev_mults.get(f.severity.lower(), 0.1)
        conf_m = conf_mults.get(f.confidence.lower(), 1.0)
        status_p = status_pens.get(f.status, 0.0)
        urgency = _compute_urgency(f.legal_deadline, profile)

        finding_weight = reg_w * sev_m * conf_m * urgency
        total_weight += finding_weight

        penalty_amount = finding_weight * status_p
        weighted_sum += penalty_amount

        penalties.append(
            ScoringPenalty(
                regulation=f.regulation,
                rule_id=f.rule_id,
                severity=f.severity,
                amount=round(penalty_amount, 4),
                reason=f.explanation,
                evidence_refs=f.inputs_used if f.inputs_used else [],
            )
        )

    # 4. Normalize and clamp
    if total_weight > 0:
        raw_score = 100.0 - (weighted_sum / total_weight * 100.0)
    else:
        raw_score = 100.0

    score = round(max(0.0, min(100.0, raw_score)), 1)

    # 5. Confidence from DQ
    confidence_score = round(max(0.0, min(100.0, dq_coverage_pct)), 1)

    # Suppressed penalties
    suppressed_penalties = [
        ScoringPenalty(
            regulation=f.regulation,
            rule_id=f.rule_id,
            severity=f.severity,
            amount=0.0,
            reason=f.explanation,
            evidence_refs=f.inputs_used if f.inputs_used else [],
            suppressed=True,
            suppressed_by=f"{f.regulation}:{f.rule_id}",
        )
        for f in suppressed
    ]

    return ScoreResult(
        score=score,
        confidence_score=confidence_score,
        penalties=penalties,
        suppressed_penalties=suppressed_penalties,
        profile_id=profile.get("id", "unknown"),
        profile_version=profile.get("version", "0.0.0"),
    )
