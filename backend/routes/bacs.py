"""
PROMEOS Routes - BACS Expert endpoints
Full BACS assessment, CVC system management, data quality, seed demo.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db

from models import (
    Site, BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection,
    CvcSystemType, CvcArchitecture, InspectionStatus,
)
from services.bacs_engine import (
    compute_putile, evaluate_bacs, compute_tri,
    compute_inspection_schedule, ENGINE_VERSION,
)

router = APIRouter(prefix="/api/regops/bacs", tags=["BACS Expert"])


# ── Full assessment ──

@router.get("/site/{site_id}")
def get_bacs_assessment(site_id: int, db: Session = Depends(get_db)):
    """Full BACS assessment for a site: asset + systems + assessment + inspections + DQ."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    asset = db.query(BacsAsset).filter(BacsAsset.site_id == site_id).first()
    if not asset:
        return {"site_id": site_id, "configured": False, "asset": None, "assessment": None}

    systems = db.query(BacsCvcSystem).filter(BacsCvcSystem.asset_id == asset.id).all()
    assessment = (
        db.query(BacsAssessment)
        .filter(BacsAssessment.asset_id == asset.id)
        .order_by(BacsAssessment.assessed_at.desc())
        .first()
    )
    inspections = db.query(BacsInspection).filter(BacsInspection.asset_id == asset.id).all()

    # BACS-specific data quality gate
    dq = _compute_bacs_dq(asset, systems)

    return {
        "site_id": site_id,
        "configured": True,
        "asset": _serialize_asset(asset),
        "systems": [_serialize_system(s) for s in systems],
        "assessment": _serialize_assessment(assessment) if assessment else None,
        "inspections": [_serialize_inspection(i) for i in inspections],
        "data_quality": dq,
    }


@router.post("/recompute/{site_id}")
def recompute_bacs(site_id: int, db: Session = Depends(get_db)):
    """Recompute BACS assessment, persist result."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    assessment = evaluate_bacs(db, site_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="No BacsAsset configured for this site")

    db.commit()
    return {
        "site_id": site_id,
        "assessment": _serialize_assessment(assessment),
    }


# ── Score explain ──

@router.get("/score_explain/{site_id}")
def get_score_explain(site_id: int, db: Session = Depends(get_db)):
    """Putile steps + threshold + TRI + penalties breakdown."""
    asset = db.query(BacsAsset).filter(BacsAsset.site_id == site_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="No BacsAsset for this site")

    systems = db.query(BacsCvcSystem).filter(BacsCvcSystem.asset_id == asset.id).all()
    putile_result = compute_putile(systems)

    assessment = (
        db.query(BacsAssessment)
        .filter(BacsAssessment.asset_id == asset.id)
        .order_by(BacsAssessment.assessed_at.desc())
        .first()
    )

    return {
        "site_id": site_id,
        "putile": putile_result,
        "assessment_summary": {
            "is_obligated": assessment.is_obligated if assessment else None,
            "threshold": assessment.threshold_applied if assessment else None,
            "deadline": assessment.deadline_date.isoformat() if assessment and assessment.deadline_date else None,
            "tri_years": assessment.tri_years if assessment else None,
            "tri_exemption": assessment.tri_exemption_possible if assessment else None,
            "compliance_score": assessment.compliance_score if assessment else None,
            "confidence_score": assessment.confidence_score if assessment else None,
        },
        "evidence_trace": json.loads(assessment.evidence_json) if assessment and assessment.evidence_json else {},
    }


# ── Data quality ──

@router.get("/data_quality/{site_id}")
def get_bacs_data_quality(site_id: int, db: Session = Depends(get_db)):
    """BACS-specific DQ gate: BLOCKED / WARNING / OK."""
    asset = db.query(BacsAsset).filter(BacsAsset.site_id == site_id).first()
    if not asset:
        return {
            "site_id": site_id,
            "gate_status": "BLOCKED",
            "missing_critical": [{"field": "bacs_asset", "impact": "No BACS asset configured"}],
            "missing_important": [],
        }

    systems = db.query(BacsCvcSystem).filter(BacsCvcSystem.asset_id == asset.id).all()
    return _compute_bacs_dq(asset, systems)


# ── Asset CRUD ──

@router.post("/asset")
def create_bacs_asset(
    site_id: int,
    is_tertiary: bool = True,
    pc_date: str = None,
    db: Session = Depends(get_db),
):
    """Create BacsAsset for a site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    existing = db.query(BacsAsset).filter(BacsAsset.site_id == site_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="BacsAsset already exists for this site")

    from datetime import date as date_cls
    asset = BacsAsset(
        site_id=site_id,
        is_tertiary_non_residential=is_tertiary,
        pc_date=date_cls.fromisoformat(pc_date) if pc_date else None,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _serialize_asset(asset)


@router.post("/asset/{asset_id}/system")
def add_cvc_system(
    asset_id: int,
    system_type: str,
    architecture: str,
    units_json: str = "[]",
    db: Session = Depends(get_db),
):
    """Add a CVC system to an asset."""
    asset = db.query(BacsAsset).filter(BacsAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="BacsAsset not found")

    sys = BacsCvcSystem(
        asset_id=asset_id,
        system_type=CvcSystemType(system_type),
        architecture=CvcArchitecture(architecture),
        units_json=units_json,
        engine_version=ENGINE_VERSION,
    )
    db.add(sys)
    db.commit()
    db.refresh(sys)
    return _serialize_system(sys)


@router.put("/system/{system_id}")
def update_cvc_system(
    system_id: int,
    units_json: str = None,
    architecture: str = None,
    db: Session = Depends(get_db),
):
    """Update a CVC system."""
    sys = db.query(BacsCvcSystem).filter(BacsCvcSystem.id == system_id).first()
    if not sys:
        raise HTTPException(status_code=404, detail="CVC system not found")

    if units_json is not None:
        sys.units_json = units_json
    if architecture is not None:
        sys.architecture = CvcArchitecture(architecture)
    sys.engine_version = ENGINE_VERSION
    db.commit()
    db.refresh(sys)
    return _serialize_system(sys)


@router.delete("/system/{system_id}")
def delete_cvc_system(system_id: int, db: Session = Depends(get_db)):
    """Remove a CVC system."""
    sys = db.query(BacsCvcSystem).filter(BacsCvcSystem.id == system_id).first()
    if not sys:
        raise HTTPException(status_code=404, detail="CVC system not found")

    db.delete(sys)
    db.commit()
    return {"deleted": system_id}


# ── Ops monitoring ──

@router.get("/site/{site_id}/ops")
def get_bacs_ops(site_id: int, db: Session = Depends(get_db)):
    """BACS operational monitoring panel: KPIs, consumption links, heatmap."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    from services.bacs_ops_monitor import get_bacs_ops_panel
    return get_bacs_ops_panel(db, site_id)


# ── Seed demo ──

@router.post("/seed_demo")
def seed_bacs_demo(db: Session = Depends(get_db)):
    """Seed 10 demo BACS assets with diverse CVC configurations."""
    from services.bacs_seed import seed_bacs_demo as do_seed
    result = do_seed(db)
    db.commit()
    return result


# ── Serialization helpers ──

def _serialize_asset(asset: BacsAsset) -> dict:
    return {
        "id": asset.id,
        "site_id": asset.site_id,
        "is_tertiary_non_residential": asset.is_tertiary_non_residential,
        "pc_date": asset.pc_date.isoformat() if asset.pc_date else None,
        "renewal_events": json.loads(asset.renewal_events_json or "[]"),
        "responsible_party": json.loads(asset.responsible_party_json or "{}"),
    }


def _serialize_system(sys: BacsCvcSystem) -> dict:
    return {
        "id": sys.id,
        "asset_id": sys.asset_id,
        "system_type": sys.system_type.value,
        "architecture": sys.architecture.value,
        "units": json.loads(sys.units_json or "[]"),
        "putile_kw_computed": sys.putile_kw_computed,
    }


def _serialize_assessment(a: BacsAssessment) -> dict:
    return {
        "id": a.id,
        "assessed_at": a.assessed_at.isoformat() if a.assessed_at else None,
        "is_obligated": a.is_obligated,
        "threshold_applied": a.threshold_applied,
        "deadline_date": a.deadline_date.isoformat() if a.deadline_date else None,
        "trigger_reason": a.trigger_reason.value if a.trigger_reason else None,
        "tri_exemption_possible": a.tri_exemption_possible,
        "tri_years": a.tri_years,
        "confidence_score": a.confidence_score,
        "compliance_score": a.compliance_score,
        "findings": json.loads(a.findings_json or "[]"),
        "engine_version": a.engine_version,
    }


def _serialize_inspection(i: BacsInspection) -> dict:
    return {
        "id": i.id,
        "inspection_date": i.inspection_date.isoformat() if i.inspection_date else None,
        "due_next_date": i.due_next_date.isoformat() if i.due_next_date else None,
        "report_ref": i.report_ref,
        "status": i.status.value,
    }


def _compute_bacs_dq(asset: BacsAsset, systems: list[BacsCvcSystem]) -> dict:
    """BACS-specific DQ gate with critical + important tiers."""
    missing_critical = []
    missing_important = []

    # Critical checks
    if not asset.is_tertiary_non_residential:
        missing_critical.append({"field": "is_tertiary_non_residential", "impact": "Must be tertiary non-residential"})
    if not asset.pc_date:
        missing_critical.append({"field": "pc_date", "impact": "PC date needed for calendar logic"})
    if not systems:
        missing_critical.append({"field": "cvc_inventory", "impact": "No CVC systems inventoried"})
    else:
        has_valid = any(json.loads(s.units_json or "[]") for s in systems)
        if not has_valid:
            missing_critical.append({"field": "cvc_units", "impact": "No kW data in CVC systems"})

    responsible = json.loads(asset.responsible_party_json or "{}")
    if not responsible.get("type"):
        missing_important.append({"field": "responsible_party", "impact": "Responsible party needed for audit"})

    # Important checks (TRI data)
    # These are checked at API level — we just note they are needed
    missing_important.append({"field": "tri_data", "impact": "TRI context needed for exemption check (best-effort)"})

    if missing_critical:
        gate_status = "BLOCKED"
    elif missing_important:
        gate_status = "WARNING"
    else:
        gate_status = "OK"

    return {
        "gate_status": gate_status,
        "missing_critical": missing_critical,
        "missing_important": missing_important,
    }
