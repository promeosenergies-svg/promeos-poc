"""
seed_annotations_helios.py -- Cree les ground truth annotations pour le dataset HELIOS.
Les anomalies injectees par seed_data.py sont labelisees comme verite terrain.
Premier golden dataset pour mesurer la precision des regles.

Usage:
    cd backend && python scripts/seed_annotations_helios.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import SessionLocal
from models import Annotation


HELIOS_GROUND_TRUTH = [
    # (site_name, anomaly_type, rule_id, label)
    ("Paris Bureaux", "cvc_drift", "ANOMALY_RULE_CVC_DRIFT", "confirmed_anomaly"),
    ("Lyon Bureaux", "eclairage_oublie", "ANOMALY_RULE_BASE_NUIT_001", "confirmed_anomaly"),
    ("Marseille Ecole", "pic_canicule", "ANOMALY_RULE_HEAT_PEAK", "confirmed_anomaly"),
    ("Nice Hotel", "panne_detectee", "ANOMALY_RULE_SENSOR_FAULT", "confirmed_anomaly"),
    ("Toulouse Entrepot", "transition_saison", "ANOMALY_RULE_SEASONAL_SHIFT", "confirmed_anomaly"),
]


def seed_helios_annotations():
    """Cree les annotations ground truth depuis les anomalies seedees."""
    db = SessionLocal()
    created = 0

    for site_name, anomaly_type, rule_id, label in HELIOS_GROUND_TRUTH:
        # Check if already seeded
        existing = (
            db.query(Annotation)
            .filter_by(
                annotator_id="seed:helios_v1",
                rule_id=rule_id,
                label=label,
            )
            .first()
        )
        if existing:
            continue

        annotation = Annotation(
            object_type="anomaly",
            object_id=0,
            label=label,
            confidence=1.0,
            annotator_type="seed",
            annotator_id="seed:helios_v1",
            org_id=1,
            rule_id=rule_id,
            note=f"Ground truth HELIOS -- {anomaly_type} ({site_name})",
        )
        db.add(annotation)
        created += 1

    db.commit()
    db.close()
    print(f"[seed_helios] {created} annotations ground truth creees (total: {len(HELIOS_GROUND_TRUTH)})")
    return created


if __name__ == "__main__":
    seed_helios_annotations()
