"""
RouterAgent — Route chaque demande d'annotation vers le meilleur annotateur.
Priorise par trust_weight et domaine. Escalade si impact financier > 5000 EUR.
"""

from sqlalchemy.orm import Session
from models import AnnotatorProfile


class RouterAgent:
    ESCALATION_RULES = [
        lambda item: item.get("severity") == "HIGH" and item.get("domain") == "compliance",
        lambda item: item.get("financial_impact_eur", 0) > 5000,
        lambda item: item.get("is_first_occurrence", False),
    ]

    def route(self, annotation_request: dict, db: Session) -> dict:
        """Route vers le meilleur annotateur disponible."""
        org_id = annotation_request.get("org_id", 1)

        profiles = (
            db.query(AnnotatorProfile).filter_by(org_id=org_id).order_by(AnnotatorProfile.trust_weight.desc()).all()
        )

        candidates = [p for p in profiles if p.trust_weight > 0.3]
        must_human = any(rule(annotation_request) for rule in self.ESCALATION_RULES)

        if must_human:
            candidates = [p for p in candidates if p.annotator_type == "human"]

        return {
            "candidates": [c.annotator_id for c in candidates[:3]],
            "must_human": must_human,
            "selected": candidates[0].annotator_id if candidates else "auto_annotator",
        }
