"""
AutoAnnotator — Annote automatiquement si confiance >= seuil.
Pour les cas evidents (seed ground truth, regles deterministes haute confiance).
"""

from sqlalchemy.orm import Session
from models import Annotation


class AutoAnnotator:
    CONFIDENCE_THRESHOLD = 0.85

    def annotate(
        self,
        db: Session,
        object_type: str,
        object_id: int,
        label: str,
        confidence: float,
        org_id: int = 1,
        rule_id: str | None = None,
        note: str | None = None,
    ) -> Annotation | None:
        """Cree une annotation automatique si confidence >= seuil."""
        if confidence < self.CONFIDENCE_THRESHOLD:
            return None

        annotation = Annotation(
            object_type=object_type,
            object_id=object_id,
            label=label,
            confidence=confidence,
            annotator_type="rule_engine",
            annotator_id="auto_annotator",
            org_id=org_id,
            rule_id=rule_id,
            note=note,
            needs_review=confidence < 0.95,
        )
        db.add(annotation)
        db.commit()
        return annotation
