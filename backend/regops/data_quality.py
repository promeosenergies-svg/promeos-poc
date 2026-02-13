"""
PROMEOS RegOps - Data Quality Gate
Compute data quality report: coverage, confidence, gate status per regulation.
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from models import Site, Batiment, Evidence, TypeEvidence, StatutEvidence
from .data_quality_specs import DATA_QUALITY_SPECS


@dataclass
class DataQualityReport:
    coverage_pct: float
    confidence_score: float
    missing_critical: list[dict] = field(default_factory=list)
    missing_optional: list[dict] = field(default_factory=list)
    gate_status: str = "OK"
    per_regulation: dict = field(default_factory=dict)


def _get_field_value(site, batiments, evidences, field_name: str):
    """Resolve a field name to its current value."""
    # Site-level fields
    if hasattr(site, field_name):
        return getattr(site, field_name, None)

    # Batiment-level
    if field_name == "cvc_power_kw":
        for b in batiments:
            if b.cvc_power_kw is not None:
                return b.cvc_power_kw
        return None

    # Evidence-based booleans
    if field_name == "has_bacs_attestation":
        return any(
            e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE
            for e in evidences
        )

    if field_name == "has_bacs_derogation":
        return any(
            e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE
            for e in evidences
        )

    return None


def _is_filled(value) -> bool:
    """Check if a value counts as present (not None, not empty, not False for booleans that represent presence)."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def compute_data_quality(db: Session, site_id: int) -> DataQualityReport:
    """
    Compute data quality gate for a site.

    1. Load site + batiments + evidences
    2. For each regulation: check critical and optional fields
    3. Compute coverage_pct = filled / total
    4. confidence_score = 100 - 20*missing_critical - 5*missing_optional, clamp [0,100]
    5. gate_status: BLOCKED if critical missing, WARNING if optional missing, OK otherwise
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return DataQualityReport(
            coverage_pct=0.0,
            confidence_score=0.0,
            gate_status="BLOCKED",
            missing_critical=[{"field": "site", "regulation": "all", "impact": "Site not found"}],
        )

    batiments = db.query(Batiment).filter(Batiment.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()

    missing_critical = []
    missing_optional = []
    per_regulation = {}
    total_fields = 0
    filled_fields = 0

    for reg_name, spec in DATA_QUALITY_SPECS.items():
        critical_ok = 0
        critical_total = len(spec["critical"])
        optional_ok = 0
        optional_total = len(spec["optional"])

        for f in spec["critical"]:
            total_fields += 1
            val = _get_field_value(site, batiments, evidences, f)
            if _is_filled(val):
                filled_fields += 1
                critical_ok += 1
            else:
                missing_critical.append({
                    "field": f,
                    "regulation": reg_name,
                    "impact": f"Required for {reg_name} evaluation",
                })

        for f in spec["optional"]:
            total_fields += 1
            val = _get_field_value(site, batiments, evidences, f)
            if _is_filled(val):
                filled_fields += 1
                optional_ok += 1
            else:
                missing_optional.append({
                    "field": f,
                    "regulation": reg_name,
                    "impact": f"Improves {reg_name} confidence",
                })

        reg_status = "OK"
        if critical_ok < critical_total:
            reg_status = "BLOCKED"
        elif optional_ok < optional_total:
            reg_status = "WARNING"

        per_regulation[reg_name] = {
            "critical_ok": critical_ok,
            "critical_total": critical_total,
            "optional_ok": optional_ok,
            "optional_total": optional_total,
            "status": reg_status,
        }

    # Coverage
    coverage_pct = (filled_fields / max(1, total_fields)) * 100.0

    # Confidence score
    raw_confidence = 100.0 - 20 * len(missing_critical) - 5 * len(missing_optional)
    confidence_score = round(max(0.0, min(100.0, raw_confidence)), 1)

    # Gate status
    if missing_critical:
        gate_status = "BLOCKED"
    elif missing_optional:
        gate_status = "WARNING"
    else:
        gate_status = "OK"

    return DataQualityReport(
        coverage_pct=round(coverage_pct, 1),
        confidence_score=confidence_score,
        missing_critical=missing_critical,
        missing_optional=missing_optional,
        gate_status=gate_status,
        per_regulation=per_regulation,
    )
