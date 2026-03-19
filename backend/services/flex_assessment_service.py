"""Flex assessment service — enriches flex_mini with FlexAsset data."""

import json
import logging
from sqlalchemy.orm import Session
from models.flex_models import FlexAsset, FlexAssessment
from services.flex_mini import compute_flex_mini

logger = logging.getLogger("promeos.flex_assessment")

CONTROLLABILITY_FACTOR = {
    "hvac": 0.6,
    "irve": 0.5,
    "cold_storage": 0.2,
    "thermal_storage": 0.3,
    "battery": 0.9,
    "pv": 0.3,
    "lighting": 0.4,
    "process": 0.15,
    "other": 0.1,
}


def compute_flex_assessment(db: Session, site_id: int) -> dict:
    """Compute flex assessment using FlexAssets if available, fallback to heuristic."""
    assets = (
        db.query(FlexAsset)
        .filter(
            FlexAsset.site_id == site_id,
            FlexAsset.status == "active",
        )
        .all()
    )

    if assets:
        return _asset_based_assessment(db, site_id, assets)
    else:
        return _heuristic_assessment(db, site_id)


def _asset_based_assessment(db: Session, site_id: int, assets: list) -> dict:
    """Assessment from real asset inventory."""
    levers = []
    total_kw = 0
    total_kwh_year = 0

    for asset in assets:
        power = asset.power_kw or 0
        factor = CONTROLLABILITY_FACTOR.get(
            asset.asset_type.value if hasattr(asset.asset_type, "value") else asset.asset_type, 0.1
        )
        flex_kw = power * factor if asset.is_controllable else 0
        flex_kwh_year = flex_kw * 2000  # ~2000 hours/year exploitable

        total_kw += flex_kw
        total_kwh_year += flex_kwh_year

        levers.append(
            {
                "lever": asset.asset_type.value if hasattr(asset.asset_type, "value") else asset.asset_type,
                "label": asset.label,
                "asset_id": asset.id,
                "score": min(100, int(flex_kw / max(power, 1) * 100 * factor)),
                "kw": round(flex_kw, 1),
                "kwh_year": round(flex_kwh_year, 0),
                "source": "asset",
                "confidence": asset.confidence,
                "controllable": asset.is_controllable,
                "control_method": asset.control_method.value
                if asset.control_method and hasattr(asset.control_method, "value")
                else asset.control_method,
            }
        )

    score = min(100, int(total_kw / max(total_kw + 10, 1) * 100))

    # 4 dimensions
    controllable_count = sum(1 for a in assets if a.is_controllable)
    verified_count = sum(1 for a in assets if a.confidence in ("high", "medium"))

    technical_readiness = min(100, int(controllable_count / max(len(assets), 1) * 100))
    data_confidence = min(100, int(verified_count / max(len(assets), 1) * 100))
    economic_relevance = min(100, int(total_kw * 0.5))  # simplified: more kW = more relevant

    # Regulatory alignment
    has_bacs = any(a.bacs_cvc_system_id for a in assets)
    reg_status = "aligned" if has_bacs and controllable_count > 0 else "partial" if has_bacs else "unknown"

    # Persist assessment
    assessment = FlexAssessment(
        site_id=site_id,
        flex_score=score,
        potential_kw=round(total_kw, 1),
        potential_kwh_year=round(total_kwh_year, 0),
        source="asset_based",
        confidence="medium" if any(a.confidence in ("high", "medium") for a in assets) else "low",
        levers_json=json.dumps(levers),
        kpi_confidence="medium",
    )
    assessment.technical_readiness_score = technical_readiness
    assessment.data_confidence_score = data_confidence
    assessment.economic_relevance_score = economic_relevance
    assessment.regulatory_alignment_status = reg_status
    db.merge(assessment)
    db.flush()

    return {
        "site_id": site_id,
        "flex_score": score,
        "potential_kw": round(total_kw, 1),
        "potential_kwh_year": round(total_kwh_year, 0),
        "levers": levers,
        "source": "asset_based",
        "confidence": assessment.confidence,
        "asset_count": len(assets),
        "dimensions": {
            "technical_readiness": technical_readiness,
            "data_confidence": data_confidence,
            "economic_relevance": economic_relevance,
            "regulatory_alignment": reg_status,
        },
        "kpi": {
            "definition": "Potentiel de flexibilite estime par site",
            "formula": "SUM(asset_power_kw * controllability_factor)",
            "unit": "kW",
            "period": "instantane",
            "perimeter": "site",
            "source": "services/flex_assessment_service.py",
            "confidence": assessment.confidence,
        },
    }


def _heuristic_assessment(db: Session, site_id: int) -> dict:
    """Fallback to existing flex_mini heuristic."""
    try:
        result = compute_flex_mini(db, site_id)
        result["source"] = "heuristic"
        result["confidence"] = "low"
        result["asset_count"] = 0
        result["kpi"] = {
            "definition": "Potentiel de flexibilite estime par heuristique",
            "formula": "Scoring heuristique HVAC/IRVE/Froid",
            "unit": "score 0-100",
            "period": "instantane",
            "perimeter": "site",
            "source": "services/flex_mini.py",
            "confidence": "low",
        }
        return result
    except Exception as e:
        logger.warning("flex_mini failed for site %d: %s", site_id, e)
        return {
            "site_id": site_id,
            "flex_score": 0,
            "potential_kw": 0,
            "potential_kwh_year": 0,
            "levers": [],
            "source": "heuristic",
            "confidence": "low",
            "asset_count": 0,
            "kpi": {"definition": "Non evaluable", "confidence": "none"},
        }


def sync_bacs_to_flex_assets(db: Session, site_id: int) -> dict:
    """Sync BacsCvcSystem records to FlexAsset inventory."""
    from models.bacs_models import BacsCvcSystem, BacsAsset
    from models.base import not_deleted

    assets_created = 0
    assets_updated = 0

    bacs_assets = (
        db.query(BacsAsset)
        .filter(
            BacsAsset.site_id == site_id,
            not_deleted(BacsAsset),
        )
        .all()
    )

    for ba in bacs_assets:
        cvc_systems = db.query(BacsCvcSystem).filter(BacsCvcSystem.asset_id == ba.id).all()
        for cvc in cvc_systems:
            existing = db.query(FlexAsset).filter(FlexAsset.bacs_cvc_system_id == cvc.id).first()

            TYPE_MAP = {"heating": "hvac", "cooling": "hvac", "ventilation": "hvac"}
            asset_type = TYPE_MAP.get(
                cvc.system_type.value if hasattr(cvc.system_type, "value") else cvc.system_type, "hvac"
            )

            # GTB class informs but does NOT determine controllability
            # Class A/B suggests automation capability, not confirmed controllability
            gtb_suggests_control = cvc.system_class in ("A", "B") if cvc.system_class else False

            if existing:
                existing.power_kw = cvc.putile_kw_computed
                existing.gtb_class = cvc.system_class
                existing.data_source = "bacs_sync"
                # Don't auto-set is_controllable — leave for operator confirmation
                # Only set control_method hint
                existing.control_method = "gtb" if gtb_suggests_control else existing.control_method
                existing.notes = (
                    f"GTB classe {cvc.system_class or '?'} — pilotabilite a confirmer"
                    if not existing.notes
                    else existing.notes
                )
                assets_updated += 1
            else:
                fa = FlexAsset(
                    site_id=site_id,
                    bacs_cvc_system_id=cvc.id,
                    asset_type=asset_type,
                    label=f"CVC {cvc.system_type.value if hasattr(cvc.system_type, 'value') else cvc.system_type} ({cvc.putile_kw_computed or 0:.0f} kW)",
                    power_kw=cvc.putile_kw_computed,
                    is_controllable=False,  # Never auto-set — requires operator confirmation
                    control_method="gtb" if gtb_suggests_control else "unknown",
                    gtb_class=cvc.system_class,
                    data_source="bacs_sync",
                    confidence="low",  # Always low until confirmed
                    notes=f"Synchro BACS — GTB classe {cvc.system_class or '?'}, pilotabilite a confirmer",
                )
                db.add(fa)
                assets_created += 1

    db.flush()
    return {"created": assets_created, "updated": assets_updated}
