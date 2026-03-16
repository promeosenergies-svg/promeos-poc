"""
PROMEOS — BACS Alerts Engine.
Detecte les echeances critiques et genere des alertes structurees.
Prepare la structure pour futures notifications in-app / email.
"""

from datetime import date, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session

from models.bacs_models import BacsAsset, BacsInspection
from models.bacs_regulatory import BacsExploitationStatus, BacsProofDocument
from models.bacs_remediation import BacsRemediationAction


def compute_bacs_alerts(db: Session, asset_id: int) -> List[Dict]:
    """Genere les alertes BACS pour un actif. Chaque alerte a : type, severity, message, due_at."""
    alerts = []
    today = date.today()

    # 1. Inspection due / overdue
    inspections = db.query(BacsInspection).filter(BacsInspection.asset_id == asset_id).all()
    completed = [i for i in inspections if i.status.value == "completed"]
    if completed:
        last = max(completed, key=lambda i: i.inspection_date or i.created_at)
        if last.due_next_date:
            days_until = (last.due_next_date - today).days
            if days_until < 0:
                alerts.append(
                    {
                        "type": "inspection_overdue",
                        "severity": "critical",
                        "message": f"Inspection en retard de {abs(days_until)} jour(s) (echeance {last.due_next_date})",
                        "due_at": last.due_next_date.isoformat(),
                        "entity_type": "BacsInspection",
                        "entity_id": last.id,
                    }
                )
            elif days_until <= 180:
                alerts.append(
                    {
                        "type": "inspection_due_soon",
                        "severity": "high" if days_until <= 90 else "medium",
                        "message": f"Prochaine inspection dans {days_until} jour(s) ({last.due_next_date})",
                        "due_at": last.due_next_date.isoformat(),
                        "entity_type": "BacsInspection",
                        "entity_id": last.id,
                    }
                )
    else:
        alerts.append(
            {
                "type": "inspection_missing",
                "severity": "high",
                "message": "Aucune inspection completee — planifier la premiere inspection",
                "due_at": None,
                "entity_type": "BacsAsset",
                "entity_id": asset_id,
            }
        )

    # 2. Preuves manquantes ou expirees
    proofs = db.query(BacsProofDocument).filter(BacsProofDocument.asset_id == asset_id).all()
    expected = {"attestation_bacs", "rapport_inspection", "consignes", "formation"}
    present = {p.document_type for p in proofs}
    missing = expected - present

    for doc_type in missing:
        alerts.append(
            {
                "type": "proof_missing",
                "severity": "high",
                "message": f"Preuve manquante : {doc_type}",
                "due_at": None,
                "entity_type": "BacsProofDocument",
                "entity_id": None,
            }
        )

    for p in proofs:
        if p.valid_until and p.valid_until < today:
            alerts.append(
                {
                    "type": "proof_expired",
                    "severity": "high",
                    "message": f"Preuve expiree : {p.document_type} (valide jusqu'au {p.valid_until})",
                    "due_at": p.valid_until.isoformat(),
                    "entity_type": "BacsProofDocument",
                    "entity_id": p.id,
                }
            )

    # 3. Actions correctives en retard
    actions = (
        db.query(BacsRemediationAction)
        .filter(BacsRemediationAction.asset_id == asset_id, BacsRemediationAction.status != "closed")
        .all()
    )
    for a in actions:
        if a.due_at and a.due_at < today:
            alerts.append(
                {
                    "type": "action_overdue",
                    "severity": "high",
                    "message": f"Action corrective en retard : {a.blocker_cause[:80]} (echeance {a.due_at})",
                    "due_at": a.due_at.isoformat(),
                    "entity_type": "BacsRemediationAction",
                    "entity_id": a.id,
                }
            )

    # 4. Formation absente ou expiree
    exp = db.query(BacsExploitationStatus).filter(BacsExploitationStatus.asset_id == asset_id).first()
    if exp:
        if not exp.operator_trained:
            alerts.append(
                {
                    "type": "training_missing",
                    "severity": "high",
                    "message": "Formation exploitant non demontree",
                    "due_at": None,
                    "entity_type": "BacsExploitationStatus",
                    "entity_id": exp.id,
                }
            )
        elif exp.training_date and (today - exp.training_date).days > 3 * 365:
            alerts.append(
                {
                    "type": "training_expired",
                    "severity": "medium",
                    "message": f"Formation exploitant de plus de 3 ans ({exp.training_date})",
                    "due_at": (exp.training_date + timedelta(days=3 * 365)).isoformat(),
                    "entity_type": "BacsExploitationStatus",
                    "entity_id": exp.id,
                }
            )

    # Trier par severite
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 9))

    return alerts
