"""
ProfilerAgent — Calcule trust_weight hebdomadaire par annotateur.
Analyse le ratio FP, la couverture par domaine, et detecte les biais.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import Annotation, AnnotatorProfile


# Trust weights initiaux par role IAM
DEFAULT_TRUST_BY_ROLE = {
    "daf": {"billing": 0.70, "consumption": 0.30, "compliance": 0.40, "archetype": 0.25},
    "energy_manager": {"billing": 0.50, "consumption": 0.80, "compliance": 0.60, "archetype": 0.75},
    "resp_immobilier": {"billing": 0.35, "consumption": 0.55, "compliance": 0.75, "archetype": 0.70},
    "dg_owner": {"billing": 0.45, "consumption": 0.35, "compliance": 0.65, "archetype": 0.40},
}


class ProfilerAgent:
    """Recalcule les profils annotateurs."""

    def run(self, db: Session, org_id: int = 1):
        """Recalcule tous les profils de l'org."""
        profiles = db.query(AnnotatorProfile).filter_by(org_id=org_id).all()
        updated = 0

        for profile in profiles:
            annotations = db.query(Annotation).filter_by(annotator_id=profile.annotator_id, org_id=org_id).all()

            if not annotations:
                continue

            total = len(annotations)
            fp_count = sum(1 for a in annotations if a.label == "false_positive")
            fp_rate = fp_count / total if total > 0 else 0

            # Ajuster trust_weight selon FP rate
            if fp_rate > 0.5:
                profile.trust_weight = max(0.1, profile.trust_weight - 0.1)
            elif fp_rate < 0.1 and total >= 10:
                profile.trust_weight = min(1.0, profile.trust_weight + 0.05)

            profile.annotation_count = total
            profile.last_active_at = datetime.now(timezone.utc)
            profile.computed_at = datetime.now(timezone.utc)
            profile.computed_by = "profiler_agent"
            updated += 1

        db.commit()
        return {"updated": updated}
