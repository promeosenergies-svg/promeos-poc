"""
PROMEOS - Routes API pour la Knowledge Base Usages
Archetypes, anomaly rules, recommendations, provenance, reload
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import (
    KBVersion, KBArchetype, KBMappingCode, KBAnomalyRule,
    KBRecommendation, KBTaxonomy, KBStatus
)
from services.kb_service import KBService
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel


router = APIRouter(prefix="/api/kb", tags=["Knowledge Base"])


# --- Pydantic response models ---

class ArchetypeResponse(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    kwh_m2_min: Optional[int] = None
    kwh_m2_max: Optional[int] = None
    kwh_m2_avg: Optional[int] = None
    segment_tags: Optional[list] = None
    naf_codes: Optional[list] = None
    confidence: str
    source_section: Optional[str] = None

    class Config:
        from_attributes = True


class AnomalyRuleResponse(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    rule_type: str
    severity: str
    confidence: str
    source_section: Optional[str] = None

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    action_type: str
    target_asset: Optional[str] = None
    savings_min_pct: Optional[float] = None
    savings_max_pct: Optional[float] = None
    ice_score: Optional[float] = None
    confidence: str
    source_section: Optional[str] = None

    class Config:
        from_attributes = True


class ProvenanceResponse(BaseModel):
    item_type: str
    item_code: str
    doc_id: Optional[str] = None
    version: Optional[str] = None
    source_path: Optional[str] = None
    source_sha256: Optional[str] = None
    source_section: Optional[str] = None
    confidence: str
    status: str


class KBStatsResponse(BaseModel):
    archetypes_count: int
    anomaly_rules_count: int
    recommendations_count: int
    naf_mappings_count: int
    kb_version: Optional[str] = None
    kb_doc_id: Optional[str] = None
    kb_sha256: Optional[str] = None


class ReloadResponse(BaseModel):
    status: str
    archetypes_loaded: int
    rules_loaded: int
    recommendations_loaded: int
    message: str


# --- Endpoints ---

@router.get("/archetypes", response_model=List[ArchetypeResponse])
def list_archetypes(
    segment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all KB archetypes with optional segment filter"""
    query = db.query(KBArchetype).filter_by(status=KBStatus.VALIDATED)

    if segment:
        # Simple filter on JSON array
        query = query.filter(KBArchetype.segment_tags.contains(segment))

    archetypes = query.all()

    result = []
    for arch in archetypes:
        naf_codes = [m.naf_code for m in db.query(KBMappingCode).filter_by(archetype_id=arch.id).all()]
        result.append(ArchetypeResponse(
            id=arch.id,
            code=arch.code,
            title=arch.title,
            description=arch.description,
            kwh_m2_min=arch.kwh_m2_min,
            kwh_m2_max=arch.kwh_m2_max,
            kwh_m2_avg=arch.kwh_m2_avg,
            segment_tags=arch.segment_tags,
            naf_codes=naf_codes,
            confidence=arch.confidence.value if arch.confidence else "medium",
            source_section=arch.source_section
        ))

    return result


@router.get("/archetypes/{code}", response_model=ArchetypeResponse)
def get_archetype(code: str, db: Session = Depends(get_db)):
    """Get archetype by code"""
    arch = db.query(KBArchetype).filter_by(code=code, status=KBStatus.VALIDATED).first()
    if not arch:
        raise HTTPException(status_code=404, detail=f"Archetype '{code}' not found")

    naf_codes = [m.naf_code for m in db.query(KBMappingCode).filter_by(archetype_id=arch.id).all()]

    return ArchetypeResponse(
        id=arch.id,
        code=arch.code,
        title=arch.title,
        description=arch.description,
        kwh_m2_min=arch.kwh_m2_min,
        kwh_m2_max=arch.kwh_m2_max,
        kwh_m2_avg=arch.kwh_m2_avg,
        segment_tags=arch.segment_tags,
        naf_codes=naf_codes,
        confidence=arch.confidence.value if arch.confidence else "medium",
        source_section=arch.source_section
    )


@router.get("/archetypes/by-naf/{naf_code}", response_model=ArchetypeResponse)
def get_archetype_by_naf(naf_code: str, db: Session = Depends(get_db)):
    """Get archetype by NAF code"""
    service = KBService(db)
    arch = service.get_archetype_by_naf(naf_code)
    if not arch:
        raise HTTPException(status_code=404, detail=f"No archetype found for NAF code '{naf_code}'")

    naf_codes = [m.naf_code for m in db.query(KBMappingCode).filter_by(archetype_id=arch.id).all()]

    return ArchetypeResponse(
        id=arch.id,
        code=arch.code,
        title=arch.title,
        description=arch.description,
        kwh_m2_min=arch.kwh_m2_min,
        kwh_m2_max=arch.kwh_m2_max,
        kwh_m2_avg=arch.kwh_m2_avg,
        segment_tags=arch.segment_tags,
        naf_codes=naf_codes,
        confidence=arch.confidence.value if arch.confidence else "medium",
        source_section=arch.source_section
    )


@router.get("/rules", response_model=List[AnomalyRuleResponse])
def list_anomaly_rules(
    archetype_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all KB anomaly rules"""
    query = db.query(KBAnomalyRule).filter_by(status=KBStatus.VALIDATED)
    rules = query.all()

    return [AnomalyRuleResponse(
        id=r.id,
        code=r.code,
        title=r.title,
        description=r.description,
        rule_type=r.rule_type,
        severity=r.severity,
        confidence=r.confidence.value if r.confidence else "medium",
        source_section=r.source_section
    ) for r in rules]


@router.get("/recommendations", response_model=List[RecommendationResponse])
def list_recommendations(
    archetype_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all KB recommendations, sorted by ICE score"""
    query = db.query(KBRecommendation).filter_by(status=KBStatus.VALIDATED)
    recos = query.order_by(KBRecommendation.ice_score.desc()).all()

    return [RecommendationResponse(
        id=r.id,
        code=r.code,
        title=r.title,
        description=r.description,
        action_type=r.action_type,
        target_asset=r.target_asset,
        savings_min_pct=r.savings_min_pct,
        savings_max_pct=r.savings_max_pct,
        ice_score=r.ice_score,
        confidence=r.confidence.value if r.confidence else "medium",
        source_section=r.source_section
    ) for r in recos]


@router.get("/search")
def search_kb(
    q: str = Query(..., min_length=2, description="Search query"),
    type: Optional[str] = Query(None, description="Filter by type: archetype, rule, recommendation"),
    db: Session = Depends(get_db)
):
    """Full-text search across KB items"""
    results = []
    search_term = f"%{q}%"

    if not type or type == "archetype":
        archetypes = db.query(KBArchetype).filter(
            KBArchetype.title.ilike(search_term) |
            KBArchetype.description.ilike(search_term) |
            KBArchetype.code.ilike(search_term)
        ).all()
        for a in archetypes:
            results.append({
                "type": "archetype",
                "code": a.code,
                "title": a.title,
                "description": a.description,
                "confidence": a.confidence.value if a.confidence else "medium"
            })

    if not type or type == "rule":
        rules = db.query(KBAnomalyRule).filter(
            KBAnomalyRule.title.ilike(search_term) |
            KBAnomalyRule.description.ilike(search_term) |
            KBAnomalyRule.code.ilike(search_term)
        ).all()
        for r in rules:
            results.append({
                "type": "rule",
                "code": r.code,
                "title": r.title,
                "description": r.description,
                "severity": r.severity,
                "confidence": r.confidence.value if r.confidence else "medium"
            })

    if not type or type == "recommendation":
        recos = db.query(KBRecommendation).filter(
            KBRecommendation.title.ilike(search_term) |
            KBRecommendation.description.ilike(search_term) |
            KBRecommendation.code.ilike(search_term)
        ).all()
        for r in recos:
            results.append({
                "type": "recommendation",
                "code": r.code,
                "title": r.title,
                "description": r.description,
                "ice_score": r.ice_score,
                "confidence": r.confidence.value if r.confidence else "medium"
            })

    return {"query": q, "results": results, "total": len(results)}


@router.get("/provenance/{item_type}/{code}", response_model=ProvenanceResponse)
def get_provenance(item_type: str, code: str, db: Session = Depends(get_db)):
    """Get full provenance information for a KB item"""
    if item_type == "archetype":
        item = db.query(KBArchetype).filter_by(code=code).first()
    elif item_type == "rule":
        item = db.query(KBAnomalyRule).filter_by(code=code).first()
    elif item_type == "recommendation":
        item = db.query(KBRecommendation).filter_by(code=code).first()
    else:
        raise HTTPException(status_code=400, detail="item_type must be: archetype, rule, recommendation")

    if not item:
        raise HTTPException(status_code=404, detail=f"{item_type} '{code}' not found")

    # Get version info
    kb_version = None
    if item.kb_version_id:
        kb_version = db.query(KBVersion).filter_by(id=item.kb_version_id).first()

    return ProvenanceResponse(
        item_type=item_type,
        item_code=code,
        doc_id=kb_version.doc_id if kb_version else None,
        version=kb_version.version if kb_version else None,
        source_path=kb_version.source_path if kb_version else None,
        source_sha256=kb_version.source_sha256 if kb_version else None,
        source_section=item.source_section,
        confidence=item.confidence.value if item.confidence else "medium",
        status=item.status.value if item.status else "validated"
    )


@router.get("/stats", response_model=KBStatsResponse)
def get_kb_stats(db: Session = Depends(get_db)):
    """Get KB statistics"""
    archetypes_count = db.query(KBArchetype).filter_by(status=KBStatus.VALIDATED).count()
    rules_count = db.query(KBAnomalyRule).filter_by(status=KBStatus.VALIDATED).count()
    recos_count = db.query(KBRecommendation).filter_by(status=KBStatus.VALIDATED).count()
    naf_count = db.query(KBMappingCode).count()

    kb_version = db.query(KBVersion).filter_by(is_active=True).first()

    return KBStatsResponse(
        archetypes_count=archetypes_count,
        anomaly_rules_count=rules_count,
        recommendations_count=recos_count,
        naf_mappings_count=naf_count,
        kb_version=kb_version.version if kb_version else None,
        kb_doc_id=kb_version.doc_id if kb_version else None,
        kb_sha256=kb_version.source_sha256 if kb_version else None
    )


@router.post("/reload", response_model=ReloadResponse)
def reload_kb(db: Session = Depends(get_db)):
    """Reload KB from YAML files into database"""
    service = KBService(db)

    # Base paths
    base_doc_dir = Path("docs/base_documentaire/usages_energetiques_b2b")
    yaml_dir = Path("docs/kb/items/usages")

    # 1. Load KB version from manifest
    try:
        kb_version = service.load_kb_version_from_manifest(base_doc_dir / "manifest.json")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 2. Load items from YAML
    archetypes_count = service.load_archetypes_from_yaml(yaml_dir, kb_version.id)
    rules_count = service.load_anomaly_rules_from_yaml(yaml_dir, kb_version.id)
    recos_count = service.load_recommendations_from_yaml(yaml_dir, kb_version.id)

    total = archetypes_count + rules_count + recos_count

    return ReloadResponse(
        status="ok",
        archetypes_loaded=archetypes_count,
        rules_loaded=rules_count,
        recommendations_loaded=recos_count,
        message=f"KB reloaded: {total} items from {kb_version.doc_id} v{kb_version.version}"
    )
