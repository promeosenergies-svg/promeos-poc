"""
PROMEOS - Routes API pour la Knowledge Base Usages
Archetypes, anomaly rules, recommendations, provenance, reload
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import (
    KBVersion, KBArchetype, KBMappingCode, KBAnomalyRule,
    KBRecommendation, KBTaxonomy, KBStatus, KBConfidence
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

@router.get("/ping")
def kb_ping():
    """Smoke test — KB endpoint is reachable"""
    return {"ok": True}


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


@router.get("/usages-stats", response_model=KBStatsResponse)
def get_kb_stats(db: Session = Depends(get_db)):
    """Get KB usages statistics (archetypes, rules, recommendations)"""
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


# ── V11.1: POST /search (body-based FTS search) ──────────────────────────

class KBSearchBody(BaseModel):
    q: str = "*"
    domain: Optional[str] = None
    type: Optional[str] = None
    include_drafts: bool = False
    limit: int = 50


@router.post("/search")
def search_kb_post(body: KBSearchBody, db: Session = Depends(get_db)):
    """POST full-text search — accepts JSON body with q, domain, type, include_drafts, limit.
    Resolves the frontend 405 (backend only had GET /search).
    """
    results = []
    search_term = f"%{body.q}%" if body.q and body.q != "*" else "%"
    statuses = [KBStatus.VALIDATED]
    if body.include_drafts:
        statuses = [KBStatus.VALIDATED, KBStatus.DRAFT]

    # Archetypes
    if not body.type or body.type == "archetype":
        q = db.query(KBArchetype).filter(KBArchetype.status.in_(statuses))
        if body.q and body.q != "*":
            q = q.filter(
                KBArchetype.title.ilike(search_term) |
                KBArchetype.description.ilike(search_term) |
                KBArchetype.code.ilike(search_term)
            )
        for a in q.limit(body.limit).all():
            results.append({
                "type": "archetype", "code": a.code, "title": a.title,
                "description": a.description,
                "confidence": a.confidence.value if a.confidence else "medium",
                "status": a.status.value if a.status else "validated",
            })

    # Rules
    if not body.type or body.type == "rule":
        q = db.query(KBAnomalyRule).filter(KBAnomalyRule.status.in_(statuses))
        if body.q and body.q != "*":
            q = q.filter(
                KBAnomalyRule.title.ilike(search_term) |
                KBAnomalyRule.description.ilike(search_term) |
                KBAnomalyRule.code.ilike(search_term)
            )
        for r in q.limit(body.limit).all():
            results.append({
                "type": "rule", "code": r.code, "title": r.title,
                "description": r.description,
                "confidence": r.confidence.value if r.confidence else "medium",
                "status": r.status.value if r.status else "validated",
            })

    # Recommendations
    if not body.type or body.type == "recommendation":
        q = db.query(KBRecommendation).filter(KBRecommendation.status.in_(statuses))
        if body.q and body.q != "*":
            q = q.filter(
                KBRecommendation.title.ilike(search_term) |
                KBRecommendation.description.ilike(search_term) |
                KBRecommendation.code.ilike(search_term)
            )
        for r in q.limit(body.limit).all():
            results.append({
                "type": "recommendation", "code": r.code, "title": r.title,
                "description": r.description,
                "confidence": r.confidence.value if r.confidence else "medium",
                "status": r.status.value if r.status else "validated",
            })

    trimmed = results[:body.limit]
    return {"results": trimmed, "total": len(trimmed)}


# ── V11.1: GET /stats (rich stats shape expected by KBExplorerPage) ────────

@router.get("/stats")
def get_kb_full_stats(db: Session = Depends(get_db)):
    """Full KB statistics — resolves the frontend 404 (backend only had /usages-stats).
    Returns total_items, by_status, by_domain, individual counts, and version info.
    """
    archetypes_val = db.query(KBArchetype).filter_by(status=KBStatus.VALIDATED).count()
    archetypes_draft = db.query(KBArchetype).filter_by(status=KBStatus.DRAFT).count()
    rules_val = db.query(KBAnomalyRule).filter_by(status=KBStatus.VALIDATED).count()
    rules_draft = db.query(KBAnomalyRule).filter_by(status=KBStatus.DRAFT).count()
    recos_val = db.query(KBRecommendation).filter_by(status=KBStatus.VALIDATED).count()
    recos_draft = db.query(KBRecommendation).filter_by(status=KBStatus.DRAFT).count()
    naf_count = db.query(KBMappingCode).count()

    kb_version = db.query(KBVersion).filter_by(is_active=True).first()

    total_validated = archetypes_val + rules_val + recos_val
    total_draft = archetypes_draft + rules_draft + recos_draft

    return {
        "total_items": total_validated + total_draft,
        "by_status": {
            "validated": total_validated,
            "draft": total_draft,
        },
        # by_domain: domain column not yet on KB models; empty dict avoids frontend runtime errors
        "by_domain": {},
        "archetypes_count": archetypes_val,
        "rules_count": rules_val,
        "recommendations_count": recos_val,
        "naf_mappings_count": naf_count,
        "kb_version": kb_version.version if kb_version else None,
        "kb_doc_id": kb_version.doc_id if kb_version else None,
        "kb_sha256": kb_version.source_sha256 if kb_version else None,
    }


class SeedDemoResponse(BaseModel):
    status: str
    archetypes_seeded: int
    rules_seeded: int
    recommendations_seeded: int
    naf_mappings_seeded: int
    message: str


@router.post("/seed_demo", response_model=SeedDemoResponse)
def seed_demo_kb(db: Session = Depends(get_db)):
    """Seed KB with a minimal demo pack. Idempotent — skips items that already exist."""

    # ── KB Version (idempotent) ──
    kb_version = db.query(KBVersion).filter_by(doc_id="PROMEOS_DEMO_KB").first()
    if not kb_version:
        kb_version = KBVersion(
            doc_id="PROMEOS_DEMO_KB",
            version="1.0.0-demo",
            date="2025-01-01",
            source_path="seed_demo",
            source_sha256="demo_" + "0" * 58,
            author="PROMEOS Demo Seed",
            description="Minimal demo knowledge base for PROMEOS POC",
            is_active=True,
            status=KBStatus.VALIDATED,
        )
        db.add(kb_version)
        db.flush()

    vid = kb_version.id

    # ── Archetypes (10) ──
    DEMO_ARCHETYPES = [
        {"code": "BUREAU_STANDARD",     "title": "Bureau standard",            "kwh_m2_min": 150, "kwh_m2_max": 250, "kwh_m2_avg": 200, "segments": ["tertiaire", "bureau"],           "conf": KBConfidence.HIGH},
        {"code": "BUREAU_PERFORMANT",   "title": "Bureau performant RT2012",   "kwh_m2_min": 80,  "kwh_m2_max": 150, "kwh_m2_avg": 115, "segments": ["tertiaire", "bureau", "HQE"],    "conf": KBConfidence.HIGH},
        {"code": "COMMERCE_ALIMENTAIRE","title": "Commerce alimentaire",       "kwh_m2_min": 400, "kwh_m2_max": 800, "kwh_m2_avg": 550, "segments": ["commerce", "alimentaire"],       "conf": KBConfidence.HIGH},
        {"code": "RESTAURATION_SERVICE","title": "Restauration & service",     "kwh_m2_min": 250, "kwh_m2_max": 450, "kwh_m2_avg": 350, "segments": ["restauration"],                  "conf": KBConfidence.MEDIUM},
        {"code": "INDUSTRIE_LEGERE",    "title": "Industrie legere",           "kwh_m2_min": 80,  "kwh_m2_max": 200, "kwh_m2_avg": 140, "segments": ["industrie", "PMI"],              "conf": KBConfidence.MEDIUM},
        {"code": "INDUSTRIE_LOURDE",    "title": "Industrie lourde (process)", "kwh_m2_min": 300, "kwh_m2_max": 1500,"kwh_m2_avg": 800, "segments": ["industrie", "process"],          "conf": KBConfidence.MEDIUM},
        {"code": "LOGISTIQUE_ENTREPOT", "title": "Entrepot logistique",        "kwh_m2_min": 30,  "kwh_m2_max": 100, "kwh_m2_avg": 60,  "segments": ["logistique", "entrepot"],        "conf": KBConfidence.HIGH},
        {"code": "SANTE_HOPITAL",       "title": "Etablissement de sante",     "kwh_m2_min": 200, "kwh_m2_max": 400, "kwh_m2_avg": 300, "segments": ["sante", "hopital"],              "conf": KBConfidence.MEDIUM},
        {"code": "ENSEIGNEMENT",        "title": "Enseignement & formation",   "kwh_m2_min": 80,  "kwh_m2_max": 180, "kwh_m2_avg": 130, "segments": ["enseignement", "formation"],     "conf": KBConfidence.HIGH},
        {"code": "DATACENTER",          "title": "Datacenter & salle serveur", "kwh_m2_min": 500, "kwh_m2_max": 3000,"kwh_m2_avg":1200, "segments": ["IT", "datacenter"],              "conf": KBConfidence.HIGH},
    ]

    archetypes_seeded = 0
    archetype_map = {}
    for a in DEMO_ARCHETYPES:
        existing = db.query(KBArchetype).filter_by(code=a["code"]).first()
        if existing:
            archetype_map[a["code"]] = existing.id
            continue
        obj = KBArchetype(
            code=a["code"], title=a["title"], description=f"Archetype demo: {a['title']}",
            kwh_m2_min=a["kwh_m2_min"], kwh_m2_max=a["kwh_m2_max"], kwh_m2_avg=a["kwh_m2_avg"],
            segment_tags=a["segments"], confidence=a["conf"],
            status=KBStatus.VALIDATED, kb_version_id=vid, source_section="demo_seed",
        )
        db.add(obj)
        db.flush()
        archetype_map[a["code"]] = obj.id
        archetypes_seeded += 1

    # ── NAF Mappings (30) ──
    DEMO_NAF = [
        ("70.10Z", "BUREAU_STANDARD"),  ("70.22Z", "BUREAU_STANDARD"),
        ("69.10Z", "BUREAU_STANDARD"),  ("69.20Z", "BUREAU_PERFORMANT"),
        ("62.01Z", "BUREAU_PERFORMANT"),("62.02A", "BUREAU_PERFORMANT"),
        ("47.11B", "COMMERCE_ALIMENTAIRE"), ("47.11C", "COMMERCE_ALIMENTAIRE"),
        ("47.11D", "COMMERCE_ALIMENTAIRE"), ("47.21Z", "COMMERCE_ALIMENTAIRE"),
        ("56.10A", "RESTAURATION_SERVICE"), ("56.10B", "RESTAURATION_SERVICE"),
        ("56.21Z", "RESTAURATION_SERVICE"), ("56.30Z", "RESTAURATION_SERVICE"),
        ("25.11Z", "INDUSTRIE_LEGERE"),  ("25.62A", "INDUSTRIE_LEGERE"),
        ("28.11Z", "INDUSTRIE_LEGERE"),  ("24.10Z", "INDUSTRIE_LOURDE"),
        ("24.20Z", "INDUSTRIE_LOURDE"),  ("20.11Z", "INDUSTRIE_LOURDE"),
        ("52.10A", "LOGISTIQUE_ENTREPOT"),("52.10B", "LOGISTIQUE_ENTREPOT"),
        ("49.41A", "LOGISTIQUE_ENTREPOT"),("86.10Z", "SANTE_HOPITAL"),
        ("86.21Z", "SANTE_HOPITAL"),     ("86.22A", "SANTE_HOPITAL"),
        ("85.10Z", "ENSEIGNEMENT"),      ("85.20Z", "ENSEIGNEMENT"),
        ("63.11Z", "DATACENTER"),        ("63.12Z", "DATACENTER"),
    ]

    naf_seeded = 0
    for naf_code, arch_code in DEMO_NAF:
        arch_id = archetype_map.get(arch_code)
        if not arch_id:
            continue
        existing = db.query(KBMappingCode).filter_by(naf_code=naf_code, archetype_id=arch_id).first()
        if existing:
            continue
        db.add(KBMappingCode(
            naf_code=naf_code, archetype_id=arch_id,
            confidence=KBConfidence.HIGH, priority=1, kb_version_id=vid,
        ))
        naf_seeded += 1

    # ── Anomaly Rules (15) ──
    DEMO_RULES = [
        {"code": "RULE-BASE-NUIT-001",    "title": "Talon nocturne excessif",          "rule_type": "base_nuit",    "severity": "high",     "conf": KBConfidence.HIGH},
        {"code": "RULE-BASE-NUIT-002",    "title": "Ratio nuit/jour > 80%",            "rule_type": "base_nuit",    "severity": "medium",   "conf": KBConfidence.HIGH},
        {"code": "RULE-WEEKEND-001",      "title": "Surconsommation weekend",          "rule_type": "weekend",      "severity": "medium",   "conf": KBConfidence.HIGH},
        {"code": "RULE-WEEKEND-002",      "title": "Weekend > 90% jours ouvres",       "rule_type": "weekend",      "severity": "high",     "conf": KBConfidence.MEDIUM},
        {"code": "RULE-PUISSANCE-001",    "title": "Puissance souscrite surdimensionnee","rule_type": "puissance",  "severity": "medium",   "conf": KBConfidence.HIGH},
        {"code": "RULE-PUISSANCE-002",    "title": "Depassement puissance souscrite",  "rule_type": "puissance",    "severity": "critical", "conf": KBConfidence.HIGH},
        {"code": "RULE-SAISONNIER-001",   "title": "Profil saisonnier absent",         "rule_type": "saisonnier",   "severity": "low",      "conf": KBConfidence.MEDIUM},
        {"code": "RULE-SAISONNIER-002",   "title": "Surconsommation estivale anormale","rule_type": "saisonnier",   "severity": "medium",   "conf": KBConfidence.MEDIUM},
        {"code": "RULE-TENDANCE-001",     "title": "Derive haussiere > 10%/an",        "rule_type": "tendance",     "severity": "medium",   "conf": KBConfidence.MEDIUM},
        {"code": "RULE-TENDANCE-002",     "title": "Consommation constante (pas de MDE)","rule_type": "tendance",   "severity": "low",      "conf": KBConfidence.LOW},
        {"code": "RULE-FACTURATION-001",  "title": "Ecart facture vs releve > 5%",     "rule_type": "facturation",  "severity": "high",     "conf": KBConfidence.HIGH},
        {"code": "RULE-FACTURATION-002",  "title": "Doublon de facture detecte",       "rule_type": "facturation",  "severity": "critical", "conf": KBConfidence.HIGH},
        {"code": "RULE-QUALITE-001",      "title": "Trous de donnees > 48h",           "rule_type": "qualite",      "severity": "medium",   "conf": KBConfidence.HIGH},
        {"code": "RULE-QUALITE-002",      "title": "Valeurs negatives detectees",      "rule_type": "qualite",      "severity": "high",     "conf": KBConfidence.HIGH},
        {"code": "RULE-BENCHMARK-001",    "title": "kWh/m2 > P90 du segment",          "rule_type": "benchmark",    "severity": "medium",   "conf": KBConfidence.MEDIUM},
    ]

    rules_seeded = 0
    for r in DEMO_RULES:
        if db.query(KBAnomalyRule).filter_by(code=r["code"]).first():
            continue
        db.add(KBAnomalyRule(
            code=r["code"], title=r["title"], description=f"Regle demo: {r['title']}",
            rule_type=r["rule_type"], severity=r["severity"],
            confidence=r["conf"], status=KBStatus.VALIDATED,
            kb_version_id=vid, source_section="demo_seed", archetype_codes=["*"],
        ))
        rules_seeded += 1

    # ── Recommendations (10) ──
    DEMO_RECOS = [
        {"code": "RECO-ECLAIRAGE-LED",    "title": "Passage LED integral",         "action": "equipment", "target": "eclairage",  "smin": 30, "smax": 60, "I": 7, "C": 9, "E": 8},
        {"code": "RECO-CVC-REGULATION",    "title": "Regulation CVC intelligente",  "action": "equipment", "target": "hvac",       "smin": 15, "smax": 35, "I": 8, "C": 7, "E": 5},
        {"code": "RECO-BACS-CLASSE-B",     "title": "GTB BACS classe B minimum",    "action": "regulation","target": "gtb",        "smin": 10, "smax": 25, "I": 7, "C": 8, "E": 4},
        {"code": "RECO-ARRET-WEEKEND",     "title": "Programmation arret weekend",  "action": "behavior",  "target": "hvac",       "smin": 5,  "smax": 15, "I": 5, "C": 8, "E": 9},
        {"code": "RECO-FROID-MAINTENANCE", "title": "Maintenance froid alimentaire","action": "equipment", "target": "froid",      "smin": 10, "smax": 20, "I": 6, "C": 7, "E": 6},
        {"code": "RECO-PUISSANCE-OPTIM",   "title": "Optimisation puissance souscrite","action": "contract","target": "compteur",  "smin": 3,  "smax": 10, "I": 4, "C": 9, "E": 9},
        {"code": "RECO-ISOLATION-COMBLES", "title": "Isolation combles & toiture",  "action": "equipment", "target": "enveloppe",  "smin": 10, "smax": 25, "I": 7, "C": 6, "E": 3},
        {"code": "RECO-AUTOCONSO-PV",      "title": "Autoconsommation PV",         "action": "equipment", "target": "production", "smin": 15, "smax": 40, "I": 8, "C": 5, "E": 3},
        {"code": "RECO-SOBRIETE-SENSIB",   "title": "Plan de sobriete energetique","action": "behavior",  "target": "global",     "smin": 5,  "smax": 15, "I": 5, "C": 6, "E": 8},
        {"code": "RECO-CONTRAT-OPTIM",     "title": "Reneg contrat fournisseur",   "action": "contract",  "target": "contrat",    "smin": 5,  "smax": 20, "I": 6, "C": 7, "E": 7},
    ]

    recos_seeded = 0
    for r in DEMO_RECOS:
        if db.query(KBRecommendation).filter_by(code=r["code"]).first():
            continue
        ice = (r["I"] * r["C"] * r["E"]) / 1000
        db.add(KBRecommendation(
            code=r["code"], title=r["title"], description=f"Recommandation demo: {r['title']}",
            action_type=r["action"], target_asset=r["target"],
            savings_min_pct=r["smin"], savings_max_pct=r["smax"],
            impact_score=r["I"], confidence_score=r["C"], ease_score=r["E"],
            ice_score=ice, confidence=KBConfidence.MEDIUM,
            status=KBStatus.VALIDATED, kb_version_id=vid,
            source_section="demo_seed", archetype_codes=["*"],
        ))
        recos_seeded += 1

    db.commit()

    total = archetypes_seeded + rules_seeded + recos_seeded + naf_seeded
    if total == 0:
        return SeedDemoResponse(
            status="already_seeded",
            archetypes_seeded=0, rules_seeded=0, recommendations_seeded=0, naf_mappings_seeded=0,
            message="Demo KB deja presente — aucun ajout",
        )

    return SeedDemoResponse(
        status="ok",
        archetypes_seeded=archetypes_seeded, rules_seeded=rules_seeded,
        recommendations_seeded=recos_seeded, naf_mappings_seeded=naf_seeded,
        message=f"Demo KB seedee: {total} items",
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
