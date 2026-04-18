"""
PROMEOS - Flex Routes (Mini + Foundations Sprint 21)
GET  /api/sites/{site_id}/flex/mini — flex potential score + top 3 levers
GET  /api/flex/assets               — list flex assets
POST /api/flex/assets               — create flex asset
PATCH /api/flex/assets/{asset_id}   — update flex asset
POST /api/flex/assets/sync-from-bacs — sync BACS CVC to flex assets
GET  /api/flex/assessment           — flex assessment (asset-based or heuristic)
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Body, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from services.flex_mini import compute_flex_mini
from services.scope_utils import resolve_org_id
from middleware.auth import get_optional_auth, AuthContext
from middleware.cx_logger import log_cx_event_first_only, CX_MODULE_ACTIVATED
from schemas.flex_schemas import (
    FlexAssetResponse,
    FlexAssetListResponse,
    FlexAssessmentResponse,
    RegOppResponse,
    RegOppListResponse,
    TariffWindowListResponse,
    TariffWindowCreateResponse,
    BacsSyncResponse,
    FlexPrioritizationResponse,
    FlexPortfolioResponse,
)


# --- Org-scoping helper ---
def _check_site_org(db: Session, site_id: int, org_id: int):
    """Verify site belongs to org. Raises 404/403."""
    from models import Site, Portefeuille, EntiteJuridique

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, "Site non trouvé")
    if not site.portefeuille_id:
        raise HTTPException(403, "Site hors périmètre")
    pf = db.get(Portefeuille, site.portefeuille_id)
    if not pf:
        raise HTTPException(403, "Site hors périmètre")
    ej = db.get(EntiteJuridique, pf.entite_juridique_id)
    if not ej or ej.organisation_id != org_id:
        raise HTTPException(403, "Site hors périmètre")
    return site


# --- Original router: /api/sites prefix (flex mini) ---
router = APIRouter(prefix="/api/sites", tags=["Flex Mini"])


@router.get("/{site_id}/flex/mini")  # dict libre, structure variable
def flex_mini(
    site_id: int,
    request: Request,
    start: Optional[str] = Query(None, description="Period start (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="Period end (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Mini flex potential: score 0-100 + top 3 levers with justification."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return compute_flex_mini(db, site_id, start, end)


# --- New router: /api/flex prefix (Sprint 21 Foundations) ---
flex_foundation_router = APIRouter(prefix="/api/flex", tags=["Flex Foundations"])


@flex_foundation_router.get("/assets", response_model=FlexAssetListResponse)
def list_flex_assets(
    request: Request,
    site_id: Optional[int] = Query(None),
    asset_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List flex assets, scoped to org and optionally filtered by site."""
    from models.flex_models import FlexAsset
    from models import Site, Portefeuille, EntiteJuridique

    org_id = resolve_org_id(request, auth, db)
    if site_id:
        _check_site_org(db, site_id, org_id)

    q = (
        db.query(FlexAsset)
        .join(Site, FlexAsset.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(FlexAsset.status == "active", EntiteJuridique.organisation_id == org_id)
    )
    if site_id:
        q = q.filter(FlexAsset.site_id == site_id)
    if asset_type:
        q = q.filter(FlexAsset.asset_type == asset_type)
    assets = q.all()
    return {"total": len(assets), "assets": [_serialize_flex_asset(a) for a in assets]}


@flex_foundation_router.post("/assets", response_model=FlexAssetResponse)
def create_flex_asset(
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    idempotency_key: str | None = Query(None, description="Cle d'idempotence"),
):
    """Create a flex asset. Supporte idempotency_key."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, body["site_id"], org_id)
    from models.flex_models import FlexAsset

    # Idempotence : retourne l'asset existant si meme cle
    if idempotency_key:
        existing = (
            db.query(FlexAsset)
            .filter(
                FlexAsset.label == idempotency_key,
                FlexAsset.site_id == body.get("site_id"),
                FlexAsset.status == "active",
            )
            .first()
        )
        if existing:
            return _serialize_flex_asset(existing)

    # Validate confidence rule
    if body.get("confidence") == "high" and not body.get("data_source"):
        raise HTTPException(status_code=400, detail="confidence=high requires data_source")

    asset = FlexAsset(
        site_id=body["site_id"],
        batiment_id=body.get("batiment_id"),
        bacs_cvc_system_id=body.get("bacs_cvc_system_id"),
        asset_type=body["asset_type"],
        label=body["label"],
        power_kw=body.get("power_kw"),
        energy_kwh=body.get("energy_kwh"),
        is_controllable=body.get("is_controllable", False),
        control_method=body.get("control_method"),
        gtb_class=body.get("gtb_class"),
        data_source=body.get("data_source"),
        confidence=body.get("confidence", "unverified"),
        notes=body.get("notes"),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Sprint CX 3 P0.4 : fire CX_MODULE_ACTIVATED 1ère activation flex par l'org.
    # Option A (check AuditLog avant fire) : flood-proof car create_flex_asset
    # peut être appelé N fois/jour. Le dedup_key matche module_key=flex.
    log_cx_event_first_only(
        db,
        org_id,
        auth.user.id if auth else None,
        CX_MODULE_ACTIVATED,
        dedup_key='"module_key": "flex"',
        context={"module_key": "flex", "trigger": "create_flex_asset"},
    )
    db.commit()
    return _serialize_flex_asset(asset)


@flex_foundation_router.patch("/assets/{asset_id}", response_model=FlexAssetResponse)
def update_flex_asset(
    asset_id: int,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Update a flex asset."""
    from models.flex_models import FlexAsset

    org_id = resolve_org_id(request, auth, db)
    asset = db.query(FlexAsset).filter(FlexAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset non trouve")
    _check_site_org(db, asset.site_id, org_id)
    for key in (
        "label",
        "power_kw",
        "energy_kwh",
        "is_controllable",
        "control_method",
        "gtb_class",
        "data_source",
        "confidence",
        "status",
        "notes",
    ):
        if key in body:
            setattr(asset, key, body[key])
    if body.get("confidence") == "high" and not (body.get("data_source") or asset.data_source):
        raise HTTPException(status_code=400, detail="confidence=high requires data_source")
    db.commit()
    return _serialize_flex_asset(asset)


@flex_foundation_router.post("/assets/sync-from-bacs", response_model=BacsSyncResponse)
def sync_bacs(
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    idempotency_key: str | None = Query(None, description="Cle d'idempotence"),
):
    """Sync CVC systems from BACS to FlexAsset inventory. Supporte idempotency_key."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, body["site_id"], org_id)
    from services.flex_assessment_service import sync_bacs_to_flex_assets

    # Idempotence simple : si la cle est fournie, on verifie qu'un sync recent existe
    if idempotency_key:
        from models.flex_models import FlexAsset

        recent = (
            db.query(FlexAsset)
            .filter(
                FlexAsset.site_id == body["site_id"],
                FlexAsset.data_source == "bacs_sync",
            )
            .first()
        )
        if recent:
            return {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    site_id = body["site_id"]
    result = sync_bacs_to_flex_assets(db, site_id)
    db.commit()
    return result


@flex_foundation_router.get("/assessment", response_model=FlexAssessmentResponse)
def get_flex_assessment(
    request: Request,
    site_id: int = Query(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get flex assessment for a site (asset-based or heuristic fallback)."""
    from services.flex_assessment_service import compute_flex_assessment

    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return compute_flex_assessment(db, site_id)


@flex_foundation_router.get("/regulatory-opportunities", response_model=RegOppListResponse)
def list_regulatory_opportunities(
    request: Request,
    site_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List regulatory opportunities (APER, CEE, BACS flex, NEBCO)."""
    from models.flex_models import RegulatoryOpportunity
    from models import Site, Portefeuille, EntiteJuridique

    org_id = resolve_org_id(request, auth, db)
    if site_id:
        _check_site_org(db, site_id, org_id)

    q = (
        db.query(RegulatoryOpportunity)
        .join(Site, RegulatoryOpportunity.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    if site_id:
        q = q.filter(RegulatoryOpportunity.site_id == site_id)
    if regulation:
        q = q.filter(RegulatoryOpportunity.regulation == regulation)
    items = q.order_by(RegulatoryOpportunity.deadline.asc().nullslast()).all()
    return {"total": len(items), "opportunities": [_serialize_reg_opp(o) for o in items]}


@flex_foundation_router.post("/regulatory-opportunities", response_model=RegOppResponse)
def create_regulatory_opportunity(
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create a regulatory opportunity for a site."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, body["site_id"], org_id)
    from datetime import datetime
    from models.flex_models import RegulatoryOpportunity

    # Validate APER subtypes
    if body["regulation"] == "aper":
        if body.get("is_obligation") and body.get("obligation_type") not in (
            "solarisation_ombriere",
            "solarisation_toiture",
            None,
        ):
            raise HTTPException(
                status_code=400, detail="APER obligation_type: solarisation_ombriere ou solarisation_toiture"
            )

        APER_OPPORTUNITIES = {"autoconsommation_individuelle", "acc", "stockage_batterie", "revente_surplus"}
        if (
            not body.get("is_obligation")
            and body.get("opportunity_type")
            and body["opportunity_type"] not in APER_OPPORTUNITIES
        ):
            raise HTTPException(
                status_code=400, detail=f"APER opportunity_type: {', '.join(sorted(APER_OPPORTUNITIES))}"
            )

    # Parse deadline string to datetime if provided
    deadline_raw = body.get("deadline")
    deadline_val = None
    if deadline_raw:
        if isinstance(deadline_raw, str):
            try:
                deadline_val = datetime.fromisoformat(deadline_raw)
            except ValueError:
                deadline_val = datetime.strptime(deadline_raw, "%Y-%m-%d")
        else:
            deadline_val = deadline_raw

    opp = RegulatoryOpportunity(
        site_id=body["site_id"],
        regulation=body["regulation"],
        is_obligation=body.get("is_obligation", False),
        obligation_type=body.get("obligation_type"),
        opportunity_type=body.get("opportunity_type"),
        eligible=body.get("eligible"),
        eligibility_reason=body.get("eligibility_reason"),
        eligibility_caveat=body.get("eligibility_caveat"),
        surface_m2=body.get("surface_m2"),
        surface_type=body.get("surface_type"),
        threshold_m2=body.get("threshold_m2"),
        deadline=deadline_val,
        deadline_source=body.get("deadline_source"),
        cee_eligible=body.get("cee_eligible"),
        cee_caveat=body.get(
            "cee_caveat", "Eligibilite potentielle — volume et valorisation a confirmer par operateur CEE agree"
        ),
        cee_tri_min_years=body.get("cee_tri_min_years", 3),
        source_regulation=body.get("source_regulation"),
        notes=body.get("notes"),
    )
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return _serialize_reg_opp(opp)


@flex_foundation_router.get("/tariff-windows", response_model=TariffWindowListResponse)
def list_tariff_windows(
    segment: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List tariff windows (saisonnalisees, versionnees)."""
    from models.flex_models import TariffWindow

    q = db.query(TariffWindow)
    if segment:
        q = q.filter(TariffWindow.segment == segment)
    if season:
        q = q.filter(TariffWindow.season == season)
    return {
        "total": q.count(),
        "windows": [
            {
                "id": w.id,
                "name": w.name,
                "segment": w.segment,
                "season": w.season,
                "months": w.months,
                "period_type": w.period_type,
                "start_time": w.start_time,
                "end_time": w.end_time,
                "day_types": w.day_types,
                "price_component_eur_kwh": w.price_component_eur_kwh,
                "effective_from": w.effective_from,
                "source": w.source,
            }
            for w in q.all()
        ],
    }


@flex_foundation_router.post("/tariff-windows", response_model=TariffWindowCreateResponse)
def create_tariff_window(body: dict = Body(...), db: Session = Depends(get_db)):
    """Create a tariff window."""
    import json
    import re
    from models.flex_models import TariffWindow

    # Validate period_type
    VALID_PERIODS = {"HC_NUIT", "HC_SOLAIRE", "HP", "POINTE", "SUPER_POINTE"}
    if body["period_type"] not in VALID_PERIODS:
        raise HTTPException(
            status_code=400, detail=f"period_type invalide. Valeurs: {', '.join(sorted(VALID_PERIODS))}"
        )

    # HC_SOLAIRE requires explicit season != "toute_annee" to prevent implicit generic usage
    if body["period_type"] == "HC_SOLAIRE" and body.get("season") == "toute_annee":
        raise HTTPException(
            status_code=400, detail="HC_SOLAIRE ne peut pas etre applique toute l'annee — specifier une saison"
        )

    # Validate time format
    for field in ("start_time", "end_time"):
        if not re.match(r"^\d{2}:\d{2}$", body[field]):
            raise HTTPException(status_code=400, detail=f"{field} doit etre au format HH:MM")

    w = TariffWindow(
        calendar_id=body.get("calendar_id"),
        name=body["name"],
        segment=body.get("segment"),
        season=body["season"],
        months=json.dumps(body["months"]) if isinstance(body["months"], list) else body["months"],
        period_type=body["period_type"],
        start_time=body["start_time"],
        end_time=body["end_time"],
        day_types=json.dumps(body.get("day_types", ["all"])),
        price_component_eur_kwh=body.get("price_component_eur_kwh"),
        effective_from=body.get("effective_from"),
        source=body.get("source"),
        source_ref=body.get("source_ref"),
        notes=body.get("notes"),
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "name": w.name, "period_type": w.period_type}


@flex_foundation_router.get("/portfolios/{portfolio_id}/flex-prioritization", response_model=FlexPrioritizationResponse)
def flex_prioritization(
    portfolio_id: int,
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Portfolio-scoped flex prioritization — PROMEOS canonical path."""
    from models import Site, Portefeuille, EntiteJuridique
    from models.flex_models import FlexAsset
    from models.base import not_deleted
    from services.flex_assessment_service import compute_flex_assessment

    org_id = resolve_org_id(request, auth, db)

    portfolio = db.query(Portefeuille).filter(Portefeuille.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portefeuille non trouvé")
    # Verify portfolio belongs to org
    ej = db.get(EntiteJuridique, portfolio.entite_juridique_id)
    if not ej or ej.organisation_id != org_id:
        raise HTTPException(status_code=403, detail="Portefeuille hors périmètre")

    sites = (
        db.query(Site)
        .filter(
            Site.portefeuille_id == portfolio_id,
            not_deleted(Site),
        )
        .all()
    )

    rankings = []
    for site in sites:
        assessment = compute_flex_assessment(db, site.id)
        asset_count = db.query(FlexAsset).filter(FlexAsset.site_id == site.id, FlexAsset.status == "active").count()
        rankings.append(
            {
                "site_id": site.id,
                "site_name": site.nom,
                "flex_score": assessment.get("flex_score", 0),
                "potential_kw": assessment.get("potential_kw", 0),
                "source": assessment.get("source", "unknown"),
                "confidence": assessment.get("confidence", "low"),
                "asset_count": asset_count,
                "dimensions": assessment.get("dimensions", {}),
            }
        )

    rankings.sort(key=lambda r: -(r["flex_score"] or 0))

    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.nom if portfolio else None,
        "total_sites": len(rankings),
        "total_potential_kw": sum(r["potential_kw"] for r in rankings),
        "avg_flex_score": round(sum(r["flex_score"] for r in rankings) / max(len(rankings), 1), 1),
        "rankings": rankings,
    }


@flex_foundation_router.get("/portfolio", response_model=FlexPortfolioResponse)
def flex_portfolio(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Portfolio-level flex ranking: quick wins by site."""
    from models import Site, Portefeuille, EntiteJuridique
    from models.flex_models import FlexAsset
    from models.base import not_deleted
    from services.flex_assessment_service import compute_flex_assessment

    org_id = resolve_org_id(request, auth, db)

    sites = (
        db.query(Site)
        .join(Portefeuille)
        .join(EntiteJuridique)
        .filter(
            EntiteJuridique.organisation_id == org_id,
            not_deleted(Site),
        )
        .all()
    )

    rankings = []
    for site in sites:
        assessment = compute_flex_assessment(db, site.id)
        asset_count = db.query(FlexAsset).filter(FlexAsset.site_id == site.id, FlexAsset.status == "active").count()

        rankings.append(
            {
                "site_id": site.id,
                "site_name": site.nom,
                "flex_score": assessment.get("flex_score", 0),
                "potential_kw": assessment.get("potential_kw", 0),
                "source": assessment.get("source", "unknown"),
                "confidence": assessment.get("confidence", "low"),
                "asset_count": asset_count,
                "dimensions": assessment.get("dimensions", {}),
            }
        )

    rankings.sort(key=lambda r: -(r["flex_score"] or 0))

    return {
        "total_sites": len(rankings),
        "total_potential_kw": sum(r["potential_kw"] for r in rankings),
        "avg_flex_score": round(sum(r["flex_score"] for r in rankings) / max(len(rankings), 1), 1),
        "rankings": rankings,
    }


def _serialize_flex_asset(a) -> dict:
    return {
        "id": a.id,
        "site_id": a.site_id,
        "batiment_id": a.batiment_id,
        "bacs_cvc_system_id": a.bacs_cvc_system_id,
        "asset_type": a.asset_type.value if hasattr(a.asset_type, "value") else a.asset_type,
        "label": a.label,
        "power_kw": a.power_kw,
        "energy_kwh": a.energy_kwh,
        "is_controllable": a.is_controllable,
        "control_method": a.control_method.value
        if a.control_method and hasattr(a.control_method, "value")
        else a.control_method,
        "gtb_class": a.gtb_class,
        "data_source": a.data_source,
        "confidence": a.confidence,
        "status": a.status,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_reg_opp(o) -> dict:
    return {
        "id": o.id,
        "site_id": o.site_id,
        "regulation": o.regulation,
        "is_obligation": o.is_obligation,
        "obligation_type": o.obligation_type,
        "opportunity_type": o.opportunity_type,
        "eligible": o.eligible,
        "eligibility_reason": o.eligibility_reason,
        "eligibility_caveat": o.eligibility_caveat,
        "surface_m2": o.surface_m2,
        "surface_type": o.surface_type,
        "threshold_m2": o.threshold_m2,
        "deadline": o.deadline.isoformat() if o.deadline else None,
        "deadline_source": o.deadline_source,
        "cee_eligible": o.cee_eligible,
        "cee_caveat": o.cee_caveat,
        "cee_tri_min_years": o.cee_tri_min_years,
        "source_regulation": o.source_regulation,
        "notes": o.notes,
    }
