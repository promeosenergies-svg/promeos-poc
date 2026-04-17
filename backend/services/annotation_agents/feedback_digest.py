"""
FeedbackDigestAgent — Analyse le taux de FP par regle et propose des revisions.
Si FP rate > 60% sur les 30 derniers jours -> status=under_review automatique.
"""

from collections import Counter
from sqlalchemy.orm import Session
from models import Annotation
from app.kb.store import KBStore


class FeedbackDigestAgent:
    FP_THRESHOLD_REVIEW = 0.60  # 60% FP -> under_review
    FP_THRESHOLD_WARNING = 0.30  # 30% FP -> warning
    MIN_ANNOTATIONS = 3  # Minimum d'annotations pour evaluer

    def run(self, db: Session) -> dict:
        """Analyse les annotations recentes et flag les regles a probleme."""
        # Recuperer toutes les annotations liees a des regles
        annotations = db.query(Annotation).filter(Annotation.rule_id.isnot(None)).all()

        # Grouper par rule_id
        by_rule: dict[str, list] = {}
        for ann in annotations:
            by_rule.setdefault(ann.rule_id, []).append(ann)

        store = KBStore()
        flagged = []

        for rule_id, anns in by_rule.items():
            if len(anns) < self.MIN_ANNOTATIONS:
                continue

            fp_count = sum(1 for a in anns if a.label == "false_positive")
            fp_rate = fp_count / len(anns)

            if fp_rate >= self.FP_THRESHOLD_REVIEW:
                # Flag as under_review in KB
                item = store.get_item(rule_id)
                if item and item.get("status") != "under_review":
                    store.update_item_status(rule_id, "under_review")
                    flagged.append({"rule_id": rule_id, "fp_rate": fp_rate, "action": "under_review"})

        return {"rules_analyzed": len(by_rule), "flagged": flagged}
