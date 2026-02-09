"""
PROMEOS - Guardrails Engine
Prevents incoherent actions: validation rules for compliance workflow.
"""
from typing import List

from sqlalchemy.orm import Session

from models import (
    Site, Obligation, Evidence, Batiment,
    StatutConformite, TypeObligation, TypeEvidence, StatutEvidence,
)


class GuardrailViolation:
    """A single guardrail violation."""

    def __init__(self, code: str, message: str, severity: str = "error"):
        self.code = code
        self.message = message
        self.severity = severity  # "error" blocks action, "warning" allows with notice

    def to_dict(self):
        return {"code": self.code, "message": self.message, "severity": self.severity}


def check_bacs_conforme(db: Session, site_id: int) -> List[GuardrailViolation]:
    """Cannot mark BACS conforme without valid attestation or CVC data."""
    violations = []

    evidences = db.query(Evidence).filter(
        Evidence.site_id == site_id,
        Evidence.type == TypeEvidence.ATTESTATION_BACS,
    ).all()

    has_valid_attestation = any(
        e.statut == StatutEvidence.VALIDE for e in evidences
    )
    if not has_valid_attestation:
        violations.append(GuardrailViolation(
            code="BACS_NO_ATTESTATION",
            message="Impossible de marquer BACS conforme sans attestation BACS valide.",
        ))

    batiment = db.query(Batiment).filter(Batiment.site_id == site_id).first()
    if not batiment or not batiment.cvc_power_kw:
        violations.append(GuardrailViolation(
            code="BACS_NO_CVC_DATA",
            message="Donnees puissance CVC manquantes. Renseigner le batiment d'abord.",
        ))

    return violations


def check_decret_trajectory(db: Session, site_id: int) -> List[GuardrailViolation]:
    """Warn if decret tertiaire avancement is too low."""
    violations = []

    obligations = db.query(Obligation).filter(
        Obligation.site_id == site_id,
        Obligation.type == TypeObligation.DECRET_TERTIAIRE,
    ).all()

    for ob in obligations:
        if ob.avancement_pct < 60:
            violations.append(GuardrailViolation(
                code="DECRET_LOW_AVANCEMENT",
                message=f"Avancement insuffisant ({ob.avancement_pct:.0f}%). Minimum 60% requis pour la trajectoire.",
                severity="warning",
            ))

    return violations


def check_evidence_completeness(db: Session, site_id: int) -> List[GuardrailViolation]:
    """Warn if site has MANQUANT evidences."""
    violations = []

    manquantes = db.query(Evidence).filter(
        Evidence.site_id == site_id,
        Evidence.statut == StatutEvidence.MANQUANT,
    ).count()

    if manquantes > 0:
        violations.append(GuardrailViolation(
            code="EVIDENCE_GAPS",
            message=f"{manquantes} preuve(s) manquante(s). Fournir les documents avant validation.",
            severity="warning",
        ))

    return violations


def validate_site(db: Session, site_id: int) -> dict:
    """Run all guardrails for a site. Returns aggregated result."""
    violations = []
    violations.extend(check_bacs_conforme(db, site_id))
    violations.extend(check_decret_trajectory(db, site_id))
    violations.extend(check_evidence_completeness(db, site_id))

    errors = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]

    return {
        "site_id": site_id,
        "valid": len(errors) == 0,
        "errors": [v.to_dict() for v in errors],
        "warnings": [v.to_dict() for v in warnings],
    }
