"""
PROMEOS RegOps - Regle BACS (GTB/GTC)
Legacy wrapper: delegates to bacs_engine v2 for compatibility.
"""

from ..schemas import Finding
from services.bacs_engine import evaluate_legacy


def evaluate(site, batiments: list, evidences: list, config: dict) -> list[Finding]:
    return evaluate_legacy(site, batiments, evidences, config)
